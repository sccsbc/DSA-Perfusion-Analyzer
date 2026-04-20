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
