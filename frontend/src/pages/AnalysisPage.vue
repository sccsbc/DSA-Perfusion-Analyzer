<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import DsaViewer from '@/components/DsaViewer.vue'
import FrameNavigator from '@/components/FrameNavigator.vue'
import TicChart from '@/components/TicChart.vue'
import ResidueChart from '@/components/ResidueChart.vue'
import ResultTable from '@/components/ResultTable.vue'
import { useStudyStore } from '@/stores/studyStore'
import { useAnalysisStore } from '@/stores/analysisStore'
import { getStudy, analyzeStudy } from '@/api/dsaApi'
import type { PlacedPoint } from '@/types'

const route = useRoute()
const router = useRouter()
const studyStore = useStudyStore()
const analysisStore = useAnalysisStore()

const studyLoading = ref(false)
const studyError = ref<string | null>(null)
const activeTab = ref('tic')

/** 当前半径滑动条：根据下一个选点类型自动切换 AIF/ROI 半径 */
const currentRadius = computed({
  get: () => {
    const next = analysisStore.nextPointConfig
    if (!next) return analysisStore.roiRadius
    return next.id === 'aif' ? analysisStore.aifRadius : analysisStore.roiRadius
  },
  set: (v: number) => {
    const next = analysisStore.nextPointConfig
    if (!next || next.id !== 'aif') {
      analysisStore.roiRadius = v
    } else {
      analysisStore.aifRadius = v
    }
  },
})

const radiusLabel = computed(() => {
  const next = analysisStore.nextPointConfig
  return next?.id === 'aif' ? 'AIF' : 'ROI'
})

// 确保 study 数据已加载（处理页面刷新 session 丢失）
onMounted(async () => {
  const studyId = route.params.studyId as string
  if (studyStore.hasStudy && studyStore.studyId === studyId) {
    return
  }
  studyLoading.value = true
  try {
    const study = await getStudy(studyId)
    studyStore.setStudy(study)
  } catch {
    studyError.value = '会话已过期，请重新上传 DICOM 文件'
  } finally {
    studyLoading.value = false
  }
})

function goHome() {
  studyStore.clear()
  analysisStore.clearPoints()
  router.push('/')
}

