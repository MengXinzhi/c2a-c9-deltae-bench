# DeltaE-Bench reference run

Seed `20261231` | probe 8 items/cell | eval 6 items/cell | truth sample 40 items/cell

> **Scope.** These numbers come from six *simulated* solvers, not from a frontier model. They validate the instrument (that it discriminates, and that the control predictors behave as the design predicts). Plug a real model in via `deltabench.adapters` to obtain real results.

## 1. Ability profiles (the 'objective self')

| Solver | probe acc | unseen-family acc | per-family probe acc |
|---|---|---|---|
| SolverA(arith-leaning) | 0.625 | 0.775 | arith=0.79, code=0.71, logic=0.62, rule=0.46, symbol=0.54 |
| SolverB(pattern-leaning) | 0.692 | 0.480 | arith=0.46, code=0.79, logic=0.71, rule=0.79, symbol=0.71 |
| SolverC(generalist) | 0.675 | 0.625 | arith=0.75, code=0.67, logic=0.42, rule=0.67, symbol=0.88 |
| SolverD(trace-leaning) | 0.667 | 0.490 | arith=0.58, code=0.83, logic=0.79, rule=0.54, symbol=0.58 |
| SolverE(weak) | 0.375 | 0.370 | arith=0.42, code=0.33, logic=0.42, rule=0.38, symbol=0.33 |

## 2. Headline metrics

| Solver | acc | DeltaE cold | DeltaE warm | AUROC inner | AUROC popdiff | CU cold | CU warm |
|---|---|---|---|---|---|---|---|
| SolverA(arith-leaning) | 0.633 | +0.085 | +0.026 | 0.772 | 0.851 | 0.667 | 0.833 |
| SolverB(pattern-leaning) | 0.644 | +0.038 | +0.084 | 0.759 | 0.654 | 0.500 | 0.500 |
| SolverC(generalist) | 0.589 | +0.110 | +0.135 | 0.668 | 0.771 | 0.333 | 0.444 |
| SolverD(trace-leaning) | 0.622 | +0.125 | +0.085 | 0.728 | 0.716 | 0.571 | 0.714 |
| SolverE(weak) | 0.411 | +0.287 | +0.067 | 0.830 | 0.864 | 0.533 | 0.933 |

*CU = budgeted control utility: 0 = the self-model is worthless for choosing what to attempt, 1 = it selects as well as an oracle.*

## 2b. What a calibration fix does -- and does not -- change

| Solver | ECE | DeltaE | Brier | AUROC | cue-residual AUROC |
|---|---|---|---|---|---|
| SolverA(arith-leaning) | 0.135 -&gt; 0.087 | +0.073 -&gt; +0.023 | 0.192 -&gt; 0.199 | 0.772 -&gt; 0.709 | 0.495 -&gt; 0.425 |
| SolverB(pattern-leaning) | 0.127 -&gt; 0.129 | +0.063 -&gt; +0.032 | 0.190 -&gt; 0.206 | 0.759 -&gt; 0.664 | 0.581 -&gt; 0.482 |
| SolverC(generalist) | 0.178 -&gt; 0.163 | +0.094 -&gt; +0.081 | 0.225 -&gt; 0.233 | 0.668 -&gt; 0.657 | 0.447 -&gt; 0.426 |
| SolverD(trace-leaning) | 0.114 -&gt; 0.133 | +0.065 -&gt; +0.022 | 0.214 -&gt; 0.197 | 0.728 -&gt; 0.735 | 0.397 -&gt; 0.373 |
| SolverE(weak) | 0.254 -&gt; 0.186 | +0.246 -&gt; -0.024 | 0.238 -&gt; 0.234 | 0.830 -&gt; 0.651 | 0.398 -&gt; 0.217 |

`P6` subtracts, from every prediction, a constant estimated on the agent's own probe block. That is an ordinary self-calibration step. It collapses ECE and DeltaE -- the two metrics most often quoted -- while resolution metrics barely move. **A benchmark that ranks on ECE or DeltaE alone can be defeated by this predictor without any improvement in metacognition.**

For reference, the predictors are: `P0` constant 0.5; `P1` the run's marginal accuracy; `P2` a logistic model over surface text features; `P3` the normative item difficulty with no self-access; `P4` the agent's intrinsic pre-answer signal; `P5` a logit-space blend of that signal with the authored self-model; `P6` `P4` after a self-calibration shift; `P7` the authored self-model alone; `P9` an oracle ceiling. Block B1 contains only predictors that need no self-history.

## 3. Block B1 -- cold self-prediction (no self-history)

**SolverA(arith-leaning)**

