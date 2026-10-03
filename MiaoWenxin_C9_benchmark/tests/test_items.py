"""Ground-truth verification for the item generators.

A benchmark is only as good as its reference answers.  These tests recompute
every generated answer *independently of the generator* -- re-parsing the
rendered prompt and solving it from scratch -- so a green run is direct evidence
that the scoring key is not silently wrong.

For ``rule_induce`` the verification is stronger still: we brute-force every
operator composition up to the generator's maximum length, keep the ones that
reproduce all three worked examples, and check that at least one of them also
reproduces the reference answer for the query.  That establishes the reference
answer is *derivable from the examples given*, which is the property the task
claims to have.
"""

from __future__ import annotations

import itertools
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import random  # noqa: E402

from deltabench.items import (  # noqa: E402
    FAMILIES, LEVELS, _apply_ops, make_item,
)

_OPS = ("REV", "DUP_FIRST", "SWAP_END", "ROT_L", "DROP_ODD")


def test_arith_mod_answers_are_correct():
    rng = random.Random(11)
    for level in LEVELS:
        for _ in range(25):
            it = make_item("arith_mod", level, rng, 0)
            m = re.search(r"\(\((\d+) \* (\d+)\) \+ (\d+)\) mod (\d+)", it.prompt)
            assert m, it.prompt
            a, x, b, mod = (int(g) for g in m.groups())
            assert it.answer == str((a * x + b) % mod), it.prompt


def test_precedence_rendered_text_matches_structural_answer():
    """The rendered expression must evaluate (with real Python precedence) to
    exactly the stored answer -- this guards the paren-stripping optimisation."""
    rng = random.Random(12)
    for level in LEVELS:
        for _ in range(25):
            it = make_item("precedence", level, rng, 0)
            expr = it.prompt.strip().splitlines()[-1].strip()
            assert eval(expr) == int(it.answer), it.prompt  # noqa: S307 - digits/ops/parens only


def test_logic_chain_answers_are_correct():
    rng = random.Random(13)
    for level in LEVELS:
        for _ in range(15):
            it = make_item("logic_chain", level, rng, 0)
            lines = it.prompt.splitlines()
            bindings = dict(
                (k, int(v)) for k, v in re.findall(r"(x\d+)=(\d)", lines[0])
            )
            expr = lines[2].strip()
            # XOR must be substituted before OR, otherwise "OR" matches inside it
            py = re.sub(r"\bXOR\b", "^", expr)
            py = re.sub(r"\bAND\b", "and", py)
            py = re.sub(r"\bOR\b", "or", py)
            for name, val in sorted(bindings.items(), key=lambda kv: -len(kv[0])):
                py = py.replace(name, str(val))
            assert int(eval(py)) == int(it.answer), it.prompt  # noqa: S307


def test_symbol_map_answers_are_correct():
    rng = random.Random(14)
    for level in LEVELS:
        for _ in range(25):
            it = make_item("symbol_map", level, rng, 0)
            line0, line1 = it.prompt.splitlines()[0], it.prompt.splitlines()[1]
            # drop the Chinese lead-in, otherwise it is swallowed into the first key
            table_txt = line0.split("：", 1)[1]
            table = dict(
                (a, b) for a, b in re.findall(r"([^\s,>]+)->([^\s,]+)", table_txt)
            )
            src = re.search(r"将字符串 (\S+) 逐字符替换", line1).group(1)
            assert it.answer == "".join(table.get(c, c) for c in src), it.prompt


def test_code_trace_answers_are_correct():
    rng = random.Random(15)
    for level in LEVELS:
        for _ in range(20):
            it = make_item("code_trace", level, rng, 0)
            p = it.prompt
            start = int(re.search(r"acc = (\d+)", p).group(1))
            n = int(re.search(r"range\((\d+)\)", p).group(1))
            a, b, m = (int(g) for g in re.search(
                r"acc = \(acc \* (\d+) \+ (\d+)\) % (\d+)", p).groups())
            k = int(re.search(r"acc % (\d+) == 0", p).group(1))
            c = int(re.search(r"acc = \(acc \+ (\d+)\) %", p).group(1))
            acc = start
            for _ in range(n):
                acc = (acc * a + b) % m
                if acc % k == 0:
                    acc = (acc + c) % m
            assert it.answer == str(acc), it.prompt


