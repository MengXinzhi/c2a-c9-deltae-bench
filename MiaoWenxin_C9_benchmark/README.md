# ΔE-Bench — Metacognitive Self-Model Benchmark

**Track 2 / Metacognition** · 闭环节点式基准：测量一个智能体能否**建立、维持、迁移并真正使用**关于自身能力边界的显式自我模型。

题目的正确答案由生成器自身产出（精确匹配判分，无需 LLM 裁判）；每个规则实例由运行种子现场采样，因此题目表面**不可能存在于任何训练语料**中。

---

## 1. 快速开始

### 1.1 环境

**零第三方依赖。** 只需要 Python 3.10+（开发与验证使用 3.13）。

```bash
python run_benchmark.py                 # 完整参考运行（约 1 秒）
python run_benchmark.py --seed 7        # 换种子
python run_benchmark.py --models SolverA,SolverB
```

输出写入 `results/`：`results.json`（全量指标）、`results.md`（Markdown 表）、
`report.html`（自包含页面，内嵌 SVG 图）、`figures/*.svg`。

### 1.2 跑测试

```bash
python tests/test_metrics.py     # 10 项：指标是否按理论行为工作
python tests/test_items.py       #  9 项：题目参照答案是否正确（独立重算）+ 信息量
python tests/test_pipeline.py    #  7 项：协议的设计断言是否成立
```

也可以 `python -m pytest tests -q`（pytest 可选，不是依赖）。

全部 26 项应为绿色。这些测试不是冒烟测试——它们各自断言一条**设计属性**，例如
"常量预测器 ECE 必须为 0 但 Brier 必须变差"、"自我真值预测器必须饱和到 AUROC>0.99"、
"文本线索读者在表面伪装下必须比自我模型损失更多分辨力"。

### 1.3 接入真实模型

本仓库**未接入真实前沿模型**（提交时无 API 凭据）。接入方式：

```bash
export DELTABENCH_BASE_URL=https://api.example.com/v1
export DELTABENCH_MODEL=<model-id>
export DELTABENCH_API_KEY=<key>

python -c "
import sys; sys.path.insert(0,'src')
from deltabench.adapters import from_env, OpenAIMetaPredictor, OpenAIBetPredictor
client = from_env()
verbal  = OpenAIMetaPredictor(client)   # 作答前先预测自己答对的概率
bet     = OpenAIBetPredictor(client)    # 第二通道：为本题下注 1..10 分
print('configured:', client.model)
"
```

`adapters.py` 是唯一触网模块，协议代码无需改动。

> ⚠️ **诚实边界**：`results/` 中所有数字来自 6 个**模拟求解器**，不是真实模型。
> 它们验证的是**仪器**（能否区分、控制项是否按设计行为），不是关于任何真实模型的结论。
> 详见 `../MiaoWenxin_C9_测试结果.md`。

---

## 2. 协议：六区块闭环

每个求解器跑一遍，得到一条完整的学习轨迹：

| 区块 | 名称 | 做什么 | 关键产出 |
|---|---|---|---|
| **B0** | 能力探针 | 智能体在 5 个技能族 × 3 个难度档上作答，**不看预测** | 自身结果台账（自我观察的唯一来源） |
| **B1** | 冷启动自预测 | 新题，作答前先给 `P(我答对)` | ΔE₀、AUROC₀（无自我历史） |
| **B2** | 自我模型撰写 | 给它**原始台账**，要求产出一份**显式自我模型**（每单元格的成功概率） | SMA：在**留出单元格**上评分 |
| **B3** | 热启动自预测 | 新题 + 可用的自我模型 | ΔE₁、AUROC₁、Brier₁ |
| **B4** | 表面伪装探针 | 线索与真实难度**反向**的题目 | 分辨力损失 = 自我知识 vs 难度刻板印象 |
| **B5** | 预算控制 | 从题池中挑 25% 作答 | 控制效用 CU（能否用自我模型改善**决策**） |
| **B6** | 未见技能探针 | 一个**从未见过**的技能族 | 自我模型能否外推到新技能 |

**KSTAR 映射**：B0 = 执行 A 并观察 R；B2 = 由 ΔR 更新 K，并把它**写下来**；
B3/B5 = 用更新后的 K 改变下一轮行为；B6 = 检验更新后的 K 是否泛化。
指标 ΔE = KSTAR 中的认知偏差（预测成功概率 − 实际成功率）。

---

## 3. 三条设计决策（决定了这个基准能不能测到该测的东西）

### 3.1 目标值是**模型特异**的，所以不可从语料查得

真实正确性由求解器实际解出的答案决定（`solvers.py`），不是声明的概率。
`SolverA` 强于算术、弱于规则归纳；`SolverB` 完全相反。
因此"我会不会做对这道题"的答案**只存在于这个模型的运行历史里**——
任何外部世界知识（含"这道题看起来难不难"）都无法给出它。
这是 Track 1 的"程序性生成保证新颖"手法，移植到元认知：**不可查的不是题目，而是你自己。**

### 3.2 用"客观难度"做控制项，用来证伪

