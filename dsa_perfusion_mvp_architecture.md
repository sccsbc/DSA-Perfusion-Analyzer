# DSA 灌注分析软件（MVP）架构设计与交互方案

> 技术栈：Vue 3 (前端) + Python (后端)  
> 部署模式：医院内网本地化部署 / 单机版浏览器访问  
> 依据文档：`dsa_perfusion_mvp_research.md`  
> 记录日期：2025-04-14

---

## 1. 技术选型确认与理由

### 1.1 前端：Vue 3 + TypeScript
**选择理由**：
- 用户对 Vue 生态熟悉，开发效率高。
- 医学影像标注工具天然是“组件化”的：播放器、图层叠加、侧边数据面板、图表，Vue 的组件化和响应式状态管理非常适合。
- 可以通过浏览器运行，避免了跨平台桌面客户端的打包和分发问题（在医院场景下，打开浏览器访问 `localhost` 或内网 IP 是最简单的部署方式）。

**推荐配套库**：
| 库 | 用途 | 理由 |
|----|------|------|
| **Vue 3 (Composition API)** | 核心框架 | 更好的 TS 支持，逻辑复用更灵活 |
| **Pinia** | 状态管理 | 比 Vuex 更轻量，TypeScript 友好 |
| **Element Plus / Arco Design** | UI 组件库 | 医学工具需要稳健的表格、按钮、滑块、弹窗 |
| **ECharts** | TIC 曲线绘制 | 国产成熟库，时间序列曲线、多系列对比非常成熟 |
| **Fabric.js / Konva.js** | Canvas 标注交互 | 在 DSA 图像上画圆/矩形/点，并支持拖拽调整 |

### 1.2 后端：Python + FastAPI
**选择理由**：
- Python 是医学图像处理（`pydicom`, `numpy`, `scipy`, `scikit-image`）的事实标准语言。
- FastAPI 比 Flask 在异步 IO、API 文档自动生成（Swagger UI）、数据校验（Pydantic）方面更现代，适合前后端分离开发。
- 计算任务虽然快（1 秒内），但用 FastAPI 的异步支持可以更好地处理文件上传和并发请求。

**推荐配套库**：
| 库 | 用途 |
|----|------|
| **FastAPI** | Web 框架 |
| **Uvicorn** | ASGI 服务器 |
| **Pydantic** | 数据模型校验 |
| **pydicom** | DICOM 读取 |
| **numpy / scipy / scikit-image** | 数学计算、反卷积、图像处理 |
| **matplotlib / PIL** | 伪彩图生成 |
| **pandas / openpyxl** | 报告导出 |

### 1.3 为什么不直接在前端解析 DICOM？
DICOM 格式复杂，包含多帧、16-bit 灰度、私有标签、JPEG 2000 压缩等。虽然 `cornerstone.js` 可以在浏览器里解析 DICOM，但：
- 需要引入额外的 WADO/DICOM 解析库，增加前端复杂度。
- 前端做像素级计算（反卷积）不现实，必须发到后端做。
- **更优方案**：后端负责解析 DICOM，提取出**帧序列图片（PNG/JPEG）**和**元数据（JSON）**，前端只负责展示普通图片和接收坐标。这样前后端职责清晰，开发成本最低。

---

## 2. 系统整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                           医生工作站（浏览器）                        │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    Vue 3 前端应用                              │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │  │
│  │  │  DSA 播放器   │  │  标注画布     │  │   数据分析面板    │   │  │
│  │  │ (帧序列控制)  │  │ (AIF/ROI)    │  │ (TIC曲线/参数表) │   │  │
│  │  └──────────────┘  └──────────────┘  └──────────────────┘   │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTP (REST API + WebSocket)
                                    │ (医院内网 / localhost)
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Python 后端 (FastAPI)                       │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  API Layer: 文件上传、任务管理、结果查询、报告导出               │  │
│  │  Service Layer: DICOM 解析、TIC 提取、反卷积计算、伪彩图生成    │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              │                                      │
│                              ▼                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  本地文件存储:                                                   │  │
│  │  /uploads/     - 原始 DICOM 文件                                │  │
│  │  /previews/    - 解析后的帧序列 PNG + metadata JSON             │  │
│  │  /results/     - 计算结果 JSON + 伪彩图 PNG + 报告 PDF/Excel    │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

