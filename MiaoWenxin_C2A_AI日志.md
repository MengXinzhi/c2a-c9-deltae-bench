# AI 生成日志 / AI Generation Log

**作者 / Author:** MiaoWenxin
**挑战 / Challenge:** C2A — Track 2 Metacognition（元认知）
**日期 / Date:** 2026-10-03
**对应交付物:** `MiaoWenxin_C2A_proposal.md`（v2 定稿）、`MiaoWenxin_C2A_proposal_v1.md`（初版留档）

---

## 工具 / Tools Used

- **WorkBuddy（Agent 模式）** — 论文精读、文献调研、方案构思、提案撰写、迭代优化、逻辑自检
- **Web Search** — 核实 2026 年元认知评测方向的最新文献（关键，见下"调研"节）
- **本机文件读取** — `materials\C2A-guide.pdf`、`materials\deepmind-agi-cognitive-framework-summary.pdf`、`materials\c2a-starter.zip`

> 说明：本挑战要求"全流程 AI 驱动，每个手动步骤反向举证"。下文的"手动步骤说明"节逐条给出为什么某些环节必须由人来做。

---

## 1. 论文精读 / Paper Analysis

- **方法：** 把 DeepMind 框架的两份材料（官方 PDF 摘要版 + 完整论文）交给 AI，要求提取四件事：
  1. 10 个认知能力的定义与它们之间的层级/依赖关系；
  2. 论文判定"当前评估缺口最大"的 5 个赛道分别缺口在哪；
  3. 论文提出的三阶段评估协议（held-out 任务 → 人类基线 → 认知画像）；
  4. 元认知（Track 2）一节对"幻觉根因"的论述原文与结论。
- **关键提取（直接决定了选题）：** 论文把元认知定义为"对自身认知过程的监控与理解"，并明确把它列为**幻觉的关键根源**——一个无法区分"我知道"与"我不知道"的系统，会用同样的语气说出对的和错的内容。这一句给出了 Track 2 最硬的问题陈述，也是最终选它的第一理由。
- **第二关键提取：** 论文的评估协议要求"held-out 任务 + 人类基线 + 认知画像"，这直接变成提案里"评测集三分"（台账单元格 / 插值档 / 外推族）与"人类基线采集方案"两节。
- **迭代：** 1 轮精读 + 2 轮追问。第一轮追问"5 个赛道里哪几个和 KSTAR 的 ΔE 最对口"（答案是 Learning 与 Metacognition）；第二轮追问"论文是否已经给出元认知的可操作规程"，结论是——**论文只给了定义和缺口，没有给可执行协议**，这正是本提案的空间。

---

## 2. Benchmark 调研 / Benchmark Research

这一步是提案的成败关键，也是我**主动要求 AI 先搜索再动笔**的地方。

- **搜索策略（真实检索方向）：**
  - Query 1: `DeepMind measuring progress toward AGI cognitive framework metacognition` （核实一手框架）
  - Query 2: `LLM metacognition benchmark calibration confidence 2026`
  - Query 3: `language models know what they know P(IK) Kadavath`
  - Query 4: `metacognitive calibration LLM benchmark MIRROR knowing-doing gap`
  - Query 5: `LLM uncertainty verbalized confidence Xiong ICLR`
  - Query 6: `metacognitive monitoring battery LLM 2026`
  - Query 7: `LLM metacognition limited evidence Ackerman ICLR 2026`
- **发现的关键参考（全部为真实可查文献）：**
  - **Kadavath et al. (2022), P(IK)** — 第一次系统提出"作答前预测自己是否会做对"。它是本方向的地基，但它用**监督值头**做单题判断，且不涉及"预测会不会随经历更新"。
  - **Xiong et al. (2024, ICLR)** — 系统比较了黑箱/白箱置信度提取，证明"让模型直接输出置信度"是可行的，但有系统性偏差。
  - **MIRROR (arXiv:2604.19809, 2026)** — 分层元认知校准基准，提出 knowing-doing gap、跨域迁移层次。**并且给出一个对本提案至关重要的否定结果**：把模型自己的校准分**直接喂回**给它，并不显著降低 confident failure rate（p > 0.05），只有外部架构约束有效。
  - **Metacognitive Monitoring Battery (arXiv:2604.15702, 2026)** — 测监控—控制耦合，发现**行为通道优于言语通道**。这启发我把"控制"做成有客观最优解的预算任务（B5/CU）。
  - **Ackerman (ICLR 2026)** — 用博弈范式绕开"廉价自我报告"，并明确指出现有大模型**缺少一个专门回忆自己过往动作的结构**（"the missing hippocampus"）。
  - 经典认知科学锚点：Fleming & Lau (2014)、Maniscalco & Lau (2012)、Nelson & Narens (1990)、Kruger & Dunning (1999)、Lichtenstein & Fischhoff (1977)、Gigerenzer et al. (1991)、Guo et al. (2017)、Murphy (1973)。
