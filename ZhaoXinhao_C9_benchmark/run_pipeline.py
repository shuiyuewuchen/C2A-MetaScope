"""MetaScope 一键流水线：生成数据 → 运行模型 → 评估 → 输出报告。

用法：
  python run_pipeline.py                       # mock 模型快速验证（默认）
  python run_pipeline.py --mode api --base-url https://... --api-key ... --model gpt-4o
  python run_pipeline.py --mode file --predictions my_predictions.jsonl

任何 OpenAI 兼容接口均可（GPT / Claude / Gemini / DeepSeek / 豆包等）。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from metascope.generator import generate_test, generate_train, save_items
from metascope.runner import run_mock, run_api, run_from_file
from metascope.evaluate import evaluate, render_markdown


def main() -> None:
    ap = argparse.ArgumentParser(description="MetaScope benchmark pipeline")
    ap.add_argument("--mode", choices=["mock", "api", "file"], default="mock")
    ap.add_argument("--mock-kind", choices=["poor", "good"], default="poor",
                    help="mock 模型类型：poor=校准不佳（默认），good=校准良好对照组")
    ap.add_argument("--n-a", type=int, default=30, help="Task A (unanswerable) 题数")
    ap.add_argument("--n-b", type=int, default=40, help="Task B (answerable) 题数")
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--with-self", action="store_true", default=True,
                    help="是否收集 Task C 自我判断")
    ap.add_argument("--base-url", default=None)
    ap.add_argument("--api-key", default=None)
    ap.add_argument("--model", default="mock-model")
    ap.add_argument("--predictions", default=None, help="file 模式下的预测 JSONL")
    ap.add_argument("--out-dir", default=None, help="输出目录（默认 benchmark 根目录）")
    args = ap.parse_args()

    root = Path(args.out_dir) if args.out_dir else Path(__file__).resolve().parent
    data_dir = root / "metascope" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    # 1) 生成数据集（幂等：seed 固定则内容固定）
    train_path = data_dir / "metascope_train.jsonl"
    test_path = data_dir / "metascope_test.jsonl"
    save_items(generate_train(seed=args.seed), train_path)
    save_items(generate_test(seed=args.seed, n_a=args.n_a, n_b=args.n_b), test_path)
    from metascope.generator import load_items
    items = load_items(test_path)
    print(f"[pipeline] 数据集已生成: train={train_path} test={test_path} ({len(items)} 题)")

    # 2) 运行模型
    preds = None
    if args.mode == "mock":
        preds = run_mock(items, seed=args.seed, with_self=args.with_self,
                         kind=args.mock_kind)
        model_name = "mock-calibration-poor" if args.mock_kind == "poor" else "mock-calibration-good"
    elif args.mode == "api":
        if not (args.base_url and args.api_key and args.model):
            ap.error("--mode api 需要 --base-url --api-key --model")
        preds = run_api(items, args.base_url, args.api_key, args.model,
                        with_self=args.with_self)
        model_name = args.model
    else:  # file
        if not args.predictions:
            ap.error("--mode file 需要 --predictions <file.jsonl>")
        preds = run_from_file(items, args.predictions)
        model_name = Path(args.predictions).stem

    # 3) 保存预测
    pred_path = data_dir / f"predictions_{model_name.replace(' ', '_')}.jsonl"
    with open(pred_path, "w", encoding="utf-8") as f:
        for p in preds:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    print(f"[pipeline] 预测已保存: {pred_path}")

    # 4) 评估
    results = evaluate(items, preds)
    report = render_markdown(results, model_name)
    report_path = root / f"report_{model_name.replace(' ', '_')}.md"
    report_path.write_text(report, encoding="utf-8")
    print(report)
    print(f"[pipeline] 报告 -> {report_path}")


if __name__ == "__main__":
    main()
