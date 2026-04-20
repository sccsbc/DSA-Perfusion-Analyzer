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