**部署说明**：
- 最轻量模式：医生和软件在同一台电脑上，后端用 `uvicorn main:app --host 127.0.0.1 --port 8000`，前端用 `npm run dev` 或打包成静态文件由 FastAPI 的 `StaticFiles` 直接托管。
- 院内局域网模式：后端部署在一台服务器上，医生通过内网 IP 访问。此时需要考虑**多用户并发**和**数据隔离**（见第 8 节）。

---

## 3. 前端交互设计详述

### 3.1 页面路由设计
建议采用 SPA（单页应用），通过左侧导航栏切换主要功能区：

```
/                      -> 首页（上传 DICOM）
/study/:studyId        -> 核心分析页面（播放器 + 标注 + 分析面板）
/history               -> 历史记录列表
/settings              -> 系统设置（正则化参数、阈值等）
```

### 3.2 核心分析页面 `/study/:studyId` 布局
采用典型的医学影像工作站三栏布局：

```
┌──────────────────────────────────────────────────────────────────────┐
│  顶部工具栏：病例信息 | 播放控制(播放/暂停/逐帧/速度) | 保存/导出按钮  │
├────────────────────┬──────────────────────────┬────────────────────┤
│                    │                          │                    │
│   左侧：DSA 播放器  │     中间：标注画布        │   右侧：数据面板    │
│   + 帧缩略图列表    │     + 伪彩图叠加层        │   + TIC 曲线      │
│                    │                          │   + 参数表格      │
│   [DSA Frame 12]   │   ┌──────────────────┐   │   + ROI 列表      │
│   [DSA Frame 13]   │   │                  │   │                    │
│   [DSA Frame 14]   │   │   [DSA Image]    │   │   ─────────────   │
│   [DSA Frame 15]   │   │   [Overlay]      │   │   📈 TIC 曲线      │
│                    │   │   [AIF Circle]   │   │                    │
│                    │   │   [ROI Square]   │   │   ─────────────   │
│                    │   │                  │   │   📊 参数结果      │
│                    │   └──────────────────┘   │   TTP: 2.1s       │
│                    │                          │   AUC: 145.3      │
│                    │   图层控制：              │   CBF: 0.82       │
│                    │   [ ] 显示血管掩膜        │   MTT: 3.4s       │
│                    │   [x] 显示 DSA-CBF 伪彩图 │   Tmax: 1.2s      │
│                    │   [ ] 显示 DSA-Tmax 伪彩图│                    │
│                    │                          │   ─────────────   │
│                    │                          │   📋 ROI 列表      │
│                    │                          │   ROI-1 [删除]    │
│                    │                          │   ROI-2 [删除]    │
│                    │                          │   ROI-3 [删除]    │
│                    │                          │                    │
└────────────────────┴──────────────────────────┴────────────────────┘
```

### 3.3 DSA 播放器组件设计
**功能需求**：
- 播放/暂停、逐帧前进/后退、跳转到指定帧。
- 播放速度可调（0.5x, 1x, 2x）。
- 时间轴滑块显示当前帧和总帧数。
- 底部缩略图列表（类似视频剪辑软件），方便快速定位关键帧（如对比剂到达帧）。

**技术实现**：
- 后端将 DICOM 解析为 `frame_001.png`, `frame_002.png` ... 序列。
- 前端用 `<img>` 或 `<canvas>` 按顺序切换 `src`。
- 为了性能，可预加载前后 N 帧到内存中。
- **像素坐标统一**：前端展示的图片尺寸必须与原始 DICOM 的像素矩阵尺寸**严格一致**，或后端记录一个缩放比例 `scale = display_size / original_size`。这是确保医生点选坐标能映射回后端的关键。

