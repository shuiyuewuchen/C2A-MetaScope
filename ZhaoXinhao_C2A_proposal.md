# MetaScope：衡量大模型元认知能力的校准基准

# MetaScope: A Calibration Benchmark for Metacognition in LLMs

**赛道 / Track:** Track 2 — Metacognition（元认知）
**作者 / Author:** 赵心皓 (Zhao Xinhao)
**日期 / Date:** 2026-10-05

---

## 1. 赛道选择与动机 / Track Selection & Motivation

为什么选元认知？因为它是幻觉问题的根源，也是五个赛道中"缺口最大、成本最高"的一个。当前 LLM 在知识题上可以答得很准，但我们无法知道**它自己是否知道**它答得准。一个模型可以 90% 正确，却在剩下 10% 的错误上给出 100% 的自信——这正是 DeepMind 框架指出的核心风险：元认知缺失直接决定系统能否被安全部署。

**KSTAR 连接：** KSTAR 循环中的 ΔE 是"预期与实际"的认知偏差，而元认知评估的本质就是**量化 ΔE**。模型声明的置信度（预期 E）与真实正确率（实际 R）之间的差距，就是可以被直接测量的认知偏差。我们把 ΔE 从哲学概念变成三个可计算指标：ECE（期望校准误差）、Brier Score、AUROC——这正是本 benchmark 的理论支点。

**Why Metacognition?** Because it is the root cause of hallucination and the costliest evaluation gap among the five tracks. KSTAR's ΔE (cognitive bias between expectation and reality) can be operationalized: the gap between a model's claimed confidence (E) and its true accuracy (R) is measurable via ECE, Brier score, and AUROC.

---

## 2. Benchmark 设计思路 / Benchmark Design

**MetaScope 用四层任务族覆盖论文定义的元认知三维结构（知识→监控→控制），并针对每一维给出 KSTAR ΔE 的可计算定义。**

### Task A — 知识边界感知（元认知知识）
程序化生成**不可回答问题**：用规则拼接出"捏造的实体"（虚构科学家、不存在的化合物、伪造历史事件），确保任何训练数据中都不可能存在正确答案。模型必须识别"我不知道"而非编造。
- 指标：幻觉率（对不可回答问题强行作答的比例）、边界识别率
- **核心创新：** 程序化生成保证题目新颖性和不可记忆性，彻底解决数据污染（借鉴 ARC 的 held-out 哲学，但用文本形式实现）

### Task B — 置信度校准（元认知监控）
多领域知识题（借鉴 MMLU 的领域分层），模型输出答案 + 置信度（0-100%）。
- 指标：ECE、Brier、AUROC（正确/错误答案的置信度区分度）、校准曲线斜率
- **领域分层校准：** 按领域分别计算校准误差，检测"弱领域过度自信"——即机器版的 Dunning-Kruger 效应

### Task C — 错误监控（元认知监控）
回答后（不告知对错）让模型预测"我这次答对了吗"；或给模型两个候选答案，让它判断哪个更可能是对的。
- 指标：meta-accuracy（自我预测与事实的正确率匹配度）、JOL 判断校准

### Task D — 选择性控制（元认知控制）
允许模型选择"放弃回答"。测量弃答后的 coverage-accuracy 曲线与 AURAC（风险-覆盖曲线下面积）。
- 指标：选择性增益（弃答后剩余答案准确率提升幅度）、弃答正确率
- **KSTAR 映射：** 模型感知到 ΔE≠0（低置信）→ 触发控制行动（弃答），这是元认知闭环的最终检验

### 三角验证（贯穿全benchmark的创新）
对比三种置信度来源：**语言化置信度**（"我 80% 确定"）、**行为置信度**（是否弃答）、**内在置信度**（token 概率）。三者的一致性就是模型"说一套做一套"的程度——即 ΔE 的行为化度量。

| 认知科学理论 | 对应任务 | 测量指标 |
|---|---|---|
| Metacognitive knowledge (Flavell 1979) | Task A | 幻觉率 |
| Confidence calibration (Fleming & Lau 2014) | Task B | ECE / Brier / AUROC |
| Error monitoring (Yeung & Summerfield 2012) | Task C | meta-accuracy |
| Metacognitive control (Nelson 1990) | Task D | AURAC / 选择性增益 |

---

