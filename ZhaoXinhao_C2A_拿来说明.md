# 拿来说明 / Attribution

**作者 / Author:** 赵心皓 (Zhao Xinhao)
**挑战 / Challenge:** C2A — Track 2 Metacognition
**日期 / Date:** 2026-10-05

---

## 借鉴来源 / References

| 来源 / Source | 链接 / Link | 核心思想 / Key Idea |
|---------------|-------------|---------------------|
| DeepMind AGI 认知框架 (Burnell et al., 2026) | [PDF](https://storage.googleapis.com/deepmind-media/DeepMind.com/Blog/measuring-progress-toward-agi/measuring-progress-toward-agi-a-cognitive-framework.pdf) | 元认知三维结构（知识/监控/控制）+ 三阶段评估协议 + 评估缺口分析 |
| MMLU (Hendrycks et al., 2020) | [arXiv:2009.03300](https://arxiv.org/abs/2009.03300) | 多领域知识分层（57 学科）为 Task B 领域校准提供结构 |
| SQuAD 2.0 (Rajpurkar et al., 2018) | [arXiv:1806.03822](https://arxiv.org/abs/1806.03822) | 不可回答问题（unanswerable questions）评估范式 |
| El-Yaniv & Wiener (2010) Selective Classification | [JMLR](https://www.jmlr.org/papers/volume11/el-yaniv10a/el-yaniv10a.pdf) | coverage-accuracy / risk-coverage 曲线的选择性预测框架 |
| Guo et al. (2017) ECE | [ICML](https://arxiv.org/abs/1706.04599) | 期望校准误差（ECE）指标定义 |
| Fleming & Lau (2014) | [Frontiers](https://www.frontiersin.org/journals/human-neuroscience/articles/10.3389/fnhum.2014.00443/full) | 元认知测量方法论（type-2 指标、置信度校准） |
| Kruger & Dunning (1999) | [JPSP](https://doi.org/10.1037/0022-3514.77.6.1121) | 低能力者过度自信效应（弱领域校准差） |
| Lichtenstein et al. (1982) | [Book](https://www.cambridge.org/core/books/judgment-under-uncertainty/calibration-of-probabilities-the-state-of-the-art-to-1980/2d19d3499665d9ce4a70de1a3e1c16df) | 人类普遍过度自信：置信 65-70% vs 准确率 ~50% |
| ARC (Chollet, 2019) | [arXiv:1911.01547](https://arxiv.org/abs/1911.01547) | held-out / 防污染设计哲学：任务必须不可记忆 |
| Ye et al. (2024) LLM-Uncertainty-Bench | [NeurIPS](https://papers.nips.cc/paper_files/paper/2024/hash/1bdcb065d40203a00bd39831153338bb-Abstract-Datasets_and_Benchmarks_Track.html) | 把不确定性量化纳入 LLM 评估框架 |
| ConfidenceBench (2026) | [Semantic Scholar](https://www.semanticscholar.org/paper/ConfidenceBench:-Evaluating-Confidence-Calibration-ffrench-Constant-Yang/6c362117719fd783d67cc2a949ad23e903d33f07) | 语言化置信度的 Brier score 独立评估轴 |
| AbstentionBench (Zhang et al., 2025) | [arXiv:2506.09038](https://arxiv.org/pdf/2506.09038) | LLM 弃答（abstention）的系统评估框架 |
| KSTAR 框架 | 课程资料 | ΔE（认知偏差）+ 置信度校准映射 |
| Flavell (1979) | [APA](https://doi.org/10.1037/0003-066X.34.10.906) | 元认知知识/监控二分法的经典来源 |

---

## 拿来的部分 / Adopted

### 从 MMLU 拿了什么
- **拿了：** 多领域知识 MCQ 的分层结构（领域标签、知识广度）
- **为什么好用：** 领域分层是"机器版 Dunning-Kruger"检测的前提——按领域分别计算校准误差才能暴露弱领域过度自信

### 从 SQuAD 2.0 拿了什么
- **拿了：** "不可回答问题"的评估思想——模型必须识别无法回答的问题而非强行作答
- **为什么好用：** 直接对应元认知知识维度（Knowledge of limitations），是测"是否知道自己不知道"的最直接范式

### 从 El-Yaniv 选择性预测拿了什么
- **拿了：** coverage-accuracy 曲线与风险-覆盖权衡的框架
- **为什么好用：** 弃答（abstention）是元认知控制的唯一可观测行为出口，AURAC 提供精确评分

### 从 DeepMind 框架拿了什么
- **拿了：** 元认知三维结构（知识/监控/控制）作为任务族的顶层分类；三阶段评估协议中"人类基线"的必要性
- **为什么好用：** 保证 benchmark 与论文定义严格对齐，评审可一眼看出理论锚点

### 从 ARC 拿了什么
- **拿了：** "任务必须不可记忆、held-out"的防污染设计哲学
- **为什么好用：** 程序化生成伪实体题正是这一哲学在文本领域的实现

### 从 KSTAR 拿了什么
- **拿了：** ΔE（认知偏差）作为统一评估主轴——每个指标都是 ΔE 的某种量化形式
- **为什么好用：** 让 benchmark 从"统计测量"上升为"理论驱动测量"，与课程体系直接对接

---

## 去掉的部分 / Removed

| 来源 | 他们做了什么 | 我不要 | 原因 |
|------|------------|--------|------|
| SQuAD 2.0 | 抽取式问答（从文档中找答案） | 去掉抽取式格式，改用四选一 MCQ | 抽取式自动评分依赖 F1 匹配，容错低、易误判；MCQ 精确评分且可程序化生成 |
| KalshiBench | 真实世界预测市场问题（等待事件发生） | 去掉真实事件依赖 | 无法程序化生成、需要等待真实结果、训练数据可能已含相关信息 |
| AbstentionBench | 人工收集各类弃答数据 | 去掉人工收集 | 扩展性差、成本高；我们改为全自动程序生成 |
| MMLU | 57 学科的全部题目 | 不用 MMLU 原题 | 原题已公开、存在数据污染风险；我们只借用"领域分层"结构，题目由程序生成 |
| ConfidenceBench | 仅测语言化置信度 | 不限于单一置信度来源 | 引入三角验证（语言/行为/内在），测"说做一致性" |
| BIG-Bench | 大规模多任务框架 | 不直接采用 | 范围过大，一周内不可实现；聚焦元认知单维度 |
| ARC | 视觉网格变换 | 不用视觉格式 | 视觉格式难以程序化生成大量伪实体题；文本 MCQ 更适合元认知测量 |

---

## 我的改进 / My Improvements

### 改进 1：程序化生成的不可回答问题（核心创新）

- **现有方法的问题：** SQuAD 2.0 的不可回答问题是人工构造的（数量有限、可能泄漏）；KalshiBench 依赖真实事件（不可生成）
- **我的改进：** 用规则引擎程序化生成"伪实体问题"——虚构人名 + 领域模板 + 干扰项，保证每个题目在训练数据中不存在
- **效果：** 无限新题、零污染、可精确控制难度（伪实体命名模式的可信度梯度）

### 改进 2：ΔE 主轴 + 四任务族递进结构

- **现有方法的问题：** 校准研究大多只测"已知道多少"（MMLU 校准），把知识缺失与不确定性混为一谈
- **我的改进：** 四任务族按"知识边界（不知道什么）→ 已知知识上的校准（知道多少）→ 错误监控（是否知道自己答错）→ 控制（是否据此弃答）"递进，每个任务族对应 ΔE 的一个侧面
- **效果：** 从"静态校准"升级为"元认知全生命周期评估"

### 改进 3：三角验证（语言 vs 行为 vs 内在置信度）

- **现有方法的问题：** 多数 benchmark 只用单一置信度来源（token 概率或语言声明），无法检测"说一套做一套"
- **我的改进：** 同一题目收集三种置信度信号并对比一致性
- **效果：** 新增"置信度一致性"评估轴——如果模型口头说 90% 确定但拒绝弃答时准确率只有 60%，说明其元认知监控与控制脱节

### 改进 4：领域分层校准（机器版 Dunning-Kruger）

- **现有方法的问题：** 整体 ECE 会掩盖"弱领域过度自信"的模式
- **我的改进：** 按领域标签分别计算校准误差，输出领域级校准热图
- **效果：** 能识别模型"在哪些领域高估自己"——直接对应 Dunning-Kruger 效应的核心预测，也便于开发者定位改进目标
