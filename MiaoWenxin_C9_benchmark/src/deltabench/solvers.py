"""Simulated *ability* solvers.

These stand in for frontier models so that the benchmark is fully runnable
offline.  They are deliberately separated from the metacognitive channel: an
ability solver only produces an answer, and correctness is whatever it is.  A
metacognitive predictor is a *different* object that may or may not have access
to the signal behind that correctness.

Two properties matter for the benchmark's validity:

1. **Different models have different competence profiles.**  ``SolverA`` is
   strong on arithmetic and weak on rule induction; ``SolverB`` is the reverse.
   A single "how hard is this item" rating therefore cannot describe both, which
   is what makes the target of self-prediction *model-specific* and hence
   unanswerable from any external corpus.
2. **Correctness is realised, not just declared.**  A solver returns an actual
   answer string that is compared against the reference, so the benchmark never
   needs to trust a stated probability.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from .items import Item, FAMILIES, LEVELS


def _sig(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


@dataclass
class SolverProfile:
    name: str
    skill: dict[str, float]
    slope: dict[str, float] = field(default_factory=dict)
    default_slope: float = 0.55

    def p_correct(self, family: str, level: int) -> float:
        base = self.skill.get(family, 0.0)
        slope = self.slope.get(family, self.default_slope)
        return _sig(1.6 * (base - slope * (level - 3.0)))


def _uniform(value: float) -> dict[str, float]:
    return {f: value for f in FAMILIES}


PROFILES: dict[str, SolverProfile] = {
    # arithmetic-dominant: fast, reliable on closed-form numeric work,
    # brittle on induction from examples.
    "SolverA": SolverProfile(
        name="SolverA(arith-leaning)",
        skill={
            "arith_mod": 0.95, "precedence": 0.85, "code_trace": 0.45,
            "logic_chain": 0.40, "symbol_map": 0.25, "rule_induce": -0.35,
        },
        slope={"arith_mod": 0.20, "precedence": 0.28, "code_trace": 0.55,
               "logic_chain": 0.60, "symbol_map": 0.70, "rule_induce": 0.95},
    ),
    # pattern-dominant: mirrors the profile shape often reported for
    # code/pattern-tuned checkpoints -- the exact opposite weakness map.
    "SolverB": SolverProfile(
        name="SolverB(pattern-leaning)",
        skill={
            "arith_mod": -0.30, "precedence": -0.10, "code_trace": 0.60,
            "logic_chain": 0.55, "symbol_map": 0.80, "rule_induce": 0.85,
        },
        slope={"arith_mod": 0.85, "precedence": 0.70, "code_trace": 0.40,
               "logic_chain": 0.45, "symbol_map": 0.25, "rule_induce": 0.30},
    ),
    # mid-capability generalist.
    "SolverC": SolverProfile(
        name="SolverC(generalist)",
        skill=_uniform(0.35),
        slope=_uniform(0.50),
    ),
    # tracer-dominant.
    "SolverD": SolverProfile(
        name="SolverD(trace-leaning)",
        skill={
            "arith_mod": 0.30, "precedence": 0.20, "code_trace": 0.95,
            "logic_chain": 0.90, "symbol_map": -0.10, "rule_induce": 0.05,
        },
        slope={"arith_mod": 0.60, "precedence": 0.65, "code_trace": 0.15,
               "logic_chain": 0.20, "symbol_map": 0.75, "rule_induce": 0.70},
    ),
    # low-capability: used to check the benchmarks floor behaviour.
    "SolverE": SolverProfile(
        name="SolverE(weak)",
        skill=_uniform(-0.55),
        slope=_uniform(0.80),
    ),
}


def _distractor(item: Item, rng: random.Random) -> str:
    """A plausible-but-wrong answer, so correctness is genuinely realised."""
    ans = item.answer
    if ans.lstrip("-").isdigit():
        n = int(ans)
        delta = rng.choice((-10, -3, -2, -1, 1, 2, 3, 10))
        return str(n + delta)
    if ans in ("0", "1") and len(ans) == 1:
        return "1" if ans == "0" else "0"
    if len(ans) <= 1:
        return rng.choice(tuple("0123456789"))
    kind = rng.choice(("swap", "drop", "dup", "sub"))
    if kind == "swap":
        i = rng.randrange(len(ans) - 1)
        return ans[:i] + ans[i + 1] + ans[i] + ans[i + 2:]
    if kind == "drop":
        i = rng.randrange(len(ans))
        return ans[:i] + ans[i + 1:]
    if kind == "dup":
        i = rng.randrange(len(ans))
        return ans[:i] + ans[i] + ans[i:]
    from .items import SYMBOLS
    i = rng.randrange(len(ans))
    return ans[:i] + rng.choice(SYMBOLS) + ans[i + 1:]


class SimulatedSolver:
    """An ability solver with a fixed competence profile."""

    def __init__(self, profile: SolverProfile, seed: int = 0):
        self.profile = profile
        self.rng = random.Random(seed)

    @property
    def name(self) -> str:
        return self.profile.name

    def solve(self, item: Item) -> tuple[str, bool]:
        p = self.profile.p_correct(item.family, item.level)
        if self.rng.random() < p:
            return item.answer, True
        return _distractor(item, self.rng), False

    def run(self, items: list[Item]) -> list[tuple[Item, str, bool]]:
        return [(it, *self.solve(it)) for it in items]