| Predictor | DeltaE | ECE | Brier | AUROC | cue-residual AUROC |
|---|---|---|---|---|---|
| P0 Null (always 0.5) | -0.078 | 0.078 | 0.250 | 0.500 | 0.174 |
| P1 BaseRate (marginal) | 0.047 | 0.047 | 0.246 | 0.500 | 0.174 |
| P2 CueOnly (stereotype) | 0.042 | 0.164 | 0.182 | 0.826 | 0.500 |
| P3 PopDifficulty (no self) | -0.153 | 0.177 | 0.192 | 0.834 | 0.731 |
| P4 InnerSignal(cold) | 0.085 | 0.144 | 0.202 | 0.770 | 0.563 |
| P6 BiasCorrected(inner) | 0.067 | 0.097 | 0.196 | 0.774 | 0.478 |
| P9 SelfOracle (ceiling) | -0.005 | 0.030 | 0.001 | 1.000 | 1.000 |

**SolverB(pattern-leaning)**

| Predictor | DeltaE | ECE | Brier | AUROC | cue-residual AUROC |
|---|---|---|---|---|---|
| P0 Null (always 0.5) | -0.189 | 0.189 | 0.250 | 0.500 | 0.195 |
| P1 BaseRate (marginal) | 0.003 | 0.003 | 0.214 | 0.500 | 0.195 |
| P2 CueOnly (stereotype) | -0.002 | 0.080 | 0.170 | 0.805 | 0.500 |
| P3 PopDifficulty (no self) | -0.264 | 0.313 | 0.296 | 0.652 | 0.487 |
| P4 InnerSignal(cold) | 0.038 | 0.126 | 0.180 | 0.753 | 0.521 |
| P6 BiasCorrected(inner) | -0.007 | 0.131 | 0.174 | 0.762 | 0.517 |
| P9 SelfOracle (ceiling) | -0.011 | 0.030 | 0.001 | 1.000 | 1.000 |

**SolverC(generalist)**

| Predictor | DeltaE | ECE | Brier | AUROC | cue-residual AUROC |
|---|---|---|---|---|---|
| P0 Null (always 0.5) | -0.111 | 0.111 | 0.250 | 0.500 | 0.167 |
| P1 BaseRate (marginal) | 0.064 | 0.064 | 0.242 | 0.500 | 0.167 |
| P2 CueOnly (stereotype) | 0.054 | 0.156 | 0.181 | 0.833 | 0.500 |
| P3 PopDifficulty (no self) | -0.186 | 0.216 | 0.191 | 0.848 | 0.731 |
| P4 InnerSignal(cold) | 0.110 | 0.148 | 0.213 | 0.743 | 0.523 |
| P6 BiasCorrected(inner) | 0.016 | 0.185 | 0.128 | 0.923 | 0.701 |
| P9 SelfOracle (ceiling) | -0.007 | 0.030 | 0.001 | 1.000 | 1.000 |

**SolverD(trace-leaning)**

| Predictor | DeltaE | ECE | Brier | AUROC | cue-residual AUROC |
|---|---|---|---|---|---|
| P0 Null (always 0.5) | -0.089 | 0.089 | 0.250 | 0.500 | 0.228 |
| P1 BaseRate (marginal) | 0.078 | 0.078 | 0.248 | 0.500 | 0.228 |
| P2 CueOnly (stereotype) | 0.074 | 0.122 | 0.191 | 0.772 | 0.500 |
| P3 PopDifficulty (no self) | -0.164 | 0.273 | 0.261 | 0.677 | 0.522 |
| P4 InnerSignal(cold) | 0.125 | 0.125 | 0.201 | 0.786 | 0.522 |
| P6 BiasCorrected(inner) | 0.046 | 0.097 | 0.181 | 0.810 | 0.520 |
| P9 SelfOracle (ceiling) | -0.005 | 0.030 | 0.001 | 1.000 | 1.000 |

**SolverE(weak)**

| Predictor | DeltaE | ECE | Brier | AUROC | cue-residual AUROC |
|---|---|---|---|---|---|
| P0 Null (always 0.5) | 0.111 | 0.111 | 0.250 | 0.500 | 0.074 |
| P1 BaseRate (marginal) | -0.014 | 0.014 | 0.238 | 0.500 | 0.074 |
| P2 CueOnly (stereotype) | -0.014 | 0.144 | 0.122 | 0.926 | 0.500 |
| P3 PopDifficulty (no self) | 0.036 | 0.153 | 0.159 | 0.840 | 0.489 |
| P4 InnerSignal(cold) | 0.287 | 0.293 | 0.299 | 0.677 | 0.262 |
| P6 BiasCorrected(inner) | -0.009 | 0.125 | 0.207 | 0.709 | 0.283 |
| P9 SelfOracle (ceiling) | 0.007 | 0.030 | 0.001 | 1.000 | 1.000 |

## 4. Block B3 -- warm self-prediction (authored self-model available)

**SolverA(arith-leaning)**

