# DSA 灌注分析工具

DSA 灌注参数计算脚本，支持医生交互式点选 AIF 和 ROI，自动计算灌注参数。

---

## 快速开始

### 方式一：有 Conda（推荐）

```bash
cd backend

# 第一次：创建环境
conda env create -f environment.yml

# 每次使用前：激活环境
conda activate dsa-perfusion

# 运行分析
python src/interactive_picker.py "你的dicom文件路径.dcm" "输出目录/"
```

### 方式二：没有 Conda（用 Python 自带 venv）

```bash
cd backend

# 第一次：创建虚拟环境
python -m venv .venv

# 每次使用前：激活虚拟环境
# macOS / Linux:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# 第一次：安装依赖
pip install -r requirements.txt

# 运行分析
python src/interactive_picker.py "你的dicom文件路径.dcm" "输出目录/"
```

---

## 使用流程

1. **运行命令**，等待弹窗显示 DSA 图像
2. **鼠标点击选点**（顺序不能错）：
   - 第 1 个点 = **AIF**（红色标记）
   - 第 2~4 个点 = **ROI**（绿、蓝、黄色标记）
3. **选完 4 个点后按 Enter 键**（或关闭窗口），程序继续计算
4. 查看弹出的结果图表（TIC 曲线、参数表、Residue Function）
5. 结果自动保存到输出目录：
   - `result.json` — 数值结果
   - `analysis.png` — 结果图表

---

## AIF 选点建议

选择 **颈内动脉床突上段**（supraclinoid ICA），大致位于 **蝶鞍上方**、颈内动脉入颅后的第一段。位置正确对后续计算影响很大。

---

## 输出参数说明

| 参数 | 说明 |
|------|------|
| TTP | Time-to-Peak，达峰时间（秒） |
| AUC | Area Under Curve，曲线下面积 |
| Wash-in slope | 最大上升斜率 |
| DSA-CBF | 脑血流量（反卷积计算） |
| DSA-MTT | 平均通过时间 |
| DSA-Tmax | 最大残留函数时间 |

---

## 反卷积参数计算方法

基于指示剂稀释理论（Indicator Dilution Theory）和 SVD 反卷积。

### 1. 理论基础

ROI 区域的时间-密度曲线 `Cvoi(t)` 与 AIF 的 `Cart(t)` 满足卷积关系：

```
Cvoi(t) = CBF · ρvoi · (Cart * r)(t)
```

- `CBF`：脑血流量（待求）
- `ρvoi`：ROI 区域的平均像素强度
- `r(t)`：residue function（残留函数），max(r(t)) = 1
- `*`：卷积运算

### 2. SVD 反卷积

将上式改写为矩阵形式 `A · k = Cvoi`，其中 A 是由 `Cart(t)` 构建的下三角循环矩阵。

对 A 做 SVD 分解：`A = U · S · V^T`

求解 flow-scaled residue function：

```
k(t) = V · diag(1/s_i) · U^T · Cvoi(t) = CBF · ρvoi · r(t)
```

**正则化**：截断小于 `0.05 · s_max` 的奇异值，抑制噪声放大。

### 3. 参数计算公式

```
DSA-CBF   = max(k(t)) / ρvoi
DSA-Tmax  = argmax{k(t)} × dt          (dt 为帧间隔时间)
DSA-CBV   = sum(k(t)) × dt / ρvoi
DSA-MTT   = DSA-CBV / DSA-CBF
```

### 4. 预处理步骤

1. **基线校正**：TIC 减去前 3 帧的平均值
2. **时间域高斯滤波**：sigma = 1.0，平滑降噪
3. **非负截断**：将负值置 0，避免数值问题

---

## 支持的数据格式

- 单文件多帧 DICOM（`.dcm`）
- 多文件 DICOM 序列（整个文件夹）
