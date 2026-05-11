import { defineStore } from 'pinia'
import type { PlacedPoint, AnalyzeResponse } from '@/types'
import { POINT_CONFIGS } from '@/types'

interface AnalysisState {
  placedPoints: PlacedPoint[]
  results: AnalyzeResponse | null
  isAnalyzing: boolean
  error: string | null
  aifRadius: number
  roiRadius: number
}

export const useAnalysisStore = defineStore('analysis', {
  state: (): AnalysisState => ({
    placedPoints: [],
    results: null,
    isAnalyzing: false,
    error: null,
    aifRadius: 10,
    roiRadius: 15,
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
  },

  actions: {
    addPoint(x: number, y: number) {
      const config = this.nextPointConfig
      if (!config) return
      const isAif = config.id === 'aif'
      this.placedPoints.push({
        id: config.id,
        x,
        y,
        radius: isAif ? this.aifRadius : this.roiRadius,
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

    /** 实时更新所有已放置点的半径 */
    updateRadii(aifR: number, roiR: number) {
      this.aifRadius = aifR
      this.roiRadius = roiR
      for (const pt of this.placedPoints) {
        if (pt.id === 'aif') {
          pt.radius = aifR
        } else {
          pt.radius = roiR
        }
      }
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