| Predictor | DeltaE | ECE | Brier | AUROC | cue-residual AUROC |
|---|---|---|---|---|---|
| P0 Null (always 0.5) | -0.133 | 0.133 | 0.250 | 0.500 | 0.169 |
| P1 BaseRate (marginal) | -0.008 | 0.008 | 0.232 | 0.500 | 0.169 |
| P2 CueOnly (stereotype) | -0.016 | 0.144 | 0.168 | 0.831 | 0.500 |
| P3 PopDifficulty (no self) | -0.208 | 0.216 | 0.198 | 0.851 | 0.757 |
| P4 InnerSignal(cold) | 0.073 | 0.135 | 0.192 | 0.772 | 0.495 |
| P5 KSTAR-blend(w=0.25) | 0.050 | 0.140 | 0.172 | 0.830 | 0.531 |
| P5 KSTAR-blend(w=0.50) | 0.026 | 0.174 | 0.138 | 0.929 | 0.709 |
| P5 KSTAR-blend(w=0.75) | 0.021 | 0.146 | 0.127 | 0.913 | 0.836 |
| P6 BiasCorrected(inner) | 0.023 | 0.087 | 0.199 | 0.709 | 0.425 |
| P7 SelfModelOnly | -0.008 | 0.087 | 0.134 | 0.876 | 0.824 |
| P9 SelfOracle (ceiling) | -0.008 | 0.030 | 0.001 | 1.000 | 1.000 |

**SolverB(pattern-leaning)**

| Predictor | DeltaE | ECE | Brier | AUROC | cue-residual AUROC |
|---|---|---|---|---|---|
| P0 Null (always 0.5) | -0.144 | 0.144 | 0.250 | 0.500 | 0.252 |
| P1 BaseRate (marginal) | 0.047 | 0.047 | 0.231 | 0.500 | 0.252 |
| P2 CueOnly (stereotype) | 0.037 | 0.100 | 0.196 | 0.748 | 0.500 |
| P3 PopDifficulty (no self) | -0.219 | 0.313 | 0.285 | 0.654 | 0.553 |
| P4 InnerSignal(cold) | 0.063 | 0.127 | 0.190 | 0.759 | 0.581 |
| P5 KSTAR-blend(w=0.25) | 0.067 | 0.183 | 0.190 | 0.726 | 0.562 |
| P5 KSTAR-blend(w=0.50) | 0.084 | 0.109 | 0.195 | 0.723 | 0.601 |
| P5 KSTAR-blend(w=0.75) | 0.059 | 0.180 | 0.186 | 0.728 | 0.671 |
| P6 BiasCorrected(inner) | 0.032 | 0.129 | 0.206 | 0.664 | 0.482 |
| P7 SelfModelOnly | 0.047 | 0.172 | 0.209 | 0.662 | 0.622 |
| P9 SelfOracle (ceiling) | -0.009 | 0.030 | 0.001 | 1.000 | 1.000 |

**SolverC(generalist)**

| Predictor | DeltaE | ECE | Brier | AUROC | cue-residual AUROC |
|---|---|---|---|---|---|
| P0 Null (always 0.5) | -0.089 | 0.089 | 0.250 | 0.500 | 0.202 |
| P1 BaseRate (marginal) | 0.086 | 0.086 | 0.250 | 0.500 | 0.202 |
| P2 CueOnly (stereotype) | 0.070 | 0.111 | 0.190 | 0.798 | 0.500 |
| P3 PopDifficulty (no self) | -0.164 | 0.206 | 0.224 | 0.771 | 0.646 |
| P4 InnerSignal(cold) | 0.094 | 0.178 | 0.225 | 0.668 | 0.447 |
| P5 KSTAR-blend(w=0.25) | 0.154 | 0.182 | 0.206 | 0.836 | 0.573 |
| P5 KSTAR-blend(w=0.50) | 0.135 | 0.161 | 0.196 | 0.818 | 0.614 |
| P5 KSTAR-blend(w=0.75) | 0.102 | 0.153 | 0.192 | 0.797 | 0.682 |
| P6 BiasCorrected(inner) | 0.081 | 0.163 | 0.233 | 0.657 | 0.426 |
| P7 SelfModelOnly | 0.086 | 0.135 | 0.197 | 0.763 | 0.696 |
| P9 SelfOracle (ceiling) | -0.005 | 0.030 | 0.001 | 1.000 | 1.000 |

**SolverD(trace-leaning)**

| Predictor | DeltaE | ECE | Brier | AUROC | cue-residual AUROC |
|---|---|---|---|---|---|
| P0 Null (always 0.5) | -0.122 | 0.122 | 0.250 | 0.500 | 0.134 |
| P1 BaseRate (marginal) | 0.044 | 0.044 | 0.237 | 0.500 | 0.134 |
| P2 CueOnly (stereotype) | 0.038 | 0.140 | 0.156 | 0.866 | 0.500 |
| P3 PopDifficulty (no self) | -0.197 | 0.269 | 0.250 | 0.716 | 0.528 |
| P4 InnerSignal(cold) | 0.065 | 0.114 | 0.214 | 0.728 | 0.397 |
| P5 KSTAR-blend(w=0.25) | 0.077 | 0.102 | 0.171 | 0.831 | 0.498 |
| P5 KSTAR-blend(w=0.50) | 0.085 | 0.131 | 0.145 | 0.907 | 0.645 |
| P5 KSTAR-blend(w=0.75) | 0.055 | 0.121 | 0.139 | 0.882 | 0.778 |
| P6 BiasCorrected(inner) | 0.022 | 0.133 | 0.197 | 0.735 | 0.373 |
| P7 SelfModelOnly | 0.044 | 0.108 | 0.140 | 0.872 | 0.801 |
| P9 SelfOracle (ceiling) | -0.007 | 0.030 | 0.001 | 1.000 | 1.000 |

