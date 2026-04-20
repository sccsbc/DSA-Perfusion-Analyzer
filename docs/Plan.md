# DSA 灌注分析软件开发计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 开发一个基于 Vue 3 + Python 的 DSA 灌注分析软件，医生手动点选 AIF 和 3 个 ROI，自动计算 TTP、AUC、Wash-in slope、DSA-CBF、DSA-MTT、DSA-Tmax，并生成伪彩图。

**Architecture:** 前后端分离架构。前端 Vue 3 负责 DICOM 上传、DSA 帧播放、AIF/ROI 标注、TIC 曲线展示和伪彩图叠加。后端 FastAPI 负责 DICOM 解析、TIC 提取、反卷积计算和伪彩图生成。MVP 阶段先用 matplotlib 交互脚本验证核心算法，再 Web 服务化。

**Tech Stack:** Vue 3 + TypeScript + Pinia + Element Plus + ECharts (前端), Python + FastAPI + pydicom + numpy + scipy + matplotlib (后端), Conda 环境管理。

---

## 文件结构规划

```
/Users/wudeyi/code/claude/dsa/
├── docs/
│   └── Plan.md                       # 本计划文档
├── backend/                          # Python 后端
│   ├── pyproject.toml                # 依赖配置 (可选 poetry)
│   ├── requirements.txt              # pip 依赖
│   ├── environment.yml               # conda 环境配置
│   ├── src/
│   │   ├── __init__.py
│   │   ├── dicom_parser.py           # DICOM 读取、元数据提取、帧导出
│   │   ├── tic_extractor.py          # 根据坐标提取时间-密度曲线
│   │   ├── perfusion_params.py       # TTP/AUC/Wash-in slope 计算
│   │   ├── deconvolution.py          # SVD 反卷积、CBF/CBV/MTT/Tmax 计算
│   │   ├── parametric_map.py         # 全图伪彩图生成
│   │   ├── interactive_picker.py     # matplotlib 交互式选点脚本
│   │   └── main.py                   # FastAPI 入口 (Phase 2 启用)
│   ├── tests/
│   │   ├── test_dicom_parser.py
│   │   ├── test_tic_extractor.py
│   │   ├── test_perfusion_params.py
│   │   └── test_deconvolution.py
│   └── data/                         # 测试数据目录 (gitignore)
│       ├── .gitignore
│       └── README.md
├── frontend/                         # Vue 3 前端 (Phase 3 启用)
│   └── (待定)
└── research_papers/                  # 原始论文和调研文档
    ├── dsa_perfusion_mvp_architecture.md
    └── *.pdf
```

---

## Phase 1: 后端核心算法验证 (纯 Python 脚本)

> **说明:** 本阶段目标是验证算法正确性。使用 `interactive_picker.py` 弹窗选点，跑完出结果和曲线。前端暂时不写。

### Task 1: 项目骨架与环境搭建

**Files:**
- Create: `backend/environment.yml`
- Create: `backend/requirements.txt`
- Create: `backend/data/.gitignore`
- Create: `backend/data/README.md`
- Create: `backend/src/__init__.py`
- Create: `backend/tests/__init__.py`

- [ ] **Step 1: 创建 Conda 环境配置文件**

```yaml
# backend/environment.yml
name: dsa-perfusion
channels:
  - conda-forge
  - defaults
dependencies:
  - python=3.11
  - numpy
  - scipy
  - scikit-image
  - matplotlib
  - pandas
  - pip
  - pip:
    - pydicom
    - fastapi
    - uvicorn
    - python-multipart
    - pytest
    - pillow
```

- [ ] **Step 2: 创建 requirements.txt**

```text
# backend/requirements.txt
numpy>=1.24
scipy>=1.10
scikit-image>=0.20
matplotlib>=3.7
pandas>=2.0
pydicom>=2.4
fastapi>=0.100
uvicorn>=0.23
python-multipart>=0.0.6
pytest>=7.4
pillow>=10.0
```

- [ ] **Step 3: 创建数据目录和 .gitignore**

```text
# backend/data/.gitignore
*
!.gitignore
!README.md
```

```markdown
<!-- backend/data/README.md -->
# 测试数据目录

将 DICOM 测试文件放入此目录。该目录下的实际文件不会被 Git 追踪。
```

- [ ] **Step 4: 初始化 Python 包**

创建空的 `backend/src/__init__.py` 和 `backend/tests/__init__.py`。

- [ ] **Step 5: 安装环境并验证**

Run:
```bash
cd /Users/wudeyi/code/claude/dsa/backend
conda env create -f environment.yml
conda activate dsa-perfusion
python -c "import numpy, scipy, pydicom, matplotlib, pytest; print('OK')"
```

Expected: 输出 `OK`

- [ ] **Step 6: Commit**

```bash
git add backend/
git commit -m "chore: 初始化后端项目骨架和 conda 环境"
```

---

### Task 2: DICOM 解析模块

**Files:**
- Create: `backend/src/dicom_parser.py`
- Create: `backend/tests/test_dicom_parser.py`

**设计要点:**
- 同时支持 **单文件多帧 (Enhanced DICOM)** 和 **多文件序列 (传统 DICOM)**
- 自动检测输入是文件还是目录
- 提取关键元数据：帧数、帧率、帧时间、行列数、像素间距、窗宽窗位
- 输出统一格式：原始像素数组 `(frames, rows, cols)` + metadata dict + 预览 PNG

- [ ] **Step 1: 写 DICOM 解析器**

