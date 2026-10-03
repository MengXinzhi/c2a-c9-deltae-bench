"""Item generation for DeltaE-Bench.

The benchmark needs items whose (a) ground truth is machine-checkable without an
LLM judge, and (b) *rule instance* is freshly sampled per run, so the correct
answer cannot be sourced from any training corpus.

Design summary
--------------
* Six procedurally generated micro-skill families, five difficulty levels each.
* Every item's reference answer is produced by the generator that built it
  (exact-match scoring).
* Each item carries a ``cue_salience`` value: the surface-level "this looks
  hard / this looks easy" signal a reader would pick up.  It is a *controlled
  design variable* -- in ``normal`` mode it tracks true difficulty, in
  ``stroop`` mode it is inverted.  This is the manipulation that lets us tell
  genuine self-knowledge apart from difficulty stereotyping.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field, asdict

FAMILIES: tuple[str, ...] = (
    "arith_mod",
    "symbol_map",
    "rule_induce",
    "code_trace",
    "logic_chain",
    "precedence",
)

LEVELS: tuple[int, ...] = (1, 2, 3, 4, 5)

# ASCII-only symbols: keeps every artifact encoding-safe on any terminal.
SYMBOLS = ("#", "@", "%", "&", "*", "+", "=", "?")


@dataclass
class Item:
    """One test item.

    ``answer`` is the generator-produced reference answer.  Scoring is exact
    string match, so no human or model judge enters the scoring loop.
    """

    iid: str
    family: str
    level: int                     # 1 (easiest) .. 5 (hardest), hidden from the model
    prompt: str
    answer: str
    cue_salience: float            # 0..1 surface-implied difficulty (design variable)
    population_difficulty: float   # 0..1 normative difficulty, known from the generator
    mode: str = "normal"           # normal | stroop
    meta: dict = field(default_factory=dict)

    @property
    def len_chars(self) -> int:
        return len(self.prompt)

    @property
    def digit_count(self) -> int:
        return sum(ch.isdigit() for ch in self.prompt)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["len_chars"] = self.len_chars
        d["digit_count"] = self.digit_count
        return d


# --------------------------------------------------------------------------
# family generators
# --------------------------------------------------------------------------

_PRIMES = (97, 101, 211, 499, 997, 2003, 4999)
_ORNAMENT = (
    "背景说明：本条目由跨区域档案整理小组统一编号，编号规则、复核顺序与归档时点仅用于行政留痕，"
    "与本题求解无关。附件清单与登记人签名栏见附录，以下为正式题目。",
    "阅读提示：为保证题干格式一致，下列文字为版式填充内容，不承载任何解题信息；"
    "请忽略其中的编号与日期，直接回答正式题目。",
    "说明：以下文字来自模板页眉，用于说明本批条目的归档方式，与题目内容无关。",
)


def _sig(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _gen_arith_mod(level: int, rng: random.Random) -> tuple[str, str]:
    a = rng.randint(2, 9 + 3 * level)
    b = rng.randint(0, 25 * level)
    m = rng.choice(_PRIMES)
    lo = 10 ** (level - 1)
    x = rng.randint(lo, lo * 10 - 1)
    prompt = (
        f"计算 (({a} * {x}) + {b}) mod {m}。\n"
        f"只输出最终的整数结果，不要输出推理过程。"
    )
    return prompt, str((a * x + b) % m)


def _gen_symbol_map(level: int, rng: random.Random) -> tuple[str, str]:
    """Rejection-sampled so the source string really does change.

    Without the retry, a source string drawn from characters that the active
    mapping does not touch renders the item trivial: the answer is just the input
    repeated back.  Correctness tests pass on such items; informativeness tests
    do not.
    """
    alphabet = rng.sample(SYMBOLS, 6)
    targets = rng.sample(SYMBOLS, len(alphabet))
    table = dict(zip(alphabet, targets))
    n_map = min(2 + level, len(alphabet))
    active = dict(list(table.items())[:n_map])

    for _ in range(200):
        s = [rng.choice(alphabet) for _ in range(3 + level)]
        changed = sum(1 for ch in s if ch in active and active[ch] != ch)
        if changed >= 2:
            break
    else:  # pragma: no cover - extremely unlikely
        s = list(active)[: 3 + level]

    mapping_txt = ", ".join(f"{k}->{v}" for k, v in active.items())
    prompt = (
        f"替换表（仅下列字符参与替换，其余字符原样保留）：{mapping_txt}\n"
        f"将字符串 {''.join(s)} 逐字符替换，输出替换后的字符串。"
    )
    out = "".join(active.get(ch, ch) for ch in s)
    return prompt, out


def _apply_ops(ops: list[str], s: str) -> str:
    for op in ops:
        if op == "REV":
            s = s[::-1]
        elif op == "DUP_FIRST":
            s = s[0] + s if s else s
        elif op == "SWAP_END":
            s = s[-1] + s[1:-1] + s[0] if len(s) > 1 else s
        elif op == "ROT_L":
            s = s[1:] + s[0] if s else s
        elif op == "DROP_ODD":
            s = "".join(c for i, c in enumerate(s) if i % 2 == 0)
        else:  # pragma: no cover - guarded by construction
            raise ValueError(f"unknown op {op}")
    return s


def _gen_rule_induce(level: int, rng: random.Random) -> tuple[str, str]:
    """Rejection-sampled until the hidden composition is non-trivial.

    This matters more than it looks.  ``SWAP_END`` acts as the identity whenever
    the first and last characters agree, ``DROP_ODD`` on a 2-character string,
    and so on.  Left unchecked, a large share of items degenerate into
    "three examples that map each input to itself" -- the model can then answer
    by echoing the query, and the item carries zero information about rule
    induction.  Reference-answer correctness tests cannot detect this; an
    explicit non-triviality loop can.
    """
    pool = ["REV", "DUP_FIRST", "SWAP_END", "ROT_L", "DROP_ODD"]
    n_ops = 1 + level // 2 + (1 if level >= 4 else 0)

    ops: list[str] = []
    examples: list[tuple[str, str]] = []
    query = ""

    for _ in range(300):
        ops = [rng.choice(pool) for _ in range(n_ops)]
        candidates = ["".join(rng.choice(SYMBOLS[:5]) for _ in range(4))
                      for _ in range(4)]
        # every input, including the query, must actually be transformed
        if not all(_apply_ops(ops, s) != s for s in candidates):
            continue
        # the examples must not be redundant copies of one another
        if len({candidates[i] for i in range(3)}) < 3:
            continue
        examples = [(s, _apply_ops(ops, s)) for s in candidates[:3]]
        query = candidates[3]
        break
    else:  # pragma: no cover - the search space is large enough in practice
        ops = ["REV", "ROT_L"]
        examples = [(s, _apply_ops(ops, s)) for s in ("#%&*", "@#*%", "%*@#")]
        query = "*@%#"

    ex_txt = "\n".join(f"  {a} -> {b}" for a, b in examples)
    prompt = (
        "下面三条示例展示了同一个变换。请从示例中归纳出规则，"
        f"并把它应用到查询字符串上。\n{ex_txt}\n  查询: {query}\n"
        "输出变换后的字符串。"
    )
    return prompt, _apply_ops(ops, query)


def _gen_code_trace(level: int, rng: random.Random) -> tuple[str, str]:
    a = rng.randint(2, 7)
    b = rng.randint(1, 25)
    m = rng.choice(_PRIMES)
    k = rng.choice((2, 3, 5))
    c = rng.randint(1, 15)
    n = 2 + 2 * level
    start = rng.randint(0, m - 1)

    acc = start
    for _ in range(n):
        acc = (acc * a + b) % m
        if acc % k == 0:
            acc = (acc + c) % m

    prompt = (
        "阅读下面的伪代码并逐步执行，输出最终 acc 的值。\n"
        "```\n"
        f"acc = {start}\n"
        f"for i in range({n}):\n"
        f"    acc = (acc * {a} + {b}) % {m}\n"
        f"    if acc % {k} == 0:\n"
        f"        acc = (acc + {c}) % {m}\n"
        "```\n"
        "只输出整数结果。"
    )
    return prompt, str(acc)


def _gen_logic_chain(level: int, rng: random.Random) -> tuple[str, str]:
    n_inputs = 3 + level // 2
    bits = {f"x{i}": rng.randint(0, 1) for i in range(n_inputs)}
    names = list(bits)

    def apply(op: str, a: bool, b: bool) -> bool:
        if op == "AND":
            return a and b
        if op == "OR":
            return a or b
        return bool(a) ^ bool(b)

    # Expression is a nested tuple, evaluated structurally -- never via eval().
    node: tuple = ("lit", rng.choice(names))
    for _ in range(2 + level):
        op = rng.choice(("AND", "OR", "XOR"))
        node = ("op", op, node, ("lit", rng.choice(names)))

    def render(n: tuple) -> str:
        if n[0] == "lit":
            return n[1]
        return f"({render(n[2])} {n[1]} {render(n[3])})"

    def evaluate(n: tuple) -> bool:
        if n[0] == "lit":
            return bool(bits[n[1]])
        return apply(n[1], evaluate(n[2]), evaluate(n[3]))

    expr = render(node)
    answer = str(int(evaluate(node)))
    given = ", ".join(f"{k}={v}" for k, v in bits.items())
    prompt = (
        f"给定布尔输入 {given}，其中 AND/OR/XOR 为按位运算。\n"
        f"求表达式的值：\n  {expr}\n只输出 0 或 1。"
    )
    return prompt, answer


_PREC = {"+": 1, "-": 1, "*": 2}


def _gen_precedence(level: int, rng: random.Random) -> tuple[str, str]:
    def build(depth: int) -> tuple:
        if depth == 0:
            return ("num", rng.randint(1, 9 + 3 * level))
        op = rng.choice(("+", "-", "*"))
        if rng.random() < 0.5:
            return ("op", op, build(depth - 1), build(depth - 1))
        return ("op", op, build(depth - 1), ("num", rng.randint(1, 9 + 3 * level)))

    def render(n: tuple, parent_prec: int = 0) -> str:
        if n[0] == "num":
            return str(n[1])
        op = n[1]
        prec = _PREC[op]
        s = f"{render(n[2], prec)} {op} {render(n[3], prec + 1)}"
        # parenthesise only when precedence would otherwise change the meaning,
        # so the rendered text and the structural evaluation always agree.
        return f"({s})" if prec < parent_prec else s

    def evaluate(n: tuple) -> int:
        if n[0] == "num":
            return n[1]
        a, b = evaluate(n[2]), evaluate(n[3])
        return a + b if n[1] == "+" else (a - b if n[1] == "-" else a * b)

    node = build(level)
    expr = render(node)
    answer = str(evaluate(node))
    prompt = (
        "按标准运算优先级（先乘后加减，括号优先）计算下列表达式，输出整数结果。\n"
        f"  {expr}"
    )
    return prompt, answer


_GENERATORS = {
    "arith_mod": _gen_arith_mod,
    "symbol_map": _gen_symbol_map,
    "rule_induce": _gen_rule_induce,
    "code_trace": _gen_code_trace,
    "logic_chain": _gen_logic_chain,
    "precedence": _gen_precedence,
}

# The *normative* view of which micro-skills are hard -- i.e. what a model could
# get from world knowledge without ever testing itself.  The offsets are spread
# widely and deliberately contradict several solvers' true profiles: no single
# external difficulty rating can describe both SolverA and SolverB, which is what
# makes the target of self-prediction model-specific.
_FAMILY_OFFSET = {
    "arith_mod": -0.20,     # "arithmetic is easy"
    "symbol_map": -0.10,
    "rule_induce": +0.30,   # "rule induction is hard"
    "code_trace": +0.15,
    "logic_chain": 0.00,
    "precedence": -0.15,
}


def _population_difficulty(family: str, level: int) -> float:
    raw = 0.10 + 0.155 * level + _FAMILY_OFFSET[family]
    return max(0.05, min(0.95, raw))


def make_item(
    family: str,
    level: int,
    rng: random.Random,
    idx: int,
    mode: str = "normal",
) -> Item:
    """Build one item.  ``mode='stroop'`` inverts surface salience vs. difficulty."""
    prompt, answer = _GENERATORS[family](level, rng)

    if mode == "normal":
        salience = _sig(0.9 * (level - 3)) + rng.gauss(0.0, 0.045)
    elif mode == "stroop":
        # Surface says the opposite of the truth, and easy items are dressed up
        # with verbose, irrelevant framing.
        salience = _sig(-0.9 * (level - 3)) + rng.gauss(0.0, 0.045)
        if level <= 2:
            prompt = rng.choice(_ORNAMENT) + "\n" + prompt
    else:
        raise ValueError(f"unknown mode {mode!r}")

    return Item(
        iid=f"{family}-L{level}-{idx:04d}-{mode}",
        family=family,
        level=level,
        prompt=prompt,
        answer=answer,
        cue_salience=max(0.0, min(1.0, salience)),
        population_difficulty=_population_difficulty(family, level),
        mode=mode,
    )


def make_grid(
    rng: random.Random,
    per_cell: int = 4,
    families: tuple[str, ...] = FAMILIES,
    levels: tuple[int, ...] = LEVELS,
    mode: str = "normal",
    prefix: str = "",
) -> list[Item]:
    """Full (family x level) grid -- the capability probe / held-out cells."""
    items: list[Item] = []
    idx = 0
    for family in families:
        for level in levels:
            for _ in range(per_cell):
                it = make_item(family, level, rng, idx, mode=mode)
                it.iid = f"{prefix}{it.iid}"
                items.append(it)
                idx += 1
    return items


def make_stratified(
    rng: random.Random,
    per_cell: int,
    cells: list[tuple[str, int]],
    mode: str = "normal",
    prefix: str = "",
) -> list[Item]:
    items: list[Item] = []
    idx = 0
    for family, level in cells:
        for _ in range(per_cell):
            it = make_item(family, level, rng, idx, mode=mode)
            it.iid = f"{prefix}{it.iid}"
            items.append(it)
            idx += 1
    return items