**SolverE(weak)**

| Predictor | DeltaE | ECE | Brier | AUROC | cue-residual AUROC |
|---|---|---|---|---|---|
| P0 Null (always 0.5) | 0.089 | 0.089 | 0.250 | 0.500 | 0.097 |
| P1 BaseRate (marginal) | -0.036 | 0.036 | 0.243 | 0.500 | 0.097 |
| P2 CueOnly (stereotype) | -0.041 | 0.135 | 0.132 | 0.903 | 0.500 |
| P3 PopDifficulty (no self) | 0.014 | 0.162 | 0.153 | 0.864 | 0.520 |
| P4 InnerSignal(cold) | 0.246 | 0.254 | 0.238 | 0.830 | 0.398 |
| P5 KSTAR-blend(w=0.25) | 0.182 | 0.205 | 0.188 | 0.876 | 0.406 |
| P5 KSTAR-blend(w=0.50) | 0.067 | 0.177 | 0.119 | 0.925 | 0.575 |
| P5 KSTAR-blend(w=0.75) | 0.012 | 0.127 | 0.127 | 0.877 | 0.677 |
| P6 BiasCorrected(inner) | -0.024 | 0.186 | 0.234 | 0.651 | 0.217 |
| P7 SelfModelOnly | -0.036 | 0.085 | 0.130 | 0.850 | 0.783 |
| P9 SelfOracle (ceiling) | 0.005 | 0.030 | 0.001 | 1.000 | 1.000 |

## 5. Block B4 -- surface disguise (cue/difficulty inverted)

**SolverA(arith-leaning)**

| Predictor | DeltaE | ECE | Brier | AUROC | cue-residual AUROC |
|---|---|---|---|---|---|
| P0 Null (always 0.5) | -0.122 | 0.122 | 0.250 | 0.500 | 0.795 |
| P1 BaseRate (marginal) | 0.003 | 0.003 | 0.235 | 0.500 | 0.795 |
| P2 CueOnly (stereotype) | -0.004 | 0.419 | 0.348 | 0.205 | 0.500 |
| P3 PopDifficulty (no self) | -0.197 | 0.214 | 0.191 | 0.861 | 0.853 |
| P4 InnerSignal(cold) | 0.041 | 0.159 | 0.194 | 0.752 | 0.843 |
| P5 KSTAR-blend(w=0.25) | 0.056 | 0.153 | 0.163 | 0.877 | 0.890 |
| P5 KSTAR-blend(w=0.50) | 0.058 | 0.179 | 0.145 | 0.924 | 0.913 |
| P5 KSTAR-blend(w=0.75) | 0.019 | 0.148 | 0.127 | 0.931 | 0.917 |
| P6 BiasCorrected(inner) | 0.010 | 0.088 | 0.173 | 0.815 | 0.870 |
| P7 SelfModelOnly | 0.003 | 0.115 | 0.134 | 0.900 | 0.899 |
| P9 SelfOracle (ceiling) | -0.007 | 0.030 | 0.001 | 1.000 | 1.000 |

**SolverB(pattern-leaning)**

| Predictor | DeltaE | ECE | Brier | AUROC | cue-residual AUROC |
|---|---|---|---|---|---|
| P0 Null (always 0.5) | -0.178 | 0.178 | 0.250 | 0.500 | 0.650 |
| P1 BaseRate (marginal) | 0.014 | 0.014 | 0.219 | 0.500 | 0.650 |
| P2 CueOnly (stereotype) | 0.019 | 0.292 | 0.267 | 0.350 | 0.500 |
| P3 PopDifficulty (no self) | -0.253 | 0.281 | 0.304 | 0.622 | 0.650 |
| P4 InnerSignal(cold) | 0.037 | 0.118 | 0.148 | 0.864 | 0.903 |
| P5 KSTAR-blend(w=0.25) | 0.029 | 0.125 | 0.151 | 0.869 | 0.840 |
| P5 KSTAR-blend(w=0.50) | 0.025 | 0.152 | 0.157 | 0.810 | 0.790 |
| P5 KSTAR-blend(w=0.75) | 0.023 | 0.131 | 0.161 | 0.771 | 0.769 |
| P6 BiasCorrected(inner) | -0.012 | 0.094 | 0.175 | 0.734 | 0.798 |
| P7 SelfModelOnly | 0.014 | 0.131 | 0.175 | 0.726 | 0.728 |
| P9 SelfOracle (ceiling) | -0.011 | 0.030 | 0.001 | 1.000 | 1.000 |

