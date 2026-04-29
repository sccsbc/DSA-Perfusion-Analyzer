"""反卷积计算模块测试。"""

import numpy as np
import pytest

from src.deconvolution import (
    build_circulant_matrix,
    svd_deconvolution,
    temporal_gaussian_filter,
)


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

    # 真实参数
    cbf_true = 0.8
    r_true = np.exp(-times / 1.5)

    # k(t) = CBF * r(t)，ρvoi = 1.0
    k_true = cbf_true * r_true

    # 卷积得到 tic
    tic = np.convolve(aif, k_true, mode="full")[:n]

    result = svd_deconvolution(aif, tic, dt=dt, sigma=0.5, regularization_lambda=0.1)

    # 验证 CBF 在合理范围（误差 < 15%）
    assert result["dsa_cbf"] == pytest.approx(cbf_true, rel=0.15)
    # 验证 MTT 在合理范围
    assert result["dsa_mtt"] == pytest.approx(1.5, rel=0.15)
    # 验证 Tmax 接近 0（指数衰减从 t=0 开始）
    assert result["dsa_tmax"] == pytest.approx(0.0, abs=0.5)
    assert len(result["flow_scaled_residue"]) == n


def test_svd_deconvolution_no_signal():
    """当输入几乎无信号时，应返回合理的安全值。"""
    aif = np.ones(10, dtype=np.float32)
    tic = np.ones(10, dtype=np.float32)
    result = svd_deconvolution(aif, tic, dt=0.33, sigma=0.5, regularization_lambda=0.1)
    # 基线校正后信号几乎为 0，cbf 应该接近 0
    assert result["dsa_cbf"] < 1.0
