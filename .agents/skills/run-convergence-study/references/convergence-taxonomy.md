# 数值传播收敛性实验体系指南 (Convergence Taxonomy)

在基于离散网格的光学波动传播仿真中，“网格收敛性分析”是最基础且最容易产生概念混淆的环节。本项目严格区分以下三种在数学和物理上完全正交的收敛性实验，并附加输出采样收敛性要求。

---

## 1. 三种经常被混淆的收敛性

```
┌────────────────────────────────────────────────────────────────────────┐
│                        收敛性实验分类 (Convergence)                      │
├─────────────────────┬─────────────────────┬────────────────────────────┤
│ 1. 分辨率收敛        │ 2. 物理窗口收敛      │ 3. 算法 Padding 收敛        │
│ (Resolution)        │ (Physical Domain)   │ (Algorithmic Padding)      │
├─────────────────────┼─────────────────────┼────────────────────────────┤
│ 保持物理域 L 不变   │ 保持采样间距 Δx 不变 │ 保持物理网格与采样完全不变 │
│ 增大网格数 N         │ 增大物理窗口 L       │ 仅增加 FFT 计算内部补零     │
│ (Δx 减小，网格细化) │ (N 随之增大)         │ (消除周期卷积环绕假象)     │
└─────────────────────┴─────────────────────┴────────────────────────────┘
```

### A. 分辨率收敛（Resolution Convergence）
* **实验目的**：检验空间离散化精细度（Spatial Discretization）对传播结果的影响，验证是否存在空间欠采样或相位变化过快引起的离散误差。
* **控制变量**：
  $$\text{Physical Window } L = \text{constant}$$
  $$N \rightarrow 2N \rightarrow 4N \quad \Longrightarrow \quad \Delta x \rightarrow \frac{\Delta x}{2} \rightarrow \frac{\Delta x}{4}$$
* **绝对红线**：
  > **每一次细化都必须从底层的连续 `FieldSource` 重新采样。**
  > **严禁**对旧数组进行双线性或样条插值（Bilinear Upsampling），因为插值无法还原在粗网格上已经发生的混叠（Aliasing）。
* **无 `FieldSource` 时的处理规则**：
  若用户仅提供固定尺寸离散数组（如 `512×512 array`）且无法提供连续生成器，系统必须将分辨率收敛性标记为 `UNVERIFIED`，不得擅自插值测试并谎称“已收敛”。

---

### B. 物理窗口收敛（Physical-Domain / Window Convergence）
* **实验目的**：检验有限计算窗口是否足够宽，避免因截断实际光束尾翼或衍射旁瓣而引入边界反射/虚假衍射。
* **控制变量**：
  $$\text{Sampling Interval } \Delta x = \text{constant}$$
  $$L \rightarrow 1.5L \rightarrow 2L \quad \Longrightarrow \quad N \rightarrow 1.5N \rightarrow 2N$$
* **紧支集与非紧支集区别（核心陷阱）**：
  1. **严格紧支集场（Compact-Support）**：如理想方孔（Square Aperture），原物理窗口外已知光场严格为 0。此时直接在原数组外部补零（Zero-padding）等价于扩大物理仿真区域。
  2. **非紧支集场（Noncompact-Support）**：如高斯光束（Gaussian）、艾里光束（Airy beam）或任意连续波前，原窗口外往往存在具有物理意义的振幅尾翼。
  > **对于非紧支集光场，对旧数组直接补零 $\neq$ 扩大物理仿真域！**
  > 真正的物理窗口收敛必须调用 `FieldSource.sample(larger_grid)` 重新计算扩展区域的实际物理振幅。

---

### C. 算法 Padding 收敛（Algorithmic Padding Convergence）
* **实验目的**：检验 FFT 卷积算子内部的零填充裕量，评估离散循环卷积（Circular Convolution）是否向中心区域造成了混叠干扰。
* **控制变量**：
  $$\text{Physical Field } U(x, y) = \text{constant}$$
  $$\text{Physical Grid } (N_x, N_y, \Delta x, \Delta y) = \text{constant}$$
  $$\text{FFT Padding Factor } p \in [1.0, 1.5, 2.0, \dots]$$
* **说明**：此实验不改变物理输入，纯属算法层面的数值抑制（通过扩展频域计算尺寸并在 IFFT 后裁剪回原物理尺寸）。

---

## 2. 输出采样收敛（Output Sampling Convergence）
对于单步 Fresnel 或 Fraunhofer 等变网格传播方法，输出端物理网格尺寸直接与传播距离和输入参数耦合：
$$\Delta x_{\rm out} = \frac{\lambda z}{N \Delta x_{\rm in}}$$
如果用户指定了固定的探测器采样间距（Requested Output Grid），传播后必须经过显式插值重采样。收敛引擎必须区分**传播物理误差**与**探测器插值误差**，确保比较在公共物理坐标区间内完成。

---

## 3. 收敛判定准则与状态语义

收敛引擎对每一组实验计算相邻精细度之间的复振幅相对误差（Complex Field Relative Error）与光强相对误差（Intensity Relative Error）：

$$\epsilon = \frac{\|U_{\rm fine} - U_{\rm coarse}\|_{L_2}}{\|U_{\rm fine}\|_{L_2}}$$

* 若 $\epsilon \le \text{tolerance}$（默认典型值为 $1\%$ 或 $10^{-2}$）：状态报告为 `CONVERGED_AT_TOLERANCE`。
* 若连续细化后 $\epsilon > \text{tolerance}$：状态报告为 `NOT_CONVERGED`，并输出相邻步的实际误差与发散趋势。
* 若输入缺少连续生成函数：状态明确标注为 `UNVERIFIED`。
