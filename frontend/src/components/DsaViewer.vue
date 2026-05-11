<script setup lang="ts">
import { ref, computed, reactive, onMounted, nextTick } from 'vue'
import { useResizeObserver } from '@vueuse/core'
import { useAnalysisStore } from '@/stores/analysisStore'

const props = defineProps<{
  imageUrl: string | null
  imageWidth: number
  imageHeight: number
}>()

const analysisStore = useAnalysisStore()
const imgRef = ref<HTMLImageElement | null>(null)

/** 图片实际渲染尺寸（受 CSS 约束后） */
const displaySize = reactive({ width: 0, height: 0 })

function updateDisplaySize() {
  if (!imgRef.value) return
  displaySize.width = imgRef.value.clientWidth
  displaySize.height = imgRef.value.clientHeight
}

/** 点击事件：将页面坐标转换为图像像素坐标后添加选点 */
function onImageClick(event: MouseEvent) {
  if (!imgRef.value || !props.imageUrl) return

  const rect = imgRef.value.getBoundingClientRect()
  const scaleX = props.imageWidth / rect.width
  const scaleY = props.imageHeight / rect.height
  const px = Math.round((event.clientX - rect.left) * scaleX)
  const py = Math.round((event.clientY - rect.top) * scaleY)

  if (px < 0 || px >= props.imageWidth || py < 0 || py >= props.imageHeight) return

  if (analysisStore.placedPoints.length >= 4) {
    return  // 已满 4 个点，不响应点击
  }

  analysisStore.addPoint(px, py)
}

/** SVG overlay 中的圆坐标：像素坐标 -> 百分比 */
function toOverlayX(px: number) {
  if (displaySize.width === 0) return 0
  return (px / props.imageWidth) * 100
}

function toOverlayY(py: number) {
  if (displaySize.height === 0) return 0
  return (py / props.imageHeight) * 100
}

const showOverlay = computed(() => analysisStore.placedPoints.length > 0)

useResizeObserver(imgRef, updateDisplaySize)
onMounted(() => {
  nextTick(updateDisplaySize)
})
</script>

<template>
  <div class="dsa-viewer" @click="onImageClick">
    <n-empty
      v-if="!imageUrl"
      description="请先上传 DICOM 文件"
      class="viewer-placeholder"
    />

    <template v-else>
      <img
        ref="imgRef"
        :src="imageUrl"
        class="dsa-image"
        alt="DSA Frame"
        @load="updateDisplaySize"
        draggable="false"
      />

      <svg
        v-if="showOverlay"
        class="point-overlay"
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
      >
        <g v-for="pt in analysisStore.placedPoints" :key="pt.id">
          <circle
            :cx="toOverlayX(pt.x)"
            :cy="toOverlayY(pt.y)"
            :r="2.5"
            :fill="pt.color"
            :stroke="pt.color"
            stroke-width="0.3"
            opacity="0.35"
          />
          <circle
            :cx="toOverlayX(pt.x)"
            :cy="toOverlayY(pt.y)"
            :r="2.5"
            fill="none"
            :stroke="pt.color"
            stroke-width="0.4"
            opacity="0.9"
            class="circle-border"
          />
          <line
            :x1="toOverlayX(pt.x) - 3" :y1="toOverlayY(pt.y)"
            :x2="toOverlayX(pt.x) + 3" :y2="toOverlayY(pt.y)"
            :stroke="pt.color" stroke-width="0.2" opacity="0.9"
          />
          <line
            :x1="toOverlayX(pt.x)" :y1="toOverlayY(pt.y) - 3"
            :x2="toOverlayX(pt.x)" :y2="toOverlayY(pt.y) + 3"
            :stroke="pt.color" stroke-width="0.2" opacity="0.9"
          />
          <text
            :x="toOverlayX(pt.x)" :y="toOverlayY(pt.y) - 4"
            text-anchor="middle" :fill="pt.color"
            font-size="4" font-weight="bold" class="point-label"
          >{{ pt.label }}</text>
        </g>
      </svg>

      <div v-if="analysisStore.nextPointConfig" class="placement-hint">
        点击图像放置 <span :style="{ color: analysisStore.nextPointConfig.color, fontWeight: 'bold' }">
          {{ analysisStore.nextPointConfig.label }}
        </span>（{{ analysisStore.placedPoints.length + 1 }}/4）
      </div>
      <div v-else class="placement-hint placement-full">
        已放置全部 4 个点，点击已有选点可移除
      </div>
    </template>
  </div>
</template>

<style scoped>
.dsa-viewer {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
  cursor: crosshair;
  min-height: 400px;
}

.viewer-placeholder {
  position: absolute;
}

.dsa-image {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  user-select: none;
  -webkit-user-drag: none;
}

.point-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.circle-border {
  filter: drop-shadow(0 0 1px rgba(0,0,0,0.7));
}

.point-label {
  paint-order: stroke;
  stroke: rgba(0, 0, 0, 0.8);
  stroke-width: 1px;
}

.placement-hint {
  position: absolute;
  bottom: 12px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0, 0, 0, 0.75);
  color: #fff;
  padding: 6px 16px;
  border-radius: 6px;
  font-size: 13px;
  white-space: nowrap;
  pointer-events: none;
}

.placement-full {
  color: rgba(255, 255, 255, 0.6);
}
</style>