- **调研的一个转折（写进日志因为它是真实的失败/转向）：** 检索后我判断"测模型有无元认知"这条路在 2026 年**已经相当拥挤**（MIRROR、Battery、Ackerman 都在这条线上）。如果只是再做一个"测校准"的基准，创新性会被稀释。
  → **因此把命题整体挪了一格**：不问"你此刻是否了解自己"，而问"**给你一份关于你自己的原始记录，你能不能写出一份可复用的自我模型，并在换题、换技能、题面被伪装时它仍然有用**"。
  这一步把创新点从"测量有没有"移到"测量能不能写出 / 维持 / 迁移 / 使用"，正是 KSTAR 里 ΔR→K 那段被跳过的循环。
- **评估结果：** 共调研 12+ 个来源，最终以 **Kadavath（形式）、MIRROR（否定结果与迁移层次）、Ackerman（效度警告）、Metacognitive Battery（行为通道）**为四个主要借鉴来源，其余作为理论锚点。

---

## 3. 提案撰写 / Proposal Writing

- **初稿生成（v1）：** Prompt 提供了"赛道 = Track 2 + KSTAR ΔE 映射 + 调研出的四个主要来源 + 核心想法（闭环自我模型）"，要求按课程要求的 20/40/20/20 四段结构生成初稿。AI 一次性给出了 `MiaoWenxin_C2A_proposal_v1.md`。
- **迭代次数：3 轮（v1 → v2 定稿）。**
  - **第 1 轮（补人类基线）：** v1 的人类基线一节只有定性描述，缺少"被试量、每人题目数、检验力"这类可执行数字。要求补出 N=30 的采集方案与基于 SD(ΔE)≈0.15 的检验力估算。
  - **第 2 轮（补负控制与噪声下限）：** 我提出一个关键质疑——"只报 ΔE 或 ECE 是不是可以被骗？" 顺着这个质疑，AI 与我一起构造出了 **P6 BiasCorrected 负控制**（只做一次常量平移就能把 ECE 与 ΔE 压到接近 0，而分辨力指标不动），并把 **SMA 噪声下限**写进指标套件。这两点是 v2 相比 v1 最重要的方法学增量。
  - **第 3 轮（补真实示例 + 信息量约束）：** v1 里的题目示例是我手写的占位符。要求用**参考实现真实生成**的题目替换（最终用 seed=20261231 的 `rule_induce` 难度 3 题），并如实写出开发中踩到的 `SWAP_END` 退化坑与拒绝采样约束。
- **人工修改 / 人工判断：**
  - **赛道定位的搬迁**（从"测有没有"到"测能不能写出并迁移"）是我基于调研结果做的判断，不是 AI 提出的。
  - **三个控制项的取舍**：决定保留 P3 PopDifficulty（用来证伪）、加 P6 负控制、把"伪装区块"从相关性检验升级为**符号检验**——这三条是概念层面的设计决策。
  - **结论边界的撰写**：明确写出"现有数字来自模拟求解器，不是真实模型"这一诚实边界，是我坚持加的。

---

## 4. 手动步骤说明 / Manual Steps Justification

| 手动步骤 | 为什么这一步没有（或不能完全）交给 AI |
|---|---|
| 选择"闭环自我模型"而非"再做一个校准基准" | 这是对**研究拥挤度**的判断：需要知道 2026 年这条线已经有多少人在做。AI 能给出候选文献，但"要不要换命题"是价值判断 |
| 决定加入 P6 负控制与 SMA 噪声下限 | 源于我对"单一指标是否可被平凡策略击败"的怀疑。AI 最初只按常规报了 ECE/ΔE，是**人的质疑**逼出了这条设计 |
| 把关"人类基线必须让正确率落在 20%–80%" | 来自 Lichtenstein & Fischhoff 的硬-易效应与个人对"地板/天花板效应"的经验判断，属于把文献规律翻译成设计约束 |
| 结论边界的最终措辞 | 涉及"哪些能说、哪些不能说"的学术诚实，必须由人拍板 |
| 题目示例替换为真实生成结果 | 需要实际运行参考实现并核对输出，属工程事实核对，不能靠生成 |

---

## 5. AI 段位自评 / AI Usage Level

**🔵 进阶** — 多轮对话迭代优化 prompt，审阅并修正 AI 输出，主动设计 workflow（先检索→再定命题→再分阶段写作）。

核心判断（把命题从"测有没有元认知"挪到"测自我模型能否写出/维持/迁移/使用"）是**人机协同**产生的：AI 提供了文献事实与候选方向，人做出了"哪里已经有太多人、哪里还有空白"的判断。提案不是纯 AI 生成，也不是纯人工——这一点在 v2 与 v1 的差异里可以直接看出来。
