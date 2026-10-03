"""DeltaE-Bench -- a closed-loop benchmark for metacognitive self-model
maintenance in LLM agents.

Public entry points:

    from deltabench.runner import Config, run_all, run_one
    from deltabench import metrics

The package has no third-party dependencies and is deterministic given a seed.
"""

from . import items, metrics, metacog, solvers  # noqa: F401
from .runner import Config, run_all, run_one  # noqa: F401

__version__ = "1.0.0"
__all__ = ["items", "metrics", "metacog", "solvers", "Config", "run_all", "run_one"]
