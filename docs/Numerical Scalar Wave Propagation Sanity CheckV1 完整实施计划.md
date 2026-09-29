# Numerical Scalar Wave Propagation Sanity Check
## V1 完整实施计划

## 0. 本文档用途

这是一份独立的工程实施说明。

执行 Agent 不需要知道任何此前对话，只需要按照本文档完成：

1. 理论与 checker 审计；
2. numerical validation core；
3. propagation adapter；
4. convergence engine；
5. report system；
6. benchmark；
7. self-accelerating beam 案例；
8. differentiable optics 案例；
9. 测试和文档。

本文档给出的模块名、类名、函数名仅供参考，可以调整。

但以下内容属于设计约束，不应随意改变：

- 项目范围；
- checker 分类；
- validation semantics；
- convergence 实验定义；
- threshold provenance；
- reference hierarchy；
- benchmark 和 application cases；
- Definition of Done。

---

# 1. 项目背景

项目起点是一篇关于 numerical diffraction sanity check 的文章：

[《你的 Loss 在下降，但优化的可能只是数值伪影》。](https://www.believed-breadfruit.top/2026/09/20/2026-09-21-%E4%BD%A0%E7%9A%84Loss%E5%9C%A8%E4%B8%8B%E9%99%8D-%E4%BD%86%E4%BC%98%E5%8C%96%E7%9A%84%E5%8F%AF%E8%83%BD%E5%8F%AA%E6%98%AF%E6%95%B0%E5%80%BC%E4%BC%AA%E5%BD%B1/)

文章从一个 differentiable-optics 问题出发：

$$
\text{phase modulator}
\rightarrow
\text{propagation}
\rightarrow
\text{loss}
\rightarrow
\text{autograd}
\rightarrow
\text{optimizer}
$$

即使：

$$
Loss\downarrow
$$

也不能证明 forward propagation 是正确的。

文章进一步通过方孔实验讨论了：

- grid sampling；
- Nyquist frequency；
- computation window；
- FFT frequency spacing；
- wrap-around；
- zero-padding；
- ASM transfer-function sampling；
- BLAS；
- Fresnel / Fraunhofer approximation；
- DI cross-check。

这些问题是真实存在的；例如 Matsushima & Shimobaba 明确指出标准 Angular Spectrum Method 会因为 transfer function 的 sampling 出现严重 numerical error，并提出 band-limited ASM；Shen & Wang 则系统研究了 diffraction numerical integration 中 sampling interval 和 computation window 对结果的影响。

但有一个重要原则：

> **原文章中的指标和阈值不能直接当作本项目标准。**

文章应当被看作：

> candidate failure modes + exploratory diagnostics + experimental evidence

而不是：

> formal checker specification。

例如文章中的：

$$
\eta_{\rm edge}
$$

$$
f_{\rm safe}
$$

$$
\Delta\phi_{\max}\approx\pi
$$

$$
99.9\%\text{ effective spectrum}
$$

以及某些 WARN / FAIL 数值，都需要重新审计其数学含义和来源。文章本身也已经把部分条件描述为工程警戒线，而非严格物理边界。

因此 V1 的第一个阶段不是写 checker，而是：

$$
\boxed{\text{Checker Audit}}
$$

---

# 2. 项目正式定位

V1 定义为：

> **A validation toolkit for numerical reliability in scalar free-space wave propagation.**

更准确地说：

> 给定一个 scalar diffraction numerical setup，检查其 sampling、finite-domain、propagator discretization 和 propagation-model approximation 是否存在明显风险，并通过数值收敛实验评估结果对离散参数是否稳定。

项目回答的问题是：

> **当前 numerical result 在测试过的离散条件和容差下，有多少证据支持它是稳定的？**

项目不应宣称回答：

> “这个结果一定是真实物理。”

更不能宣称：

> “通过所有 checker 就等于实验一定正确。”

---

# 3. V1 范围

V1 只处理：

```text
monochromatic
scalar field
2D transverse field
free-space propagation
FFT / diffraction-based numerical propagation
```

重点方法：

```text
Angular Spectrum Method
Fresnel propagation
Fraunhofer propagation
Rayleigh–Sommerfeld / Direct Integration reference
```

核心 numerical problems：

```text
input representation
spatial resolution
finite computation domain
FFT periodicity / padding
propagation-kernel sampling
model approximation
numerical convergence
```

---

# 4. 明确不做

V1 不需要扩展成：

- full optical design software；
- lens-system validator；
- imaging-system validator；
- PSF / MTF industrial analysis；
- polarization；
- vector diffraction；
- high-NA vectorial optics；
- metasurface solver；
- Maxwell solver；
- camera ISP；
- holography-specific evaluation；
- polychromatic propagation；
- experimental calibration framework。

如果运行条件明显进入这些范围，可以报告：

```text
OUT_OF_SCOPE
```

而不是继续扩展实现。

---

# 5. V1 的应用案例

只做三个层次。

## 5.1 Canonical numerical benchmark

方孔衍射。

目的：

- regression；
- analytic-scale comparison；
- replication of original article；
- artificially create failure modes。

---

## 5.2 Research case

Self-accelerating beam propagation。

目的：

证明 validator 可以用于真实的 propagation research workflow。

不新增 beam-specific checker。

---

## 5.3 Optimization case

Differentiable optics / inverse design。

目的：

展示：

$$
Loss\downarrow
$$

与：

$$
\text{forward model numerically trustworthy}
$$

是两个不同问题。

---

# 6. Validation 的核心哲学

整个项目必须区分五种东西。

## 6.1 Derived Quantity

数学定义直接决定的量，例如：

$$
L_x=N_x\Delta x
$$

$$
\Delta f_x=\frac1{L_x}
$$

$$
f_{N,x}=\frac1{2\Delta x}.
$$

它们没有 PASS / FAIL。

---

## 6.2 Diagnostic

用于解释风险，但不能单独证明结果正确。

例如：

$$
\eta_{\rm edge}
$$

ASM phase step；

Fresnel number；

field boundary energy；

effective bandwidth。

默认只展示数值。

---

## 6.3 Method-Specific Criterion

只适用于特定 numerical formulation，并且必须有明确推导或文献依据。

例如：

> Matsushima BLAS 中针对 standard ASM sampling 导出的 admissible spectral region。

不能拿一个 ASM criterion 去判断所有 Fresnel / DI propagator。

Voelz & Roggemann 的工作特别强调：不同 FFT diffraction formulations 存在不同 sampling regimes，undersampling / oversampling 的后果也依赖具体传播算法。

---

## 6.4 Empirical Convergence

通过改变 discretization：

$$
\Delta x,\ L,\ padding,\ output\ sampling
$$

直接观察结果是否稳定。

这是 V1 最重要的 evidence 类型之一。

---

## 6.5 Independent Cross-Reference

与：

- analytic solution；
- independently converged DI；
- independently converged alternative propagator；

比较。

Cross-reference 自身也必须经过 convergence。

不能写：

```text
DI = truth
```

只能写：

```text
DI reference converged to tolerance X
```

原文章本身也明确指出 DI 仍受 sampling、finite window 和 quadrature error 限制。

---

# 7. Checker Audit：开发第一阶段

任何 checker 在实现前，都必须完成以下 specification：

```text
id
failure mode
quantity / formula
required inputs
applicable propagators
mathematical assumptions
assessment type
threshold
threshold provenance
reference
possible false positive
possible false negative
recommended follow-up
```

其中：

```text
assessment type
```

必须属于：

```text
DERIVED
DIAGNOSTIC
FORMAL_CRITERION
CONVERGENCE
CROSS_REFERENCE
SCOPE_CHECK
```

---

# 8. Threshold Provenance

任何 threshold 必须记录来源。

允许：

```text
THEORETICAL
LITERATURE
PROJECT_DEFAULT
USER_DEFINED
```

例如：

```text
π phase step
```

如果只是项目经验：

```text
threshold_provenance = PROJECT_DEFAULT
```

而不能包装成：

```text
Nyquist theorem
```

用户自定义：

```text
relative_error < 1%
```

则必须记录：

```text
threshold_provenance = USER_DEFINED
```

---

# 9. 是否允许 PASS / FAIL

并不是所有 result 都应该有 PASS / FAIL。

### Derived Quantity

只输出 value。

### Diagnostic

默认：

```text
INFO
```

可以附：

```text
risk_hint
```

但没有 formal PASS。

### Formal Criterion

只有当：

- criterion 来源明确；
- assumptions 满足；
- implementation 已验证；

才允许：

```text
PASS / FAIL
```

### Convergence

建议输出：

```text
CONVERGED_AT_TOLERANCE
NOT_CONVERGED
UNVERIFIED
```

而不是泛化的 PASS。

### Cross-reference

输出：

```text
AGREES_AT_TOLERANCE
DISAGREES
UNVERIFIED
```

---

# 10. Simulation Contract

项目需要一个统一 simulation description。

具体 API 名称可以变化。

至少表达以下信息。

---

# 11. Field Representation

必须区分两类输入。

## 11.1 Sampled Array

用户直接传：

```text
complex ndarray
complex torch.Tensor
```

工具只知道：

$$
U[i,j].
$$

这时存在一个重要限制：

> 已经发生在 continuous → sampled 过程中的 aliasing，无法仅根据这个 sampled array 被完全检测出来。

因为高于 Nyquist 的连续频率如果已经 alias 回低频：

$$
U_{\rm continuous}
\rightarrow
U_{\rm sampled}
$$

之后再做 FFT，并不能恢复被折叠前的信息。

因此只有 sampled array 时：

```text
input_sampling_validation = UNVERIFIED
```

仍可以运行：

- spectrum diagnostic；
- boundary diagnostic；
- propagation checks；
- padding checks。

但不能声称：

> input is adequately sampled。

---

# 12. Field Generator

为了真正执行 resolution convergence，推荐支持：

```text
FieldSource / FieldGenerator
```

概念接口：

```python
field = source.sample(grid)
```

例如：

```text
SquareAperture
AnalyticBeam
UserDefinedCallable
PhaseProfile
```

当网格变成：

$$
\Delta x/2
$$

时，不是对旧 array interpolation，而是重新计算：

$$
U(x,y)
$$

在新的 physical coordinates 上的值。

这是：

> true resolution refinement。

---

# 13. Torch Tensor

如果 input 是 Torch tensor：

validator 的 static analysis 可以：

```text
detach
→ CPU
→ numerical analysis
```

不得修改 computation graph。

Differentiable-optics example 中：

validator 与训练 graph 必须分离。

---

# 14. Grid

至少包含：

$$
N_x,N_y
$$

$$
\Delta x,\Delta y.
$$

自动计算：

$$
L_x=N_x\Delta x,
\qquad
L_y=N_y\Delta y
$$

$$
\Delta f_x=\frac1{L_x},
\qquad
\Delta f_y=\frac1{L_y}
$$

$$
f_{N,x}=\frac1{2\Delta x},
\qquad
f_{N,y}=\frac1{2\Delta y}.
$$

注意：

FFT endpoint convention、coordinate origin、`fftshift` convention 必须全项目统一并写入测试。

---

# 15. Wave

至少：

$$
\lambda.
$$

V1 默认：

```text
monochromatic
scalar
homogeneous medium
```

如未来支持 refractive index：

$$
\lambda_{\rm medium}=\frac{\lambda_0}{n}
$$

必须明确 wavelength 字段代表 vacuum 还是 medium wavelength。

V1 可以暂时固定：

```text
vacuum wavelength + n = 1
```

以避免歧义。

---

# 16. Propagation Geometry

必须包含：

$$
z.
$$

支持：

```text
single z
z array
```

多 z 很重要，因为 accelerating beam 和 sampling risk 通常都随 propagation distance 变化。

---

# 17. Output Geometry

如果 propagator 允许 input/output 不同 grid，必须记录：

```text
output shape
output spacing
output offset
output physical extent
```

TorchOptics 当前就将 output `shape / spacing / offset` 作为 propagation interface 的显式参数，并在必要时执行 interpolation。

因此 report 中必须区分：

```text
propagation grid
```

和：

```text
requested output grid
```

否则 interpolation error 会被误认为 propagation error。

---

# 18. ROI

Dynamic comparison 必须定义物理 ROI。

不能只按：

```text
array[128:384]
```

比较。

应该记录：

```text
x_min
x_max
y_min
y_max
```

如果没有 user ROI：

默认使用各 configuration 共同覆盖的最大中心 physical region。

---

# 19. Propagation Configuration

至少记录：

```text
method
backend
padding
bandlimit
evanescent policy
interpolation
```

例如：

```text
method        ASM
backend       waveprop
padding       2x
bandlimit     false
evanescent    retain
```

---

# 20. Derived Grid Report

每次 validation 必须首先生成：

```text
Nx, Ny
dx, dy
Lx, Ly
dfx, dfy
Nyquist x/y
wavelength
z
method
```

这一部分永远不是 checker。

它只是：

> numerical simulation contract 的完整展示。

---

# 21. Candidate Checker A：Input Spectrum Diagnostic

保留原文章中的 spectrum analysis，但重新定义其含义。

角谱：

$$
A(f_x,f_y)=\mathcal F\{U_0(x,y)\}
$$

能量：

$$
S=|A|^2.
$$

---

# 22. Edge Spectral Energy

允许计算例如：

$$
\eta_{\rm edge}
=
\frac{
\sum_{|f_x|>\alpha f_{N,x}\ \lor\ |f_y|>\alpha f_{N,y}}
|A|^2
}{
\sum |A|^2
}.
$$

原文章使用：

$$
\alpha=0.8.
$$

这是项目 diagnostic，不是理论边界。

因此：

```text
type = DIAGNOSTIC
alpha = configurable
```

输出：

```text
edge spectral energy = ...
```

不能输出：

```text
input sampling PASS
```

---

# 23. Effective Spectrum

原文章使用：

```text
99.9% spectral energy
```

定义有效频带。

新版不把：

$$
99.9\%
$$

固定为物理标准。

实现应支持：

```text
energy_coverage = configurable
```

例如：

```text
95%
99%
99.9%
```

推荐提供两个描述：

```text
radial energy quantile
x/y projected energy quantile
```

这样非圆对称 field 不会被单一 radial bandwidth 过度简化。

这些都是：

```text
DIAGNOSTIC
```

---

# 24. Candidate Checker B：Input Resolution

这是对旧文章“输入采样检查”的重要修正。

例如：

$$
a/\Delta x=50
$$

只能说明：

> 已知 characteristic size $a$ 被约 50 个 sample 表示。

不能证明连续输入没有 aliasing。

因此：

```text
feature pixels = diagnostic
```

没有统一的：

```text
>10 pixels = PASS
```

规则。

---

# 25. Resolution Convergence

真正的 input-resolution validation 是：

保持 physical domain：

$$
L=\text{constant}
$$

增加：

$$
N
$$

因此：

$$
\Delta x\downarrow.
$$

例如：

$$
N
\rightarrow2N
\rightarrow4N
$$

$$
\Delta x
\rightarrow\Delta x/2
\rightarrow\Delta x/4.
$$

每一次都必须：

> 从 underlying continuous FieldSource 重新采样。

不能：

```text
bilinear upscale old array
```

因为 interpolation 无法恢复 aliased information。

---

# 26. 只有 Array 时如何处理

如果用户只提供：

```text
512 × 512 array
```

没有 continuous generator：

resolution convergence 无法真实执行。

Report：

```text
Input resolution:
UNVERIFIED

Reason:
The validator only received an already sampled field.
A finer physical sampling cannot be reconstructed reliably
from the existing array.
```

这是重要的产品行为。

---

# 27. Candidate Checker C：Spatial Boundary Diagnostic

计算 field 在当前 computation-domain edge 附近的能量。

例如定义 edge strip：

```text
outer p% of spatial domain
```

然后：

$$
\eta_{\rm spatial-edge}
=
\frac{E_{\rm edge}}{E_{\rm total}}.
$$

它可以快速提醒：

> field 已经明显接近 boundary。

但：

```text
p
threshold
```

仍属于 project heuristic。

因此只作为 diagnostic。

Zemax POP 也明确强调，需要在 beam 周围保留 guard band；场靠近 numerical array 边缘会产生 aliasing。但官方建议同样强调 sampling 与 width 之间需要权衡，而不是一个普适固定百分比。

---

# 28. 原文章 f_safe 的处理

文章定义：

$$
f_{\rm safe}
=
\frac{L}{2\lambda z}
$$

用近轴关系：

$$
x\approx\lambda z f
$$

估计不同 spectral component 是否可能跑出 computation window。

新版：

> 不把它作为 core checker。

可以保留成：

```text
paraxial FOV preview
```

类型：

```text
DIAGNOSTIC
```

Report 必须注明：

- paraxial estimate；
- 不考虑完整 field support；
- 不考虑 interference；
- 不能取代 convergence。

---

# 29. 三种经常被混淆的 convergence

新版必须明确拆开以下三个实验。

---

# 30. A：Resolution Convergence

目的：

> 检查 spatial discretization。

固定：

$$
L.
$$

改变：

$$
\Delta x.
$$

要求：

> regenerate input field。

---

# 31. B：Physical-Domain / Window Convergence

目的：

> 检查有限 simulation domain 是否足够。

固定：

$$
\Delta x.
$$

增加：

$$
L.
$$

即：

$$
N\uparrow.
$$

但这里存在重要区别。

对于 compact-support input，例如理想方孔：

原窗口外已知：

$$
U=0.
$$

因此可以直接扩展 zero region。

但对于：

- Gaussian；
- Airy-like beam；
- accelerating beam；
- arbitrary noncompact field；

原窗口外并不一定为 0。

这时：

> zero-padding old array ≠ enlarging the physical simulation domain。

真正的 domain convergence 必须使用：

```text
FieldSource.sample(larger_grid)
```

重新生成更大 physical window。

---

# 32. C：Algorithmic Padding Convergence

这是另一个问题。

保持：

```text
physical input problem
```

不变，只改变 propagation implementation 内部：

```text
FFT padding
```

例如：

```text
1×
2×
4×
```

目的是测试：

- circular convolution；
- periodic boundary;
- internal FFT representation。

TorchOptics 当前 ASM 默认会使用 padding 来抑制 periodic boundary artifact；官方文档明确将 `asm_pad` 暴露为 propagation 参数。

因此新版不允许把：

```text
physical window convergence
```

与：

```text
FFT padding convergence
```

合并成同一个 checker。

---

# 33. Candidate Checker D：ASM Propagator Sampling

ASM：

$$
H(f_x,f_y)=
\exp\left[
i2\pi z
\sqrt{
\frac1{\lambda^2}
-f_x^2-f_y^2
}
\right].
$$

标准 ASM 在有限 sampled grid 上不是自动可靠。

Matsushima & Shimobaba 2009 明确指出，AS 即使在 Fresnel region 内也可能因为 transfer-function sampling 出现严重 numerical errors，因此提出 bandwidth limitation。

---

# 34. 正式 ASM Criterion

执行 Agent 必须：

1. 获取 Matsushima & Shimobaba 2009；
2. 阅读 sampling / band-limit derivation；
3. 找到 paper 中 exact admissible frequency condition；
4. 确认其 FFT/grid conventions；
5. 与 waveprop implementation 对照；
6. 编写 independent unit test；
7. 才能将其实现为 formal criterion。

禁止根据模型记忆直接写公式。

如果无法取得原文完整推导：

> V1 不得伪造 formal BLAS criterion。

可以先只提供 diagnostics + convergence。

---

# 35. ASM Phase-Step Diagnostic

文章计算：

$$
\Delta\phi_x
=
|\phi(f_x+\Delta f_x,f_y)-\phi(f_x,f_y)|
$$

以及：

$$
\Delta\phi_y.
$$

这个量应保留，因为解释性很强。

必须使用：

> analytical unwrapped phase。

不能对：

$$
\arg H
$$

直接做差，因为：

$$
\arg H\in[-\pi,\pi]
$$

会隐藏多周期变化。

输出：

```text
max phase step
phase-step distribution
phase step inside selected spectral support
```

但：

$$
\Delta\phi<\pi
$$

不能默认成为 formal PASS criterion。

原文章本身只是将约 $\pi$ 作为工程警戒线。

因此：

```text
type = DIAGNOSTIC
```

---

# 36. BLAS

V1 validator 不需要自己发明新的 BLAS。

允许：

```text
backend bandlimit
```

或者实现 paper algorithm。

但原则：

```text
detect
→ explain
→ optionally rerun comparison
```

不能：

```text
detect
→ silently enable BLAS
→ pretend original configuration was valid
```

waveprop 当前已经支持 band-limited angular spectrum，并提供专门 example 展示其作用。

---

# 37. Evanescent Components

传播波：

$$
q=
\sqrt{f_x^2+f_y^2}
\leq\frac1\lambda.
$$

倏逝波：

$$
q>\frac1\lambda.
$$

可以输出：

```text
evanescent input energy
evanescent policy
```

如果 backend：

```text
drop / decay / retain
```

必须写进 metadata。

该项主要是：

```text
SCOPE_CHECK / DIAGNOSTIC
```

如果大量信息依赖 subwavelength components：

report 应提醒：

```text
scalar free-space V1 may not be sufficient
```

而不是扩展到 Maxwell solver。

---

# 38. Candidate Checker E：Fresnel Approximation

Fresnel 与 ASM 的区别属于：

> model approximation error。

不是：

> FFT sampling error。

因此必须和 numerical discretization 分开报告。

ASM phase：

$$
\phi_A=
2\pi z
\sqrt{
1/\lambda^2-f_x^2-f_y^2
}.
$$

Fresnel 使用其 paraxial quadratic approximation。

可以计算 active spectral region 中：

$$
\Delta\phi_{A-F}.
$$

这是有物理意义的 approximation diagnostic。

但：

```text
1 rad
```

不能默认视为严格适用边界。

原文章本身已经明确说明该尺度只是 conservative screening。

因此默认：

```text
type = DIAGNOSTIC
```

如果用户定义：

```text
allowed_phase_error = ...
```

则可以按用户 tolerance 给结果。

---

# 39. Candidate Checker F：Fraunhofer Approximation

如果 input 有明确 characteristic aperture scale：

$$
a
$$

可以计算：

$$
N_F=\frac{a^2}{\lambda z}.
$$

也可以估计 neglected quadratic phase。

但：

$$
N_F
$$

首先是：

```text
regime indicator
```

不是 universally calibrated boolean checker。

因此默认：

```text
type = DIAGNOSTIC
```

只有用户明确指定 acceptable approximation tolerance 时，再产生 criterion status。

---

# 40. Characteristic Size 必须是 Optional

任意 field 并不都有唯一：

$$
a.
$$

因此：

```text
aperture_size
beam_radius
characteristic_size
```

都不能是 Simulation Contract 的必填项。

没有该参数：

```text
Fraunhofer regime diagnostic = NOT_APPLICABLE
```

而不是猜一个数。

---

# 41. Rayleigh–Sommerfeld / DI Checker

DI 不能直接定义为 ground truth。

如果使用 DI：

必须检查自身的：

- spatial resolution；
- quadrature convergence；
- finite input domain；
- output grid。

Diffractio 已经提供了一个 RS `quality_factor` 并明确引用 Shen & Wang 2006；其文档还展示了 quality<1 并不一定直接意味着结果错误，尤其当实际 mask 小于完整计算区域时。这个例子非常适合提醒项目：**一个 quality metric 的解释范围必须明确。**

因此不要直接复制：

```text
quality > 1 → universal PASS
```

可以研究其实现作为参考。

---

# 42. Reference Hierarchy

需要 cross-check 时，优先级：

```text
1. analytic / semi-analytic reference
2. independently converged high-accuracy numerical reference
3. independently implemented alternative method
4. same-library alternative method
```

例如方孔远场 sinc：

比：

```text
waveprop ASM vs waveprop DI
```

具有更强独立性。

---

# 43. Output Comparison Metrics

至少实现以下 metric。

---

# 44. Intensity Relative Error

$$
\epsilon_I=
\frac{
\|I_a-I_b\|_2
}{
\|I_b\|_2
}.
$$

---

# 45. Complex Field Relative Error

先消除 global phase：

$$
\alpha=
\arg
\left(
\sum U_b^*U_a
\right)
$$

$$
U'_a=
U_ae^{-i\alpha}.
$$

再计算：

$$
\epsilon_U=
\frac{
\|U'_a-U_b\|_2
}{
\|U_b\|_2
}.
$$

---

# 46. Phase Error

只在 amplitude / intensity 足够大的位置统计。

默认 mask 可以由：

```text
relative intensity threshold
```

配置。

不能在：

$$
|U|\approx0
$$

区域讨论 phase accuracy。

---

# 47. Power Diagnostic

可以输出：

$$
P=\sum|U|^2\Delta x\Delta y.
$$

用于：

- obvious normalization errors；
- unexpected truncation；
- backend consistency。

但不要自动将 power difference 解释成 propagation error，因为：

- cropped ROI；
- evanescent handling；
- finite observation window；

都可能改变统计到的 power。

---

# 48. Common Physical Coordinates

任何 two-run comparison 必须在：

> 同一 physical coordinates

上比较。

不能仅根据 array index。

流程：

```text
get physical coordinates
→ determine common ROI
→ align grids
→ interpolate only when unavoidable
→ record interpolation method
→ compare
```

如果 interpolation error 本身不可忽略：

应首先统一 grid，而不是继续比较。

---

# 49. Output Sampling Convergence

当 propagator 支持不同 output spacing 时，增加：

```text
output-grid convergence
```

例如固定 physical observation window：

$$
\Delta x_{\rm out}
\downarrow
$$

观察 result 是否稳定。

对于始终 same-grid ASM 的最小 V1，这不是必跑项。

应：

```text
conditional
```

而不是强制所有 simulation 执行。

---

# 50. Validation Engine 的正式层级

最终 report 按五层组织。

## Layer 0 — Contract

Simulation parameters。

## Layer 1 — Diagnostics

解释 potential risk。

## Layer 2 — Method-specific criteria

有文献推导的 formal constraints。

## Layer 3 — Convergence

直接改变 numerical discretization。

## Layer 4 — Cross-reference

与独立 reference 对照。

这比简单：

```text
PASS / WARNING / FAIL
```

更准确。

---

# 51. 不提供虚假的 Global PASS

默认禁止输出：

```text
Simulation is physically correct.
```

可以输出：

```text
Numerical stability is supported for the tested
resolution, physical domain, and propagation configuration
at the requested tolerance.
```

或者：

```text
Validation incomplete:
input-resolution convergence was not available.
```

---

# 52. Validation State

整个 report 可以有 summary state：

```text
SUPPORTED_AT_TOLERANCE
NOT_CONVERGED
UNVERIFIED
OUT_OF_SCOPE
```

如果存在多个维度，则分别输出：

```text
input_resolution
physical_domain
algorithmic_padding
propagator_sampling
model_approximation
reference_agreement
```

不要压成一个无法解释的分数。

---

# 53. Report Result Schema

每个 item 至少包含：

```text
id
title
category
assessment_type
applicable_methods
value
unit
status
formula
assumptions
threshold
threshold_provenance
source
interpretation
recommended_action
```

例如：

```text
id:
asm.phase_step

assessment_type:
DIAGNOSTIC

value:
11.7π

status:
INFO

interpretation:
The analytical ASM transfer-function phase changes
rapidly between adjacent frequency samples in the
selected spectral support.

threshold:
none

recommended_action:
Run the literature-derived ASM sampling criterion
and padding/domain convergence.
```

---

# 54. Source 信息

Formal checker 必须记录：

```text
authors
title
year
DOI
equation / section if possible
```

不要只写：

```text
according to literature
```

---

# 55. Propagation Adapter

核心 checker 与具体 propagation library 分离。

概念接口：

```python
result = propagate(
    field,
    input_grid,
    output_grid,
    wavelength,
    z,
    configuration,
)
```

返回：

```text
complex field
x coordinates
y coordinates
metadata
```

---

# 56. V1 Backend

优先建立一个稳定 backend。

推荐：

```text
waveprop
```

原因不是把 waveprop 当标准答案，而是它已经同时提供：

- Fraunhofer；
- Fresnel；
- ASM；
- evanescent handling；
- bandlimited ASM；
- DI；
- FFT-DI；

并有 square aperture 和 band-limiting examples。

---

# 57. TorchOptics Adapter

第二个 adapter：

```text
TorchOptics
```

主要用于：

> differentiable optics example。

重点研究：

```text
Field
PlanarGrid
spacing
shape
ASM
DIM
asm_pad
output sampling
```

不用研究整个 TorchOptics API。

TorchOptics 当前明确把 field geometry 与 propagation configuration 分开，并提供 ASM / DIM 及 Fresnel variants；ASM 默认 padding 也说明成熟库本身将 FFT boundary effect 当作实现层重要问题。

---

# 58. Mature Library 调研边界

执行 Agent 只需要研究以下内容。

### waveprop

目标：

```text
coordinate convention
padding
bandlimit
DI
ASM
output coordinates
```

### TorchOptics

目标：

```text
data model
grid representation
padding
output plane
method selection
```

### Diffractio

目标：

```text
quality_factor design
how numerical quality is exposed to users
```

### OpticStudio POP

目标：

```text
sampling vs array width
guard band
engineering warnings
```

OpticStudio 官方明确指出 array width 太大可能导致 beam 上 sampling 不足，而 width 太小又会发生 aliasing，因此实际软件也不会把“单纯增大窗口”当成无条件改善。

这些库：

> 只作为工程设计与文献定位参考。

禁止因为调研成熟库而增加 V1 功能范围。

---

# 59. Square Aperture Benchmark

保留原文章参数作为 regression scenario：

$$
N=512
$$

$$
\Delta x=2\,\mu m
$$

$$
\lambda=532\,nm
$$

$$
a=100\,\mu m.
$$

测试：

$$
z=
1,\ 10,\ 100,\ 150\,mm.
$$

由定义：

$$
L=1.024\,mm
$$

$$
\Delta f\approx976.6\,m^{-1}
$$

$$
f_N=250\,mm^{-1}.
$$

这些 derived values 应精确复现。

---

# 60. 原文章结果不是 Golden Truth

原文章中出现：

$$
\eta_{\rm edge}\approx0.42\%
$$

以及不同 MSE / phase-step 数值。

这些可以用于：

```text
replication sanity
```

但不能直接 hard-code 成：

```text
assert value == article_value
```

必须确认：

- FFT normalization；
- field definition；
- frequency coordinates；
- ROI；
- padding；
- backend version；
- interpolation；
- bandlimit implementation。

---

# 61. Square Aperture Analytic Scale

方孔 Fraunhofer 第一零点：

$$
x_1\approx\frac{\lambda z}{a}.
$$

对应：

```text
1 mm    ≈ 5.32 μm
10 mm   ≈ 53.2 μm
100 mm  ≈ 532 μm
150 mm  ≈ 798 μm
```

它是非常有用的 physical-scale reference。

但：

> 不能拿远场 formula 去验证近场完整 field。

只比较它真正适用的量。

---

# 62. Benchmark 必须制造多个 Failure Mode

测试至少包括：

```text
well-resolved / short-distance case
insufficient domain case
insufficient internal padding case
ASM sampling-risk case
Fresnel approximation difference
Fraunhofer misuse
```

Validator 应能分别解释。

不要设计成：

```text
bad case → 一个红灯
```

---

# 63. Self-Accelerating Beam Case

使用已有研究 field。

目的不是学习新的 accelerating-beam theory。

流程：

```text
field generator
→ z sweep
→ validator
→ propagation
→ convergence
```

输出随 z 变化的：

```text
domain convergence
padding convergence
ASM diagnostics
```

重点展示：

> 同一个 grid 并不会因为 z 改变后仍然自动有效。

---

# 64. Accelerating Beam 的窗口检查

这类场可能不是 compact support。

因此必须展示新版架构的重要区别：

```text
old-array zero padding
```

不能替代：

```text
regenerate field on larger physical domain
```

这也是它比方孔更真实的 test。

---

# 65. Differentiable Optics Case

建立最小 pipeline：

```text
trainable phase
→ complex field
→ propagation
→ target
→ loss
→ backward
→ optimizer
```

构造两组 setup。

---

# 66. Case A：Numerically Weak Setup

故意选择至少一个经过 benchmark 验证的 numerical problem：

例如：

```text
insufficient physical domain
```

或：

```text
ASM transfer-function sampling problem
```

训练仍然运行。

展示：

$$
Loss\downarrow.
$$

---

# 67. Case B：Numerically Supported Setup

通过：

```text
resolution convergence
domain convergence
padding convergence
method-specific check
```

获得更可靠的 setup。

重新训练。

---

# 68. Differentiable Optics 最终比较

至少显示：

```text
loss curve
phase map
output intensity
validation report
independent forward verification
```

最重要的是：

> 把优化后 phase 放进更严格的 / independently validated propagation configuration，再验证性能。

如果：

```text
training propagator performance 很好
```

但：

```text
validated propagator performance 崩掉
```

这就是最直观的 numerical overfitting evidence。

---

# 69. Checker Specification 文档

正式写代码之前必须产出：

```text
docs/check-spec.md
```

至少有以下表：

| Check | Type | Failure mode | Formula | Applicability | Threshold | Source | Validation |
|---|---|---|---|---|---|---|---|
| Grid identities | Derived | — | exact | all | — | DFT | unit |
| Spectral edge energy | Diagnostic | spectral crowding | defined | sampled field | configurable | project | synthetic |
| Resolution convergence | Convergence | spatial undersampling | numerical | regeneratable source | user tol | numerical analysis | refinement |
| Domain convergence | Convergence | finite-domain error | numerical | all | user tol | numerical analysis | enlargement |
| FFT padding convergence | Convergence | periodic/circular artifact | numerical | FFT methods | user tol | implementation | padding sweep |
| ASM phase step | Diagnostic | transfer-function variation | analytic | ASM | none | explanatory | BLAS cases |
| ASM admissible band | Formal | ASM aliasing | paper-derived | ASM | paper | Matsushima | paper replication |
| Fresnel remainder | Diagnostic | paraxial approximation | analytic | Fresnel | user/project | expansion | ASM comparison |
| Fresnel number | Diagnostic | Fraunhofer regime | analytic | aperture known | none | Fourier optics | analytic |
| Reference agreement | Cross-ref | aggregate discrepancy | metric | available reference | user tol | numerical | benchmark |

正式开发过程中可以细化，但不能删除其分类。

---

# 70. Unit Tests

至少覆盖：

### Grid identities

$$
L=N\Delta x
$$

$$
\Delta f=1/L
$$

$$
f_N=1/(2\Delta x).
$$

### Padding relation

如果 computational array：

$$
N\rightarrow2N
$$

且：

$$
\Delta x=\text{constant}
$$

则：

$$
L_{\rm computational}\rightarrow2L
$$

$$
\Delta f\rightarrow\Delta f/2.
$$

### Global phase invariance

若：

$$
U_2=U_1e^{i\alpha}
$$

则 aligned complex-field error：

$$
\epsilon_U\approx0.
$$

### Scaling invariance

对于 normalized spectral-energy metrics：

$$
U\rightarrow cU
$$

结果应保持不变。

### Coordinate consistency

x/y ordering、rows/columns、FFT frequencies 必须测试。

waveprop README 特别说明第一 array dimension 对应 y、第二 dimension 对应 x，因此 adapter 不能假设所有库使用相同 dimension convention。

---

# 71. Synthetic Tests

创建少量纯 numerical synthetic fields。

用途：

```text
known band-limited field
near-Nyquist sinusoid
single plane wave
global-phase-shifted copy
```

这不是新的 optical application。

只是检验 checker 自己。

例如 near-Nyquist sinusoid 应明显出现在 spectral diagnostic 中。

---

# 72. Convergence Tests

## Resolution

要求 FieldSource。

验证：

$$
L=\text{fixed}
$$

$$
\Delta x\downarrow.
$$

## Physical domain

要求：

$$
\Delta x=\text{fixed}
$$

$$
L\uparrow.
$$

非 compact field 必须 regenerate。

## Padding

physical problem 不变：

```text
pad 0
pad 1×
pad 2×
...
```

检查 convergence。

---

# 73. Error Injection Tests

建议主动构造：

```text
undersampled input
too-small window
no padding
long-distance unbandlimited ASM
wrong Fraunhofer regime
```

确认 report 能定位相应风险。

这比只测试 happy path 更重要。

---

# 74. Formal ASM Criterion Verification

如果实现 Matsushima criterion：

必须至少 reproducing 一个：

```text
standard ASM visibly wrong
BLAS corrected
```

的 paper-like numerical scenario。

然后再用：

```text
waveprop implementation
```

交叉验证。

如果无法完成这一点：

criterion 暂时标：

```text
EXPERIMENTAL
```

而不是正式发布。

---

# 75. API 最低目标

最终用户体验可类似：

```python
report = validate(
    source=source,
    grid=grid,
    wavelength=wavelength,
    z=z,
    propagator=config,
    tolerance=tolerance,
)
```

如果只有 array：

```python
report = validate(
    field=array,
    ...
)
```

validator 自动知道：

```text
resolution convergence unavailable
```

---

# 76. Dynamic Validation API

可以类似：

```python
report.run_resolution_convergence()
report.run_domain_convergence()
report.run_padding_convergence()
```

或者 config-driven。

具体命名可改变。

核心语义不能混淆。

---

# 77. Output

至少：

```text
terminal / text summary
JSON
```

推荐：

```text
plots
```

例如：

```text
spectrum
spatial edge
convergence curve
ASM admissible region
```

但 UI 不属于核心阶段。

---

# 78. JSON 目的

JSON 应可供：

- CI；
- Jupyter；
- future Web UI；
- VSCode；
- differentiable-optics pipeline；

消费。

不要把 report 只做成 print。

---

# 79. 工程目录建议

不是强约束。

```text
core/
    grid
    field
    simulation
    coordinates
    report

diagnostics/
    spectrum
    boundaries
    asm_phase
    model_regime

criteria/
    asm_sampling

convergence/
    resolution
    domain
    padding
    output_grid

metrics/
    intensity
    field
    phase
    power

adapters/
    waveprop
    torchoptics

benchmarks/
    square_aperture

examples/
    accelerating_beam
    differentiable_optics

tests/
docs/
```

最重要的原则：

> 按 numerical responsibility 分层。

不要按：

```text
square_aperture_checker
air_beam_checker
inverse_design_checker
```

组织。

---

# 80. 实施 Phase 0：Research Audit

这是新版新增的强制阶段。

Agent 首先：

1. 读取原文章；
2. 建 candidate-check list；
3. 获取关键论文；
4. 对每个 checker 判断理论身份；
5. 删除没有清楚意义的判定；
6. 给所有 threshold 标来源；
7. 完成 `check-spec.md`。

这一阶段：

> 不写正式 checker implementation。

---

# 81. Phase 0 必读来源

### Shen & Wang, 2006

Fabin Shen, Anbo Wang

“Fast-Fourier-transform based numerical integration method for the Rayleigh–Sommerfeld diffraction formula”

Applied Optics 45, 1102–1110.

DOI：

```text
10.1364/AO.45.001102
```

重点：

```text
sampling
computation window
FFT-AS
FFT-DI
numerical accuracy
```


---

# 82. Matsushima & Shimobaba, 2009

“Band-Limited Angular Spectrum Method for Numerical Simulation of Free-Space Propagation in Far and Near Fields”

Optics Express 17, 19662–19673.

DOI：

```text
10.1364/OE.17.019662
```

重点：

```text
ASM transfer function
sampling
aliasing
band limit
admissible spectral region
```


---

# 83. Voelz & Roggemann, 2009

“Digital simulation of scalar optical diffraction: revisiting chirp function sampling criteria and consequences”

Applied Optics 48, 6132–6142.

DOI：

```text
10.1364/AO.48.006132
```

重点：

```text
ideal sampling
undersampling
oversampling
different FFT propagation formulations
sampling consequences
```

这篇尤其用于防止项目错误地寻找：

> one universal diffraction sampling rule。


---

# 84. 成熟实现参考

只读与本项目相关部分：

```text
waveprop
TorchOptics
Diffractio
OpticStudio POP documentation
```

不要求用户本人阅读。

执行 Agent 自行使用 web / repository / docs 工具完成。

---

# 85. Phase 1：Core Data Model

实现：

```text
Simulation Contract
Grid
SampledField
FieldSource
OutputPlane
PropagationConfig
ROI
ReportResult
```

验收：

> 可以完整描述一个 simulation，而不运行 propagation。

---

# 86. Phase 2：Derived Quantities + Diagnostics

实现：

```text
grid derived quantities
FFT spectrum
spectral energy
energy quantiles
spectral-edge diagnostic
spatial-edge diagnostic
ASM analytical phase-step diagnostic
Fresnel-number diagnostic
Fresnel phase remainder
evanescent diagnostic
```

这时：

> 不需要 propagator backend。

验收：

```text
static report
```

已经可运行。

---

# 87. Phase 3：Metrics + Coordinate Alignment

实现：

```text
physical ROI
common grid
intensity error
complex-field error
global phase alignment
phase mask
power diagnostic
```

这是所有 convergence 的公共基础。

在此阶段先把：

```text
x/y
shape
spacing
offset
```

处理正确。

不要急着做 applications。

---

# 88. Phase 4：Convergence Engine

实现三个独立模块：

```text
resolution convergence
physical-domain convergence
algorithmic-padding convergence
```

如果 backend 支持：

```text
output-grid convergence
```

可作为 conditional feature。

验收：

validator 已经能回答：

```text
改变 numerical discretization 后，
结果是否在 tolerance 内稳定？
```

这是 V1 最重要的里程碑。

---

# 89. Phase 5：Propagation Adapters

先：

```text
waveprop
```

再：

```text
TorchOptics
```

每个 adapter 必须有：

```text
coordinate tests
normalization tests
simple propagation tests
metadata tests
```

禁止直接假设两个 library coordinate convention 一样。

---

# 90. Phase 6：ASM Formal Sampling Criterion

在 Phase 0 的研究结果基础上：

实现 Matsushima method-specific condition。

注意：

> 只有研究已经足够明确时才实现。

否则：

```text
defer formal criterion
```

并保留：

```text
phase diagnostic
+
convergence
+
BLAS comparison
```

项目宁可少一个 checker，也不能放一个错误的“标准”。

---

# 91. Phase 7：Square Aperture Regression

复现文章。

至少输出：

```text
1 / 10 / 100 / 150 mm
```

下：

```text
ASM
Fresnel
Fraunhofer
DI
```

以及：

```text
resolution convergence
domain convergence
padding convergence
BLAS comparison
reference comparison
```

如果这一阶段不能解释实验趋势：

> 禁止进入 application demo。

---

# 92. Phase 8：Accelerating Beam

只替换：

```text
FieldSource
```

checker architecture 不变。

使用多个 z。

重点验证：

```text
domain enlargement
noncompact input
z-dependent propagation risk
```

---

# 93. Phase 9：Differentiable Optics

建立：

```text
bad numerical configuration
validated configuration
```

两个 inverse-design 实验。

最终将训练出的设计拿到：

```text
independent / stricter propagation configuration
```

验证。

这一步是整个项目最重要的展示案例。

---

# 94. Phase 10：Report / CLI / Documentation

最后才做：

```text
CLI
pretty console output
JSON
figures
README
examples
```

不要先做 Web 页面。

---

# 95. README 结构

推荐：

```text
Why this project exists

30-second example

What this project can validate

What it cannot validate

Validation hierarchy

Diagnostics vs criteria vs convergence

Example: square aperture

Example: accelerating beam

Example: differentiable optics

How to interpret UNVERIFIED

Backends

References
```

---

# 96. README 首要声明

README 需要明确：

> This toolkit does not prove physical correctness.

它只提供：

> evidence about numerical stability and known sampling / discretization risks within the tested scalar propagation model.

---

# 97. CLI 报告示例

最终风格可以类似：

```text
NUMERICAL PROPAGATION VALIDATION

Simulation
----------------------------------
Grid              512 × 512
Spacing           2.0 μm
Window            1.024 mm
Wavelength        532 nm
Distance          100 mm
Method            ASM

Derived
----------------------------------
Δf                 976.6 m⁻¹
Nyquist            250 mm⁻¹

Diagnostics
----------------------------------
Spectral edge       0.42 %
ASM phase step      ...
Boundary energy     ...

Formal criteria
----------------------------------
ASM sampling        ...

Convergence
----------------------------------
Input resolution    UNVERIFIED
Domain              NOT CONVERGED
FFT padding         NOT CONVERGED

Reference
----------------------------------
DI agreement        ...

Summary
----------------------------------
Numerical reliability has not yet
been demonstrated at the requested tolerance.
```

---

# 98. Agent 在遇到不确定公式时必须做什么

禁止：

```text
凭记忆实现
```

必须：

```text
search paper
→ inspect equation
→ inspect assumptions
→ inspect implementation
→ construct numerical test
```

建议 query：

```text
Matsushima band limited angular spectrum sampling condition

Matsushima ASM transfer function aliasing derivation

Voelz Roggemann chirp sampling criteria

Shen Wang FFT AS sampling computation window

waveprop bandlimit angular spectrum implementation

TorchOptics ASM pad propagation

Diffractio RS quality factor

Zemax POP guard band sampling aliasing
```

---

# 99. Source Priority

原则：

```text
peer-reviewed paper / textbook
>
official documentation
>
mature open-source source code
>
blog
```

原项目文章属于：

```text
problem definition + experiment source
```

不能压过 primary literature。

---

# 100. 如果来源冲突

Agent 必须记录：

```text
what differs
different assumptions?
different FFT convention?
different propagation formulation?
different definition?
implementation bug?
```

然后做实验。

禁止为了复现旧文章：

> 修改数学定义去凑数字。

---

# 101. Performance

V1 首先追求：

```text
correctness
traceability
explainability
```

不是：

```text
GPU optimization
maximum speed
```

Convergence 本身就可能需要多次 propagation。

性能优化放在正确性之后。

---

# 102. Cache

后续可以缓存：

```text
FFT spectrum
frequency grid
derived quantities
propagation runs
```

避免重复计算。

但 cache 不属于最先实施内容。

---

# 103. Reproducibility

每份 report 应记录：

```text
package version
backend version
dtype
device
grid
wavelength
z
configuration
tolerances
```

因为 numerical result 可能受：

```text
float32 / float64
CPU / GPU
backend implementation
```

影响。

---

# 104. Precision

基准测试优先使用：

```text
float64 / complex128
```

建立 reference。

应用层可使用：

```text
float32 / complex64
```

但最好提供 precision comparison。

这不需要成为核心 checker，可以作为 reproducibility metadata / optional convergence test。

---

# 105. 最终 Definition of Done

V1 必须满足以下条件。

## Contract

可以描述 arbitrary 2D sampled scalar field。

可以描述 regeneratable continuous/parametric field source。

---

## Derived

正确计算：

$$
L,\Delta f,f_N
$$

和 frequency coordinates。

---

## Diagnostics

至少具备：

```text
spectrum
spectral edge
effective spectral support
spatial boundary
ASM phase-step
Fresnel/Fraunhofer regime information
evanescent information
```

---

## Convergence

必须严格区分并实现：

$$
\boxed{\text{resolution convergence}}
$$

$$
\boxed{\text{physical-domain convergence}}
$$

$$
\boxed{\text{algorithmic-padding convergence}}
$$

---

## Reference

至少支持：

```text
intensity comparison
complex-field comparison
global-phase alignment
```

---

## ASM

正式实现：

```text
literature-derived ASM criterion
```

或者：

如果未能充分验证，

明确留为：

```text
not implemented / experimental
```

绝不能使用旧文章的 $\Delta\phi<\pi$ 冒充 formal standard。

---

## Backends

至少一个 production-ready propagator adapter。

推荐：

```text
waveprop
```

并完成：

```text
TorchOptics
```

用于 differentiable optics example。

---

## Benchmark

Square aperture benchmark 能复现：

```text
short-distance agreement
long-distance finite-grid problems
padding/domain improvements
BLAS effect
model-approximation differences
```

不要求精确复制旧文章每个浮点数。

---

## Applications

完成：

```text
self-accelerating beam
differentiable optics
```

两个真实案例。

---

## Report

至少：

```text
human-readable
JSON
```

并明确区分：

```text
derived
diagnostic
formal criterion
convergence
cross-reference
scope
```

---

## Documentation

每个 checker 都能回答：

```text
它在检查什么？
公式是什么？
适用于什么方法？
假设是什么？
它属于哪种 evidence？
threshold 从哪里来？
没通过说明什么？
通过又能证明到什么程度？
下一步应该怎么做？
```

---

# 106. 最终开发原则

如果实现过程中需要在：

> “多做几个 checker”

与：

> “证明已有 checker 的含义是正确的”

之间选择：

永远选后者。

如果需要在：

> “支持更多 optics applications”

与：

> “把 resolution / domain / padding convergence 做正确”

之间选择：

永远选后者。

如果一个指标：

> 有解释价值，但没有可靠 threshold

就让它保持：

```text
DIAGNOSTIC
```

不要为了让 report 看起来更像成熟产品而制造 PASS / FAIL。

最终项目的价值不是：

> 提供一堆绿色勾。

而是：

$$
\boxed{
\text{把 numerical diffraction 中“为什么相信这个结果”变成一套可复现、可追踪的工程证据。}
}
$$