**推荐做法**：
- 后端生成的预览图尺寸 = 原始 DICOM 像素尺寸（如 1024×1024）。
- 前端用 CSS 控制 `<img>` 的显示大小（`max-width: 100%`），但鼠标/触摸事件的坐标需要按 `original_size / client_size` 的比例换算。

### 3.4 标注画布组件设计（最关键）
这是医生与软件交互的核心，建议用 **Fabric.js** 或 **Konva.js** 在 `<canvas>` 上实现。

**两种标注模式**：
1. **AIF 标记模式**：点击图像一次，生成一个固定大小的圆形（如直径 20 像素，对应原始图像上的 20×20 区域）。圆形可拖拽调整位置，可调整半径大小。
2. **ROI 标记模式**：点击图像一次，生成一个固定大小的正方形/圆形（如 30×30 像素）。同样支持拖拽和缩放。

**为什么推荐固定大小而不是自由绘制？**
- 医学图像标注的一致性更好，减少医生间的操作差异。
- 后端处理更简单，不需要解析复杂的多边形。
- Paper 2 中 perfDSA 的 AIF 提取也是取分割区域内的像素平均，区域大小对最终结果影响不大（PCC=0.99），位置正确性更重要。

**交互细节**：
- AIF 只能标记 **1 个**。
- ROI 最多标记 **3 个**（可配置，默认 3 个）。
- 每个标记物有不同的颜色：AIF = 红色，ROI-1 = 绿色，ROI-2 = 蓝色，ROI-3 = 黄色。
- 鼠标悬停在标记物上时，显示 tooltip（如 "AIF - supraclinoid ICA"）。
- 提供 "清除所有标记" 和 "撤销上一步" 按钮。
- **AIF 引导提示**：当医生准备标记 AIF 时，在画布旁边显示示意图或文字："请选择颈内动脉床突上段（supraclinoid ICA，大致位于蝶鞍上方）"。

### 3.5 TIC 曲线展示组件（ECharts）
- **X 轴**：时间（秒），从 DICOM 的时间戳或帧率换算得到。
- **Y 轴**：灰度值（或相对浓度，经基线校正后）。
- **曲线系列**：
  - AIF 曲线：红色实线，线宽稍粗。
  - ROI-1/2/3 曲线：对应颜色的虚线/细实线。
- **交互功能**：
  - 鼠标悬停显示具体时间和灰度值。
  - 图例可点击隐藏/显示某条曲线。
  - 在曲线上标注关键时间点（如 TTP、Tmax）。

### 3.6 伪彩图叠加展示
这是从 perfDSA 学到的最有临床价值的功能。

**实现方式**：
- 后端生成伪彩图 PNG（如 DSA-CBF 图、DSA-Tmax 图），尺寸与原始 DSA 一致。
- 前端用 CSS `mix-blend-mode: multiply` 或 `opacity: 0.6` 将伪彩图叠加在原始 DSA 帧上。
- 医生可通过右侧图层面板选择显示/隐藏某类伪彩图。
- 叠加时只显示血管区域（背景透明），后端在生成伪彩图时就要把背景设为透明像素（alpha=0）。

**颜色映射方案建议**：
- `jet` 或 `turbo` colormap 是医学影像的惯例，医生熟悉。
- 提供颜色条（Colorbar）显示数值范围。

---

## 4. 后端 API 设计（RESTful）

### 4.1 API 概览

```yaml
POST   /api/upload              # 上传 DICOM 文件
GET    /api/studies             # 获取病例列表
GET    /api/studies/{id}        # 获取病例详情
DELETE /api/studies/{id}        # 删除病例
GET    /api/studies/{id}/frames # 获取帧序列列表和 metadata
POST   /api/studies/{id}/analyze # 提交 AIF+ROI 坐标，执行计算
GET    /api/studies/{id}/results # 获取计算结果
GET    /api/studies/{id}/parametric/{type} # 获取伪彩图 (type: cbf, mtt, tmax)
GET    /api/studies/{id}/export/{format}   # 导出报告 (pdf 或 excel)
```