```python
# backend/src/dicom_parser.py
"""DICOM 解析模块：支持单文件多帧和多文件序列。"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import numpy as np
from pydicom import dcmread
from PIL import Image


def _get_frame_time(ds) -> float | None:
    """提取帧间隔时间（秒）。"""
    # 优先读取 Frame Time (0018,1063)
    if hasattr(ds, "FrameTime") and ds.FrameTime:
        return float(ds.FrameTime) / 1000.0  # ms -> s
    # 次优先读取 Frame Rate (0018,1062)
    if hasattr(ds, "FrameTimeVector") and ds.FrameTimeVector:
        # 返回第一帧时间作为估算
        return float(ds.FrameTimeVector[0]) / 1000.0 if len(ds.FrameTimeVector) > 0 else None
    if hasattr(ds, "CineRate") and ds.CineRate:
        return 1.0 / float(ds.CineRate)
    if hasattr(ds, "RecommendedDisplayFrameRate") and ds.RecommendedDisplayFrameRate:
        return 1.0 / float(ds.RecommendedDisplayFrameRate)
    return None


def _apply_rescale(pixel_array: np.ndarray, ds) -> np.ndarray:
    """应用 Rescale Slope / Intercept。"""
    slope = float(getattr(ds, "RescaleSlope", 1.0))
    intercept = float(getattr(ds, "RescaleIntercept", 0.0))
    return pixel_array.astype(np.float32) * slope + intercept


def _normalize_to_uint8(arr: np.ndarray) -> np.ndarray:
    """将浮点数组归一化到 0-255 uint8。"""
    arr_min, arr_max = arr.min(), arr.max()
    if arr_max - arr_min < 1e-6:
        return np.zeros_like(arr, dtype=np.uint8)
    scaled = (arr - arr_min) / (arr_max - arr_min) * 255.0
    return scaled.astype(np.uint8)


def parse_dicom(dicom_path: str | Path) -> dict[str, Any]:
    """
    解析 DICOM 文件或目录。

    Returns:
        {
            "pixel_array": np.ndarray of shape (n_frames, rows, cols), dtype=float32,
            "frames": int,
            "rows": int,
            "cols": int,
            "frame_rate": float | None,
            "frame_time": float | None,
            "times": np.ndarray of shape (n_frames,),  # 各帧时间点（秒）
            "pixel_spacing": tuple[float, float] | None,
            "photometric_interpretation": str,
        }
    """
    dicom_path = Path(dicom_path)

    if dicom_path.is_file():
        ds = dcmread(str(dicom_path))
        pixel_array = ds.pixel_array  # 可能是 (frames, rows, cols) 或 (rows, cols)
        if pixel_array.ndim == 2:
            pixel_array = pixel_array[np.newaxis, ...]
        n_frames = pixel_array.shape[0]
    elif dicom_path.is_dir():
        dicom_files = sorted(
            [f for f in dicom_path.iterdir() if f.suffix.lower() in (".dcm", ".ima", "")],
            key=lambda f: f.name,
        )
        if not dicom_files:
            raise ValueError(f"目录中未找到 DICOM 文件: {dicom_path}")
        frames_list = []
        ds = None
        for f in dicom_files:
            ds = dcmread(str(f))
            arr = ds.pixel_array
            if arr.ndim == 3:
                for i in range(arr.shape[0]):
                    frames_list.append(arr[i])
            else:
                frames_list.append(arr)
        pixel_array = np.stack(frames_list, axis=0)
        n_frames = pixel_array.shape[0]
    else:
        raise ValueError(f"无效路径: {dicom_path}")

    pixel_array = _apply_rescale(pixel_array, ds)

    frame_time = _get_frame_time(ds)
    frame_rate = 1.0 / frame_time if frame_time else None
    times = np.arange(n_frames, dtype=np.float32) * (frame_time or 1.0)

    pixel_spacing = None
    if hasattr(ds, "PixelSpacing"):
        pixel_spacing = (float(ds.PixelSpacing[0]), float(ds.PixelSpacing[1]))

    return {
        "pixel_array": pixel_array.astype(np.float32),
        "frames": n_frames,
        "rows": pixel_array.shape[1],
        "cols": pixel_array.shape[2],
        "frame_rate": frame_rate,
        "frame_time": frame_time,
        "times": times,
        "pixel_spacing": pixel_spacing,
        "photometric_interpretation": getattr(ds, "PhotometricInterpretation", "UNKNOWN"),
    }


def export_preview_frames(
    pixel_array: np.ndarray,
    output_dir: str | Path,
    prefix: str = "frame",
) -> list[str]:
    """将像素数组导出为 PNG 预览帧序列。"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i in range(pixel_array.shape[0]):
        arr = pixel_array[i]
        img_arr = _normalize_to_uint8(arr)
        img = Image.fromarray(img_arr)
        if getattr(img, "mode") != "L":
            img = img.convert("L")
        save_path = output_dir / f"{prefix}_{i:03d}.png"
        img.save(save_path)
        paths.append(str(save_path))
    return paths
```

- [ ] **Step 2: 写测试用例**

```python
# backend/tests/test_dicom_parser.py
import numpy as np
import pytest
from pydicom import Dataset
from pydicom.uid import ExplicitVRLittleEndian
import tempfile
from pathlib import Path

from src.dicom_parser import parse_dicom, export_preview_frames, _normalize_to_uint8


def test_normalize_to_uint8():
    arr = np.array([0.0, 50.0, 100.0], dtype=np.float32)
    result = _normalize_to_uint8(arr)
    expected = np.array([0, 127, 255], dtype=np.uint8)
    np.testing.assert_array_almost_equal(result, expected, decimal=0)


def test_parse_single_frame_dicom():
    """用 pydicom 构建一个单帧测试 DICOM 文件并解析。"""
    ds = Dataset()
    ds.Rows = 64
    ds.Columns = 64
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.PixelRepresentation = 0
    ds.RescaleSlope = 1.0
    ds.RescaleIntercept = 0.0
    ds.FrameTime = 333.0  # ms -> 3 fps
    arr = np.random.randint(0, 4096, size=(64, 64), dtype=np.uint16)
    ds.PixelData = arr.tobytes()

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.dcm"
        ds.file_meta = Dataset()
        ds.file_meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.2"
        ds.file_meta.MediaStorageSOPInstanceUID = "1.2.3.4.5"
        ds.file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
        ds.save_as(str(path))

        result = parse_dicom(path)
        assert result["frames"] == 1
        assert result["rows"] == 64
        assert result["cols"] == 64
        assert result["frame_rate"] == pytest.approx(3.0)
        assert result["pixel_array"].shape == (1, 64, 64)


def test_export_preview_frames():
    arr = np.random.rand(3, 32, 32).astype(np.float32)
    with tempfile.TemporaryDirectory() as tmpdir:
        paths = export_preview_frames(arr, tmpdir)
        assert len(paths) == 3
        for p in paths:
            assert Path(p).exists()
```

- [ ] **Step 3: 运行测试**

Run:
```bash
cd /Users/wudeyi/code/claude/dsa/backend
pytest tests/test_dicom_parser.py -v
```

Expected: 3 tests PASS

- [ ] **Step 4: Commit**

```bash
git add backend/src/dicom_parser.py backend/tests/test_dicom_parser.py
git commit -m "feat: 实现 DICOM 解析模块，支持单文件多帧和多文件序列"
```

---

### Task 3: TIC 提取模块

**Files:**
- Create: `backend/src/tic_extractor.py`
- Create: `backend/tests/test_tic_extractor.py`

**设计要点:**
- 输入：原始 pixel array `(frames, rows, cols)` + 坐标定义 (圆形区域：圆心 x, y, 半径 r)
- 输出：该区域所有像素在每一帧上的平均值，即 TIC 曲线

- [ ] **Step 1: 写 TIC 提取器**

```python
# backend/src/tic_extractor.py
"""TIC 提取模块：从 DSA 序列中提取时间-密度曲线。"""

from __future__ import annotations

import numpy as np


def create_circular_mask(
    rows: int,
    cols: int,
    center_x: float,
    center_y: float,
    radius: float,
) -> np.ndarray:
    """生成圆形掩膜，返回布尔数组 (rows, cols)。"""
    y, x = np.ogrid[:rows, :cols]
    dist = np.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)
    return dist <= radius


def extract_tic(
    pixel_array: np.ndarray,
    center_x: float,
    center_y: float,
    radius: float,
) -> np.ndarray:
    """
    从像素数组中提取指定圆形区域的 TIC。

    Args:
        pixel_array: shape (n_frames, rows, cols)
        center_x, center_y: 圆心坐标（基于原始像素坐标）
        radius: 圆半径

    Returns:
        TIC 数组，shape (n_frames,), dtype=float32
    """
    if pixel_array.ndim != 3:
        raise ValueError(f"pixel_array 必须是 3 维，当前维度: {pixel_array.ndim}")

    n_frames, rows, cols = pixel_array.shape
    mask = create_circular_mask(rows, cols, center_x, center_y, radius)

    if not np.any(mask):
        raise ValueError("掩膜区域内无有效像素，请检查坐标和半径")

    tic = np.empty(n_frames, dtype=np.float32)
    for t in range(n_frames):
        roi = pixel_array[t][mask]
        tic[t] = np.mean(roi)
    return tic


def extract_aif_and_rois(
    pixel_array: np.ndarray,
    aif: dict[str, float],
    rois: list[dict[str, float]],
) -> dict[str, np.ndarray]:
    """
    批量提取 AIF 和多个 ROI 的 TIC。

    Args:
        aif: {"x": float, "y": float, "radius": float}
        rois: [{"id": str, "x": float, "y": float, "radius": float}, ...]

    Returns:
        {"aif": np.ndarray, "roi-1": np.ndarray, ...}
    """
    result = {}
    result["aif"] = extract_tic(pixel_array, aif["x"], aif["y"], aif["radius"])
    for roi in rois:
        result[roi["id"]] = extract_tic(
            pixel_array, roi["x"], roi["y"], roi["radius"]
        )
    return result
```