**SolverC(generalist)**

| Predictor | DeltaE | ECE | Brier | AUROC | cue-residual AUROC |
|---|---|---|---|---|---|
| P0 Null (always 0.5) | -0.011 | 0.011 | 0.250 | 0.500 | 0.759 |
| P1 BaseRate (marginal) | 0.164 | 0.164 | 0.277 | 0.500 | 0.759 |
| P2 CueOnly (stereotype) | 0.160 | 0.318 | 0.347 | 0.241 | 0.500 |
| P3 PopDifficulty (no self) | -0.086 | 0.141 | 0.212 | 0.752 | 0.770 |
| P4 InnerSignal(cold) | 0.164 | 0.215 | 0.229 | 0.750 | 0.817 |
| P5 KSTAR-blend(w=0.25) | 0.184 | 0.198 | 0.235 | 0.772 | 0.838 |
| P5 KSTAR-blend(w=0.50) | 0.163 | 0.184 | 0.218 | 0.809 | 0.845 |
| P5 KSTAR-blend(w=0.75) | 0.174 | 0.207 | 0.228 | 0.795 | 0.840 |
| P6 BiasCorrected(inner) | 0.146 | 0.160 | 0.214 | 0.789 | 0.848 |
| P7 SelfModelOnly | 0.164 | 0.225 | 0.256 | 0.708 | 0.787 |
| P9 SelfOracle (ceiling) | -0.001 | 0.030 | 0.001 | 1.000 | 1.000 |

**SolverD(trace-leaning)**

| Predictor | DeltaE | ECE | Brier | AUROC | cue-residual AUROC |
|---|---|---|---|---|---|
| P0 Null (always 0.5) | -0.156 | 0.156 | 0.250 | 0.500 | 0.651 |
| P1 BaseRate (marginal) | 0.011 | 0.011 | 0.226 | 0.500 | 0.651 |
| P2 CueOnly (stereotype) | 0.007 | 0.326 | 0.305 | 0.349 | 0.500 |
| P3 PopDifficulty (no self) | -0.231 | 0.262 | 0.263 | 0.705 | 0.723 |
| P4 InnerSignal(cold) | 0.054 | 0.113 | 0.192 | 0.722 | 0.762 |
| P5 KSTAR-blend(w=0.25) | 0.047 | 0.111 | 0.164 | 0.831 | 0.790 |
| P5 KSTAR-blend(w=0.50) | 0.048 | 0.157 | 0.138 | 0.909 | 0.821 |
| P5 KSTAR-blend(w=0.75) | 0.027 | 0.074 | 0.141 | 0.856 | 0.796 |
| P6 BiasCorrected(inner) | 0.015 | 0.077 | 0.186 | 0.741 | 0.744 |
| P7 SelfModelOnly | 0.011 | 0.098 | 0.136 | 0.858 | 0.802 |
| P9 SelfOracle (ceiling) | -0.009 | 0.030 | 0.001 | 1.000 | 1.000 |

**SolverE(weak)**

| Predictor | DeltaE | ECE | Brier | AUROC | cue-residual AUROC |
|---|---|---|---|---|---|
| P0 Null (always 0.5) | 0.100 | 0.100 | 0.250 | 0.500 | 0.893 |
| P1 BaseRate (marginal) | -0.025 | 0.025 | 0.241 | 0.500 | 0.893 |
| P2 CueOnly (stereotype) | -0.027 | 0.497 | 0.448 | 0.107 | 0.500 |
| P3 PopDifficulty (no self) | 0.025 | 0.137 | 0.157 | 0.843 | 0.899 |
| P4 InnerSignal(cold) | 0.251 | 0.255 | 0.260 | 0.739 | 0.936 |
| P5 KSTAR-blend(w=0.25) | 0.164 | 0.205 | 0.164 | 0.905 | 0.940 |
| P5 KSTAR-blend(w=0.50) | 0.094 | 0.186 | 0.121 | 0.930 | 0.935 |
| P5 KSTAR-blend(w=0.75) | 0.028 | 0.099 | 0.114 | 0.907 | 0.909 |
| P6 BiasCorrected(inner) | 0.022 | 0.057 | 0.195 | 0.763 | 0.939 |
| P7 SelfModelOnly | -0.025 | 0.062 | 0.117 | 0.872 | 0.897 |
| P9 SelfOracle (ceiling) | 0.006 | 0.030 | 0.001 | 1.000 | 1.000 |

## 6. Block B6 -- unseen skill family

**SolverA(arith-leaning)**