### 4.2 关键接口详细设计

#### `POST /api/upload`
**请求**：multipart/form-data，字段 `file`
**响应**：
```json
{
  "study_id": "uuid-string",
  "patient_id": "123456",
  "series_description": "DSA Cerebral AP",
  "frame_count": 24,
  "frame_rate": 3.0,
  "width": 1024,
  "height": 1024,
  "status": "pending_processing"
}
```
**后端逻辑**：
1. 保存原始 DICOM 到 `/uploads/{study_id}/`。
2. 异步解析 DICOM，生成预览图到 `/previews/{study_id}/`。
3. 提取 metadata（帧率、像素尺寸、时间戳等）存入 JSON。

#### `GET /api/studies/{id}/frames`
**响应**：
```json
{
  "study_id": "uuid-string",
  "frames": [
    {"index": 0, "url": "/previews/{id}/frame_000.png", "time": 0.0},
    {"index": 1, "url": "/previews/{id}/frame_001.png", "time": 0.33},
    ...
  ],
  "width": 1024,
  "height": 1024,
  "frame_rate": 3.0
}
```

#### `POST /api/studies/{id}/analyze`
**请求体**：
```json
{
  "aif": {
    "x": 512,
    "y": 340,
    "radius": 10
  },
  "rois": [
    {"id": "roi-1", "x": 400, "y": 300, "radius": 15},
    {"id": "roi-2", "x": 600, "y": 350, "radius": 15},
    {"id": "roi-3", "x": 500, "y": 450, "radius": 15}
  ],
  "settings": {
    "regularization_lambda": 0.1,
    "baseline_frames": 3
  }
}
```
**注意**：坐标 `(x, y)` 必须基于原始 DICOM 像素坐标系，而非前端显示尺寸。前端在发送请求前需要做坐标换算。

**响应**：
```json
{
  "status": "success",
  "tic_curves": {
    "aif": [0, 5, 45, 120, 89, ...],
    "roi-1": [0, 2, 30, 80, 60, ...],
    ...
  },
  "time_points": [0.0, 0.33, 0.66, ...],
  "parameters": {
    "roi-1": {
      "ttp": 2.31,
      "auc": 156.4,
      "wash_in_slope": 68.2,
      "dsa_cbf": 0.74,
      "dsa_mtt": 3.82,
      "dsa_tmax": 1.65
    },
    ...
  },
  "parametric_maps": {
    "cbf": "/results/{id}/cbf_map.png",
    "mtt": "/results/{id}/mtt_map.png",
    "tmax": "/results/{id}/tmax_map.png"
  }
}
```

### 4.3 坐标换算的关键细节
这是前后端对接中最容易出错的地方。

**场景**：原始 DICOM 是 1024×1024，前端容器由于屏幕限制显示为 600×600。

**换算公式**：
```javascript
// 前端发送时：将屏幕坐标转换为原始像素坐标
const scaleX = originalWidth / displayedWidth;
const scaleY = originalHeight / displayedHeight;

const backendX = Math.round(screenX * scaleX);
const backendY = Math.round(screenY * scaleY);
```

**更稳妥的做法**：
- 后端生成的预览图尺寸 = 原始 DICOM 尺寸（如 1024×1024）。
- 前端 `<img>` 的 `naturalWidth/naturalHeight` = 1024，但 CSS `width/height` = 600。
- 监听鼠标事件时，用 `event.offsetX / img.clientWidth * img.naturalWidth` 计算原始坐标。

**边缘情况**：
- 若 DICOM 本身是矩形（如 512×480），预览图也保持 512×480，不做强制正方形裁剪。
- 若 DICOM 需要旋转或翻转（如某些设备的 DICOM 有方向标签），后端在生成预览图时就要完成旋转，确保前后端方向一致。