def test_rule_induce_answer_is_derivable_from_the_given_examples():
    rng = random.Random(16)
    checked = 0
    for level in LEVELS:
        for _ in range(6):
            it = make_item("rule_induce", level, rng, 0)
            body = it.prompt.splitlines()
            pairs = [
                tuple(m.groups())
                for m in re.finditer(r"(\S+) -> (\S+)", it.prompt)
            ]
            assert len(pairs) == 3, it.prompt
            query = re.search(r"查询: (\S+)", it.prompt).group(1)

            max_len = 1 + level // 2 + (1 if level >= 4 else 0)
            consistent = False
            for length in range(1, max_len + 1):
                for ops in itertools.product(_OPS, repeat=length):
                    if all(_apply_ops(list(ops), s) == d for s, d in pairs):
                        if _apply_ops(list(ops), query) == it.answer:
                            consistent = True
                            break
                if consistent:
                    break
            assert consistent, f"no operator composition explains item:\n{it.prompt}"
            checked += 1
    assert checked >= 20
    del body


def test_items_are_informative_not_just_correct():
    """Correctness tests are not enough.

    A generator can emit items whose reference answer is perfectly correct *and*
    obtainable with a degenerate strategy.  The worst case found during
    development: ``SWAP_END`` is the identity whenever a string's first and last
    characters agree, so whole batches of ``rule_induce`` items reduced to
    "echo the query".  Every correctness assertion passed.  This test is the
    guard that would have caught it.
    """
    rng = random.Random(4242)
    echo_hits, echo_total = 0, 0

    for family in ("rule_induce", "symbol_map"):
        for level in LEVELS:
            for _ in range(30):
                it = make_item(family, level, rng, 0)
                if family == "symbol_map":
                    src = re.search(r"将字符串 (\S+) 逐字符替换", it.prompt).group(1)
                else:
                    src = re.search(r"查询: (\S+)", it.prompt).group(1)
                    pairs = re.findall(r"(\S+) -> (\S+)", it.prompt)
                    # the worked examples must each be a real transformation
                    assert all(a != b for a, b in pairs), it.prompt
                    # and they must not be redundant copies of one another
                    assert len({a for a, _ in pairs}) == 3, it.prompt
                echo_total += 1
                echo_hits += int(it.answer == src)

    echo_rate = echo_hits / echo_total
    assert echo_rate < 0.10, f"'echo the input' solves {echo_rate:.0%} of items"


def test_numeric_families_are_not_answerable_by_a_constant():
    """No single constant answer should solve a large share of numeric items."""
    rng = random.Random(99)
    answers = []
    for family in ("arith_mod", "precedence", "code_trace", "logic_chain"):
        for level in LEVELS:
            for _ in range(20):
                answers.append(make_item(family, level, rng, 0).answer)
    from collections import Counter
    top = Counter(answers).most_common(1)[0]
    assert top[1] / len(answers) < 0.25, f"answer '{top[0]}' covers {top[1]}/{len(answers)}"


def test_items_are_deterministic_and_family_consistent():
    a = make_item("rule_induce", 3, random.Random(99), 0)
    b = make_item("rule_induce", 3, random.Random(99), 0)
    assert (a.prompt, a.answer) == (b.prompt, b.answer)

    rng = random.Random(7)
    seen = set()
    for _ in range(200):
        it = make_item(rng.choice(FAMILIES), rng.choice(LEVELS), rng, 0)
        assert it.answer != "" or it.family == "symbol_map"
        seen.add(it.prompt)
    assert len(seen) > 150, "generator should not collapse to a tiny item pool"


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items())
           if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} item-generator tests passed")
