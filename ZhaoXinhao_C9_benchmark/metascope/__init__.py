"""MetaScope — 元认知校准基准（Track 2 Metacognition）。

衡量 LLM 元认知能力的四任务族基准：
  Task A  知识边界感知（不可回答问题，测元认知知识）
  Task B  置信度校准（可回答知识题，测元认知监控）
  Task C  错误监控（回答后自评答对概率，测元认知监控）
  Task D  选择性控制（弃答协议，测元认知控制）

设计依据：
  - DeepMind《Measuring Progress Toward AGI: A Cognitive Framework》(2026) 附录 7.7
    元认知 = 知识(7.7.1) + 监控(7.7.2) + 控制(7.7.3)
  - KSTAR 框架：ΔE（认知偏差）= 声称置信度(E) 与真实正确率(R) 之差，
    由 ECE / Brier / AUROC / AURAC 直接量化。

纯标准库实现，零依赖，可直接运行。
"""

__version__ = "1.0.0"
__author__ = "Zhao Xinhao"

from .generator import generate_train, generate_test, load_items
from .metrics import (accuracy, ece, brier, auroc, selective_auc,
                      hallucination_rate, meta_accuracy, meta_auroc)
from .runner import run_mock, run_from_file

__all__ = [
    "generate_train", "generate_test", "load_items",
    "accuracy", "ece", "brier", "auroc", "selective_auc",
    "hallucination_rate", "meta_accuracy", "meta_auroc",
    "run_mock", "run_from_file",
]