---

## 5. 计算流程与状态管理

### 5.1 前端状态（Pinia Store 设计）
建议设计一个 `studyStore`：

```typescript
interface StudyState {
  studyId: string | null;
  frames: FrameInfo[];
  currentFrameIndex: number;
  isPlaying: boolean;
  aif: CircleAnnotation | null;
  rois: CircleAnnotation[];
  results: AnalysisResult | null;
  selectedParametricMap: 'cbf' | 'mtt' | 'tmax' | null;
}
```

### 5.2 计算任务的同步 vs 异步
根据 Paper 2，单个 DSA 序列的灌注参数图生成时间约为 **1 秒**（CPU）。对于你手动标记 3 个 ROI 的场景，计算量更小（不需要全图逐像素计算，只需要计算 AIF + 3 个 ROI + 可选的全图伪彩图）。

**建议**：
- **ROI 分析（TTP/AUC/CBF/MTT/Tmax）**：同步返回（HTTP POST 后 1-2 秒内响应）。
- **全图伪彩图生成**：如果全图很大（1024×1024 × 30 帧），反卷积计算量会大一些。虽然仍能在几秒内完成，但为了避免 HTTP 超时，可以：
  - 方案 A：也做同步，但前端显示 loading 动画（预计 3-5 秒）。
  - 方案 B：做成异步任务（`POST /analyze` 返回 task_id，`GET /tasks/{task_id}` 轮询进度），全图伪彩图生成完成后通知前端。

**MVP 推荐**：先做同步，因为计算量可控。如果后续发现全图伪彩图生成太慢，再改为异步。

---

## 6. 数据存储策略

### 6.1 文件目录结构
建议后端本地文件系统按以下结构存储：

```
/data/dsa-perfusion/
├── uploads/
│   └── {study_id}/
│       └── original.dcm
├── previews/
│   └── {study_id}/
│       ├── metadata.json
│       ├── frame_000.png
│       ├── frame_001.png
│       └── ...
├── results/
│   └── {study_id}/
│       ├── analysis.json       # 分析结果（坐标、TIC、参数）
│       ├── cbf_map.png
│       ├── mtt_map.png
│       ├── tmax_map.png
│       └── report.pdf
└── db.sqlite3                  # 可选，用于病例列表、状态追踪
```

### 6.2 数据库设计（SQLite 足够）
```sql
CREATE TABLE studies (
    id TEXT PRIMARY KEY,
    patient_id TEXT,
    study_date TEXT,
    series_description TEXT,
    frame_count INTEGER,
    frame_rate REAL,
    status TEXT,  -- 'uploaded', 'processed', 'analyzed'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE analyses (
    id TEXT PRIMARY KEY,
    study_id TEXT,
    aif_json TEXT,
    rois_json TEXT,
    results_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (study_id) REFERENCES studies(id)
);
```

---

## 7. DICOM 解析与预处理流程

这是后端最关键的一步，直接决定前端的展示质量和计算的准确性。

### 7.1 DICOM 读取步骤
1. **用 `pydicom` 读取文件**：
   - 判断是 `Enhanced DICOM`（单文件多帧）还是传统序列（多文件）。MVP 阶段可以先只支持单文件多帧（最常见）。
   - 提取 `Pixel Data`。
2. **提取元数据**：
   - `Frame Time` (0018, 1063) 或 `Frame Rate` (0018, 1062)：用于计算时间轴。
   - `Rows`, `Columns`：图像尺寸。
   - `Pixel Spacing`：像素物理间距（可选，MVP 阶段可能不需要）。
   - `Photometric Interpretation`：确认是 MONOCHROME1 还是 MONOCHROME2。