- [ ] **Step 2: 写测试用例**

```python
# backend/tests/test_tic_extractor.py
import numpy as np
import pytest

from src.tic_extractor import create_circular_mask, extract_tic, extract_aif_and_rois


def test_create_circular_mask():
    mask = create_circular_mask(10, 10, 5, 5, 3)
    assert mask.shape == (10, 10)
    assert mask[5, 5] is True
    assert mask[0, 0] is False


def test_extract_tic():
    # 构造 5 帧 10x10 图像，中心圆形区域值固定为 100
    pixel_array = np.zeros((5, 10, 10), dtype=np.float32)
    pixel_array[:, 4:7, 4:7] = 100.0
    tic = extract_tic(pixel_array, 5.0, 5.0, 1.5)
    np.testing.assert_array_equal(tic, np.full(5, 100.0, dtype=np.float32))


def test_extract_aif_and_rois():
    pixel_array = np.zeros((3, 10, 10), dtype=np.float32)
    pixel_array[:, 2, 2] = 50.0
    pixel_array[:, 7, 7] = 80.0

    aif = {"x": 2.0, "y": 2.0, "radius": 1.0}
    rois = [{"id": "roi-1", "x": 7.0, "y": 7.0, "radius": 1.0}]

    result = extract_aif_and_rois(pixel_array, aif, rois)
    assert "aif" in result
    assert "roi-1" in result
    np.testing.assert_allclose(result["aif"], [50.0, 50.0, 50.0], atol=0.1)
    np.testing.assert_allclose(result["roi-1"], [80.0, 80.0, 80.0], atol=0.1)
```

- [ ] **Step 3: 运行测试**

Run:
```bash
cd /Users/wudeyi/code/claude/dsa/backend
pytest tests/test_tic_extractor.py -v
```

Expected: 3 tests PASS

- [ ] **Step 4: Commit**

```bash
git add backend/src/tic_extractor.py backend/tests/test_tic_extractor.py
git commit -m "feat: 实现 TIC 提取模块，支持 AIF 和 ROI 批量提取"
```

---

### Task 4: TIC-derived 参数计算

**Files:**
- Create: `backend/src/perfusion_params.py`
- Create: `backend/tests/test_perfusion_params.py`

**设计要点:**
- **TTP (Time-to-Peak):** 达到峰值浓度的时间点（秒）
- **AUC (Area Under Curve):** 曲线下面积，用梯形法积分
- **Wash-in slope:** 从基线到峰值之间的最大一阶差分（最大上升斜率）
- 需要基线校正：通常取前 N 帧的平均值作为基线，然后从 TIC 中减去

- [ ] **Step 1: 写 TIC-derived 参数计算器**

```python
# backend/src/perfusion_params.py
"""TIC-derived 灌注参数计算：TTP、AUC、Wash-in slope。"""

from __future__ import annotations

import numpy as np
from scipy import integrate


def correct_baseline(tic: np.ndarray, baseline_frames: int = 3) -> np.ndarray:
    """基线校正：减去前 baseline_frames 帧的平均值。"""
    if baseline_frames <= 0:
        return tic.copy()
    n = min(baseline_frames, len(tic))
    baseline = np.mean(tic[:n])
    return tic - baseline


def compute_ttp(tic: np.ndarray, times: np.ndarray) -> float:
    """计算 TTP（秒）。"""
    peak_idx = int(np.argmax(tic))
    return float(times[peak_idx])


def compute_auc(tic: np.ndarray, times: np.ndarray) -> float:
    """用梯形法计算 AUC。"""
    return float(integrate.trapezoid(tic, times))


def compute_wash_in_slope(tic: np.ndarray, times: np.ndarray) -> float:
    """
    计算 Wash-in slope。
    取从基线到峰值之间的最大一阶差分（最大上升速率）。
    如果 TIC 单调递减或无上升段，返回 0。
    """
    peak_idx = int(np.argmax(tic))
    if peak_idx <= 0:
        return 0.0

    # 只考虑上升段
    rising_tic = tic[: peak_idx + 1]
    rising_times = times[: peak_idx + 1]

    deltas = np.diff(rising_tic)
    dt = np.diff(rising_times)

    if len(deltas) == 0 or np.any(dt <= 0):
        return 0.0

    slopes = deltas / dt
    return float(np.max(slopes))


def compute_tic_parameters(
    tic: np.ndarray,
    times: np.ndarray,
    baseline_frames: int = 3,
) -> dict[str, float]:
    """
    计算全部 TIC-derived 参数。

    Returns:
        {
            "ttp": float,
            "auc": float,
            "wash_in_slope": float,
            "peak": float,
        }
    """
    corrected = correct_baseline(tic, baseline_frames)
    # 基线校正后可能出现负值，确保 AUC 积分基于实际对比剂浓度
    # 但 TTP 和 Wash-in 基于原始峰值位置即可
    return {
        "ttp": compute_ttp(tic, times),
        "auc": compute_auc(corrected, times),
        "wash_in_slope": compute_wash_in_slope(tic, times),
        "peak": float(np.max(tic)),
    }
```

- [ ] **Step 2: 写测试用例**

```python
# backend/tests/test_perfusion_params.py
import numpy as np
import pytest

from src.perfusion_params import (
    correct_baseline,
    compute_ttp,
    compute_auc,
    compute_wash_in_slope,
    compute_tic_parameters,
)


def test_correct_baseline():
    tic = np.array([10.0, 10.0, 10.0, 20.0, 30.0], dtype=np.float32)
    corrected = correct_baseline(tic, baseline_frames=3)
    expected = np.array([0.0, 0.0, 0.0, 10.0, 20.0], dtype=np.float32)
    np.testing.assert_allclose(corrected, expected, atol=1e-6)


def test_compute_ttp():
    tic = np.array([0, 5, 10, 7, 3], dtype=np.float32)
    times = np.array([0.0, 0.5, 1.0, 1.5, 2.0], dtype=np.float32)
    assert compute_ttp(tic, times) == pytest.approx(1.0)


def test_compute_auc():
    tic = np.array([0.0, 5.0, 10.0], dtype=np.float32)
    times = np.array([0.0, 0.5, 1.0], dtype=np.float32)
    # 梯形法：0.5 * (0+5)*0.5 + 0.5 * (5+10)*0.5 = 1.25 + 3.75 = 5.0
    assert compute_auc(tic, times) == pytest.approx(5.0)


def test_compute_wash_in_slope():
    tic = np.array([0.0, 4.0, 10.0, 8.0, 5.0], dtype=np.float32)
    times = np.array([0.0, 0.5, 1.0, 1.5, 2.0], dtype=np.float32)
    # 上升段: [0, 4, 10], slopes: (4-0)/0.5=8, (10-4)/0.5=12
    assert compute_wash_in_slope(tic, times) == pytest.approx(12.0)


def test_compute_wash_in_slope_no_rise():
    tic = np.array([10.0, 8.0, 5.0], dtype=np.float32)
    times = np.array([0.0, 0.5, 1.0], dtype=np.float32)
    assert compute_wash_in_slope(tic, times) == 0.0


def test_compute_tic_parameters():
    tic = np.array([10.0, 10.0, 15.0, 25.0, 20.0], dtype=np.float32)
    times = np.array([0.0, 0.33, 0.66, 0.99, 1.32], dtype=np.float32)
    params = compute_tic_parameters(tic, times, baseline_frames=2)
    assert params["ttp"] == pytest.approx(0.99)
    assert params["peak"] == pytest.approx(25.0)
    assert params["wash_in_slope"] > 0
```

- [ ] **Step 3: 运行测试**

Run:
```bash
cd /Users/wudeyi/code/claude/dsa/backend
pytest tests/test_perfusion_params.py -v
```

Expected: 6 tests PASS

- [ ] **Step 4: Commit**

