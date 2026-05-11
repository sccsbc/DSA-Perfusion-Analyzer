"""业务逻辑层：封装 DICOM 解析、TIC 提取和灌注参数计算。"""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import numpy as np

from .dicom_parser import parse_dicom, export_preview_frames
from .deconvolution import compute_deconvolution_parameters
from .perfusion_params import compute_tic_parameters
from .tic_extractor import extract_aif_and_rois

FRAMES_DIR = Path(__file__).parent.parent / "data" / "frames"


class StudyStore:
    """内存缓存：按 study_id 存储已解析的 DICOM 数据。"""

    def __init__(self) -> None:
        self._studies: dict[str, dict] = {}

    def store(self, study_id: str, data: dict) -> None:
        self._studies[study_id] = data

    def get(self, study_id: str) -> dict | None:
        return self._studies.get(study_id)

    def remove(self, study_id: str) -> None:
        self._studies.pop(study_id, None)
        frame_path = FRAMES_DIR / study_id
        if frame_path.exists():
            shutil.rmtree(frame_path)


_study_store = StudyStore()


def get_study_store() -> StudyStore:
    return _study_store


def ingest_dicom(dicom_path: Path) -> tuple[str, dict]:
    """解析 DICOM 文件，导出 PNG 预览帧，返回 (study_id, metadata)。"""
    data = parse_dicom(str(dicom_path))
    study_id = str(uuid.uuid4())

    frames_output_dir = FRAMES_DIR / study_id
    export_preview_frames(data["pixel_array"], frames_output_dir, prefix="frame")

    store_data = {
        "pixel_array": data["pixel_array"],
        "times": data["times"],
        "frame_time": data["frame_time"],
        "frame_rate": data["frame_rate"],
        "rows": data["rows"],
        "cols": data["cols"],
        "frames": data["frames"],
        "pixel_spacing": data["pixel_spacing"],
        "photometric_interpretation": data["photometric_interpretation"],
    }
    _study_store.store(study_id, store_data)

    metadata = {
        "study_id": study_id,
        "frame_count": data["frames"],
        "rows": data["rows"],
        "cols": data["cols"],
        "fps": data["frame_rate"],
        "frame_time": data["frame_time"],
        "times": data["times"].tolist(),
        "pixel_spacing": list(data["pixel_spacing"]) if data["pixel_spacing"] else None,
    }
    return study_id, metadata


def get_frame_path(study_id: str, frame_idx: int) -> Path | None:
    """获取已缓存的 PNG 帧文件路径。"""
    frame_path = FRAMES_DIR / study_id / f"frame_{frame_idx:03d}.png"
    return frame_path if frame_path.exists() else None


def run_analysis(
    study_id: str,
    aif_coord: dict,
    rois_coords: list[dict],
    sigma: float = 1.0,
    baseline_frames: int = 3,
) -> dict:
    """完整分析流程：提取 TIC -> 计算 TIC 参数 -> 反卷积参数。"""
    study = _study_store.get(study_id)
    if study is None:
        raise ValueError(f"Study {study_id} not found")

    pixel_array: np.ndarray = study["pixel_array"]
    times: np.ndarray = study["times"]

    # 1. 提取 TIC
    aif_input = {"x": aif_coord["x"], "y": aif_coord["y"], "radius": aif_coord["radius"]}
    roi_inputs = [
        {"id": r["id"], "x": r["x"], "y": r["y"], "radius": r["radius"]}
        for r in rois_coords
    ]
    tics = extract_aif_and_rois(pixel_array, aif_input, roi_inputs)

    # 2. 计算参数
    regions: dict[str, dict] = {}
    tic_curves: dict[str, list] = {}
    residue_functions: dict[str, list] = {}

    for key, tic in tics.items():
        tic_params = compute_tic_parameters(tic, times, baseline_frames=baseline_frames)

        region_result = {
            "tic_parameters": tic_params,
            "deconvolution_parameters": None,
        }

        if key != "aif":
            deconv = compute_deconvolution_parameters(
                tics["aif"], tic, times, sigma=sigma
            )
            region_result["deconvolution_parameters"] = {
                "dsa_cbf": deconv["dsa_cbf"],
                "dsa_cbv": deconv["dsa_cbv"],
                "dsa_mtt": deconv["dsa_mtt"],
                "dsa_tmax": deconv["dsa_tmax"],
            }
            residue_functions[key] = deconv["flow_scaled_residue"].tolist()

        regions[key] = region_result
        tic_curves[key] = tic.tolist()

    return {
        "study_id": study_id,
        "regions": regions,
        "tic_curves": tic_curves,
        "residue_functions": residue_functions,
        "times": times.tolist(),
    }
