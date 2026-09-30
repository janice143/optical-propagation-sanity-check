# 文献审计与公式溯源规范 (Literature Provenance & Formula Audit)

在波动光学数值算法中，不同教材和文献之间的**符号约定（Sign Convention）**、**傅里叶变换归一化**以及**近似假设条件**存在大量差异。若直接复制代码或拼凑公式，极易引入隐蔽的相位翻转或常数倍率错误。

---

## 1. 核心原始文献库（Primary Literature Registry）

本项目涉及的核心算法和判定准则必须溯源至以下基准文献：

### A. Matsushima & Shimobaba (2009)
* **文献**：Matsushima, K., & Shimobaba, T. (2009). *Band-limited angular spectrum method for numerical simulation of free-space propagation in diffraction and holography.* Optics Express, 17(22), 19662-19673.
* **核心贡献**：带限角谱法（BLAS）。推导了角谱传递函数 $H(f_x, f_y)$ 的局部瞬时空间频率与混叠条件。
* **核心公式（矩形网格截止频宽）**：
  $$f_{x,\max} = \frac{1}{\lambda} \frac{1}{\sqrt{1 + (2 \Delta x z / L_x)^2}}$$
  当空间频率 $|f_x| > f_{x,\max}$ 时，传递函数的离散相位梯度超过 $\pi$ 发生采样混叠，必须执行频带硬截断或平滑窗衰减。

### B. Shen & Wang (2006)
* **文献**：Shen, F., & Wang, A. (2006). *Fast-Fourier-transform based numerical integration method for the Rayleigh-Sommerfeld diffraction formula.* Applied Optics, 45(6), 1102-1110.
* **核心贡献**：FFT-DI 算法。将一阶瑞利-索末菲（Rayleigh-Sommerfeld I）表面积分表示为卷积，并通过离散辛普森求积公式（Simpson's 2D Quadrature Weights）构造离散核，实现 $O(N^2 \log N)$ 复杂度的快速直接积分。

### C. Voelz & Roggemann (2009) & Voelz (2011)
* **文献**：Voelz, D. G. (2011). *Computational Fourier Optics: A MATLAB Tutorial.* SPIE Press.
* **核心贡献**：角谱法（ASM）与单步菲涅耳（Fresnel）的临界采样距离与互补适用区间：
  $$z_{\rm crit} = \frac{L \Delta x}{\lambda} = \frac{N (\Delta x)^2}{\lambda}$$
  - 当 $z < z_{\rm crit}$ 时：传统角谱传递函数满足无混叠采样，而菲涅耳冲激响应核发生欠采样；
  - 当 $z > z_{\rm crit}$ 时：传统角谱传递函数出现混叠（需 BLAS 截断），而菲涅耳积分核进入良好采样区。

---

## 2. 符号与算子约定（Invariants & Conventions）

实现任何新物理公式前，必须统一映射至本项目的全局约定：

| 物理量 / 算子 | 常用不同约定 | 本项目统一约定 |
| :--- | :--- | :--- |
| **时间简谐因子** | $e^{-i\omega t}$ 或 $e^{i\omega t}$ | **$e^{-i\omega t}$**，因此沿 $+z$ 传播的平面波空间相位为 **$e^{+i k z}$** ($k = 2\pi/\lambda$) |
| **空间频率定义** | 周期频率 $f_x$ (cyc/m) 或 角频率 $k_x$ (rad/m) | **$f_x \in [-f_N, f_N]$**，其中 $f_N = \frac{1}{2\Delta x}$；$k_x = 2\pi f_x$ |
| **2D 傅里叶变换** | 连续形式 $\iint u(x, y) e^{-i 2\pi (f_x x + f_y y)} dx dy$ | 离散 DFT 乘以物理面积步长 **$\Delta x \Delta y$**；IDFT 乘以 **$N_x N_y \Delta f_x \Delta f_y$** |
| **角谱传递函数** | $H(f_x, f_y) = \exp\left(i \frac{2\pi}{\lambda} z \sqrt{1 - \lambda^2(f_x^2 + f_y^2)}\right)$ | 衰减模式（Evanescent）：当 $\lambda^2(f_x^2 + f_y^2) > 1$ 时，为实指数衰减 **$\exp\left(-k z \sqrt{\lambda^2(f_x^2 + f_y^2) - 1}\right)$** |

---

## 3. 来源优先级与冲突仲裁机制

当不同文献或代码库对某一阈值或公式存在冲突时，按以下严格优先级仲裁：

1. **第一优先级：同行评审原始文献（Primary Peer-Reviewed Literature）**
   - 必须核实推导过程、初始假设（如近轴 vs 非近轴、单色标量假设）。
2. **第二优先级：权威经典教材（Authoritative Textbooks）**
   - Goodman *Introduction to Fourier Optics*、Voelz *Computational Fourier Optics*、Born & Wolf *Principles of Optics*。
3. **第三优先级：经过验证的成熟开源实现（Mature Implementations）**
   - 如 `waveprop`，需核实其代码中是否有针对上游 edge case 的补丁或修正。
4. **第四优先级：工程启发式经验（Engineering Heuristics）**
   - 只能作为 `DIAGNOSTIC` 提示，绝对禁止未经证明提升为 `FORMAL_CRITERION`。

---

## 4. 阈值来源登记规范（Provenance Tracking）

每一个在代码中出现的判定阈值必须指定 `ThresholdProvenance`：
- `THEORETICAL`：纯数学恒等式（如 Nyquist 采样极限）。
- `LITERATURE`：公开发表文献中的严密推导（需标注文献引用与公式编号）。
- `PROJECT_DEFAULT`：工程默认参数（如默认 $1\%$ 收敛相对误差）。
- `USER_DEFINED`：用户运行时自定义传入。