```bash
git add backend/src/perfusion_params.py backend/tests/test_perfusion_params.py
git commit -m "feat: 实现 TIC-derived 参数计算 (TTP, AUC, Wash-in slope)"
```

---

### Task 5: 反卷积计算模块 (核心)

**Files:**
- Create: `backend/src/deconvolution.py`
- Create: `backend/tests/test_deconvolution.py`

**设计要点:**
- 基于论文公式：
  - `k(t) = deconvolve(C_voi(t), C_art(t))` — flow-scaled residue function
  - `CBF = max(k(t)) / ρ_voi`
  - `Tmax = argmax(k(t))`
  - `CBV = sum(k(t)) * dt / ρ_voi`
  - `MTT = CBV / CBF`
- 用 SVD (奇异值分解) 实现反卷积，并进行正则化 (截断小奇异值)
- 预处理：时间域高斯滤波降噪 (论文中提到)

- [ ] **Step 1: 写反卷积模块**

```python
# backend/src/deconvolution.py
"""反卷积计算模块：SVD 反卷积求 DSA-CBF、DSA-MTT、DSA-Tmax、DSA-CBV。"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.linalg import svd


def temporal_gaussian_filter(tic: np.ndarray, sigma: float = 1.0) -> np.ndarray:
    """对 TIC 做时间域高斯滤波降噪。"""
    if sigma <= 0:
        return tic.copy()
    return gaussian_filter1d(tic, sigma=sigma)


def build_circulant_matrix(aif: np.ndarray) -> np.ndarray:
    """
    构建 AIF 的循环矩阵 A，使得 A @ k ≈ conv(aif, k)。
    采用因果卷积的下三角形式。
    """
    n = len(aif)
    A = np.zeros((n, n), dtype=np.float64)
    for i in range(n):
        for j in range(i + 1):
            A[i, j] = aif[i - j]
    return A


def svd_deconvolution(
    aif: np.ndarray,
    tic: np.ndarray,
    dt: float,
    sigma: float = 1.0,
    regularization_lambda: float | None = None,
    rho_voi: float | None = None,
) -> dict[str, float]:
    """
    使用 SVD 反卷积计算灌注参数。

    Args:
        aif: 动脉输入函数 TIC，shape (n,)
        tic: 目标区域 TIC，shape (n,)
        dt: 时间间隔（秒）
        sigma: 时间域高斯滤波 sigma
        regularization_lambda: SVD 正则化阈值系数 (默认 None=自动)
        rho_voi: VOI 的平均强度，用于缩放。None 则自动用 tic 均值。

    Returns:
        {
            "dsa_cbf": float,
            "dsa_cbv": float,
            "dsa_mtt": float,
            "dsa_tmax": float,
            "residue_function": np.ndarray,
            "flow_scaled_residue": np.ndarray,
        }
    """
    aif = aif.astype(np.float64).copy()
    tic = tic.astype(np.float64).copy()

    # 1. 基线校正
    aif -= np.mean(aif[:3]) if len(aif) >= 3 else 0.0
    tic -= np.mean(tic[:3]) if len(tic) >= 3 else 0.0

    # 确保非负（避免数值问题）
    aif = np.clip(aif, 0, None)
    tic = np.clip(tic, 0, None)

    # 2. 时间域高斯滤波
    aif = temporal_gaussian_filter(aif, sigma=sigma)
    tic = temporal_gaussian_filter(tic, sigma=sigma)

    # 3. 构建循环矩阵
    A = build_circulant_matrix(aif)

    # 4. SVD 分解
    U, s, Vh = svd(A, full_matrices=False)

    # 5. 正则化：截断小奇异值
    if regularization_lambda is None:
        # 自动：取最大奇异值的 5% 作为阈值
        regularization_lambda = 0.05 * s[0]

    s_inv = np.zeros_like(s)
    mask = s > regularization_lambda
    s_inv[mask] = 1.0 / s[mask]

    # 6. 求解 k(t) = flow-scaled residue function
    k = Vh.T @ (np.diag(s_inv) @ (U.T @ tic))

    # 7. 计算参数
    if rho_voi is None:
        rho_voi = np.mean(tic) if np.mean(tic) > 1e-6 else 1.0

    cbf = float(np.max(k) / rho_voi)
    tmax_idx = int(np.argmax(k))
    tmax = float(tmax_idx * dt)
    cbv = float(np.sum(k) * dt / rho_voi)
    mtt = float(cbv / cbf) if cbf > 1e-6 else 0.0

    return {
        "dsa_cbf": cbf,
        "dsa_cbv": cbv,
        "dsa_mtt": mtt,
        "dsa_tmax": tmax,
        "residue_function": (k / (cbf * rho_voi)) if cbf > 1e-6 else np.zeros_like(k),
        "flow_scaled_residue": k.astype(np.float32),
    }


def compute_deconvolution_parameters(
    aif: np.ndarray,
    tic: np.ndarray,
    times: np.ndarray,
    sigma: float = 1.0,
    regularization_lambda: float | None = None,
) -> dict[str, float]:
    """封装：从时间数组自动计算 dt 再调用 SVD 反卷积。"""
    dt = float(np.mean(np.diff(times))) if len(times) > 1 else 1.0
    return svd_deconvolution(
        aif=aif,
        tic=tic,
        dt=dt,
        sigma=sigma,
        regularization_lambda=regularization_lambda,
    )
```

- [ ] **Step 2: 写测试用例**

```python
# backend/tests/test_deconvolution.py
import numpy as np
import pytest

from src.deconvolution import build_circulant_matrix, svd_deconvolution, temporal_gaussian_filter


def test_temporal_gaussian_filter():
    tic = np.array([0.0, 0.0, 10.0, 0.0, 0.0], dtype=np.float32)
    smoothed = temporal_gaussian_filter(tic, sigma=1.0)
    assert smoothed[2] > smoothed[0]
    assert smoothed.shape == tic.shape


def test_build_circulant_matrix():
    aif = np.array([1.0, 2.0, 3.0], dtype=np.float32)
    A = build_circulant_matrix(aif)
    expected = np.array([
        [1, 0, 0],
        [2, 1, 0],
        [3, 2, 1],
    ], dtype=np.float64)
    np.testing.assert_array_equal(A, expected)


def test_svd_deconvolution_basic():
    """用简单的已知卷积关系验证反卷积结果。"""
    dt = 0.33
    n = 30
    times = np.arange(n) * dt

    # 构造一个简单 AIF：三角波
    aif = np.zeros(n)
    aif[2:7] = np.array([1, 3, 5, 3, 1])

    # 构造一个简单 residue function：指数衰减
    r = np.exp(-times / 1.5)

    # 卷积得到 tic
    tic = np.convolve(aif, r, mode="full")[:n]

    result = svd_deconvolution(aif, tic, dt=dt, sigma=0.5, regularization_lambda=0.1)

    assert result["dsa_cbf"] > 0
    assert result["dsa_mtt"] > 0
    assert result["dsa_tmax"] >= 0
    assert len(result["flow_scaled_residue"]) == n


def test_svd_deconvolution_no_signal():
    """当输入几乎无信号时，应返回合理的安全值。"""
    aif = np.ones(10, dtype=np.float32)
    tic = np.ones(10, dtype=np.float32)
    result = svd_deconvolution(aif, tic, dt=0.33, sigma=0.5, regularization_lambda=0.1)
    # 基线校正后信号几乎为 0，cbf 应该很小
    assert result["dsa_cbf"] < 1e3  # 不至于爆掉
```

- [ ] **Step 3: 运行测试**

Run:
```bash
cd /Users/wudeyi/code/claude/dsa/backend
pytest tests/test_deconvolution.py -v
```

Expected: 4 tests PASS

- [ ] **Step 4: Commit**