| Predictor | DeltaE | ECE | Brier | AUROC | cue-residual AUROC |
|---|---|---|---|---|---|
| P0 Null (always 0.5) | -0.300 | 0.300 | 0.250 | 0.500 | 0.569 |
| P1 BaseRate (marginal) | -0.175 | 0.175 | 0.191 | 0.500 | 0.569 |
| P2 CueOnly (stereotype) | -0.148 | 0.168 | 0.201 | 0.431 | 0.500 |
| P3 PopDifficulty (no self) | -0.215 | 0.306 | 0.265 | 0.458 | 0.465 |
| P4 InnerSignal(cold) | -0.090 | 0.142 | 0.135 | 0.826 | 0.833 |
| P5 KSTAR-blend(w=0.25) | -0.090 | 0.169 | 0.152 | 0.778 | 0.722 |
| P5 KSTAR-blend(w=0.50) | -0.136 | 0.175 | 0.152 | 0.792 | 0.694 |
| P5 KSTAR-blend(w=0.75) | -0.136 | 0.223 | 0.172 | 0.674 | 0.639 |
| P6 BiasCorrected(inner) | -0.084 | 0.194 | 0.121 | 0.861 | 0.806 |
| P7 SelfModelOnly | -0.177 | 0.177 | 0.191 | 0.500 | 0.569 |
| P9 SelfOracle (ceiling) | -0.018 | 0.030 | 0.001 | 1.000 | 1.000 |

**SolverB(pattern-leaning)**

| Predictor | DeltaE | ECE | Brier | AUROC | cue-residual AUROC |
|---|---|---|---|---|---|
| P0 Null (always 0.5) | -0.033 | 0.033 | 0.250 | 0.500 | 0.058 |
| P1 BaseRate (marginal) | 0.158 | 0.158 | 0.274 | 0.500 | 0.058 |
| P2 CueOnly (stereotype) | 0.125 | 0.301 | 0.171 | 0.942 | 0.500 |
| P3 PopDifficulty (no self) | 0.052 | 0.198 | 0.124 | 0.955 | 0.946 |
| P4 InnerSignal(cold) | 0.145 | 0.193 | 0.219 | 0.741 | 0.446 |
| P5 KSTAR-blend(w=0.25) | 0.143 | 0.214 | 0.275 | 0.509 | 0.089 |
| P5 KSTAR-blend(w=0.50) | 0.158 | 0.209 | 0.268 | 0.571 | 0.121 |
| P5 KSTAR-blend(w=0.75) | 0.173 | 0.185 | 0.256 | 0.781 | 0.129 |
| P6 BiasCorrected(inner) | 0.117 | 0.244 | 0.196 | 0.808 | 0.487 |
| P7 SelfModelOnly | 0.155 | 0.155 | 0.273 | 0.500 | 0.058 |
| P9 SelfOracle (ceiling) | -0.002 | 0.030 | 0.001 | 1.000 | 1.000 |

**SolverC(generalist)**

| Predictor | DeltaE | ECE | Brier | AUROC | cue-residual AUROC |
|---|---|---|---|---|---|
| P0 Null (always 0.5) | -0.167 | 0.167 | 0.250 | 0.500 | 0.185 |
| P1 BaseRate (marginal) | 0.008 | 0.008 | 0.222 | 0.500 | 0.185 |
| P2 CueOnly (stereotype) | -0.045 | 0.206 | 0.162 | 0.815 | 0.500 |
| P3 PopDifficulty (no self) | -0.082 | 0.150 | 0.174 | 0.800 | 0.545 |
| P4 InnerSignal(cold) | 0.014 | 0.133 | 0.196 | 0.695 | 0.410 |
| P5 KSTAR-blend(w=0.25) | 0.020 | 0.091 | 0.174 | 0.775 | 0.405 |
| P5 KSTAR-blend(w=0.50) | 0.007 | 0.205 | 0.172 | 0.815 | 0.375 |
| P5 KSTAR-blend(w=0.75) | 0.015 | 0.152 | 0.200 | 0.780 | 0.250 |
| P6 BiasCorrected(inner) | 0.002 | 0.167 | 0.217 | 0.625 | 0.335 |
| P7 SelfModelOnly | 0.005 | 0.005 | 0.222 | 0.500 | 0.185 |
| P9 SelfOracle (ceiling) | -0.010 | 0.030 | 0.001 | 1.000 | 1.000 |

**SolverD(trace-leaning)**

| Predictor | DeltaE | ECE | Brier | AUROC | cue-residual AUROC |
|---|---|---|---|---|---|
| P0 Null (always 0.5) | -0.033 | 0.033 | 0.250 | 0.500 | 0.268 |
| P1 BaseRate (marginal) | 0.133 | 0.133 | 0.267 | 0.500 | 0.268 |
| P2 CueOnly (stereotype) | 0.166 | 0.183 | 0.239 | 0.732 | 0.500 |
| P3 PopDifficulty (no self) | 0.052 | 0.164 | 0.134 | 0.929 | 0.853 |
| P4 InnerSignal(cold) | 0.163 | 0.167 | 0.192 | 0.853 | 0.737 |
| P5 KSTAR-blend(w=0.25) | 0.148 | 0.262 | 0.207 | 0.844 | 0.638 |
| P5 KSTAR-blend(w=0.50) | 0.129 | 0.236 | 0.245 | 0.634 | 0.504 |
| P5 KSTAR-blend(w=0.75) | 0.140 | 0.205 | 0.248 | 0.799 | 0.371 |
| P6 BiasCorrected(inner) | 0.096 | 0.244 | 0.218 | 0.746 | 0.531 |
| P7 SelfModelOnly | 0.131 | 0.131 | 0.266 | 0.500 | 0.268 |
| P9 SelfOracle (ceiling) | -0.002 | 0.030 | 0.001 | 1.000 | 1.000 |

