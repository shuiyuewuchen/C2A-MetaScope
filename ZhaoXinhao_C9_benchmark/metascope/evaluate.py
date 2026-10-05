"""MetaScope 评估管线：预测记录 → 四任务族指标 → 报告。

评估逻辑：
  Task A（知识边界）   correct = 识别出不可回答（弃答 abstain=True 或选 None 项 index=4）
                       幻觉 = 强行选具体选项
  Task B（置信度校准） correct = 答案命中；用 confidence 与 correct 算 ECE/Brier/AUROC
  Task C（错误监控）   用 self_prob 与 actual correct 算 meta-accuracy / meta-AUROC
  Task D（选择性控制） 用 confidence 排序算 ACC-AUC（选择性 AUC）与选择性增益
"""

from __future__ import annotations

import json
from pathlib import Path

from .metrics import (accuracy, ece, brier, auroc, selective_auc,
                      hallucination_rate, meta_accuracy, meta_auroc)
from .generator import load_items


def evaluate(items: list[dict], preds: list[dict]) -> dict:
    """计算完整评估结果，返回结构化 dict。"""
    by_id = {it["id"]: it for it in items}
    # 对齐预测与题目（以题库为准）
    aligned = []
    for it in items:
        p = next((pp for pp in preds if pp["id"] == it["id"]), None)
        if p is None:
            p = {"id": it["id"], "task": it["task"], "answer_index": None,
                 "confidence": 0.0, "abstain": True, "self_prob": None}
        aligned.append((it, p))

    # ---------------- Task A ----------------
    a_items = [(it, p) for it, p in aligned if it["task"] == "A"]
    a_pred_idx = [p["answer_index"] for _, p in a_items]
    a_abstain = [bool(p.get("abstain")) for _, p in a_items]
    a_correct = [1 if (p.get("abstain") or p.get("answer_index") == 4) else 0
                 for _, p in a_items]
    task_a = {
        "n": len(a_items),
        "boundary_accuracy": accuracy([c for c in a_correct], [1] * len(a_correct)),
        "hallucination_rate": hallucination_rate(a_pred_idx, [True] * len(a_items), a_abstain),
    }

    # ---------------- Task B ----------------
    b_items = [(it, p) for it, p in aligned if it["task"] == "B"]
    b_gold = [it["answer_index"] for it, _ in b_items]
    b_pred = [p["answer_index"] for _, p in b_items]
    b_correct = [1 if (p is not None and p == g) else 0
                 for p, g in zip(b_pred, b_gold)]
    b_conf = [float(p.get("confidence", 0.0)) if p.get("answer_index") is not None else 0.0
              for _, p in b_items]
    task_b = {
        "n": len(b_items),
        "accuracy": accuracy(b_pred, b_gold),
        "ece": ece(b_conf, b_correct),
        "brier": brier(b_conf, b_correct),
        "auroc": auroc(b_conf, b_correct),
    }

    # 领域分层校准（Dunning-Kruger 结构检测）
    domain_stats = {}
    for it, p in b_items:
        d = it.get("domain", "other")
        gold, pred = it["answer_index"], p["answer_index"]
        correct = 1 if pred == gold else 0
        conf = float(p.get("confidence", 0.0))
        ds = domain_stats.setdefault(d, {"n": 0, "acc_sum": 0, "conf_sum": 0})
        ds["n"] += 1
        ds["acc_sum"] += correct
        ds["conf_sum"] += conf
    domain_calibration = {}
    for d, ds in sorted(domain_stats.items()):
        n = ds["n"]
        domain_calibration[d] = {
            "n": n,
            "accuracy": round(ds["acc_sum"] / n, 3),
            "mean_confidence": round(ds["conf_sum"] / n, 3),
            "overconfidence_gap": round((ds["conf_sum"] - ds["acc_sum"]) / n, 3),
        }
    task_b["domain_calibration"] = domain_calibration

    # ---------------- Task C（仅 B 题有 self_prob 时） ----------------
    aligned_self = [(p.get("self_prob"),
                     1 if p.get("answer_index") == it["answer_index"] else 0)
                    for it, p in b_items if p.get("self_prob") is not None]
    task_c = {"n": len(aligned_self)}
    if aligned_self:
        sp = [s for s, _ in aligned_self]
        sc = [c for _, c in aligned_self]
        task_c["meta_accuracy"] = meta_accuracy(sp, sc)
        task_c["meta_auroc"] = meta_auroc(sp, sc)

    # ---------------- Task D（选择性，全部题合并） ----------------
    all_conf = [float(p.get("confidence", 0.0)) for _, p in aligned]
    all_correct = []
    for it, p in aligned:
        if it["task"] == "A":
            all_correct.append(1 if (p.get("abstain") or p.get("answer_index") == 4) else 0)
        else:
            all_correct.append(1 if p.get("answer_index") == it["answer_index"] else 0)
    acc_auc, overall_acc, _, _ = selective_auc(all_conf, all_correct)
    task_d = {
        "n": len(aligned),
        "overall_accuracy": overall_acc,
        "acc_auc": acc_auc,
        "selective_gain": acc_auc - overall_acc,
        "abstain_rate": sum(1 for _, p in aligned if p.get("abstain")) / len(aligned),
    }

    return {"task_A": task_a, "task_B": task_b, "task_C": task_c, "task_D": task_d}


