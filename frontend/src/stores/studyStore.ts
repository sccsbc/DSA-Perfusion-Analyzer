import { defineStore } from 'pinia'
import type { UploadResponse } from '@/types'

interface StudyState {
  currentStudy: UploadResponse | null
  currentFrameIndex: number
  isLoading: boolean
  error: string | null
}

export const useStudyStore = defineStore('study', {
  state: (): StudyState => ({
    currentStudy: null,
    currentFrameIndex: 0,
    isLoading: false,
    error: null,
  }),

  getters: {
    frameCount: (state) => state.currentStudy?.frame_count ?? 0,
    hasStudy: (state) => state.currentStudy !== null,
    studyId: (state) => state.currentStudy?.study_id ?? '',
    frameUrl(state): string | null {
      if (!state.currentStudy) return null
      const base = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
      return `${base}/api/studies/${state.currentStudy.study_id}/frames/${state.currentFrameIndex}`
    },
    currentFrameLabel(state): string {
      const total = state.currentStudy?.frame_count ?? 0
      return total > 0 ? `帧 ${state.currentFrameIndex + 1} / ${total}` : '--'
    },
  },

  actions: {
    setStudy(study: UploadResponse) {
      this.currentStudy = study
      this.currentFrameIndex = Math.floor(study.frame_count / 2)
      this.error = null
    },
    nextFrame() {
      if (this.currentFrameIndex < this.frameCount - 1) {
        this.currentFrameIndex++
      }
    },
    prevFrame() {
      if (this.currentFrameIndex > 0) {
        this.currentFrameIndex--
      }
    },
    goToFrame(idx: number) {
      if (idx >= 0 && idx < this.frameCount) {
        this.currentFrameIndex = idx
      }
    },
    clear() {
      this.currentStudy = null
      this.currentFrameIndex = 0
      this.error = null
    },
  },
})