## 3. 人类基线考量 / Human Baseline Considerations

**预期人类表现分布（基于认知科学文献）：**

| 人群 | Task A（识别不可回答） | Task B（常识题校准） | Task B（专业题校准） | Task D（弃答） |
|---|---|---|---|---|
| 普通成人 | 85-95% 识别 | 准确率 ~85%，过度自信 ~5-10% | 准确率下降，过度自信加剧 | 弃答率高，选择性增益大 |
| 领域专家 | ~95% | 校准良好 | 校准良好 | 精准弃答 |

文献依据：Lichtenstein et al. (1982) 发现人类平均置信度 65-70% 而准确率仅 ~50%（普遍过度自信）；Kruger & Dunning (1999) 发现低能力者在弱领域过度自信最严重——这正是 Task B 领域分层要检测的结构。

**区分度设计：**
- **过易控制：** Task A 的伪实体使用"可信命名模式"（如"Dr. Valtrexia 的量子场论贡献"），诱导幻觉，确保对 AI 有区分度
- **过难控制：** Task B 设置 40% 常识题（人类 >90%），避免地板效应
- **难度梯度：** 常识（浅）→ 专业（中）→ 伪实体（深），平滑覆盖

---

## 4. 预期创新点与可行性 / Innovation & Feasibility

### 创新点

| 现有方案局限 | MetaScope 的解决 |
|---|---|
| MMLU 校准研究只测"已知道多少" | 程序化伪实体题测"是否知道自己不知道"——把知识缺失与不确定性分离 |
| KalshiBench 依赖真实世界时间事件，无法生成 | 程序化生成，无限新题，无污染，无需等待真实结果 |
| AbstentionBench 用人工收集的数据 | 全自动生成 + 精确评分，可无限扩展 |
| 单一置信度来源（多为 token 概率） | 三角验证：语言 vs 行为 vs 内在置信度 |
| 指标单一（只看 ECE） | 四任务 × 多指标，覆盖元认知知识/监控/控制全维度 |

**最核心的创新：把 ΔE（KSTAR 认知偏差）从概念变成一套可复现的四维测量协议。**

### 可行性

| 资源 | 方案 | 时间 |
|---|---|---|
| 伪实体生成器 | Python 规则生成，< 200 行 | 1 天 |
| 数据量 | 程序生成 5,000 题（A/B/C/D 混合） | 1 天 |
| 评分函数 | ECE/Brier/AUROC/AURAC，标准库实现 | 1 天 |
| 模型测试 | API 调用 2-3 个前沿模型 | 2 天 |
| 文档 + Kaggle 提交 | README + 任务说明 | 1 天 |
| 缓冲 | 调试迭代 | 1 天 |
| **合计** | 纯文本、无 GPU、仅 API 推理 | **7 天** |

---

## 参考文献 / References

1. Burnell, R. et al. (2026). Measuring Progress Toward AGI: A Cognitive Framework. *Google DeepMind*.
2. Flavell, J.H. (1979). Metacognition and cognitive monitoring. *American Psychologist*.
3. Fleming, S.M. & Lau, H.C. (2014). How to measure metacognition. *Frontiers in Human Neuroscience*.
4. Yeung, N. & Summerfield, C. (2012). Metacognition in human decision-making. *Phil. Trans. R. Soc. B*.
5. Kruger, J. & Dunning, D. (1999). Unskilled and unaware of it. *JPSP*.
6. Lichtenstein, S., Fischhoff, B. & Phillips, L. (1982). Calibration of probabilities. *Judgment under Uncertainty*.
7. Hendrycks, D. et al. (2020). Measuring Massive Multitask Language Understanding. *ICLR*.
8. Rajpurkar, P. et al. (2018). Know What You Don't Know: SQuAD 2.0. *ACL*.
9. Chollet, F. (2019). On the Measure of Intelligence. *arXiv:1911.01547*.
10. El-Yaniv, R. & Wiener, Y. (2010). On the Foundations of Noise-free Selective Classification. *JMLR*.
11. Guo, C. et al. (2017). On Calibration of Modern Neural Networks. *ICML*.
12. Ye, F. et al. (2024). Benchmarking LLMs via Uncertainty Quantification. *NeurIPS*.
13. Zhang, S. et al. (2025). AbstentionBench: Benchmarking LLM Abstention. *arXiv:2506.09038*.
