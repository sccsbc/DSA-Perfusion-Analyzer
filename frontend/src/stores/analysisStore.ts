import { defineStore } from 'pinia'
import type { PlacedPoint, AnalyzeResponse } from '@/types'
import { POINT_CONFIGS } from '@/types'

interface AnalysisState {
  placedPoints: PlacedPoint[]
  results: AnalyzeResponse | null
  isAnalyzing: boolean
  error: string | null
}

export const useAnalysisStore = defineStore('analysis', {
  state: (): AnalysisState => ({
    placedPoints: [],
    results: null,
    isAnalyzing: false,
    error: null,
  }),

  getters: {
    aifPoint: (state): PlacedPoint | null =>
      state.placedPoints.find((p: PlacedPoint) => p.id === 'aif') ?? null,

    roiPoints: (state): PlacedPoint[] =>
      state.placedPoints.filter((p: PlacedPoint) => p.id !== 'aif'),

    canAnalyze: (state): boolean => {
      const hasAif = state.placedPoints.some((p: PlacedPoint) => p.id === 'aif')
      const hasRois = state.placedPoints.some((p: PlacedPoint) => p.id !== 'aif')
      return hasAif && hasRois && !state.isAnalyzing
    },

    nextPointConfig: (state) => {
      return POINT_CONFIGS[state.placedPoints.length] ?? null
    },

    pointsSummary: (state): string => {
      const aif = state.placedPoints.find((p: PlacedPoint) => p.id === 'aif')
      const roiCount = state.placedPoints.filter((p: PlacedPoint) => p.id !== 'aif').length
      const parts: string[] = []
      if (aif) parts.push('AIF ✓')
      else parts.push('AIF ?')
      parts.push(`ROI ${roiCount}/3`)
      return parts.join('  |  ')
    },
  },

  actions: {
    addPoint(x: number, y: number) {
      const config = this.nextPointConfig
      if (!config) return
      this.placedPoints.push({
        id: config.id,
        x,
        y,
        radius: config.radius,
        label: config.label,
        color: config.color,
      })
      this.results = null
      this.error = null
    },

    removePoint(id: string) {
      const idx = this.placedPoints.findIndex((p: PlacedPoint) => p.id === id)
      if (idx === -1) return
      this.placedPoints.splice(idx)
      this.results = null
      this.error = null
    },

    clearPoints() {
      this.placedPoints = []
      this.results = null
      this.error = null
    },

    setResults(results: AnalyzeResponse) {
      this.results = results
      this.error = null
    },

    setError(msg: string) {
      this.error = msg
    },
  },
})