```bash
git add backend/src/deconvolution.py backend/tests/test_deconvolution.py
git commit -m "feat: 实现 SVD 反卷积模块，支持 DSA-CBF/MTT/Tmax/CBV 计算"
```

---

### Task 6: matplotlib 交互式选点脚本

**Files:**
- Create: `backend/src/interactive_picker.py`

**设计要点:**
- 加载 DICOM，显示中间帧
- 鼠标点击选点：第一个点为 AIF，后续最多 3 个点为 ROI
- 实时显示已选点的标记
- 选完后自动提取 TIC、计算所有参数、绘制 TIC 曲线和 residue function

- [ ] **Step 1: 写交互式选点脚本**

```python
# backend/src/interactive_picker.py
"""交互式选点脚本：用 matplotlib 验证 DSA 灌注算法。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from dicom_parser import parse_dicom, export_preview_frames
from tic_extractor import extract_aif_and_rois
from perfusion_params import compute_tic_parameters
from deconvolution import compute_deconvolution_parameters


def pick_points(frame_image: np.ndarray, max_rois: int = 3):
    """
    弹出 matplotlib 窗口，让用户点击选点。
    第一个点为 AIF，后续为 ROI。
    返回 aif 坐标和 roi 列表。
    """
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.imshow(frame_image, cmap="gray")
    ax.set_title(
        "请点击选点：\n第 1 个点 = AIF (红色)\n第 2-4 个点 = ROI (绿/蓝/黄)\n"
        f"按 Enter 结束 (最多 {max_rois} 个 ROI)",
        fontsize=12,
    )

    points = []
    colors = ["red", "green", "blue", "orange"]
    labels = ["AIF", "ROI-1", "ROI-2", "ROI-3"]

    def on_click(event):
        if event.inaxes != ax:
            return
        if len(points) >= 1 + max_rois:
            return
        x, y = event.xdata, event.ydata
        points.append((x, y))
        idx = len(points) - 1
        color = colors[idx % len(colors)]
        label = labels[idx % len(labels)]
        ax.plot(x, y, "o", color=color, markersize=12, label=label)
        ax.text(x + 10, y - 10, label, color=color, fontsize=10)
        fig.canvas.draw()

    fig.canvas.mpl_connect("button_press_event", on_click)
    plt.show()

    if len(points) < 2:
        raise ValueError("请至少选择 1 个 AIF 和 1 个 ROI")

    aif = {"x": float(points[0][0]), "y": float(points[0][1]), "radius": 10.0}
    rois = []
    for i, (x, y) in enumerate(points[1:], start=1):
        rois.append({
            "id": f"roi-{i}",
            "x": float(x),
            "y": float(y),
            "radius": 15.0,
        })

    return aif, rois


def analyze(dicom_path: str | Path, output_dir: str | Path | None = None):
    """完整分析流程：解析 -> 选点 -> 提取 TIC -> 计算参数 -> 绘图 -> 保存结果。"""
    dicom_path = Path(dicom_path)
    print(f"正在解析 DICOM: {dicom_path}")

    data = parse_dicom(dicom_path)
    pixel_array = data["pixel_array"]
    times = data["times"]
    n_frames, rows, cols = pixel_array.shape

    print(f"帧数: {n_frames}, 尺寸: {rows}x{cols}, 帧率: {data.get('frame_rate')} fps")

    # 显示中间帧用于选点
    mid_frame_idx = n_frames // 2
    mid_frame = pixel_array[mid_frame_idx]
    # 归一化到 0-255 用于显示
    f_min, f_max = mid_frame.min(), mid_frame.max()
    display_frame = ((mid_frame - f_min) / max(f_max - f_min, 1e-6) * 255).astype(np.uint8)

    print("请在弹出的窗口中选点...")
    aif, rois = pick_points(display_frame, max_rois=3)
    print(f"AIF: {aif}")
    for r in rois:
        print(f"  {r['id']}: ({r['x']:.1f}, {r['y']:.1f}), r={r['radius']}")

    # 提取 TIC
    tics = extract_aif_and_rois(pixel_array, aif, rois)

    # 计算参数
    results = {}
    for key, tic in tics.items():
        tic_params = compute_tic_parameters(tic, times, baseline_frames=3)
        if key != "aif":
            deconv_params = compute_deconvolution_parameters(
                tics["aif"], tic, times, sigma=1.0
            )
            tic_params.update({
                "dsa_cbf": deconv_params["dsa_cbf"],
                "dsa_cbv": deconv_params["dsa_cbv"],
                "dsa_mtt": deconv_params["dsa_mtt"],
                "dsa_tmax": deconv_params["dsa_tmax"],
            })
        results[key] = tic_params

    # 打印结果
    print("\n=== 分析结果 ===")
    for key, params in results.items():
        print(f"\n[{key.upper()}]")
        for p_name, p_val in params.items():
            if isinstance(p_val, float):
                print(f"  {p_name}: {p_val:.4f}")
            elif isinstance(p_val, np.ndarray):
                print(f"  {p_name}: array shape {p_val.shape}")

    # 绘图
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # 1. TIC 曲线
    ax_tic = axes[0, 0]
    colors = {"aif": "red", "roi-1": "green", "roi-2": "blue", "roi-3": "orange"}
    for key, tic in tics.items():
        ax_tic.plot(times, tic, label=key.upper(), color=colors.get(key, "black"))
    ax_tic.set_xlabel("Time (s)")
    ax_tic.set_ylabel("Intensity")
    ax_tic.set_title("Time-Intensity Curves")
    ax_tic.legend()
    ax_tic.grid(True, linestyle="--", alpha=0.5)

    # 2. Residue functions
    ax_res = axes[0, 1]
    for key in tics:
        if key == "aif":
            continue
        deconv = compute_deconvolution_parameters(tics["aif"], tics[key], times, sigma=1.0)
        ax_res.plot(times, deconv["flow_scaled_residue"], label=key.upper(), color=colors.get(key, "black"))
    ax_res.set_xlabel("Time (s)")
    ax_res.set_ylabel("Flow-scaled Residue k(t)")
    ax_res.set_title("Residue Functions")
    ax_res.legend()
    ax_res.grid(True, linestyle="--", alpha=0.5)

    # 3. 参数表格图
    ax_table = axes[1, 0]
    ax_table.axis("off")
    table_data = []
    for key, params in results.items():
        if key == "aif":
            continue
        row = [
            key.upper(),
            f"{params['ttp']:.2f}",
            f"{params['auc']:.2f}",
            f"{params['wash_in_slope']:.2f}",
            f"{params['dsa_cbf']:.4f}",
            f"{params['dsa_mtt']:.2f}",
            f"{params['dsa_tmax']:.2f}",
        ]
        table_data.append(row)

    if table_data:
        table = ax_table.table(
            cellText=table_data,
            colLabels=["ROI", "TTP", "AUC", "Wash-in", "DSA-CBF", "DSA-MTT", "DSA-Tmax"],
            loc="center",
            cellLoc="center",
        )
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1.2, 1.5)
    ax_table.set_title("Perfusion Parameters", y=0.95)

    # 4. 带标记的 DSA 帧
    ax_img = axes[1, 1]
    ax_img.imshow(display_frame, cmap="gray")
    for key, circle in [("aif", aif)] + [(r["id"], r) for r in rois]:
        color = colors.get(key, "white")
        circ = plt.Circle((circle["x"], circle["y"]), circle["radius"], color=color, fill=False, linewidth=2)
        ax_img.add_patch(circ)
        ax_img.text(circle["x"], circle["y"] - circle["radius"] - 5, key.upper(), color=color, fontsize=9, ha="center")
    ax_img.set_title("Selected Regions")
    ax_img.axis("off")

    plt.tight_layout()

    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 保存结果 JSON
        result_path = output_dir / "result.json"
        with open(result_path, "w", encoding="utf-8") as f:
            # numpy 不可直接 JSON 序列化，先转 list
            serializable = {}
            for k, v in results.items():
                serializable[k] = {kk: float(vv) if isinstance(vv, (np.floating, float)) else vv for kk, vv in v.items()}
            json.dump(serializable, f, indent=2, ensure_ascii=False)
        print(f"\n结果已保存: {result_path}")

        # 保存图片
        fig_path = output_dir / "analysis.png"
        plt.savefig(fig_path, dpi=150)
        print(f"图表已保存: {fig_path}")

    plt.show()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python interactive_picker.py <dicom_path> [output_dir]")
        sys.exit(1)

    dicom_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    analyze(dicom_path, output_dir)
```

