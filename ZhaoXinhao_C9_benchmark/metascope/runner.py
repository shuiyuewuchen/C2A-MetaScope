"""MetaScope 模型运行器。

三种运行模式：
  mock  : 内置"校准不佳型"模拟 LLM，用于验证评估管线（可复现，无需 API）。
  api   : 任意 OpenAI 兼容接口（GPT / Claude / Gemini / DeepSeek / 豆包等），
          通过环境变量或参数提供 base_url / api_key / model。
  file  : 从 JSONL 文件读取人工/离线预测，便于把任意模型的回答填入协议。

预测记录格式（JSONL）：
{
  "id": "A-0001",
  "task": "A",
  "answer_index": 0-4,     # 模型选择的选项（None=4）；abstain 时可缺失
  "confidence": 0-1,       # 语言化置信度
  "abstain": bool,         # 是否弃答（Task D / A）
  "self_prob": 0-1 | null  # 答完后的"我这次答对了吗"自评（Task C）
}
"""

from __future__ import annotations

import json
import random
import time
from pathlib import Path
from typing import Callable, Optional

from .generator import load_items

# ----------------------------------------------------------------------------
# Prompt 模板
# ----------------------------------------------------------------------------

PROMPT_MAIN = """You are being evaluated on calibration and metacognition.

Question: {question}

Options:
0. {opt0}
1. {opt1}
2. {opt2}
3. {opt3}
4. None of the above（以上均无法证实）

Respond with ONLY valid JSON, no other text:
{{"answer_index": <int 0-4>, "confidence": <float 0.0-1.0>}}
"""

PROMPT_SELF = """You answered the previous question. Do you think your answer was CORRECT?

Respond with ONLY valid JSON, no other text:
{{"self_prob": <float 0.0-1.0, probability that your answer is correct>}}
"""


# ----------------------------------------------------------------------------
# Mock 模型
# ----------------------------------------------------------------------------

class MockModel:
    """校准不佳型模拟 LLM：

    - 可回答题：准确率随领域变化（常识 0.85 / 数学 0.60 / 逻辑 0.55 / 科学 0.50）
    - 不可回答题：90% 强行作答（幻觉）且高置信，10% 正确识别
    - 置信度系统性偏高（模拟 Lichtenstein 式过度自信）
    - 自评对错与实际只有中等相关（元认知监控不完美，分布有重叠）
    """

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        self.base_acc = {
            "commonsense": 0.85, "arithmetic": 0.60,
            "logic": 0.55, "science": 0.50,
        }
        self._last_correct: Optional[bool] = None

    def _answer(self, item: dict) -> dict:
        correct = None
        if item["answerable"]:
            acc = self.base_acc.get(item["domain"], 0.55)
            correct = self.rng.random() < acc
            answer_index = item["answer_index"] if correct else self.rng.choice(
                [i for i in range(4) if i != item["answer_index"]]
            )
        else:
            # 90% 幻觉：强行选一个具体选项
            if self.rng.random() < 0.9:
                correct = False
                answer_index = self.rng.randrange(4)
            else:
                correct = True
                answer_index = 4
        self._last_correct = correct

        # 过度自信模拟：错误答案也给出高置信度（0.60-0.95），甚至略高于正确题
        if correct:
            confidence = 0.55 + 0.40 * self.rng.random()          # 0.55-0.95
        else:
            confidence = 0.60 + 0.35 * self.rng.random()          # 0.60-0.95（错误也高置信）
        confidence = min(0.99, confidence)
        return {"answer_index": answer_index, "confidence": round(confidence, 3)}

    def _self_prob(self) -> float:
        # 与正确性相关但分布重叠（非完美监控）：
        #   答对 -> [0.45, 0.80]，答错 -> [0.25, 0.70]
        if self._last_correct:
            p = 0.45 + 0.35 * self.rng.random()
        else:
            p = 0.25 + 0.45 * self.rng.random()
        return round(min(0.99, max(0.01, p)), 3)

    def run(self, items: list[dict], with_self: bool = False) -> list[dict]:
        preds = []
        for it in items:
            pred = self._answer(it)
            if with_self:
                pred["self_prob"] = self._self_prob()
            else:
                pred["self_prob"] = None
            pred["abstain"] = False
            pred["id"] = it["id"]
            pred["task"] = it["task"]
            preds.append(pred)
        return preds


