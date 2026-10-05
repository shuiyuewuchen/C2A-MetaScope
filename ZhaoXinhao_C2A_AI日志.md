# AI 生成日志 / AI Generation Log

**作者 / Author:** 赵心皓 (Zhao Xinhao)
**挑战 / Challenge:** C2A — Track 2 Metacognition
**日期 / Date:** 2026-10-05

---

## 工具 / Tools Used

- **Doubao（豆包）AI 助手** — 论文精读、benchmark 调研、提案撰写、迭代优化
- **通用网络搜索** — 已有 benchmark 与认知科学文献调研
- **PDF 全文解析工具** — DeepMind 论文原文精读（非摘要）

---

## 论文精读 / Paper Analysis

- **方法：** 通过全文解析工具逐段读取 DeepMind 论文 PDF 原文（约 24,000 token，分两段完整读取），而非仅依赖已提供的摘要文档。
- **关键提取：**
  1. 元认知在论文附录 7.7 节的三维结构：**Metacognitive knowledge（元认知知识，含 Knowledge of limitations、Metamemory）→ Metacognitive monitoring（元认知监控，含 Confidence calibration、Judgments of learning、Error monitoring、Source judgments）→ Metacognitive control（元认知控制，含 Error correction、Learning strategy selection）**
  2. 论文 4.1 节明确指出评估缺口："large coverage gaps in areas such as metacognition, attention, learning, and social cognition"（元认知是覆盖缺口最大的能力之一）
  3. 三阶段评估协议（认知评估 → 人类基线 → 认知画像）为 benchmark 提供方法论框架
  4. 论文对任务的要求：targeted（针对性）、held-out（私密/防污染）、varied difficulty、varied structure
- **迭代：** 1 轮全文精读 + 2 轮针对性追问（元认知子能力清单、评估缺口描述、任务设计要求）

---

## Benchmark 调研 / Benchmark Research

- **搜索策略（共 9 个 query，3 轮并行）：**
  - Round 1: `LLM confidence calibration benchmark ECE selective prediction` / `LLM metacognition benchmark "knows what it doesn't know"` / `MMLU uncertainty quantification LLM-Uncertainty-Bench`
  - Round 2: `unanswerable questions SQuAD 2.0 abstention selective prediction` / `Dunning-Kruger overconfidence human calibration` / `ARC benchmark fluid intelligence`
- **发现的关键参考：**
  - **ConfidenceBench (2026)**：语言化置信度的 Brier score 评估，15 个前沿模型 —— 印证"语言置信度校准是独立评估轴"
  - **KalshiBench (2025)**：用真实世界预测市场问题测认识论校准，但**依赖真实事件、无法程序化生成** —— 这是我们要解决的核心痛点
  - **AbstentionBench (2025)**：LLM 弃答系统评估，但数据靠人工收集，扩展性受限
  - **SQuAD 2.0 (Rajpurkar 2018)**：不可回答问题设计范式，但格式是抽取式 QA 而非 MCQ
  - **LLM-Uncertainty-Bench (Ye et al., NeurIPS 2024)**：把不确定性纳入 LLM 评估的框架性工作
  - **Dunning-Kruger (1999) + Lichtenstein (1982)**：人类过度自信的经典证据，为人类基线提供理论锚点
  - **ARC (Chollet 2019)**：held-out 去污染设计哲学
- **评估结果：** 共调研 12+ 个 benchmark/文献，最终确定主要借鉴 MMLU（领域分层）、SQuAD 2.0（不可回答范式）、El-Yaniv 选择性预测（弃答指标）、ARC（防污染哲学），并针对各自的局限设计创新方案。

---

## 提案撰写 / Proposal Writing

- **初稿生成：** 基于论文精读提取的元认知三维结构，构思"四任务族覆盖知识→监控→控制"的整体框架，AI 生成双语提案初稿。
- **迭代次数：** 3 轮
  - 第 1 轮：初稿结构偏平铺，缺少统一的评估主轴。**人工指出**后，重构为"以 KSTAR ΔE 为主轴、四任务族逐层递进"的逻辑线。
  - 第 2 轮：不可回答问题（Task A）与置信度校准（Task B）的关系不清晰。重新设计为"先测知识边界、再测已知知识上的校准"的递进关系，并引入三角验证（语言/行为/内在置信度）。
  - 第 3 轮：人类基线部分缺少文献支撑。补充 Lichtenstein (1982) 与 Kruger & Dunning (1999) 的具体数据，并给出分人群预期分布表。
- **人工修改：**
  - 将"元认知监控"拆分为 Task B（置信度校准）与 Task C（错误监控）两个独立任务族，使任务与指标一一对应
  - 修正指标表：把 AURAC（风险-覆盖曲线）从"扩展指标"提升为 Task D 主指标
  - 校准参考文献列表，确保每篇引用都与实际设计决策相关
  - 难度梯度比例设定为常识 40% / 专业 40% / 伪实体 20%，避免地板效应

---

## 手动步骤说明 / Manual Steps Justification

| 手动步骤 | 为什么没用 AI |
|----------|-------------|
| 赛道选择（在五赛道中确定 Metacognition） | 需要结合个人课程背景（KSTAR 框架学习）与差异化竞争策略（示例提案已覆盖 Track 1），属于个人判断 |
| 伪实体命名模式的"可信度"设计（诱导幻觉的平衡点） | 需要权衡"足够可信以诱导幻觉"与"可被人类识别"的难度平衡，属于经验性判断 |
| 任务族数量与指标取舍 | 需要控制在一周内可实现的范围，避免设计过度膨胀 |

---

## AI 段位自评 / AI Usage Level

**🔵 进阶** — 多轮对话迭代优化 prompt，审阅并修正 AI 输出。核心设计决策（四任务族结构、ΔE 主轴、三角验证）是人工与 AI 协同构思的：AI 提供文献与框架素材，人工负责取舍与方向校正。
