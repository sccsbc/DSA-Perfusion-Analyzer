"""Pydantic 数据模型：FastAPI 请求/响应的类型定义。"""

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    study_id: str
    frame_count: int
    rows: int
    cols: int
    fps: float | None = None
    frame_time: float | None = None
    times: list[float]
    pixel_spacing: list[float] | None = None


class PointCoord(BaseModel):
    x: float
    y: float
    radius: float = Field(default=10.0, ge=1.0)


class ROIInput(BaseModel):
    id: str
    x: float
    y: float
    radius: float = Field(default=15.0, ge=1.0)


class AnalyzeRequest(BaseModel):
    aif: PointCoord
    rois: list[ROIInput] = Field(min_length=1, max_length=3)
    sigma: float = Field(default=1.0, ge=0.0)
    baseline_frames: int = Field(default=3, ge=0)


class TICParameters(BaseModel):
    ttp: float
    auc: float
    wash_in_slope: float
    peak: float


class DeconvolutionParameters(BaseModel):
    dsa_cbf: float
    dsa_cbv: float
    dsa_mtt: float
    dsa_tmax: float


class RegionResult(BaseModel):
    tic_parameters: TICParameters
    deconvolution_parameters: DeconvolutionParameters | None = None


class AnalyzeResponse(BaseModel):
    study_id: str
    regions: dict[str, RegionResult]
    tic_curves: dict[str, list[float]]
    residue_functions: dict[str, list[float]]
    times: list[float]


class ErrorResponse(BaseModel):
    detail: str
