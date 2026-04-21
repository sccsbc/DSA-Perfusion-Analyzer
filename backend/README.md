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

## 支持的数据格式

- 单文件多帧 DICOM（`.dcm`）
- 多文件 DICOM 序列（整个文件夹）
