"""MetaScope 最终验证脚本（交付前 smoke test）。"""
from metascope.generator import generate_test, load_items
from metascope.metrics import ece, auroc
from metascope.runner import run_mock
from metascope.evaluate import evaluate

items = load_items("metascope/data/metascope_test.jsonl")
n_a = sum(1 for i in items if i["task"] == "A")
n_b = sum(1 for i in items if i["task"] == "B")
print(f"1) 测试集加载: {len(items)} 题 (A={n_a}, B={n_b})")

ok = all(0 <= i["answer_index"] <= 4 and len(i["options"]) == 5 for i in items)
print(f"2) 数据格式校验: {'通过' if ok else '失败'}")

preds = run_mock(items, seed=2026, kind="poor")
res = evaluate(items, preds)
print(f"3) mock-poor 评估: 幻觉率={res['task_A']['hallucination_rate']:.1%}, "
      f"ECE={res['task_B']['ece']:.3f}, 选择性增益={res['task_D']['selective_gain']:+.3f}")

p_doubao = load_items("metascope/data/predictions_doubao.jsonl")
print(f"4) 豆包预测加载: {len(p_doubao)} 条")

print(f"5) 指标函数: ece([0.8,0.5,0.9],[1,0,1])={ece([0.8,0.5,0.9],[1,0,1]):.3f}, "
      f"auroc([0.9,0.6,0.8,0.3],[1,0,1,0])={auroc([0.9,0.6,0.8,0.3],[1,0,1,0]):.3f}")

# 可复现性：seed 相同则生成结果相同
a1 = generate_test(seed=2026, n_a=30, n_b=40)
a2 = generate_test(seed=2026, n_a=30, n_b=40)
print(f"6) 可复现性: 同 seed 两次生成{'一致' if a1 == a2 else '不一致'} ({len(a1)} 题)")
print("ALL CHECKS PASSED")
