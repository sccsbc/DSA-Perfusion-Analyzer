import apiClient from './client'
import type { UploadResponse, AnalyzeRequest, AnalyzeResponse } from '@/types'

/** 上传 DICOM 文件，返回 study 元数据 */
export async function uploadDicom(file: File): Promise<UploadResponse> {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await apiClient.post<UploadResponse>('/api/dicom/upload', formData)
  return data
}

/** 获取 DSA 帧图片的完整 URL */
export function getFrameUrl(studyId: string, frameIdx: number): string {
  return `${apiClient.defaults.baseURL}/api/studies/${studyId}/frames/${frameIdx}`
}

/** 获取 study 元数据 */
export async function getStudy(studyId: string): Promise<UploadResponse> {
  const { data } = await apiClient.get<UploadResponse>(`/api/studies/${studyId}`)
  return data
}

/** 提交 AIF/ROI 坐标进行灌注分析 */
export async function analyzeStudy(
  studyId: string,
  request: AnalyzeRequest
): Promise<AnalyzeResponse> {
  const { data } = await apiClient.post<AnalyzeResponse>(
    `/api/studies/${studyId}/analyze`,
    request
  )
  return data
}