3. **像素值处理**：
   - DSA 的 `Pixel Data` 通常已经是减影后的图像（灰度值可能为负）。
   - 应用 `Rescale Slope` 和 `Rescale Intercept` 转换为真实像素值。
   - 将像素值归一化到 0-255 用于 PNG 预览，但**保留原始 16-bit 数据用于计算**（TIC 提取必须用原始值，不能用压缩后的 8-bit PNG）。
4. **生成预览图**：
   - 对每一帧应用窗宽窗位（Window/Level）调整，或直接用 min-max 归一化到 0-255 保存为 PNG。
   - 保存 `metadata.json` 包含帧数、帧率、原始尺寸、时间数组等。

### 7.2 时间轴计算
如果 DICOM 中没有 `Frame Time` 标签，可用以下方式估算：
- 总时长 / 帧数
- 或简单地 `time[i] = i / frame_rate`

**注意**：某些 DSA 设备的帧率不是恒定的（如开始时 4 fps，后面降到 2 fps），这会影响 TTP 和 Tmax 的精确性。理想情况下应读取每帧的 `Frame Time Vector` 或 `Frame Reference Time`（如果存在）。

---

## 8. 安全、隐私与合规

### 8.1 医疗数据不出院（本地化部署）
- 该软件应**默认设计为医院内网使用**，不上传任何数据到公网。
- 后端应只监听 `127.0.0.1` 或医院内网网段，不暴露到互联网。
- 若需远程协助调试，使用医院 VPN 或 TeamViewer 等合规远程工具，**绝不可将患者 DICOM 通过个人微信/邮件传输**。

### 8.2 患者隐私信息（PHI）脱敏
- DICOM 文件包含大量患者信息（姓名、出生日期、医院号等）。
- 软件在展示病例列表时，应**优先显示匿名化 ID**（如 Study ID 或患者住院号后 4 位），而非完整姓名。
- 报告导出时，应在页眉/页脚加入免责声明（见原研究记录第 5.2 节）。

### 8.3 访问控制（院内多用户场景）
即使是内网，也建议加入简单的登录机制：
- 医生账号 + 密码（由医院 IT 或科室管理员分配）。
- 不同医生只能看到自己创建或授权访问的病例（Study 与 User 关联）。

### 8.4 法规边界
- MVP 阶段明确作为**科研工具**使用，不作为独立诊断依据。
- 如果未来打算作为医疗器械销售或临床常规使用，需要走 NMPA（中国）二类或三类医疗器械注册路径。

---

## 9. 风险项与技术决策记录（ADR）

| 决策点 | 选择方案 | 备选方案 | 决策理由 |
|--------|---------|---------|---------|
| **前端 DICOM 展示** | 后端解析为 PNG 序列，前端展示图片 | 前端用 Cornerstone.js 直接解析 DICOM | 开发成本低，前后端职责清晰，Vue 集成更简单 |
| **标注交互库** | Fabric.js / Konva.js | 纯 HTML Canvas API | 拖拽、缩放、事件管理更方便 |
| **AIF/ROI 形状** | 圆形（中心点 + 半径） | 自由绘制多边形 | 一致性好，后端处理简单，符合文献做法 |
| **计算模式** | 同步 HTTP（1-3 秒返回） | 异步任务队列 | 计算量可控，同步交互更自然 |
| **全图伪彩图** | 后端生成 PNG，前端叠加 | 前端 Canvas 逐像素着色 | 后端用 matplotlib 生成更成熟，前端性能更好 |
| **数据库** | SQLite | PostgreSQL / MySQL | 单机/轻量部署，零配置 |
| **部署方式** | 医院内网本地化 | SaaS 云服务 | 数据安全合规，避免公网传输风险 |

---

## 10. 下一步具体任务拆分（基于 Phase 1 MVP）

以下任务可以直接放入项目管理工具（如 Notion / Linear / 飞书项目）中跟踪：