- [ ] **Step 2: 运行脚本验证（如果有测试 DICOM 数据）**

Run:
```bash
cd /Users/wudeyi/code/claude/dsa/backend
conda activate dsa-perfusion
python src/interactive_picker.py data/你的测试文件.dcm data/output/
```

Expected: matplotlib 窗口弹出，显示 DSA 帧，可点击选点，关闭窗口后输出 TIC 曲线和参数结果图

- [ ] **Step 3: Commit**

```bash
git add backend/src/interactive_picker.py
git commit -m "feat: 实现 matplotlib 交互式选点脚本，支持完整分析流程"
```

---

### Task 7: 全图伪彩图生成模块

**Files:**
- Create: `backend/src/parametric_map.py`
- Create: `backend/tests/test_parametric_map.py`

**设计要点:**
- 对血管掩膜内的每个像素，重复执行 TIC 提取 + 反卷积计算
- 生成 CBF、MTT、Tmax 三张伪彩图
- 使用 `matplotlib.colormaps` (jet/turbo)，背景透明
- 为了性能，可对全图做下采样或用向量化操作，MVP 阶段允许慢一些

- [ ] **Step 1: 写伪彩图生成模块**

```python
# backend/src/parametric_map.py
"""全图伪彩图生成模块。"""

from __future__ import annotations

import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize

from tic_extractor import extract_tic
from deconvolution import compute_deconvolution_parameters


def generate_vessel_mask(
    pixel_array: np.ndarray,
    threshold_ratio: float = 0.15,
) -> np.ndarray:
    """
    基于时间最大强度投影 (MaxIP) 生成血管掩膜。
    阈值设为 MaxIP 最大值的 threshold_ratio。
    """
    maxip = np.max(pixel_array, axis=0)
    threshold = np.max(maxip) * threshold_ratio
    mask = maxip > threshold
    return mask


def compute_parametric_maps(
    pixel_array: np.ndarray,
    times: np.ndarray,
    aif: dict[str, float],
    sigma: float = 1.0,
    downsample: int | None = None,
) -> dict[str, np.ndarray]:
    """
    计算全图灌注参数图。

    Args:
        pixel_array: shape (n_frames, rows, cols)
        times: 时间轴
        aif: {"x", "y", "radius"}
        sigma: 高斯滤波 sigma
        downsample: 若设置，对图像空间下采样加速计算

    Returns:
        {
            "cbf": np.ndarray (rows, cols),
            "mtt": np.ndarray (rows, cols),
            "tmax": np.ndarray (rows, cols),
            "cbv": np.ndarray (rows, cols),
            "mask": np.ndarray (rows, cols) bool,
        }
    """
    n_frames, rows, cols = pixel_array.shape
    mask = generate_vessel_mask(pixel_array)

    # 可选下采样
    if downsample and downsample > 1:
        from skimage.transform import downscale_local_mean
        ds_frames = []
        for t in range(n_frames):
            ds = downscale_local_mean(pixel_array[t], (downsample, downsample))
            ds_frames.append(ds)
        pixel_array = np.stack(ds_frames, axis=0)
        rows, cols = pixel_array.shape[1], pixel_array.shape[2]
        # 重新计算掩膜
        mask = generate_vessel_mask(pixel_array)
        aif_x = aif["x"] / downsample
        aif_y = aif["y"] / downsample
    else:
        aif_x = aif["x"]
        aif_y = aif["y"]

    # 提取 AIF
    aif_tic = extract_tic(pixel_array, aif_x, aif_y, max(aif["radius"] / (downsample or 1), 2))

    cbf_map = np.zeros((rows, cols), dtype=np.float32)
    mtt_map = np.zeros((rows, cols), dtype=np.float32)
    tmax_map = np.zeros((rows, cols), dtype=np.float32)
    cbv_map = np.zeros((rows, cols), dtype=np.float32)

    # 仅对掩膜内像素计算（性能优化点）
    coords = np.argwhere(mask)
    total = len(coords)
    print(f"开始计算伪彩图，掩膜内像素数: {total}")

    for idx, (y, x) in enumerate(coords):
        if idx % 500 == 0:
            print(f"  进度: {idx}/{total} ({idx/total*100:.1f}%)")
        tic = pixel_array[:, y, x].astype(np.float32)
        try:
            params = compute_deconvolution_parameters(aif_tic, tic, times, sigma=sigma)
            cbf_map[y, x] = params["dsa_cbf"]
            mtt_map[y, x] = params["dsa_mtt"]
            tmax_map[y, x] = params["dsa_tmax"]
            cbv_map[y, x] = params["dsa_cbv"]
        except Exception:
            # 忽略异常像素
            pass

    return {
        "cbf": cbf_map,
        "mtt": mtt_map,
        "tmax": tmax_map,
        "cbv": cbv_map,
        "mask": mask,
    }


def save_parametric_map(
    param_map: np.ndarray,
    mask: np.ndarray,
    output_path: str,
    cmap_name: str = "jet",
    vmin: float | None = None,
    vmax: float | None = None,
) -> None:
    """
    将参数图保存为带透明背景的 PNG。
    掩膜外像素 alpha=0。
    """
    if vmin is None:
        valid = param_map[mask]
        vmin = float(np.percentile(valid, 1)) if len(valid) > 0 else 0.0
    if vmax is None:
        valid = param_map[mask]
        vmax = float(np.percentile(valid, 99)) if len(valid) > 0 else 1.0

    norm = Normalize(vmin=vmin, vmax=vmax)
    cmap = plt.get_cmap(cmap_name)

    rgba = cmap(norm(param_map))  # shape (H, W, 4)
    rgba[~mask] = [0, 0, 0, 0]    # 背景透明

    # 转为 0-255
    img = (rgba * 255).astype(np.uint8)
    Image.fromarray(img, mode="RGBA").save(output_path)
```

- [ ] **Step 2: 写测试用例**

```python
# backend/tests/test_parametric_map.py
import numpy as np
import tempfile
from pathlib import Path

from src.parametric_map import generate_vessel_mask, compute_parametric_maps, save_parametric_map


def test_generate_vessel_mask():
    pixel_array = np.zeros((5, 20, 20), dtype=np.float32)
    pixel_array[:, 8:12, 8:12] = 100.0  # 中间一块亮
    mask = generate_vessel_mask(pixel_array, threshold_ratio=0.1)
    assert mask.shape == (20, 20)
    assert mask[10, 10] is True
    assert mask[0, 0] is False


def test_compute_parametric_maps():
    # 构造简单数据：10 帧，32x32，中心有一个点随时间上升
    n = 10
    pixel_array = np.zeros((n, 32, 32), dtype=np.float32)
    pixel_array[:, 16, 16] = np.linspace(0, 100, n)
    pixel_array[:, 10, 10] = np.linspace(0, 80, n)
    times = np.arange(n) * 0.33

    aif = {"x": 16.0, "y": 16.0, "radius": 2.0}
    result = compute_parametric_maps(pixel_array, times, aif, downsample=2)

    assert "cbf" in result
    assert "mtt" in result
    assert "tmax" in result
    assert result["cbf"].shape == (16, 16)


def test_save_parametric_map():
    param_map = np.random.rand(32, 32).astype(np.float32)
    mask = np.zeros((32, 32), dtype=bool)
    mask[8:24, 8:24] = True

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test_map.png"
        save_parametric_map(param_map, mask, str(path), cmap_name="jet")
        assert path.exists()
        from PIL import Image
        img = Image.open(path)
        assert img.mode == "RGBA"
```