**SolverE(weak)**

| Predictor | DeltaE | ECE | Brier | AUROC | cue-residual AUROC |
|---|---|---|---|---|---|
| P0 Null (always 0.5) | 0.100 | 0.100 | 0.250 | 0.500 | 0.153 |
| P1 BaseRate (marginal) | -0.025 | 0.025 | 0.241 | 0.500 | 0.153 |
| P2 CueOnly (stereotype) | -0.041 | 0.204 | 0.164 | 0.847 | 0.500 |
| P3 PopDifficulty (no self) | 0.185 | 0.222 | 0.188 | 0.861 | 0.454 |
| P4 InnerSignal(cold) | 0.234 | 0.277 | 0.225 | 0.829 | 0.505 |
| P5 KSTAR-blend(w=0.25) | 0.211 | 0.218 | 0.236 | 0.792 | 0.310 |
| P5 KSTAR-blend(w=0.50) | 0.144 | 0.185 | 0.232 | 0.727 | 0.222 |
| P5 KSTAR-blend(w=0.75) | 0.071 | 0.193 | 0.217 | 0.838 | 0.204 |
| P6 BiasCorrected(inner) | -0.023 | 0.186 | 0.189 | 0.796 | 0.435 |
| P7 SelfModelOnly | -0.023 | 0.023 | 0.241 | 0.500 | 0.153 |
| P9 SelfOracle (ceiling) | 0.006 | 0.030 | 0.001 | 1.000 | 1.000 |

## 7. Self-model accuracy (SMA) -- is the authored artifact any good?

| Solver | authoring policy | SMA seen cells | SMA interpolated | SMA unseen family | noise floor | Spearman (unseen ladder) |
|---|---|---|---|---|---|---|
| SolverA(arith-leaning) | quality=1.0 | 0.092 | 0.188 | 0.201 | 0.123 | n/a |
| SolverA(arith-leaning) | quality=0.5 | 0.110 | 0.179 | 0.171 | 0.123 | 0.600 |
| SolverA(arith-leaning) | quality=0.0 | 0.200 | 0.221 | 0.190 | 0.123 | 0.600 |
| SolverB(pattern-leaning) | quality=1.0 | 0.118 | 0.142 | 0.268 | 0.113 | n/a |
| SolverB(pattern-leaning) | quality=0.5 | 0.146 | 0.198 | 0.170 | 0.113 | 1.000 |
| SolverB(pattern-leaning) | quality=0.0 | 0.312 | 0.367 | 0.105 | 0.113 | 1.000 |
| SolverC(generalist) | quality=1.0 | 0.176 | 0.215 | 0.169 | 0.118 | n/a |
| SolverC(generalist) | quality=0.5 | 0.135 | 0.164 | 0.068 | 0.118 | 1.000 |
| SolverC(generalist) | quality=0.0 | 0.186 | 0.203 | 0.046 | 0.118 | 1.000 |
| SolverD(trace-leaning) | quality=1.0 | 0.114 | 0.117 | 0.303 | 0.102 | n/a |
| SolverD(trace-leaning) | quality=0.5 | 0.166 | 0.170 | 0.203 | 0.102 | 1.000 |
| SolverD(trace-leaning) | quality=0.0 | 0.280 | 0.283 | 0.117 | 0.102 | 1.000 |
| SolverE(weak) | quality=1.0 | 0.073 | 0.255 | 0.305 | 0.077 | n/a |
| SolverE(weak) | quality=0.5 | 0.077 | 0.181 | 0.233 | 0.077 | 0.975 |
| SolverE(weak) | quality=0.0 | 0.146 | 0.156 | 0.217 | 0.077 | 0.975 |

`quality=1.0` uses only the agent's own outcome history; `quality=0.0` ignores that history and falls back on the normative difficulty prior. **The noise floor is the MAE that even a perfect estimator incurs** because per-cell accuracy is only observable through finitely many trials -- read SMA against it, not against 0. A blank Spearman entry means the authored self-model returned a single constant for that family, so no ordering exists to correlate.

## 8. Surface disguise: does confidence survive inverted cues?

