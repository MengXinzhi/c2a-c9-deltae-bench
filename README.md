# MiaoWenxin — C2A / C9 提交包索引

**作者 / Author:** MiaoWenxin
**挑战 / Challenge:** C2A / C9：衡量 AGI 的认知能力（Elite 20 · DeepMind × Kaggle Benchmark Design）
**赛道 / Track:** Track 2 — Metacognition（元认知）
**日期 / Date:** 2026-10-03

> 一句话：本提交设计并实现 **ΔE-Bench**——一个测量智能体能否**建立、维持、迁移并使用**
> 关于自身能力边界的显式自我模型的**闭环**基准（对应 KSTAR 中 ΔR→K 那段常被跳过的循环）。

---

## 文件清单（对照 `CHALLENGE.md` 的命名规范）

### Phase 1 — C2A 提案

| 规范要求 | 文件 | 说明 |
|---|---|---|
| `姓名_C2A_proposal.md` | **`MiaoWenxin_C2A_proposal.md`** | 提案正文（v2 定稿，四段式 20/40/20/20） |
| （迭代留档） | `MiaoWenxin_C2A_proposal_v1.md` | 初版，用于展示 v1→v2 迭代幅度 |
| `姓名_C2A_AI日志.md` | **`MiaoWenxin_C2A_AI日志.md`** | 论文精读、文献调研、写作过程的 AI 使用记录 |
| `姓名_C2A_拿来说明.md` | **`MiaoWenxin_C2A_拿来说明.md`** | 借鉴来源 + 拿走/去掉/改进 |

### Phase 2 — C9 正式提交

| 规范要求 | 文件 | 说明 |
|---|---|---|
| `姓名_C9_benchmark/` | **`MiaoWenxin_C9_benchmark/`** | 完整代码 + README（零依赖，26 项测试全绿） |
| `姓名_C9_task说明.md` | **`MiaoWenxin_C9_task说明.md`** | 评估任务描述 + 评分标准 |
| `姓名_C9_测试结果.md` | **`MiaoWenxin_C9_测试结果.md`** | 五个求解器的测试数据与四层区分度证据 |
| `姓名_C9_反思报告.md` | **`MiaoWenxin_C9_反思报告.md`** | AAR（目标→实际→差距→改进 + 反向举证） |
| `姓名_C9_AI日志.md` | **`MiaoWenxin_C9_AI日志.md`** | 开发全过程 AI 记录（含 10 个真实 bug 的迭代） |
| `姓名_C9_拿来说明.md` | **`MiaoWenxin_C9_拿来说明.md`** | 代码/方法层面的借鉴与定位对照 |

---

## 三分钟导读（若只想快速判断）

1. **看创新点** → `MiaoWenxin_C2A_proposal.md` §2.3「为什么它能测到元认知，而不是别的东西」
2. **看能不能跑** → `MiaoWenxin_C9_benchmark/README.md` §1「快速开始」，一条命令 1 秒跑完
3. **看有没有区分度** → `MiaoWenxin_C9_测试结果.md` §3「三个关键对照」
4. **看诚不诚实** → `MiaoWenxin_C9_测试结果.md` §0 与 §7「边界」；`MiaoWenxin_C9_benchmark/README.md` §7「已知局限」
5. **看 AI 用得怎么样** → `MiaoWenxin_C9_AI日志.md`「阶段 3：迭代开发与调试」

---

## 核心设计（一段话）

题目由程序按种子现场生成（六技能族 × 五难度档，精确匹配判分，**不调用任何 LLM 裁判**），
因此题目字符串不可能存在于语料。每个智能体跑七区块闭环：B0 能力探针 → B1 冷启动自预测 →
B2 **自己写出**显式自我模型 → B3 热启动自预测 → B4 表面伪装（线索与难度**反向**）→
B5 预算控制 → B6 未见技能。指标含 proper scoring rule（Brier）+ Murphy 分解 + AUROC +
**线索残差 AUROC** + **SMA 噪声下限** + CU + MEG，并**必报六个对照预测器**，
其中 `P3 客观难度` 是**证伪项**、`P6` 是**负控制**。

---

## 复现

```bash
cd MiaoWenxin_C9_benchmark
python run_benchmark.py --seed 20261231
python tests/test_metrics.py && python tests/test_items.py && python tests/test_pipeline.py
```

Python 3.10+，**零第三方依赖**，同种子输出逐字节一致。

---

## 诚实边界（请一并阅读）

`MiaoWenxin_C9_benchmark/results/` 中全部数字来自**模拟求解器**（提交时无 API 凭据），
证明的是**仪器可用**，**不是**关于任何真实 LLM 的结论。真实模型接入方式见
`MiaoWenxin_C9_benchmark/README.md` §1.3。
