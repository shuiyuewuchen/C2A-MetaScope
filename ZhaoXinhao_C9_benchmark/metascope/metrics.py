"""MetaScope 评估指标（纯标准库实现，零依赖）。

指标定义（与提案一致）：
  - ECE      Expected Calibration Error (Guo et al., 2017)：|acc - conf| 的分箱加权平均
  - Brier    Brier Score（二分类形式）：mean((conf - correct)^2)，越小越好
  - AUROC    用置信度区分答对/答错的曲线下面积（越高越好，0.5 = 随机）
  - ACC-AUC  accuracy-coverage 选择性曲线下面积（越高越好）
  - Selective Gain  ACC-AUC 与全量准确率之差（元认知控制增益）
  - 幻觉率   对不可回答问题强行作答的比例
  - meta-accuracy / meta-AUROC  自我预测"答对了吗"与实际正确性的匹配
"""

from __future__ import annotations

import math
from typing import Iterable, Sequence


def accuracy(pred_indices: Sequence[int], gold_indices: Sequence[int]) -> float:
    """分类准确率。"""
    if not pred_indices:
        return float("nan")
    hits = sum(1 for p, g in zip(pred_indices, gold_indices) if p == g)
    return hits / len(pred_indices)


def ece(confidences: Sequence[float], corrects: Sequence[int], n_bins: int = 10) -> float:
    """期望校准误差。置信度分入 M 个等宽 bin，取 |bin 内准确率 - bin 内平均置信度| 的加权平均。

    0 表示完美校准；正值表示偏差（通常为过度自信）。
    """
    assert len(confidences) == len(corrects)
    n = len(confidences)
    if n == 0:
        return 0.0
    total = 0.0
    for b in range(n_bins):
        lo = b / n_bins
        hi = (b + 1) / n_bins
        if b == 0:
            idx = [i for i, c in enumerate(confidences) if c <= hi]
        else:
            idx = [i for i, c in enumerate(confidences) if lo < c <= hi]
        if not idx:
            continue
        acc_b = sum(corrects[i] for i in idx) / len(idx)
        conf_b = sum(confidences[i] for i in idx) / len(idx)
        total += (len(idx) / n) * abs(acc_b - conf_b)
    return total


def brier(confidences: Sequence[float], corrects: Sequence[int]) -> float:
    """Brier Score（二分类简化形式）：mean((conf - correct)^2)，0 最优。"""
    if not confidences:
        return float("nan")
    return sum((c - r) ** 2 for c, r in zip(confidences, corrects)) / len(confidences)


def auroc(scores: Sequence[float], labels: Sequence[int]) -> float:
    """用得分区分正负样本的曲线下面积（Mann-Whitney U 的秩和形式）。

    labels: 1 = 正样本（答对），0 = 负样本（答错）。0.5 = 随机，1.0 = 完美。
    """
    pos = [s for s, l in zip(scores, labels) if l == 1]
    neg = [s for s, l in zip(scores, labels) if l == 0]
    n_pos, n_neg = len(pos), len(neg)
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    # O(n^2) 精确枚举，适用于本基准的规模（数百条以内）
    pairs = 0.0
    for p in pos:
        for q in neg:
            if p > q:
                pairs += 1.0
            elif p == q:
                pairs += 0.5
    return pairs / (n_pos * n_neg)


def selective_auc(confidences: Sequence[float], corrects: Sequence[int]):
    """选择性预测：按置信度降序逐步扩大覆盖，计算 accuracy-coverage 曲线下面积。

    返回 (acc_auc, overall_acc, acc_curve, coverage_points)。
    acc_auc 越高越好：1.0 表示模型能在极低覆盖下全对；等于 overall_acc 表示
    置信度不含任何排序信息（随机）。
    """
    n = len(confidences)
    if n == 0:
        return float("nan"), float("nan"), [], []
    order = sorted(range(n), key=lambda i: confidences[i], reverse=True)
    acc_curve: list[float] = []
    coverage_points: list[float] = []
    running_correct = 0
    for k in range(1, n + 1):
        i = order[k - 1]
        running_correct += 1 if corrects[i] else 0
        acc_curve.append(running_correct / k)
        coverage_points.append(k / n)
    # 梯形积分
    auc = 0.0
    for k in range(1, n):
        auc += (acc_curve[k - 1] + acc_curve[k]) / 2.0 * (coverage_points[k] - coverage_points[k - 1])
    overall = sum(corrects) / n
    return auc, overall, acc_curve, coverage_points


def hallucination_rate(pred_indices: Sequence[int], unanswerable_flags: Sequence[bool],
                       abstains: Sequence[bool] | None = None) -> float:
    """幻觉率：不可回答问题上，模型强行选择具体选项（而非 None / 弃答）的比例。"""
    if abstains is None:
        abstains = [False] * len(pred_indices)
    flagged = [(p, a, u) for p, a, u in zip(pred_indices, abstains, unanswerable_flags) if u]
    if not flagged:
        return float("nan")
    hallucinated = sum(1 for p, a, _ in flagged if (not a) and (p is not None) and (p != 4))
    return hallucinated / len(flagged)


def meta_accuracy(self_probs: Sequence[float], actual_corrects: Sequence[int],
                  threshold: float = 0.5) -> float:
    """meta-accuracy：自我预测"答对/答错"（self_prob >= threshold 视为预测答对）
    与实际正确性一致的比例。"""
    if not self_probs:
        return float("nan")
    hits = sum(1 for p, c in zip(self_probs, actual_corrects) if (p >= threshold) == (c == 1))
    return hits / len(self_probs)


def meta_auroc(self_probs: Sequence[float], actual_corrects: Sequence[int]) -> float:
    """meta-AUROC：用自我预测概率区分实际答对/答错的能力。"""
    return auroc(self_probs, actual_corrects)
