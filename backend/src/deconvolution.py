"""反卷积计算模块：SVD 反卷积求 DSA-CBF、DSA-MTT、DSA-Tmax、DSA-CBV。"""

from __future__ import annotations

import numpy as np
from scipy.linalg import svd
from scipy.ndimage import gaussian_filter1d


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
