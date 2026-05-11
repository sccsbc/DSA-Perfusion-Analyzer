"""FastAPI 应用入口：DSA 灌注分析 API 服务。"""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .models import (
    AnalyzeRequest,
    AnalyzeResponse,
    DeconvolutionParameters,
    ErrorResponse,
    RegionResult,
    TICParameters,
    UploadResponse,
)
from .services import FRAMES_DIR, get_frame_path, get_study_store, ingest_dicom, run_analysis

FRAMES_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="DSA Perfusion Analysis API",
    version="1.0.0",
    description="数字减影血管造影灌注参数计算服务",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post(
    "/api/dicom/upload",
    response_model=UploadResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def upload_dicom(file: UploadFile = File(...)):
    """上传 DICOM 文件，解析并返回 study 元数据。"""
    if not file.filename:
        raise HTTPException(400, detail="未提供文件")

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".dcm") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        study_id, metadata = ingest_dicom(Path(tmp_path))
        return UploadResponse(**metadata)

    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    except Exception as e:
        raise HTTPException(500, detail=f"处理 DICOM 失败: {e}")


@app.get(
    "/api/studies/{study_id}",
    response_model=UploadResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_study(study_id: str):
    """获取已上传 study 的元数据。"""
    store = get_study_store()
    study = store.get(study_id)
    if study is None:
        raise HTTPException(404, detail=f"Study {study_id} 不存在")
    return UploadResponse(
        study_id=study_id,
        frame_count=study["frames"],
        rows=study["rows"],
        cols=study["cols"],
        fps=study.get("frame_rate"),
        frame_time=study.get("frame_time"),
        times=study["times"].tolist(),
        pixel_spacing=list(study["pixel_spacing"]) if study.get("pixel_spacing") else None,
    )


@app.get(
    "/api/studies/{study_id}/frames/{frame_idx}",
    responses={200: {"content": {"image/png": {}}}, 404: {"model": ErrorResponse}},
)
async def get_frame(study_id: str, frame_idx: int):
    """获取单帧 DSA 图像（PNG 格式），frame_idx 从 0 开始。"""
    frame_path = get_frame_path(study_id, frame_idx)
    if frame_path is None:
        raise HTTPException(404, detail=f"帧 {frame_idx} 不存在")
    return FileResponse(str(frame_path), media_type="image/png")


@app.post(
    "/api/studies/{study_id}/analyze",
    response_model=AnalyzeResponse,
    responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
)
async def analyze_study(study_id: str, request: AnalyzeRequest):
    """提交 AIF/ROI 坐标进行灌注分析，返回全部参数和曲线数据。"""
    store = get_study_store()
    study = store.get(study_id)
    if study is None:
        raise HTTPException(404, detail=f"Study {study_id} 不存在")

    try:
        aif_dict = {"x": request.aif.x, "y": request.aif.y, "radius": request.aif.radius}
        rois_dicts = [
            {"id": r.id, "x": r.x, "y": r.y, "radius": r.radius}
            for r in request.rois
        ]
        results = run_analysis(
            study_id, aif_dict, rois_dicts,
            sigma=request.sigma,
            baseline_frames=request.baseline_frames,
        )

        regions: dict[str, RegionResult] = {}
        for key, region in results["regions"].items():
            tic_p = TICParameters(**region["tic_parameters"])
            deconv_p = None
            if region["deconvolution_parameters"] is not None:
                deconv_p = DeconvolutionParameters(**region["deconvolution_parameters"])
            regions[key] = RegionResult(
                tic_parameters=tic_p,
                deconvolution_parameters=deconv_p,
            )

        return AnalyzeResponse(
            study_id=results["study_id"],
            regions=regions,
            tic_curves=results["tic_curves"],
            residue_functions=results["residue_functions"],
            times=results["times"],
        )

    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    except Exception as e:
        raise HTTPException(500, detail=f"分析失败: {e}")