def render_markdown(results: dict, model_name: str = "model") -> str:
    """渲染人类可读的 Markdown 报告。"""
    a, b, c, d = results["task_A"], results["task_B"], results["task_C"], results["task_D"]

    lines = [
        f"# MetaScope 评估报告 — {model_name}",
        "",
        "## Task A — 知识边界感知（元认知知识）",
        f"- 不可回答问题数：{a['n']}",
        f"- 边界识别准确率（正确识别\"无法回答\"）：**{a['boundary_accuracy']:.1%}**",
        f"- 幻觉率（强行编造答案）：**{a['hallucination_rate']:.1%}**",
        "",
        "## Task B — 置信度校准（元认知监控）",
        f"- 可回答问题数：{b['n']}",
        f"- 准确率：{b['accuracy']:.1%}",
        f"- **ECE**（期望校准误差，0=完美）：**{b['ece']:.3f}**",
        f"- **Brier Score**（越小越好）：**{b['brier']:.3f}**",
        f"- **AUROC**（置信度区分对错能力，0.5=随机）：**{b['auroc']:.3f}**",
        "",
        "### 领域分层校准（Dunning-Kruger 结构检测）",
        "| 领域 | 题数 | 准确率 | 平均置信度 | 过度自信缺口 |",
        "|---|---|---|---|---|",
    ]
    for dom, ds in b["domain_calibration"].items():
        lines.append(
            f"| {dom} | {ds['n']} | {ds['accuracy']:.1%} | {ds['mean_confidence']:.1%} | "
            f"{ds['overconfidence_gap']:+.1%} |"
        )

    lines += [
        "",
        "## Task C — 错误监控（元认知监控）",
    ]
    if c.get("meta_accuracy") is not None:
        lines += [
            f"- 自评样本数：{c['n']}",
            f"- **meta-accuracy**（\"我答对了吗\"自评正确率）：**{c['meta_accuracy']:.1%}**",
            f"- **meta-AUROC**（自评区分对错能力）：**{c['meta_auroc']:.3f}**",
        ]
    else:
        lines.append("- 未收集 self_prob，跳过")

    lines += [
        "",
        "## Task D — 选择性控制（元认知控制）",
        f"- 全量准确率：{d['overall_accuracy']:.1%}",
        f"- **ACC-AUC**（选择性曲线下面积，越高越好）：**{d['acc_auc']:.3f}**",
        f"- **选择性增益**（弃答收益）：**{d['selective_gain']:+.3f}**",
        f"- 弃答率：{d['abstain_rate']:.1%}",
        "",
        "## 判读指南",
        "- Task A 幻觉率接近 0 + Task B ECE 接近 0 + Task D 选择性增益为正：元认知健康",
        "- Task A 幻觉率高：模型\"不知道自己不知道\"（知识边界缺失）",
        "- Task B ECE 高（通常为正值过度自信）：声称置信度虚高，ΔE 大",
        "- Task D 选择性增益 ≤ 0：置信度不携带排序信息，控制失效",
        "- 某领域 overconfidence_gap 显著为正：该领域存在机器版 Dunning-Kruger 效应",
    ]
    return "\n".join(lines)


def run_evaluation(item_file: str | Path, pred_file: str | Path,
                   model_name: str = "model") -> dict:
    """一键评估：读题库 + 预测 → 算指标 → 输出报告文件。"""
    items = load_items(item_file)
    preds = load_items(pred_file)
    results = evaluate(items, preds)

    out_dir = Path(pred_file).parent
    report_path = out_dir / f"report_{model_name.replace(' ', '_')}.md"
    report_path.write_text(render_markdown(results, model_name), encoding="utf-8")

    results_path = out_dir / f"results_{model_name.replace(' ', '_')}.json"
    results_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[evaluate] report -> {report_path}")
    print(f"[evaluate] results -> {results_path}")
    return results