`P3 PopDifficulty` 知道每道题的**规范难度**，但不知道自己的特异弱点。
它存在的意义是：**如果它能赢，这个基准测的就是难度感知，不是元认知。**
实测（模拟）：对 `SolverB` 它只有 AUROC 0.634，而 B 自己的内在信号有 0.780；
对 `SolverC` 反过来——它 0.816 高于内在信号 0.746。
**哪个赢是模型特异的**，这正说明目标不可被单一外部评分替代。

### 3.3 表面伪装 = 构造效度的符号检验

同一批单元格，B4 让**表面线索与真实难度反向**（易题套长而花哨的无关前言，难题保持简朴）。
- 读**渲染文本**的预测器（`P2`）：AUROC 掉 0.38–0.75，Brier 与 ECE 大约翻倍。
- 读**任务身份**的预测器（`P3`/`P7`）：几乎不动。

这是一个**有符号的判别检验**，而不是又一个相关系数。

---

## 4. 指标套件（以及为什么不能只看 ECE）

| 指标 | 作用 | 能骗过它的策略 |
|---|---|---|
| `ΔE` | 平均带符号偏差（KSTAR） | 任何平移修正 |
| `ECE` | 分箱校准误差 | **常量预测器**（ECE=0，零信息） |
| `Brier` | proper scoring rule | 无法欺骗 |
| `Murphy 分解` | Brier = 可靠性 − 分辨力 + 不确定性 | — |
| `AUROC` | 置信度能否给自己的对错排序 | 单调变换 |
| `cue-residual AUROC` | 扣掉表面线索模型解释后的分辨力 | — |
| `SMA` | 撰写的自我模型在**留出单元格**上的 MAE | — |
| `CU` | 预算受限下的选择质量（0=无用，1=等同预言机） | — |
| `MEG` | 言语通道与行为通道的 Brier 差 | — |

`P6 BiasCorrected` 是这套指标的**负控制**：它只从一个常量平移就能把 ECE 与 ΔE 压到接近 0，
而 AUROC / Brier / CU 基本不动。**任何用 ECE 或 ΔE 单独排名次的设计，都会输给这个预测器。**
（实测见 `results/results.md` 第 2b 节。）

---

## 5. 防作弊与效度（设计要点）

| 风险 | 应对 |
|---|---|
| 训练数据污染 | 规则实例按种子现场采样；题目字符串程序化生成 |
| 记忆台账 | 自我模型只在**留出单元格/新题**上评分 |
| 用常识难度冒充自知 | `P3` 控制项 + 伪装区块的符号检验 |
| 用"永远 50%"刷 ECE | proper scoring rule（Brier）+ 基线常数预测器对照 |
| 用输出位置/标签捷径 | 精确匹配字符串，无选项位置 |
| 用 LLM 裁判引入噪声 | 全部题目自带确定性参照答案，**不调用任何模型判分** |
| 有限样本被当成真实差距 | 报告 `sma_noise_floor`（即使完美估计量也要付的 MAE） |

参照答案的**正确性本身**也在测试范围内：`tests/test_items.py` 重新解析渲染后的题干、
独立重算答案；对 `rule_induce` 更进一步——暴力枚举所有算符组合，
验证参照答案**可由给出的三个示例推出**。

---

## 6. 目录结构

```
MiaoWenxin_C9_benchmark/
├── run_benchmark.py              单入口
├── README.md                     本文件
├── src/deltabench/
│   ├── items.py                  6 个技能族 × 5 难度档的题目生成器
│   ├── solvers.py                模拟能力求解器（模型特异的强弱画像）
│   ├── metacog.py                元认知预测器 + 自我模型撰写器
│   ├── metrics.py                ΔE/ECE/Brier/Murphy/AUROC/残差AUROC/SMA/CU/bootstrap
│   ├── runner.py                 六区块协议编排
│   ├── report.py                 Markdown 表 + 手绘 SVG + HTML 报告
│   └── adapters.py               真实模型接入（唯一触网模块）
├── tests/                        26 项断言，验证设计属性而非冒烟
└── results/                      参考运行产物
```

---

## 7. 已知局限（请一并阅读）

1. **结果来自模拟求解器，不是真实模型。** 本仓库证明仪器可用，不证明关于 LLM 的任何结论。
2. **模拟的自我模型享有"任务身份"把手**（按 `(family, level)` 索引），而真实纯文本模型没有。
   所以 B4 中 `P7` 的稳健性是**该模拟建制的性质**，不能直接推论到真实模型。
3. **cue-residual AUROC 在伪装区块内不可与正常区块比较**：线索模型的符号被翻转过，
   连常量预测器都会获得虚假的残差信号。伪装区块请看 AUROC 与 Brier。
4. **行为通道（下注）去偏系数是从探针区块拟合的单一 logit 平移**，是一个显式建模假设。
   真实运行应**直接测量**两个通道（`adapters.py` 已提供）。
5. **`MEG` 在本模拟中接近 0**（4/5 求解器），是弱结果；该构念需要真实双通道数据才有信息量。
6. **技能族只有 6 个、难度档 5 级**，分辨率有限；真实使用应扩表。

---

## 8. 复现

```bash
python run_benchmark.py --seed 20261231
```

同一 config + seed 的输出**逐字节一致**（`tests/test_pipeline.py::test_determinism_same_seed_same_result` 覆盖）。
