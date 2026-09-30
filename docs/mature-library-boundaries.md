# 成熟库（Mature Library）调研边界与工程设计参考

本文档规范本项目在调研与参考外部成熟光学传播库（`waveprop`、`TorchOptics`、`Diffractio`、`OpticStudio POP` 等）时的**核心关注点**、**工程边界**与**硬性约束**。

---

## 1. 核心定位与防范围膨胀红线

外部成熟库在本项目中的定位是：
> **只作为工程设计与文献定位参考，严禁因为调研成熟库而增加 V1 功能范围。**

### 明确不纳入 V1 的特性（保持 OUT_OF_SCOPE）
- 偏振与矢量高 NA 衍射（Vectorial / High-NA diffraction）
- 麦克斯韦全波求解（FDTD, RCWA, Maxwell solvers）
- 多波长 / 宽谱色散传播（Polychromatic propagation）
- 几何光学 / 透镜系统追踪与成像容差（Lens surface optimization / Ray tracing）
- 实验测量标定与硬件控制（Hardware calibration / SLM controls）

本项目 V1 专注于：**单色标量 2D 横向光场在自由空间基于 FFT/衍射数值传播的可靠性与稳定性评估**。

---

## 2. 目标库调研重点清单

执行 Agent 或开发者在调研成熟库时，**只关注**以下底层数值机制与工程设计：

### 2.1 waveprop
- **定位**：Python 标量波动光学传播库，项目当前的首选底层适配与交叉验证参考。
- **重点关注项**：
  1. `coordinate convention`：坐标轴与数组维度顺序（`(Ny, Nx)` 对应 $(y, x)$）、零中心化（`np.arange(-N/2, N/2) * delta`）。
  2. `padding`：频域/空间域零填充策略（如 $2N \times 2N \to N \times N$ 裁剪以模拟线性卷积、抑制周期循环卷积假象）。
  3. `bandlimit`：Matsushima & Shimobaba (2009) 频带限制角谱法（BLAS）的实现细节与边界条件。
  4. `DI (Direct Integration)`：瑞利-索末菲积分 baseline 与 Shen & Wang (2006) 的 FFT-DI 卷积核实现。
  5. `ASM`：角谱传递函数构造、消逝波（evanescent wave）指数衰减截断处理。
  6. `output coordinates`：单步/两步 Fresnel 和 Fraunhofer 导致的输出坐标缩放 $\Delta x_{\rm out} = \frac{\lambda z}{N \Delta x_{\rm in}}$。
- **关联文档**：参见 [docs/waveprop-notes.md](file:///Users/janicelan/obsidian/opticsMe/numerical-calculation/optical-propagation-sanity-check/docs/waveprop-notes.md)。

---

### 2.2 TorchOptics
- **定位**：基于 PyTorch 的可微波动光学库。
- **重点关注项**：
  1. `data model`：张量数据结构、批处理（Batch）维度处理、实部虚部与复数张量表达。
  2. `grid representation`：显式网格张量与物理步长的关联管理方式。
  3. `padding`：自动 padding 机制与 GPU 加速下的内存对齐。
  4. `output plane`：输出平面的网格重构与任意探测器间距适配方案。
  5. `method selection`：根据传播距离 $z$、波长 $\lambda$ 与网格尺寸在 ASM / Fresnel 之间的自动分流逻辑。

---

### 2.3 Diffractio
- **定位**：功能丰富的经典 Python 衍射与光学元件仿真库。
- **重点关注项**：
  1. `quality_factor design`：其内部的品质因数（Quality Factor）设计公式、采样充分性判定阈值。
  2. `how numerical quality is exposed to users`：数值质量信息在 API 与可视化界面中是如何向用户提示的（如 warning 机制、网格诊断提示、参数推荐）。

---

### 2.4 OpticStudio POP (Physical Optics Propagation)
- **定位**：工业级商业光学设计软件的物理光学传播模块。
- **重点关注项**：
  1. `sampling vs array width`（采样率与阵列宽度的工程权衡）：
     > **核心工程洞察**：OpticStudio 官方明确指出，**array width 太大可能导致 beam 上的有效 sampling 点不足，而 width 太小又会发生 aliasing**。因此工业界软件也绝不会把“单纯增大计算窗口”当成无条件的改善。
  2. `guard band`：保护带（Guard Band）比例的经验取值，光束边缘衰减到机器精度或背景噪声的工程裕量。
  3. `engineering warnings`：工业软件针对 phase aliasing、edge clipping、waist sampling 不足时的诊断警告机制。

---

## 3. 调研产出与资产沉淀规范

1. **调研输出物位置**：所有对成熟库的代码审查、公式推导与复现笔记统一存放在 `docs/` 下（如 `docs/<library>-notes.md`）。
2. **记录格式要求**：
   - 必须记录：库版本、坐标系约定、FFT 归一化规范、主要函数签名与数学依据。
   - 必须记录发现的上游缺陷或陷阱（Upstream Quirks / Edge Cases）。
3. **接口设计隔离**：
   - 核心领域模型（`src/optical_propagation_sanity_check/core/`）保持纯粹，不依赖任何第三方库的专有数据结构。
   - 外部库的具体调用必须封装在 `adapters/` 中（如当前已有 `WavepropAdapter`，未来若引入 TorchOptics 则写 `TorchOpticsAdapter`）。
