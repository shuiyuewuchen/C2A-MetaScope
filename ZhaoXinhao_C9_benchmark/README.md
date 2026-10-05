# MetaScope — 衡量大模型元认知能力的校准基准

**Track 2 · Metacognition（元认知）** · Kaggle "Measuring Progress Toward AGI: Cognitive Abilities" 参赛基准

**作者：** 赵心皓（Zhao Xinhao）
**版本：** v1.0（2026-10-05）

---

## 一、基准是什么

MetaScope 用 **4 个任务族** 覆盖 DeepMind 认知框架（Burnell et al., 2026）附录 7.7 定义的元认知三维结构，并把 KSTAR 的 ΔE（认知偏差 = 声称置信度与真实正确率之差）变成可计算的指标：

| 任务族 | 测量维度 | 核心指标 |
|---|---|---|
| **Task A 知识边界感知** | 元认知知识（知道自己不知道什么） | 幻觉率、边界识别准确率 |
| **Task B 置信度校准** | 元认知监控（知道"我答对的概率"） | ECE、Brier、AUROC、领域校准缺口 |
| **Task C 错误监控** | 元认知监控（回答后判断对错） | meta-accuracy、meta-AUROC |
| **Task D 选择性控制** | 元认知控制（根据不确定性调整行为） | ACC-AUC、选择性增益、弃答率 |

**核心创新（与现有基准的区别）：**

1. **程序化生成的不可回答问题（Task A）** —— 规则引擎生成"伪实体"（虚构科学家/化合物/历史事件），任何训练数据中都不存在正确答案。模型必须识别"无法证实"而非编造。彻底解决数据污染，可无限生成。
2. **三角验证** —— 同一题目可收集语言化置信度、行为置信度（弃答）、内在置信度（token 概率，通过 API runner 可选采集），检测模型"说"与"做"的 ΔE 一致性。
3. **领域分层校准** —— 按领域分别计算校准缺口，检测"机器版 Dunning-Kruger 效应"（弱领域过度自信）。
4. **零依赖、纯标准库** —— 无需安装任何包，任何环境可复现。

## 二、目录结构

```
ZhaoXinhao_C9_benchmark/
├── README.md                  # 本文件
├── run_pipeline.py            # 一键流水线（生成→测试→评估→报告）
├── metascope/                 # 核心包（纯标准库，零依赖）
│   ├── __init__.py
│   ├── generator.py           # 题目生成器（伪实体 + 知识题 + 数学/逻辑题）
│   ├── metrics.py             # ECE / Brier / AUROC / ACC-AUC / 幻觉率 / meta 指标
│   ├── runner.py              # 模型运行器（mock / API / file 三种模式）
│   ├── evaluate.py            # 评估管线与 Markdown 报告渲染
│   └── data/
│       ├── metascope_train.jsonl      # 示例集（10 题）
│       ├── metascope_test.jsonl       # 完整测试集（70 题：30 A + 40 B）
│       ├── test_presentation.jsonl    # 实测抽样子集（33 题，无答案版）
│       ├── hard_extra.jsonl           # very-hard 附加层（8 题）
│       ├── predictions_doubao.jsonl   # 豆包实测预测（33 题）
│       ├── predictions_doubao_hard.jsonl
│       └── predictions_mock-*.jsonl   # mock 对照预测
└── report_*.md                # 自动生成的评估报告
```

## 三、快速开始

```bash
# 1) 用内置 mock 模型跑完整流水线（校准不佳型，验证工具链）
python run_pipeline.py --n-a 30 --n-b 40 --seed 2026 --mock-kind poor

# 2) 对照：校准良好型（展示基准的区分能力）
python run_pipeline.py --n-a 30 --n-b 40 --seed 2026 --mock-kind good
```

## 四、测试任意前沿模型

### 方式一：API 模式（推荐，OpenAI 兼容接口均可）

```bash
python run_pipeline.py --mode api \
  --base-url https://api.openai.com/v1 \
  --api-key sk-xxx \
  --model gpt-4o \
  --n-a 30 --n-b 40 --seed 2026
```

支持 GPT / Claude / Gemini / DeepSeek / 豆包等任何 OpenAI 兼容服务。模型按协议输出 JSON：

```json
{"answer_index": 2, "confidence": 0.85}
```

Task C（自评）追加一轮询问：`{"self_prob": 0.8}`。Task D（弃答）可输出 `"abstain": true`。

### 方式二：文件模式（离线/人工作答）

```bash
# 1) 查看题目（无答案版，避免测试时看到标准答案）
python -c "from metascope.generator import load_items; [print(json.dumps(i, ensure_ascii=False)) for i in load_items('metascope/data/test_presentation.jsonl')]"

# 2) 按协议作答，写入 predictions_my.jsonl（字段：id, answer_index, confidence, [self_prob], [abstain]）

# 3) 评估
python run_pipeline.py --mode file --predictions predictions_my.jsonl
```

## 五、评分协议（详见 `ZhaoXinhao_C9_task说明.md`）

- **Task A**：`correct = 弃答 或 选 None 项(index=4)`；强行选具体选项记 **幻觉**。
- **Task B**：`correct = answer_index 命中标准答案`；置信度参与 ECE/Brier/AUROC 计算。
- **Task C**：`self_prob ≥ 0.5` 预测"答对"，与实际正确性对比得 meta-accuracy。
- **Task D**：按置信度降序排序计算 accuracy-coverage 曲线下面积（ACC-AUC）。

## 六、判读指南

- 幻觉率 ≈ 0 且 ECE ≈ 0 且选择性增益 > 0 → 元认知健康
- 幻觉率高 → 模型"不知道自己不知道"（知识边界缺失）
- ECE 显著为正 → 声称置信度虚高（过度自信），ΔE 大
- 某领域 overconfidence_gap 显著为正 → 该领域存在机器版 Dunning-Kruger 效应
- 选择性增益 ≤ 0 → 置信度不携带排序信息，元认知控制失效

## 七、可复现性

- 固定 `--seed` 即得到完全相同的题目集与 mock 结果（seed=2026 为默认）。
- 全部代码为 Python 3.8+ 标准库实现（`json / random / math / urllib`），无第三方依赖。
- 测试数据与预测文件均已随仓库提交，`report_*.md` 可一键重生成。

## 八、参考

- Burnell et al. (2026) *Measuring Progress Toward AGI: A Cognitive Framework* — 元认知三维结构（7.7 节）
- Guo et al. (2017) — ECE 指标；El-Yaniv & Wiener (2010) — 选择性预测
- Kruger & Dunning (1999) — 过度自信效应；Lichtenstein et al. (1982) — 人类校准基线
- Rajpurkar et al. (2018) SQuAD 2.0 — 不可回答问题范式；Hendrycks et al. (2020) MMLU — 领域分层
