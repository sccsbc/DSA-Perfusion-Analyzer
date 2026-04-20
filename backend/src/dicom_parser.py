"""DICOM 解析模块：支持单文件多帧和多文件序列。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from pydicom import dcmread


def _get_frame_time(ds) -> float | None:
    """提取帧间隔时间（秒）。"""
    # 优先读取 Frame Time (0018,1063)
    if hasattr(ds, "FrameTime") and ds.FrameTime:
        return float(ds.FrameTime) / 1000.0  # ms -> s
    # 次优先读取 Frame Rate (0018,1062)
    if hasattr(ds, "FrameTimeVector") and ds.FrameTimeVector:
        # 返回第一帧时间作为估算
        if len(ds.FrameTimeVector) > 0:
            return float(ds.FrameTimeVector[0]) / 1000.0
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
        ds = dcmread(str(dicom_path), force=True)
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
            ds = dcmread(str(f), force=True)
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
        if img.mode != "L":
            img = img.convert("L")
        save_path = output_dir / f"{prefix}_{i:03d}.png"
        img.save(save_path)
        paths.append(str(save_path))
    return paths
