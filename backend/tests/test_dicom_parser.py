"""DICOM 解析模块测试。"""

import tempfile
from pathlib import Path

import numpy as np
import pytest
from pydicom import Dataset
from pydicom.uid import ExplicitVRLittleEndian

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
        assert result["frame_rate"] == pytest.approx(3.0, abs=0.1)
        assert result["pixel_array"].shape == (1, 64, 64)


def test_export_preview_frames():
    arr = np.random.rand(3, 32, 32).astype(np.float32)
    with tempfile.TemporaryDirectory() as tmpdir:
        paths = export_preview_frames(arr, tmpdir)
        assert len(paths) == 3
        for p in paths:
            assert Path(p).exists()