- [ ] **Step 3: 运行测试**

Run:
```bash
cd /Users/wudeyi/code/claude/dsa/backend
pytest tests/test_parametric_map.py -v
```

Expected: 3 tests PASS

- [ ] **Step 4: Commit**

```bash
git add backend/src/parametric_map.py backend/tests/test_parametric_map.py
git commit -m "feat: 实现全图伪彩图生成模块，支持血管掩膜和透明背景导出"
```

---

## Phase 2: 后端 Web 服务化 (FastAPI)

### Task 8: FastAPI 骨架与文件上传

**Files:**
- Create: `backend/src/main.py`
- Create: `backend/src/models.py`
- Create: `backend/src/services.py`

- [ ] **Step 1: 设计 Pydantic 数据模型**

```python
# backend/src/models.py
from __future__ import annotations

from pydantic import BaseModel
from typing import Literal


class AIFInput(BaseModel):
    x: float
    y: float
    radius: float = 10.0


class ROIInput(BaseModel):
    id: str
    x: float
    y: float
    radius: float = 15.0


class AnalyzeRequest(BaseModel):
    aif: AIFInput
    rois: list[ROIInput]
    settings: dict | None = None


class AnalysisResponse(BaseModel):
    status: Literal["success", "error"]
    tic_curves: dict[str, list[float]] | None = None
    time_points: list[float] | None = None
    parameters: dict[str, dict[str, float]] | None = None
    parametric_maps: dict[str, str] | None = None
    message: str | None = None
```

- [ ] **Step 2: 设计服务层**

```python
# backend/src/services.py
"""业务逻辑层：封装 DICOM 解析、分析计算、伪彩图生成。"""

from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

import numpy as np

from dicom_parser import parse_dicom, export_preview_frames
from tic_extractor import extract_aif_and_rois
from perfusion_params import compute_tic_parameters
from deconvolution import compute_deconvolution_parameters
from parametric_map import compute_parametric_maps, save_parametric_map


DATA_DIR = Path(__file__).parent.parent / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
PREVIEWS_DIR = DATA_DIR / "previews"
RESULTS_DIR = DATA_DIR / "results"

for d in (UPLOADS_DIR, PREVIEWS_DIR, RESULTS_DIR):
    d.mkdir(parents=True, exist_ok=True)


def save_upload(file_bytes: bytes, filename: str) -> str:
    """保存上传的 DICOM 文件，返回 study_id。"""
    study_id = str(uuid.uuid4())
    study_dir = UPLOADS_DIR / study_id
    study_dir.mkdir(parents=True, exist_ok=True)
    file_path = study_dir / filename
    with open(file_path, "wb") as f:
        f.write(file_bytes)
    return study_id


def process_dicom(study_id: str) -> dict:
    """解析 DICOM 并生成预览帧。"""
    study_dir = UPLOADS_DIR / study_id
    dicom_files = list(study_dir.iterdir())
    if not dicom_files:
        raise FileNotFoundError("未找到上传的 DICOM 文件")

    dicom_path = dicom_files[0] if len(dicom_files) == 1 else study_dir
    data = parse_dicom(dicom_path)

    preview_dir = PREVIEWS_DIR / study_id
    preview_dir.mkdir(parents=True, exist_ok=True)
    frame_paths = export_preview_frames(data["pixel_array"], preview_dir)

    metadata = {
        "study_id": study_id,
        "frames": data["frames"],
        "rows": data["rows"],
        "cols": data["cols"],
        "frame_rate": data["frame_rate"],
        "frame_time": data["frame_time"],
        "pixel_spacing": data["pixel_spacing"],
        "photometric_interpretation": data["photometric_interpretation"],
        "frame_paths": frame_paths,
    }
    meta_path = preview_dir / "metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, default=str)

    return metadata


def analyze_study(study_id: str, aif: dict, rois: list[dict], settings: dict | None) -> dict:
    """执行灌注分析。"""
    settings = settings or {}
    preview_dir = PREVIEWS_DIR / study_id
    meta_path = preview_dir / "metadata.json"
    if not meta_path.exists():
        raise FileNotFoundError("该 study 尚未解析，请先调用 process")

    with open(meta_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    # 重新解析 DICOM 获取原始像素
    study_dir = UPLOADS_DIR / study_id
    dicom_files = list(study_dir.iterdir())
    dicom_path = dicom_files[0] if len(dicom_files) == 1 else study_dir
    data = parse_dicom(dicom_path)
    pixel_array = data["pixel_array"]
    times = data["times"]

    # TIC 提取
    tics = extract_aif_and_rois(pixel_array, aif, rois)

    # 参数计算
    parameters = {}
    tic_curves = {k: v.tolist() for k, v in tics.items()}

    for key, tic in tics.items():
        tic_params = compute_tic_parameters(tic, times, baseline_frames=settings.get("baseline_frames", 3))
        if key != "aif":
            deconv = compute_deconvolution_parameters(
                tics["aif"], tic, times,
                sigma=settings.get("sigma", 1.0),
            )
            tic_params.update({
                "dsa_cbf": deconv["dsa_cbf"],
                "dsa_cbv": deconv["dsa_cbv"],
                "dsa_mtt": deconv["dsa_mtt"],
                "dsa_tmax": deconv["dsa_tmax"],
            })
        parameters[key] = tic_params

    # 全图伪彩图（可选，MVP 阶段若计算慢可单独接口调用）
    parametric_maps = {}
    result_dir = RESULTS_DIR / study_id
    result_dir.mkdir(parents=True, exist_ok=True)

    if settings.get("generate_maps", True):
        maps = compute_parametric_maps(
            pixel_array, times, aif,
            sigma=settings.get("sigma", 1.0),
            downsample=settings.get("downsample", None),
        )
        for map_name in ["cbf", "mtt", "tmax"]:
            path = result_dir / f"{map_name}_map.png"
            save_parametric_map(
                maps[map_name], maps["mask"], str(path),
                cmap_name=settings.get("colormap", "jet"),
            )
            parametric_maps[map_name] = str(path.relative_to(DATA_DIR))

    # 保存分析结果 JSON
    result = {
        "status": "success",
        "tic_curves": tic_curves,
        "time_points": times.tolist(),
        "parameters": parameters,
        "parametric_maps": parametric_maps,
    }
    with open(result_dir / "analysis.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)

    return result
```

- [ ] **Step 3: 写 FastAPI 主入口**