async function runAnalysis() {
  if (!analysisStore.canAnalyze || !studyStore.currentStudy) return

  const aifPt = analysisStore.aifPoint
  const roiPts = analysisStore.roiPoints
  if (!aifPt) return

  analysisStore.isAnalyzing = true
  try {
    const result = await analyzeStudy(studyStore.studyId, {
      aif: { x: aifPt.x, y: aifPt.y, radius: aifPt.radius },
      rois: roiPts.map((p: PlacedPoint) => ({ id: p.id, x: p.x, y: p.y, radius: p.radius })),
      sigma: 1.0,
      baseline_frames: 3,
    })
    analysisStore.setResults(result)
  } catch (err: unknown) {
    const msg = (err as { response?: { data?: { detail?: string } }; message?: string })?.response?.data?.detail
      || (err as Error).message
      || '分析失败'
    analysisStore.setError(msg)
  } finally {
    analysisStore.isAnalyzing = false
  }
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'ArrowLeft') studyStore.prevFrame()
  else if (e.key === 'ArrowRight') studyStore.nextFrame()
  else if (e.key === 'Enter') {
    e.preventDefault()
    runAnalysis()
  }
}
onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <div v-if="studyStore.hasStudy" class="analysis-page">
    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <n-space align="center" :size="16">
        <n-button @click="goHome" quaternary>
          ← 上传新文件
        </n-button>
        <n-divider vertical />
        <span class="toolbar-info">
          帧率: {{ studyStore.currentStudy?.fps?.toFixed(1) || '--' }} fps
          &nbsp;|&nbsp;
          {{ studyStore.currentStudy?.rows }} × {{ studyStore.currentStudy?.cols }}
        </span>
        <n-divider vertical />
        <n-tag
          v-for="pt in analysisStore.placedPoints"
          :key="pt.id"
          :color="{ color: pt.color, textColor: '#fff' }"
          size="small"
          round
        >
          {{ pt.label }}
        </n-tag>
        <n-tag
          v-if="analysisStore.placedPoints.length === 0"
          type="default"
          size="small"
          round
        >
          请点击图像放置 AIF 和 ROI
        </n-tag>
        <n-divider vertical />
        <span style="font-size: 12px; color: var(--n-text-color-3); white-space: nowrap">
          {{ radiusLabel }} 半径
        </span>
        <n-slider
          v-model:value="currentRadius"
          :min="1"
          :max="20"
          :step="0.5"
          :format-tooltip="(v: number) => `${radiusLabel} ${v.toFixed(1)}px`"
          style="width: 140px"
        />
      </n-space>
      <n-space>
        <n-button
          v-if="analysisStore.placedPoints.length > 0"
          @click="analysisStore.clearPoints()"
          size="small"
          quaternary
        >
          清除选点
        </n-button>
        <n-button
          type="primary"
          :disabled="!analysisStore.canAnalyze"
          :loading="analysisStore.isAnalyzing"
          @click="runAnalysis"
          size="large"
        >
          {{ analysisStore.isAnalyzing ? '分析中...' : '开始分析' }}
        </n-button>
      </n-space>
    </div>

    <!-- 主工作区 -->
    <div class="workspace">
      <div class="left-panel">
        <DsaViewer
          :image-url="studyStore.frameUrl"
          :image-width="studyStore.currentStudy?.cols ?? 512"
          :image-height="studyStore.currentStudy?.rows ?? 512"
        />
        <FrameNavigator
          :model-value="studyStore.currentFrameIndex"
          :frame-count="studyStore.frameCount"
          @update:model-value="(v: number) => studyStore.goToFrame(v)"
        />
      </div>

      <div class="right-panel">
        <n-tabs v-model:value="activeTab" type="segment" animated>
          <n-tab-pane name="tic" tab="TIC 曲线">
            <TicChart
              :times="analysisStore.results?.times ?? studyStore.currentStudy?.times ?? []"
              :tic-curves="analysisStore.results?.tic_curves ?? {}"
              :points="analysisStore.placedPoints"
            />
          </n-tab-pane>
          <n-tab-pane name="residue" tab="Residue Function">
            <ResidueChart
              :times="analysisStore.results?.times ?? []"
              :residue-functions="analysisStore.results?.residue_functions ?? {}"
              :points="analysisStore.placedPoints"
            />
          </n-tab-pane>
          <n-tab-pane name="table" tab="参数表">
            <ResultTable :results="analysisStore.results" />
          </n-tab-pane>
        </n-tabs>
      </div>
    </div>
  </div>

  <div v-else class="analysis-loading">
    <n-spin v-if="studyLoading" size="large" />
    <p v-if="studyLoading" class="loading-text">正在加载...</p>
    <n-result
      v-if="studyError"
      status="error"
      title="无法加载"
      :description="studyError"
    >
      <template #footer>
        <n-button @click="goHome">返回上传页面</n-button>
      </template>
    </n-result>
  </div>
</template>

<style scoped>
.analysis-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--n-color-body);
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background: var(--n-color-card);
  border-bottom: 1px solid var(--n-border-color);
  flex-shrink: 0;
  flex-wrap: wrap;
  gap: 8px;
}

.toolbar-info {
  font-size: 13px;
  color: var(--n-text-color-3);
  white-space: nowrap;
}

.workspace {
  display: flex;
  flex: 1;
  gap: 12px;
  padding: 12px;
  overflow: hidden;
}

.left-panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
  min-width: 0;
}

.left-panel :deep(.dsa-viewer) {
  flex: 1;
}

.right-panel {
  width: 420px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: var(--n-color-card);
  border-radius: 8px;
  overflow: hidden;
}

.right-panel :deep(.n-tabs) {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.right-panel :deep(.n-tabs .n-tab-pane) {
  flex: 1;
  overflow: auto;
  padding: 12px;
}

.right-panel :deep(.n-tabs__content) {
  flex: 1;
  overflow: hidden;
}

.analysis-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100vh;
}

.loading-text {
  margin-top: 16px;
  color: var(--n-text-color-3);
  font-size: 15px;
}
</style>