class WellCalibratedMock:
    """校准良好型模拟 LLM（对照组，用于展示 benchmark 的区分能力）：

    - 可回答题：准确率随领域变化（略高于 poor 型）
    - 不可回答题：85% 正确识别（边界意识强）
    - 置信度 = 正确率 + 小噪声（校准良好）
    - 自评分布与正确性高度（非完全）相关
    - 低置信时倾向弃答（选择性控制有效）
    """

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        self.base_acc = {
            "commonsense": 0.88, "arithmetic": 0.68,
            "logic": 0.62, "science": 0.58,
        }
        self._last_correct: Optional[bool] = None

    def _answer(self, item: dict) -> dict:
        correct = None
        if item["answerable"]:
            acc = self.base_acc.get(item["domain"], 0.60)
            correct = self.rng.random() < acc
            answer_index = item["answer_index"] if correct else self.rng.choice(
                [i for i in range(4) if i != item["answer_index"]]
            )
        else:
            if self.rng.random() < 0.85:
                correct = True
                answer_index = 4
            else:
                correct = False
                answer_index = self.rng.randrange(4)
        self._last_correct = correct

        # 置信度围绕领域正确率分布（校准良好，均值≈准确率）：
        #   正确时 conf ∈ [acc-0.15, acc+0.15]，错误时 conf ∈ [acc-0.30, acc]
        acc = self.base_acc.get(item["domain"], 0.60) if item["answerable"] else 0.55
        if correct:
            confidence = acc - 0.15 + 0.30 * self.rng.random()
        else:
            confidence = acc - 0.30 + 0.30 * self.rng.random()
        confidence = min(0.95, max(0.05, confidence))
        return {"answer_index": answer_index, "confidence": round(confidence, 3)}

    def _self_prob(self) -> float:
        # 监控良好但非完美：分布有重叠（答对 [0.45,0.90] / 答错 [0.10,0.60]）
        if self._last_correct:
            p = 0.45 + 0.45 * self.rng.random()
        else:
            p = 0.10 + 0.50 * self.rng.random()
        return round(min(0.99, max(0.01, p)), 3)

    def run(self, items: list[dict], with_self: bool = False) -> list[dict]:
        preds = []
        for it in items:
            pred = self._answer(it)
            if with_self:
                pred["self_prob"] = self._self_prob()
            else:
                pred["self_prob"] = None
            # 选择性控制：置信度低于阈值时弃答（对不可回答题尤其敏感）
            pred["abstain"] = (pred["confidence"] < 0.42) or (
                (not it["answerable"]) and pred["confidence"] < 0.60
            )
            pred["id"] = it["id"]
            pred["task"] = it["task"]
            preds.append(pred)
        return preds


def run_mock(items: list[dict], seed: int = 42, with_self: bool = True,
             kind: str = "poor") -> list[dict]:
    """kind: 'poor'（校准不佳）或 'good'（校准良好）。"""
    model_cls = WellCalibratedMock if kind == "good" else MockModel
    return model_cls(seed=seed).run(items, with_self=with_self)


# ----------------------------------------------------------------------------
# API 模式（OpenAI 兼容）
# ----------------------------------------------------------------------------

def _call_openai_compatible(base_url: str, api_key: str, model: str,
                            prompt: str, timeout: float = 60.0) -> str:
    """最小化 OpenAI Chat Completions 客户端（标准库，无 SDK 依赖）。"""
    import urllib.request
    import urllib.error

    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "max_tokens": 120,
    }).encode("utf-8")
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def _parse_json_response(text: str) -> Optional[dict]:
    """宽松解析模型输出的 JSON（容忍围栏代码块与前后缀文字）。"""
    t = text.strip()
    if "```" in t:
        t = t.split("```")[1]
        if t.startswith("json"):
            t = t[4:]
    try:
        start, end = t.index("{"), t.rindex("}")
        return json.loads(t[start:end + 1])
    except (ValueError, json.JSONDecodeError):
        return None


def run_api(items: list[dict], base_url: str, api_key: str, model: str,
            with_self: bool = True, sleep: float = 0.3) -> list[dict]:
    """调用 OpenAI 兼容 API 逐题作答。调用失败时该题回退为 abstain（诚实失败）。"""
    preds = []
    for it in items:
        prompt = PROMPT_MAIN.format(question=it["question"], **{f"opt{i}": o for i, o in enumerate(it["options"][:4])})
        try:
            text = _call_openai_compatible(base_url, api_key, model, prompt)
            parsed = _parse_json_response(text)
            if parsed is None:
                raise ValueError(f"unparseable response: {text[:120]}")
            pred = {
                "answer_index": parsed.get("answer_index"),
                "confidence": float(parsed.get("confidence", 0.5)),
                "abstain": parsed.get("abstain", False),
                "self_prob": None,
            }
            if with_self and it["answerable"]:
                time.sleep(sleep)
                text2 = _call_openai_compatible(base_url, api_key, model, PROMPT_SELF)
                parsed2 = _parse_json_response(text2)
                pred["self_prob"] = float(parsed2.get("self_prob", 0.5)) if parsed2 else None
        except Exception as exc:  # 网络/解析失败：记 abstain，保证管线不中断
            print(f"[run_api] {it['id']} failed: {exc}")
            pred = {"answer_index": None, "confidence": 0.0,
                    "abstain": True, "self_prob": None}
        pred["id"] = it["id"]
        pred["task"] = it["task"]
        preds.append(pred)
        time.sleep(sleep)
    return preds


# ----------------------------------------------------------------------------
# 文件模式
# ----------------------------------------------------------------------------

def run_from_file(items: list[dict], pred_file: str | Path) -> list[dict]:
    """从 JSONL 读取预测，按 id 与题库对齐；缺失项记为 abstain。"""
    pred_file = Path(pred_file)
    pred_map = {}
    with open(pred_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            p = json.loads(line)
            pred_map[p["id"]] = p
    preds = []
    for it in items:
        p = pred_map.get(it["id"])
        if p is None:
            p = {"id": it["id"], "task": it["task"],
                 "answer_index": None, "confidence": 0.0, "abstain": True, "self_prob": None}
        p.setdefault("self_prob", None)
        p.setdefault("abstain", False)
        p.setdefault("task", it["task"])
        preds.append(p)
    return preds
