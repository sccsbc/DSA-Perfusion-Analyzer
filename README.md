# DSA 灌注分析系统

数字减影血管造影（DSA）灌注参数分析工具。医生在 DSA 图像上手动点选动脉输入函数（AIF）和感兴趣区（ROI），系统自动计算 TTP、AUC、Wash-in Slope、DSA-CBF、DSA-MTT、DSA-Tmax、DSA-CBV 等灌注参数，并通过时间-强度曲线和参数表展示结果。

## 技术栈

| 层 | 技术 |
|---|------|
| 前端 | Vue 3 + TypeScript + Naive UI + ECharts + Pinia |
| 后端 | Python FastAPI + NumPy + SciPy + pydicom |
| 计算核心 | SVD 反卷积（指示剂稀释理论） |

## 环境要求

- **Python** 3.11+（推荐 conda）
- **Node.js** 18+

## 快速开始

### 1. 后端

```bash
cd backend

# 方式一：conda（推荐）
conda env create -f environment.yml
conda activate dsa-perfusion

# 方式二：venv + pip
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 启动后端（端口 8000）
python run.py
```

### 2. 前端

```bash
cd frontend
npm install
npm run dev          # 启动开发服务器（端口 5173）
```

### 3. 一键启动

```bash
./start.sh           # 同时启动前后端
```

浏览器打开 `http://localhost:5173`。

## 使用流程

1. **上传 DICOM** — 点击「选择 DICOM 文件」选择 `.dcm` 文件（支持单文件多帧 DICOM）
2. **调整半径** — 工具栏滑动条调节圆圈大小（1-20px），鼠标移到图上可预览圆圈范围
3. **放置选点** — 在 DSA 图像上依次点击：
   - 第 1 个点 = **AIF**（红色）— 动脉输入函数，建议选颈内动脉床突上段
   - 第 2~4 个点 = **ROI**（绿/蓝/橙）— 感兴趣区
4. **切换帧** — 用滑块或键盘 ← → 切换帧，找到造影剂充盈最佳的帧
5. **分析** — 点击「开始分析」（或按 Enter），右侧面板显示结果

### 键盘快捷键

| 键 | 功能 |
|----|------|
| ← → | 切换帧 |
| Enter | 开始分析 |

## 输出参数

### TIC 参数（基于时间-密度曲线）

| 参数 | 说明 |
|------|------|
| TTP | Time-to-Peak，达峰时间（秒） |
| AUC | Area Under Curve，曲线下面积 |
| Wash-in Slope | 最大上升斜率 |

### 反卷积参数（SVD 反卷积）

| 参数 | 说明 |
|------|------|
| DSA-CBF | 脑血流量 |
| DSA-MTT | 平均通过时间（秒） |
| DSA-Tmax | 最大残留函数时间（秒） |
| DSA-CBV | 脑血容量 |

### 计算方法

基于指示剂稀释理论，ROI 时间-密度曲线 Cvoi(t) 与 AIF 满足卷积关系：

```
Cvoi(t) = CBF · ρvoi · (Cart ∗ r)(t)
```

通过 SVD 反卷积求解 flow-scaled residue function k(t)，自动截断小于 5% 最大奇异值的噪声分量。参数计算：

```
DSA-CBF   = max(k(t)) / ρvoi
DSA-Tmax  = argmax{k(t)} × dt
DSA-CBV   = Σ k(t) × dt / ρvoi
DSA-MTT   = DSA-CBV / DSA-CBF
```

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/dicom/upload` | 上传 DICOM，返回 study 元数据 |
| GET | `/api/studies/{id}` | 获取 study 信息 |
| GET | `/api/studies/{id}/frames/{idx}` | 获取帧图像（PNG） |
| POST | `/api/studies/{id}/analyze` | 提交 AIF/ROI 坐标进行分析 |

## 项目结构

```
dsa/
├── backend/
│   ├── src/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── models.py            # Pydantic 数据模型
│   │   ├── services.py          # 业务逻辑层
│   │   ├── dicom_parser.py      # DICOM 解析
│   │   ├── tic_extractor.py     # TIC 提取
│   │   ├── perfusion_params.py  # TIC 参数计算
│   │   ├── deconvolution.py     # SVD 反卷积
│   │   └── interactive_picker.py # matplotlib 交互脚本（独立使用）
│   ├── tests/                   # pytest 测试
│   └── run.py                   # 启动脚本
├── frontend/
│   └── src/
│       ├── pages/               # HomePage, AnalysisPage
│       ├── components/          # DsaViewer, FrameNavigator, TicChart, ...
│       ├── stores/              # Pinia studyStore, analysisStore
│       ├── api/                 # axios + API 封装
│       └── types/               # TypeScript 类型定义
└── start.sh                     # 一键启动脚本
```

## 开发

```bash
# 后端测试
cd backend && conda activate dsa-perfusion && python -m pytest tests/ -v

# 前端类型检查
cd frontend && npx vue-tsc -b
```