| Solver | Predictor | DeltaE normal | DeltaE disguised | dAUROC | dBrier |
|---|---|---|---|---|---|
| SolverA(arith-leaning) | P2 CueOnly (stereotype) | -0.016 | -0.004 | -0.627 | +0.180 |
| SolverA(arith-leaning) | P3 PopDifficulty (no self) | -0.208 | -0.197 | +0.010 | -0.007 |
| SolverA(arith-leaning) | P4 InnerSignal(cold) | +0.073 | +0.041 | -0.020 | +0.002 |
| SolverA(arith-leaning) | P7 SelfModelOnly | -0.008 | +0.003 | +0.024 | +0.001 |
| SolverA(arith-leaning) | P9 SelfOracle (ceiling) | -0.008 | -0.007 | +0.000 | +0.000 |
| SolverB(pattern-leaning) | P2 CueOnly (stereotype) | +0.037 | +0.019 | -0.398 | +0.071 |
| SolverB(pattern-leaning) | P3 PopDifficulty (no self) | -0.219 | -0.253 | -0.031 | +0.019 |
| SolverB(pattern-leaning) | P4 InnerSignal(cold) | +0.063 | +0.037 | +0.105 | -0.041 |
| SolverB(pattern-leaning) | P7 SelfModelOnly | +0.047 | +0.014 | +0.064 | -0.034 |
| SolverB(pattern-leaning) | P9 SelfOracle (ceiling) | -0.009 | -0.011 | +0.000 | +0.000 |
| SolverC(generalist) | P2 CueOnly (stereotype) | +0.070 | +0.160 | -0.557 | +0.158 |
| SolverC(generalist) | P3 PopDifficulty (no self) | -0.164 | -0.086 | -0.019 | -0.012 |
| SolverC(generalist) | P4 InnerSignal(cold) | +0.094 | +0.164 | +0.082 | +0.004 |
| SolverC(generalist) | P7 SelfModelOnly | +0.086 | +0.164 | -0.056 | +0.060 |
| SolverC(generalist) | P9 SelfOracle (ceiling) | -0.005 | -0.001 | +0.000 | -0.000 |
| SolverD(trace-leaning) | P2 CueOnly (stereotype) | +0.038 | +0.007 | -0.517 | +0.149 |
| SolverD(trace-leaning) | P3 PopDifficulty (no self) | -0.197 | -0.231 | -0.011 | +0.013 |
| SolverD(trace-leaning) | P4 InnerSignal(cold) | +0.065 | +0.054 | -0.006 | -0.022 |
| SolverD(trace-leaning) | P7 SelfModelOnly | +0.044 | +0.011 | -0.014 | -0.004 |
| SolverD(trace-leaning) | P9 SelfOracle (ceiling) | -0.007 | -0.009 | +0.000 | +0.000 |
| SolverE(weak) | P2 CueOnly (stereotype) | -0.041 | -0.027 | -0.796 | +0.315 |
| SolverE(weak) | P3 PopDifficulty (no self) | +0.014 | +0.025 | -0.022 | +0.004 |
| SolverE(weak) | P4 InnerSignal(cold) | +0.246 | +0.251 | -0.091 | +0.022 |
| SolverE(weak) | P7 SelfModelOnly | -0.036 | -0.025 | +0.022 | -0.012 |
| SolverE(weak) | P9 SelfOracle (ceiling) | +0.005 | +0.006 | +0.000 | +0.000 |

A predictor that reads the rendered text loses discrimination when the surface stops predicting difficulty. A predictor keyed on task identity does not. That contrast is the construct validity test for 'self-knowledge' vs 'difficulty stereotyping'.

## 9. Budgeted control -- does self-knowledge change behaviour?

| Solver | CU cold | CU warm | CU self-model only | oracle acc | random acc |
|---|---|---|---|---|---|
| SolverA(arith-leaning) | 0.667 | 0.833 | 0.750 | 1.000 | 0.455 |
| SolverB(pattern-leaning) | 0.500 | 0.500 | 0.333 | 1.000 | 0.727 |
| SolverC(generalist) | 0.333 | 0.444 | 0.444 | 1.000 | 0.591 |
| SolverD(trace-leaning) | 0.571 | 0.714 | 0.429 | 1.000 | 0.682 |
| SolverE(weak) | 0.533 | 0.933 | 0.733 | 1.000 | 0.318 |

## 10. Metacognitive expression gap (verbal vs behavioural channel)

| Solver | Brier verbal | Brier bet channel | gap | DeltaE verbal | DeltaE bet |
|---|---|---|---|---|---|
| SolverA(arith-leaning) | 0.192 | 0.217 | -0.026 | +0.073 | +0.036 |
| SolverB(pattern-leaning) | 0.190 | 0.194 | -0.005 | +0.063 | +0.034 |
| SolverC(generalist) | 0.225 | 0.202 | +0.023 | +0.094 | +0.102 |
| SolverD(trace-leaning) | 0.214 | 0.181 | +0.033 | +0.065 | +0.051 |
| SolverE(weak) | 0.238 | 0.206 | +0.032 | +0.246 | -0.007 |

A positive gap means the stated confidence is displaced further from reality than the signal the agent can act on: it behaves more competently than it can say, i.e. it *knows* more than it can *express*. `debias_fitted` is the single logit shift the agent learned from its own probe block. With a real model both channels are measured directly rather than modelled.
