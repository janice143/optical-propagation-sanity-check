# 基准测试与故障注入测试套件规范 (Benchmarks & Failure Modes)

本套件用于系统级回归测试与数值稳定性验证。本项目坚持一个核心原则：
> **基准测试不仅要展示算法在良好条件下的正确性，更必须主动制造典型的数值失效模式（Failure Modes），以验证校验体系（Checkers & Diagnostics）是否能如期捕捉风险并报警。**

---

## 1. 三大基准测试场景定义

### Scenario 1: 方孔近场衍射（Square Aperture Benchmark）
* **文件路径**：[`src/propagation_sanity/benchmarks/square_aperture.py`](file:///Users/janicelan/obsidian/opticsMe/numerical-calculation/optical-propagation-sanity-check/src/propagation_sanity/benchmarks/square_aperture.py)
* **物理参数**：
  - 网格尺寸：$N_x = N_y = 512$
  - 空间采样：$\Delta x = \Delta y = 2\,\mu\mathrm{m}$（物理计算窗口 $L = 1.024\,\mathrm{mm}$）
  - 波长：$\lambda = 532\,\mathrm{nm}$
  - 孔径：边长 $a = 100\,\mu\mathrm{m}$（半宽 $w = 50\,\mu\mathrm{m}$）
  - 传播距离：$z \in [1, 10, 100, 150]\,\mathrm{mm}$
* **解析尺度与菲涅耳数**：
  $$N_F = \frac{a^2}{4\lambda z}$$
  - $z=1\,\mathrm{mm}$：极近场，波前由几何投影主导；
  - $z=100\,\mathrm{mm}$：远场过渡，$N_F \approx 0.047$，进入明显衍射扩展区。
* **主动制造的失效模式（Injected Failure Modes）**：
  1. **角谱相位混叠（ASM Phase Aliasing）**：当 $z=100\,\mathrm{mm}$ 且未启用 BLAS（`bandlimit=False`）时，高频传递函数相位震荡过快，产生全图网格状混叠伪影。验证 Matsushima 判定器是否报告 `FAIL`。
  2. **周期卷积环绕（Circular Wrap-around）**：将算法填充设为 `padding=1.0`（无补零），验证衍射扩展波前从对侧边界折回的伪影，检验空间边界诊断器是否告警。

---

### Scenario 2: 自加速光束横向漂移（Self-Accelerating Airy Beam）
* **文件路径**：[`src/propagation_sanity/benchmarks/accelerating_beam.py`](file:///Users/janicelan/obsidian/opticsMe/numerical-calculation/optical-propagation-sanity-check/src/propagation_sanity/benchmarks/accelerating_beam.py)
* **物理特征**：
  - 初始场含立方相位调制：$u(x, 0) = \mathrm{Ai}(x/x_0) \exp(a x/x_0)$。
  - 沿传播方向具有抛物线横向偏转特性：$x_{\rm peak}(z) \propto \lambda^2 z^2 / x_0^3$。
* **主动制造的失效模式**：
  1. **计算窗口逃逸（Window Escape）**：随着传播距离 $z$ 增大，主瓣和振荡尾翼向一侧剧烈偏折，直接切入物理窗口边缘并被截断。验证空间边界能量泄露诊断器（`spatial_boundary_leakage`）是否由 `LOW_RISK` 跃迁为 `HIGH_RISK`。
  2. **非对称频谱截断（Asymmetric Spectral Leakage）**：验证频谱诊断器是否能探测到单侧高频分量逼近 Nyquist 截止频率。

---

### Scenario 3: 可微光学逆设计数值稳定性（Differentiable Optics Suite）
* **文件路径**：[`src/propagation_sanity/benchmarks/diff_optics.py`](file:///Users/janicelan/obsidian/opticsMe/numerical-calculation/optical-propagation-sanity-check/src/propagation_sanity/benchmarks/diff_optics.py)
* **核心对比机制**：
  - **Case A（数值薄弱设置，Numerically Weak Setup）**：
    粗网格采样、无 Guard Band 保护带、高陡度相位突变。逆向梯度优化极易“钻数值漏洞”，收敛到一个利用了离散混叠假象的虚假结构。
  - **Case B（数值完备支撑设置，Numerically Supported Setup）**：
    充分的 Nyquist 采样、频带截断保护（BLAS）、双倍补零填充。优化过程在严格物理收敛的基底上进行。
* **验证目标**：系统报告必须能在 Case A 中报出多重 `DIAGNOSTIC` 警报并判定收敛失败，而在 Case B 中显示全面稳定。

---

## 2. 自动化故障注入（Error Injection）测试原则

在单元与集成测试中，必须遵循以下断言原则：
1. **负向测试（Negative Testing）**：每次引入一个已知致命参数（如 $\Delta x > \lambda z / L$），必须断言对应的判定器输出 `FAIL`，不得漏报。
2. **正向测试（Positive Testing）**：满足理论采样条件时，必须断言输出 `PASS`，且收敛引擎相对误差小于预设 tolerance。
3. **独立性断言**：单个诊断器报错不应引发无关联检测项崩溃，所有检查结果必须完好输出在结构化 JSON 报告中。
