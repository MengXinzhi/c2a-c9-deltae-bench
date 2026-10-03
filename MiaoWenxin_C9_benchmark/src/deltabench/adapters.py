"""Adapter for evaluating a *real* frontier model.

This module is the only place the benchmark touches the network.  It is written
so that a real model can be dropped in without touching the protocol code: the
protocol asks a ``MetaPredictor`` for a pre-answer probability, and the adapter
implements exactly that interface against an OpenAI-compatible chat endpoint.

Two channels are elicited per item, matching the benchmark's dual-probe design:

1. ``predict`` -- verbalised numeric confidence, *before* the model is allowed to
   answer.
2. ``predict_behavioral`` -- a point bet over a 1..10 ladder.  Empirically,
   stated confidence is systematically over-stated, so a wagering read-out is a
   better-behaved second channel (see ``docs/`拿来说明`.md`` for the citations).

In this submission no API credential was available, so the adapter ships
unconfigured and the reported numbers come from the simulated solvers.  See
``MiaoWenxin_C9_测试结果.md`` for the exact scope of the claims.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass

from .items import Item
from .metacog import MetaPredictor, RunContext
from . import metrics as M

PROMPT_PREDICT = """你在参加一个元认知评测。下面是题目：

{item}

在你尝试作答之前，请先预测你自己答对这道题的概率。
- 输出 0 到 1 之间的一个数，保留两位小数。
- 只输出这个数，不要输出别的内容。
"""

PROMPT_ANSWER = """{item}

只输出最终答案，不要输出推理过程。
"""

PROMPT_BET = """{item}

你已对本题给出一个答案。现在为自己下注：若答对得 {{k}} 分，若答错扣 {{k}} 分。
k 取 1 到 10 之间的整数。只输出这个整数。
"""

_NUM = re.compile(r"-?\d+(?:\.\d+)?")


def _first_float(text: str, lo: float = 0.0, hi: float = 1.0) -> float | None:
    m = _NUM.search(text or "")
    if not m:
        return None
    try:
        v = float(m.group(0))
    except ValueError:
        return None
    if v > hi:  # tolerate "85" meaning 85%
        v = v / 100.0
    return max(lo, min(hi, v))


@dataclass
class ChatClient:
    base_url: str
    model: str
    api_key: str = ""
    temperature: float = 0.0
    timeout: int = 120

    def complete(self, prompt: str) -> str:
        body = json.dumps({
            "model": self.model,
            "temperature": self.temperature,
            "messages": [{"role": "user", "content": prompt}],
        }).encode("utf-8")
        req = urllib.request.Request(
            self.base_url.rstrip("/") + "/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:  # pragma: no cover - network path
            raise RuntimeError(f"model call failed: {exc}") from exc
        return data["choices"][0]["message"]["content"]


class OpenAIMetaPredictor(MetaPredictor):
    """Elicits a pre-answer probability from a real chat model."""

    name = "REAL verbalised confidence"

    def __init__(self, client: ChatClient, fallback: float = 0.5):
        self.client = client
        self.fallback = fallback
        self.log: list[dict] = []

    def predict(self, item: Item, ctx: RunContext, y: bool | None = None) -> float:
        raw = self.client.complete(PROMPT_PREDICT.format(item=item.prompt))
        val = _first_float(raw)
        self.log.append({"iid": item.iid, "raw": raw, "parsed": val})
        return self.fallback if val is None else M.clip(val)

    def answer(self, item: Item) -> str:
        return self.client.complete(PROMPT_ANSWER.format(item=item.prompt)).strip()


class OpenAIBetPredictor(MetaPredictor):
    """Second, behavioural channel: a 1..10 point bet mapped to a probability.

    Mapping is deliberately conservative -- a bet of k implies
    ``0.5 + k / 20`` -- because the point of the channel is relative ordering,
    not absolute scale.
    """

    name = "REAL behavioural bet"
    channel = "behavioral"

    def __init__(self, client: ChatClient, fallback: float = 0.5):
        self.client = client
        self.fallback = fallback
        self.log: list[dict] = []

    def predict(self, item: Item, ctx: RunContext, y: bool | None = None) -> float:
        raw = self.client.complete(PROMPT_BET.format(item=item.prompt))
        m = _NUM.search(raw or "")
        if not m:
            self.log.append({"iid": item.iid, "raw": raw, "parsed": None})
            return self.fallback
        k = max(1.0, min(10.0, float(m.group(0))))
        p = 0.5 + k / 20.0
        self.log.append({"iid": item.iid, "raw": raw, "parsed": k, "p": p})
        return M.clip(p)


def from_env(base_url_var: str = "DELTABENCH_BASE_URL",
             model_var: str = "DELTABENCH_MODEL",
             key_var: str = "DELTABENCH_API_KEY") -> ChatClient:
    """Build a client from environment variables.  Raises if unconfigured."""
    base = os.environ.get(base_url_var)
    model = os.environ.get(model_var)
    if not base or not model:
        raise RuntimeError(
            "No model configured. Set DELTABENCH_BASE_URL and DELTABENCH_MODEL "
            "(and DELTABENCH_API_KEY) to run the benchmark against a real model."
        )
    return ChatClient(base_url=base, model=model, api_key=os.environ.get(key_var, ""))