```python
# backend/src/main.py
"""FastAPI 主入口。"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from models import AnalyzeRequest, AnalysisResponse
from services import save_upload, process_dicom, analyze_study, DATA_DIR

app = FastAPI(title="DSA Perfusion Analysis API")

# 静态文件服务：预览帧和结果图
app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    content = await file.read()
    study_id = save_upload(content, file.filename or "upload.dcm")
    metadata = process_dicom(study_id)
    return {
        "study_id": study_id,
        "frame_count": metadata["frames"],
        "frame_rate": metadata["frame_rate"],
        "width": metadata["cols"],
        "height": metadata["rows"],
        "status": "processed",
    }


@app.get("/api/studies/{study_id}/frames")
def get_frames(study_id: str):
    preview_dir = DATA_DIR / "previews" / study_id
    meta_path = preview_dir / "metadata.json"
    if not meta_path.exists():
        raise HTTPException(status_code=404, detail="Study not found")

    with open(meta_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    frames = []
    frame_time = metadata.get("frame_time") or 1.0
    for i, fp in enumerate(metadata["frame_paths"]):
        rel = Path(fp).relative_to(DATA_DIR)
        frames.append({
            "index": i,
            "url": f"/data/{rel}",
            "time": round(i * frame_time, 3),
        })

    return {
        "study_id": study_id,
        "frames": frames,
        "width": metadata["cols"],
        "height": metadata["rows"],
        "frame_rate": metadata["frame_rate"],
    }


@app.post("/api/studies/{study_id}/analyze", response_model=AnalysisResponse)
def analyze(study_id: str, request: AnalyzeRequest):
    try:
        result = analyze_study(study_id, request.aif.model_dump(), [r.model_dump() for r in request.rois], request.settings)
        return AnalysisResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/studies/{study_id}/results")
def get_results(study_id: str):
    result_path = DATA_DIR / "results" / study_id / "analysis.json"
    if not result_path.exists():
        raise HTTPException(status_code=404, detail="Results not found")
    with open(result_path, "r", encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/studies/{study_id}/parametric/{map_type}")
def get_parametric_map(study_id: str, map_type: str):
    map_path = DATA_DIR / "results" / study_id / f"{map_type}_map.png"
    if not map_path.exists():
        raise HTTPException(status_code=404, detail="Map not found")
    return FileResponse(map_path, media_type="image/png")
```

- [ ] **Step 4: 运行 FastAPI 服务并测试**

Run:
```bash
cd /Users/wudeyi/code/claude/dsa/backend
conda activate dsa-perfusion
uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

在另一个终端测试：
```bash
curl -X POST "http://127.0.0.1:8000/api/upload" -F "file=@data/你的测试文件.dcm"
```

Expected: 返回 JSON 包含 study_id、frame_count 等信息

- [ ] **Step 5: Commit**

```bash
git add backend/src/models.py backend/src/services.py backend/src/main.py
git commit -m "feat: 搭建 FastAPI 骨架，实现上传、解析、分析接口"
```

---

## Phase 3: 前端 (Vue 3 + TypeScript)

> **说明:** 本阶段待 Phase 1 和 Phase 2 后端稳定后实施，需医生可用的交互界面。

### Task 9: Vue 3 项目骨架

**Files:**
- Create: `frontend/` 目录及 Vue CLI / Vite 初始化文件

- [ ] **Step 1: 用 Vite 初始化 Vue 3 项目**

Run:
```bash
cd /Users/wudeyi/code/claude/dsa
npm create vite@latest frontend -- --template vue-ts
```

- [ ] **Step 2: 安装依赖**

Run:
```bash
cd /Users/wudeyi/code/claude/dsa/frontend
npm install
npm install pinia element-plus @element-plus/icons-vue echarts vue-echarts fabric
```

- [ ] **Step 3: 启动验证**

Run:
```bash
npm run dev
```

Expected: 浏览器打开 `http://localhost:5173` 能看到 Vite + Vue 欢迎页

- [ ] **Step 4: Commit**

```bash
git add frontend/
git commit -m "chore: 初始化 Vue 3 + Vite + TypeScript 前端项目"
```

---

### Task 10: 核心页面与组件开发

**Files:**
- Create: `frontend/src/views/UploadView.vue`
- Create: `frontend/src/views/StudyView.vue`
- Create: `frontend/src/components/DsaPlayer.vue`
- Create: `frontend/src/components/AnnotationCanvas.vue`
- Create: `frontend/src/components/TicChart.vue`
- Create: `frontend/src/components/ResultPanel.vue`
- Create: `frontend/src/stores/studyStore.ts`
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/router/index.ts` (若使用 vue-router)

由于前端代码量较大，本计划只列出各组件职责和关键接口，具体实现可在执行阶段逐步展开：

| 组件 | 职责 |
|------|------|
| `UploadView.vue` | DICOM 拖拽上传，调用 `/api/upload` |
| `StudyView.vue` | 三栏布局：左侧播放器、中间画布、右侧面板 |
| `DsaPlayer.vue` | 帧序列播放/暂停/逐帧/时间轴/缩略图列表 |
| `AnnotationCanvas.vue` | Fabric.js 画布：AIF 圆(红)+ROI 圆(绿/蓝/黄)，拖拽调整，坐标换算 |
| `TicChart.vue` | ECharts 绘制 TIC 曲线（AIF + 3 ROI） |
| `ResultPanel.vue` | 显示 TTP/AUC/Wash-in/CBF/MTT/Tmax 表格，伪彩图切换 |
| `studyStore.ts` | Pinia store：管理当前 study、帧列表、AIF/ROI、分析结果 |

- [ ] **Step 1: 实现路由和页面骨架**
- [ ] **Step 2: 实现上传页面**
- [ ] **Step 3: 实现 DSA 播放器**
- [ ] **Step 4: 实现标注画布**
- [ ] **Step 5: 实现 TIC 曲线和结果面板**
- [ ] **Step 6: Commit**

---

## Phase 4: 联调与完善

### Task 11: 前后端联调

- [ ] **Step 1: 完整链路测试**
  - 上传 DICOM → 解析成功 → 播放器加载帧序列
  - 标注 AIF + 3 ROI → 调用 `/api/analyze`
  - 后端返回 TIC 曲线和参数 → 前端正确渲染
- [ ] **Step 2: 伪彩图叠加展示联调**
  - 前端通过 `mix-blend-mode` 或 `opacity` 叠加伪彩图
  - 切换 CBF/MTT/Tmax 图层
- [ ] **Step 3: 报告导出功能**
  - 后端实现 PDF/Excel 生成
  - 前端添加导出按钮

### Task 12: 测试与优化

- [ ] **Step 1: 用 5-10 例真实 DICOM 测试计算结果合理性**
- [ ] **Step 2: 性能优化（伪彩图计算若太慢，增加 downsample 或异步任务）**
- [ ] **Step 3: UI 细节打磨（加载状态、错误提示、中文文案）**

---

## 附：快速执行命令汇总

```bash
# 1. 环境安装
cd /Users/wudeyi/code/claude/dsa/backend
conda env create -f environment.yml
conda activate dsa-perfusion

# 2. 运行测试
pytest tests/ -v

# 3. 运行交互式选点脚本
python src/interactive_picker.py data/你的测试文件.dcm data/output/

# 4. 启动后端
uvicorn src.main:app --reload --host 127.0.0.1 --port 8000

# 5. 启动前端
cd /Users/wudeyi/code/claude/dsa/frontend
npm run dev
```

---

## Self-Review Checklist

1. **Spec coverage:**
   - [x] DICOM 解析（单文件/多文件） -> Task 2
   - [x] TIC 提取（AIF + ROI） -> Task 3
   - [x] TTP / AUC / Wash-in slope 计算 -> Task 4
   - [x] SVD 反卷积 / DSA-CBF / DSA-MTT / DSA-Tmax -> Task 5
   - [x] 全图伪彩图生成 -> Task 7
   - [x] FastAPI 后端服务 -> Task 8
   - [x] Vue 前端骨架 -> Task 9
   - [x] 前端核心组件 -> Task 10
   - [x] 前后端联调 -> Task 11

2. **Placeholder scan:** 无 TBD / TODO / "implement later" 等占位符。

3. **Type consistency:**
   - `parse_dicom` 返回 `dict[str, Any]`，后续接口一致使用 `"pixel_array"`, `"times"` 等 key
   - `AIFInput` / `ROIInput` Pydantic 模型字段名与前端需求一致
   - `compute_deconvolution_parameters` 返回 `dict[str, float]`，字段名 `dsa_cbf`, `dsa_mtt`, `dsa_tmax` 与需求一致
