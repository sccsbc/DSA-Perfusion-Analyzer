"""TIC-derived 参数计算测试。"""

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