### 前端（Vue 3）
- [ ] **F-01** 搭建 Vue 3 + TypeScript + Pinia + Element Plus 项目骨架
- [ ] **F-02** 实现 DICOM 上传页面（拖拽上传 + 进度条）
- [ ] **F-03** 实现 DSA 播放器组件（播放/暂停/逐帧/时间轴/缩略图列表）
- [ ] **F-04** 实现标注画布组件（Fabric.js 集成：AIF 圆 + ROI 圆，拖拽，颜色区分）
- [ ] **F-05** 实现坐标换算逻辑（屏幕坐标 ↔ 原始像素坐标）
- [ ] **F-06** 实现 TIC 曲线展示面板（ECharts 多系列曲线）
- [ ] **F-07** 实现参数结果表格（区分 TIC-derived 和 Deconvolution-based）
- [ ] **F-08** 实现伪彩图叠加展示（透明度滑块 + 图例 + 图层切换）
- [ ] **F-09** 实现报告导出按钮（触发后端 PDF/Excel 下载）

### 后端（Python + FastAPI）
- [ ] **B-01** 搭建 FastAPI 项目骨架 + 目录结构
- [ ] **B-02** 实现 DICOM 上传与本地存储接口
- [ ] **B-03** 实现 DICOM 解析服务（pydicom 读取多帧、提取 metadata、生成 PNG 预览图）
- [ ] **B-04** 实现 TIC 提取服务（根据 AIF/ROI 坐标，从原始像素中提取时间-密度曲线）
- [ ] **B-05** 实现 TIC-derived 参数计算（TTP, AUC, Wash-in slope）
- [ ] **B-06** 实现 Deconvolution 计算服务（SVD 反卷积、正则化、CBF/MTT/Tmax）
- [ ] **B-07** 实现全图伪彩图生成服务（血管掩膜 + colormap + alpha 透明背景）
- [ ] **B-08** 实现报告导出服务（PDF 图表 + Excel 表格）
- [ ] **B-09** 实现 SQLite 数据模型与 CRUD

### 联调与测试
- [ ] **I-01** 前后端接口联调（上传 → 解析 → 标记 → 计算 → 展示完整链路）
- [ ] **I-02** 用 5-10 例真实/模拟 DICOM 数据测试计算结果的合理性
- [ ] **I-03** 邀请医生进行可用性测试（AIF 选择是否顺手、结果是否直观）

---

## 11. 给你的额外建议

1. **先做一个“模拟数据模式”**：在拿到真实 DICOM 之前，你可以用 Python 生成一个合成的 DSA 序列（几条模拟血管 + 对比剂扩散动画），存成一组 PNG。这样前端团队可以立刻开始播放器、标注、曲线展示的开发，不需要等 DICOM。

2. **AIF 选择的“最佳实践提示”很重要**：在标注画布旁边放一个简短的视频或 GIF，演示 "supraclinoid ICA 在哪里"。这比文字描述有效 10 倍，能显著降低医生的学习成本。

3. **保存分析记录，支持“回放”**：每次分析的结果（AIF 坐标、ROI 坐标、计算参数）都保存到数据库。这样医生可以回顾自己之前的选点，也可以让另一位医生打开同一个病例，看到之前的标记并在此基础上修改，这对科研中的观察者一致性研究非常有价值。

4. **先做“单用户本地版”，再考虑多用户**：你的目标是快速验证临床价值。第一个版本甚至可以不需要登录系统，直接打开浏览器访问 `localhost:3000`，医生上传、分析、导出都在一台电脑上完成。等功能被认可后，再加入多用户和权限管理。

5. **全图伪彩图不要省**：虽然你只要求 3 个 ROI 的参数，但全图伪彩图（尤其是 DSA-Tmax 图）是临床医生最容易理解和接受的呈现形式。从工程角度，全图计算只是“对每个像素重复 ROI 的计算逻辑”，代码改动不大，但产品价值提升很大。

---

*本架构文档与 `dsa_perfusion_mvp_research.md` 共同构成该项目的完整方案基线。后续开发应以此为准，若有重大技术决策变更，需同步更新本文档。*
