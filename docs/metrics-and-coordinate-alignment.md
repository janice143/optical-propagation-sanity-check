# 坐标对齐与误差度量规范 (Metrics & Coordinate Alignment)

在评估数值波动光学传播的稳定性和跨算法/基准一致性时，如果缺乏统一的几何坐标基准和严密的数学度量定义，往往会导致**虚假的数值差异**（如：单纯的常数相位偏移被误判为波前畸变，或未对齐网格原点导致的几何平移误差）。

本项目严格执行以下坐标对齐体系与误差度量标准。

---

## 1. 空间与网格坐标约定（Coordinate Invariants）

### A. 轴序与零中心化
* **数组维度映射**：2D 数组形状为 `(ny, nx)`。第一维为纵轴（行，对应 $y$ 坐标），第二维为横轴（列，对应 $x$ 坐标）。
* **物理坐标中心**：坐标网格严格零中心化对称（Zero-Centered）：
  $$x = \left(-\frac{N_x}{2} + [0, 1, \dots, N_x-1]\right) \cdot \Delta x$$
  $$y = \left(-\frac{N_y}{2} + [0, 1, \dots, N_y-1]\right) \cdot \Delta y$$
* **物理视场（Field of View / Window Size）**：
  $$L_x = N_x \Delta x, \quad L_y = N_y \Delta y$$

### B. 绝对禁止“纯数组索引比较”
不同算法、后端（如 waveprop 与 TorchOptics）或不同收敛步长（如 $\Delta x$ 与 $\Delta x / 2$）产生的数组，其 shape 和采样率各不相同。
> **比较任何两个光场分布前，必须先在物理空间中建立公共重叠区域（Common Physical ROI），并在物理坐标系下进行插值或重采样比对。绝对禁止仅靠数组索引对齐（Array Index Matching）。**

---

## 2. 误差度量数学模型（Error Metrics）

核心实现位于 [`src/propagation_sanity/core/metrics.py`](file:///Users/janicelan/obsidian/opticsMe/numerical-calculation/optical-propagation-sanity-check/src/propagation_sanity/core/metrics.py)。

### A. 光强相对误差（Intensity Relative Error）
衡量能量空间分布形状的差异，对全局常数相位不敏感：
$$\varepsilon_I = \frac{\|I_a - I_b\|_{L_2}}{\|I_b\|_{L_2}} = \frac{\sqrt{\sum_{i} |I_a(x_i, y_i) - I_b(x_i, y_i)|^2}}{\sqrt{\sum_{i} |I_b(x_i, y_i)|^2}}$$
其中 $I_b$ 为基准参考场（Reference Field），$I_a$ 为待评估测试场。

### B. 全局相位消除与复振幅相对误差（Complex Field Relative Error）
不同传播算法或不同参考面定义可能引入一个全局常数相位差 $\alpha \in [-\pi, \pi]$。若直接计算复振幅差值，哪怕波前形状完全一致，也会报出高达 $200\%$ 的虚假相对误差。

1. **最优全局相位差估计（Global Phase Offset）**：
   通过内积投影求解使残差最小的常数相位因子：
   $$\alpha = \arg\left(\langle U_b, U_a \rangle\right) = \arg\left(\sum_{i} U_b^*(x_i, y_i) \cdot U_a(x_i, y_i)\right)$$
2. **对齐后的复振幅相对误差**：
   $$U'_a = U_a e^{-i\alpha}$$
   $$\varepsilon_U = \frac{\|U'_a - U_b\|_{L_2}}{\|U_b\|_{L_2}}$$

### C. 强度掩模加权的相位误差（Masked Phase Error）
在光束暗区或边缘无光区（$I(x, y) \approx 0$），复振幅的相位由双精度浮点噪声支配或存在无物理意义的相位奇点。若对全图无差别计算相位误差，底噪区会彻底污染统计指标。

* **掩模过滤机制**：
  仅在光强显著区域统计相位差异：
  $$\text{Mask}(x, y) = \left\{ (x, y) \;\middle|\; \frac{I_b(x, y)}{\max(I_b)} > \tau_{\rm threshold} \right\} \quad (\text{默认 } \tau = 0.01)$$
* **相位误差统计量**：
  在消除全局常数相位 $\alpha$ 后，对折叠相位差 $\Delta \phi = \arg\left(U'_a \cdot U_b^*\right) \in [-\pi, \pi]$ 计算：
  - $\mathrm{MeanAbs} = \frac{1}{M}\sum_{\rm Mask} |\Delta \phi|$
  - $\mathrm{RMS} = \sqrt{\frac{1}{M}\sum_{\rm Mask} (\Delta \phi)^2}$
  - $\mathrm{MaxAbs} = \max_{\rm Mask} |\Delta \phi|$

### D. 积分能量诊断（Power Diagnostic）
对于无耗自由空间传播，能量在理论上是守恒的：
$$P = \sum_{i} |U(x_i, y_i)|^2 \Delta x \Delta y$$
$$\Delta P_{\rm rel} = \frac{|P_{\rm out} - P_{\rm in}|}{P_{\rm in}}$$
* 若 $\Delta P_{\rm rel} > 0.05$（超过 $5\%$ 能量丢失）：系统报告 `DIAGNOSTIC` 警告，指示计算窗口截断严重或高频消逝波被非物理吸收。
