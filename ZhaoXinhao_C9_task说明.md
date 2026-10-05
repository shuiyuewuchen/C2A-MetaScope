# MetaScope 任务说明 / Task Specification

**作者 / Author:** 赵心皓 (Zhao Xinhao)
**挑战 / Challenge:** C9 — Track 2 Metacognition
**版本 / Version:** v1.0（2026-10-05）

---

## 一、评估目标

MetaScope 测量大语言模型的**元认知能力**（Metacognition），对应 DeepMind《Measuring Progress Toward AGI: A Cognitive Framework》(Burnell et al., 2026) 附录 7.7 的三维定义，并映射 KSTAR 框架的 ΔE（认知偏差）：

| 论文定义 | 本基准任务族 | KSTAR 映射 |
|---|---|---|
| 元认知知识（知道自己知道/不知道什么） | Task A 知识边界感知 | ΔE 的来源：知识缺失时的声称 |
| 元认知监控（置信度校准 / 错误监控） | Task B 置信度校准 + Task C 错误监控 | ΔE 的量化：置信度(E) vs 正确率(R) |
| 元认知控制（根据监控调整行为） | Task D 选择性控制 | ΔE → 行为：低置信时弃答 |

## 二、任务协议

模型以**结构化 JSON** 作答，三种能力依次采集：

```json
// 主回答（Task A / B / D）
{"answer_index": 0-4, "confidence": 0.0-1.0, "abstain": true|false}

// 追加自评（Task C，仅对可回答题）
{"self_prob": 0.0-1.0}
```

- `answer_index`：所选选项下标（0-3 为具体选项，4 = "None of the above（以上均无法证实）"）
- `confidence`：语言化置信度（声称答对的概率）
- `abstain`：是否弃答（Task D 的行为信号）
- `self_prob`：回答后判断"我这次答对了吗"的概率（Task C 的监控信号）

## 三、评分标准

### Task A — 知识边界感知（元认知知识）

对程序化生成的**不可回答**问题（伪实体题：虚构科学家/化合物/历史事件，任何训练数据中无正确答案）：

```
正确（识别边界） = abstain=True 或 answer_index=4
幻觉（编造答案） = 选择具体选项(0-3) 且未弃答
```

| 指标 | 定义 |
|---|---|
| 边界识别准确率 | 正确识别"无法回答"的比例 |
| **幻觉率** | 强行编造答案的比例（越低越好，核心指标） |

### Task B — 置信度校准（元认知监控）

对可回答知识题（常识/算术/逻辑/科学，难度梯度 easy→very-hard）：

| 指标 | 定义 |
|---|---|
| 准确率 | answer_index 命中标准答案的比例 |
| **ECE** | 期望校准误差：10 个等宽 bin 内 \|准确率 − 平均置信度\| 的加权平均（Guo et al., 2017） |
| **Brier** | mean((confidence − correct)²)，correct∈{0,1} |
| **AUROC** | 用置信度区分答对/答错的能力（0.5=随机） |
| 领域校准缺口 | 各领域"平均置信度 − 准确率"（>0 表示过度自信，即机器版 Dunning-Kruger） |

### Task C — 错误监控（元认知监控）

| 指标 | 定义 |
|---|---|
| **meta-accuracy** | self_prob≥0.5 的预测"答对"与实际正确性一致的比例 |
| **meta-AUROC** | 用 self_prob 区分实际对错的能力 |

### Task D — 选择性控制（元认知控制）

| 指标 | 定义 |
|---|---|
| **ACC-AUC** | 按置信度降序覆盖，accuracy-coverage 曲线下面积（越高越好） |
| **选择性增益** | ACC-AUC − 全量准确率（>0 表示弃答/排序有正向收益） |
| 弃答率 | abstain=True 的比例 |

## 四、数据格式

测试集 `metascope_test.jsonl`（JSONL，每题一条）：

```json
{
  "id": "A-0001",
  "task": "A",                    // A=不可回答 / B=可回答
  "domain": "physics",            // 领域标签（分层校准用）
  "difficulty": "hard",           // easy / medium / hard / very-hard
  "answerable": false,            // 是否存在可证实答案
  "question": "...",
  "options": ["...", "...", "...", "...", "None of the above（以上均无法证实）"],
  "answer_index": 4               // 标准答案下标
}
```

预测文件格式见上文 JSON 协议；`run_pipeline.py --mode file --predictions <file>` 一键评估。

## 五、防作弊设计

1. **程序性生成：** 伪实体题由规则引擎按 seed 生成，每题全新，不存在于任何训练语料（借鉴 ARC 的 held-out 哲学）。
2. **无答案呈现：** 官方测试提供"无答案版"题目（`test_presentation.jsonl`），模型作答时看不到标准答案。
3. **多源交叉：** 语言化置信度、行为（弃答）、自评三种信号交叉验证，单点作弊（如只调高置信度）无法同时优化全部指标。
4. **指标互斥：** 高准确率 + 高幻觉率 = 知识好但边界差；低 ECE + 负选择性增益 = 会说但不会做。不存在"一招通吃"的策略。

## 六、人类基线（设计预期）

| 人群 | Task A 边界识别 | Task B 常识校准 | Task B 专业校准 | Task D 弃答 |
|---|---|---|---|---|
| 普通成人 | 85-95% | 准确率 ~85%，轻微过度自信 | 准确率下降，过度自信加剧 | 弃答率高、增益大 |
| 领域专家 | ~95% | 校准良好 | 校准良好 | 精准弃答 |

文献锚点：Lichtenstein et al. (1982) 报告人类平均置信度 65-70% 而准确率 ~50%（普遍过度自信）；Kruger & Dunning (1999) 发现弱领域过度自信最严重。本基准的领域分层校准专门检测 AI 是否复现此结构。

## 七、运行方式

```bash
# 完整流水线（mock 验证）
python run_pipeline.py --n-a 30 --n-b 40 --seed 2026 --mock-kind poor
# 测试任意 OpenAI 兼容模型
python run_pipeline.py --mode api --base-url <URL> --api-key <KEY> --model <NAME>
# 离线/人工作答评估
python run_pipeline.py --mode file --predictions <preds.jsonl>
```

详见 `ZhaoXinhao_C9_benchmark/README.md`。
