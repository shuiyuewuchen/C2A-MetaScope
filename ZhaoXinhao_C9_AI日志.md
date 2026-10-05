# AI 生成日志 / AI Generation Log (C9)

**作者 / Author:** 赵心皓 (Zhao Xinhao)
**挑战 / Challenge:** C9 — Track 2 Metacognition
**日期 / Date:** 2026-10-05

---

## 工具 / Tools Used

- **Doubao（豆包）AI 助手** — 全流程：技术规格设计、代码生成、调试、文档撰写、实测执行
- **通用网络搜索** — 补充调研（ConfidenceBench、AbstentionBench、RMCB 等）
- **Python 3.14** — Benchmark 实现与验证（纯标准库）

---

## 一、提案 → 技术规格（Step 1）

**Prompt 核心内容：** 将 C2A 提案的四任务族转换为技术规格——输入/输出 JSON 协议、评分函数清单、数据集结构、防作弊机制。

**AI 产出：**
- 统一数据格式（JSONL：id/task/domain/difficulty/answerable/options/answer_index）
- 预测协议（answer_index + confidence + abstain + self_prob）
- 指标定义（ECE/Brier/AUROC/ACC-AUC/幻觉率/meta 指标）
- **迭代 2 轮：** 第 1 轮初稿缺少 Task C 的协议设计（自评触发条件），人工补充"仅对可回答题追加 self_prob"；第 2 轮明确"None 选项恒为 index 4"以统一评分。

## 二、代码开发（Step 2-3）

**开发过程（含失败与修正）：**

| 版本 | 事件 | 修正 |
|---|---|---|
| v0.1 | 生成器 first run | 发现 KNOWLEDGE_ITEMS 元组结构错误（dict() 转换失败）→ 改为显式转换函数 |
| v0.2 | 数学题生成 | 选项数 5+1 冲突（断言失败）→ 数学题只生成 4 个实体选项 |
| v0.3 | 评估管线 first run | b_conf 变量类型混淆（int vs dict）→ 修复 |
| v0.4 | mock 对照 | good 模型 ECE(0.19) > poor(0.12) 反直觉 → 重构置信度生成逻辑（围绕领域准确率分布） |
| v0.5 | mock 对照 | good 模型 meta-AUROC=1.0 不真实 → 自评分布加入重叠区间 |
| v0.6 | 难度梯度 | 实测发现前沿模型全对 → 新增 10 条 hard science + very-hard 数学/逻辑分支 + 难度分层采样 |

**AI 调试效率最高的环节：** 第 1-3 次 bug 均为类型/结构问题，AI 阅读 traceback 后 1 轮即定位修复；第 4-5 次为模拟模型行为设计问题，AI 提出重构方案后人工确认语义合理性。

## 三、模型测试（Step 4）

**测试协议设计（人工主导）：**
1. AI 生成测试集后，人工要求生成"无答案版"呈现文件（`test_presentation.jsonl`）——**避免被测模型看到标准答案**
2. 抽取难度分层样本（commonsense/science/arithmetic/logic × easy/medium/hard）
3. 人工作为被测模型（豆包大模型）按 JSON 协议逐题作答
4. 评估 → 发现全对 → 人工决策新增 very-hard 层（8 题）→ 复测
5. mock poor/good 对照实验验证基准区分能力

**关键发现（人工记录）：** 前沿模型在标准难度层全对、轻微欠自信（science -8.6%）；校准不佳模拟模型全面亮红灯。三模型梯度验证基准有效。

## 四、文档生成（Step 5）

- README、任务说明、测试结果、反思报告、本日志、拿来说明全部由 AI 起草
- **人工审阅修正点：**
  - 测试结果文档补上"全对时选择性增益无统计意义"的诚实说明（AI 初稿未提及）
  - 反思报告补充"评估口径错误"的具体教训（AI 未主动记录）
  - 确保每个数字与 `results_*.json` 实际输出一致

## 五、AI 段位自评

**🔵 进阶 → 🔴 驾驭（接近）** — 形成了完整 workflow（规格→生成→调试→测试→文档），多轮迭代优化。但核心判断（难度校准、评估口径、测试严谨性）仍需人工介入，AI 的局限在于**无法预知模型行为**（会全对）和**不会质疑自己的评估逻辑**（口径错误）。这正是反向举证的价值所在。

## 六、手动步骤说明 / Manual Steps Justification

| 手动步骤 | 为什么没用 AI |
|---|---|
| 实测子集抽样与难度配比 | 需要结合对前沿模型能力的实测判断，AI 无法预知"豆包会全对" |
| "无答案呈现"测试流程 | 保证测试可信度的关键设计，AI 若自测可能依赖训练记忆 |
| 评估口径审查（子集 vs 全量） | AI 生成的评估逻辑产生误导结果，需要人工质疑与修正 |
| 反思报告的失败经验记录 | AI 倾向于呈现成功叙事，失败教训需人工挖掘 |
