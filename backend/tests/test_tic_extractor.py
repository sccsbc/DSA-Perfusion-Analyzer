"""TIC 提取模块测试。"""

import numpy as np
import pytest

from src.tic_extractor import create_circular_mask, extract_tic, extract_aif_and_rois


def test_create_circular_mask():
    mask = create_circular_mask(10, 10, 5, 5, 3)
    assert mask.shape == (10, 10)
    assert mask[5, 5]
    assert not mask[0, 0]


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

    # radius=0.5 确保只包含中心单个像素
    aif = {"x": 2.0, "y": 2.0, "radius": 0.5}
    rois = [{"id": "roi-1", "x": 7.0, "y": 7.0, "radius": 0.5}]

    result = extract_aif_and_rois(pixel_array, aif, rois)
    assert "aif" in result
    assert "roi-1" in result
    np.testing.assert_allclose(result["aif"], [50.0, 50.0, 50.0], atol=0.1)
    np.testing.assert_allclose(result["roi-1"], [80.0, 80.0, 80.0], atol=0.1)
