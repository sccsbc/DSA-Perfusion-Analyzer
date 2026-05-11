/** 后端 API 响应类型，与 Pydantic 模型对应 */

export interface UploadResponse {
  study_id: string
  frame_count: number
  rows: number
  cols: number
  fps: number | null
  frame_time: number | null
  times: number[]
  pixel_spacing: [number, number] | null
}

export interface PointCoord {
  x: number
  y: number
  radius: number
}

export interface ROIInput extends PointCoord {
  id: string
}

export interface AnalyzeRequest {
  aif: PointCoord
  rois: ROIInput[]
  sigma?: number
  baseline_frames?: number
}

export interface TICParameters {
  ttp: number
  auc: number
  wash_in_slope: number
  peak: number
}

export interface DeconvolutionParameters {
  dsa_cbf: number
  dsa_cbv: number
  dsa_mtt: number
  dsa_tmax: number
}

export interface RegionResult {
  tic_parameters: TICParameters
  deconvolution_parameters: DeconvolutionParameters | null
}

export interface AnalyzeResponse {
  study_id: string
  regions: Record<string, RegionResult>
  tic_curves: Record<string, number[]>
  residue_functions: Record<string, number[]>
  times: number[]
}

/** 前端已放置的选点 */
export interface PlacedPoint {
  id: string       // "aif" | "roi-1" | "roi-2" | "roi-3"
  x: number
  y: number
  radius: number
  label: string    // "AIF" | "ROI-1" | ...
  color: string    // CSS 颜色
}

/** 选点配置 */
export const POINT_CONFIGS = [
  { id: 'aif', label: 'AIF', color: '#ff0000', radius: 10 },
  { id: 'roi-1', label: 'ROI-1', color: '#00cc00', radius: 15 },
  { id: 'roi-2', label: 'ROI-2', color: '#0088ff', radius: 15 },
  { id: 'roi-3', label: 'ROI-3', color: '#ff8800', radius: 15 },
] as const
