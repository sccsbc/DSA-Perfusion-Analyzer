<script setup lang="ts">
import { ref } from 'vue'
import { useAnalysisStore } from '@/stores/analysisStore'

const props = defineProps<{
  imageUrl: string | null
  imageWidth: number
  imageHeight: number
}>()

const analysisStore = useAnalysisStore()
const imgRef = ref<HTMLImageElement | null>(null)
const hoverX = ref(-1)
const hoverY = ref(-1)
const isHovering = ref(false)

/** 将像素坐标映射为相对于图片显示尺寸的百分比 */
function pxToPctX(px: number) {
  return (px / props.imageWidth) * 100
}
function pxToPctY(py: number) {
  return (py / props.imageHeight) * 100
}
function radiusToPctX(r: number) {
  return (r / props.imageWidth) * 100
}
function radiusToPctY(r: number) {
  return (r / props.imageHeight) * 100
}

function mouseToPixel(event: MouseEvent) {
  if (!imgRef.value) return null
  const rect = imgRef.value.getBoundingClientRect()
  const x = Math.round((event.clientX - rect.left) * (props.imageWidth / rect.width))
  const y = Math.round((event.clientY - rect.top) * (props.imageHeight / rect.height))
  if (x < 0 || x >= props.imageWidth || y < 0 || y >= props.imageHeight) return null
  return { x, y }
}

function onMouseMove(event: MouseEvent) {
  const pos = mouseToPixel(event)
  if (pos && analysisStore.nextPointConfig) {
    hoverX.value = pos.x
    hoverY.value = pos.y
    isHovering.value = true
  } else {
    isHovering.value = false
  }
}

function onMouseLeave() {
  isHovering.value = false
}

function onImageClick(event: MouseEvent) {
  if (!imgRef.value || !props.imageUrl) return
  if (analysisStore.placedPoints.length >= 4) return
  const pos = mouseToPixel(event)
  if (!pos) return
  analysisStore.addPoint(pos.x, pos.y)
}

/** 悬停预览圆的样式（所有数字均为百分比） */
function previewCircle() {
  if (!isHovering.value || !analysisStore.nextPointConfig) return null
  const config = analysisStore.nextPointConfig
  const isAif = config.id === 'aif'
  const r = isAif ? analysisStore.aifRadius : analysisStore.roiRadius
  return {
    cx: pxToPctX(hoverX.value),
    cy: pxToPctY(hoverY.value),
    rx: radiusToPctX(r),
    ry: radiusToPctY(r),
    color: config.color,
    label: config.label,
  }
}

function placedCircle(pt: { x: number; y: number; radius: number }) {
  return {
    cx: pxToPctX(pt.x),
    cy: pxToPctY(pt.y),
    rx: radiusToPctX(pt.radius),
    ry: radiusToPctY(pt.radius),
  }
}
</script>

<template>
  <div class="dsa-viewer">
    <n-empty
      v-if="!imageUrl"
      description="请先上传 DICOM 文件"
      class="viewer-placeholder"
    />
    <template v-else>
      <!-- 图片和 SVG 覆盖层对齐的容器 -->
      <div
        class="image-wrapper"
        @mousemove="onMouseMove"
        @mouseleave="onMouseLeave"
        @click="onImageClick"
      >
        <img
          ref="imgRef"
          :src="imageUrl"
          class="dsa-image"
          alt="DSA Frame"
          draggable="false"
        />

        <!-- SVG 覆盖层与图片完全对齐 -->
        <svg
          v-if="analysisStore.placedPoints.length > 0 || previewCircle()"
          class="point-overlay"
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
        >
          <!-- 已放置的选点：用实际半径画圆 -->
          <g v-for="pt in analysisStore.placedPoints" :key="pt.id">
            <ellipse
              :cx="placedCircle(pt).cx"
              :cy="placedCircle(pt).cy"
              :rx="placedCircle(pt).rx"
              :ry="placedCircle(pt).ry"
              :fill="pt.color"
              opacity="0.15"
            />
            <ellipse
              :cx="placedCircle(pt).cx"
              :cy="placedCircle(pt).cy"
              :rx="placedCircle(pt).rx"
              :ry="placedCircle(pt).ry"
              fill="none"
              :stroke="pt.color"
              stroke-width="0.3"
              opacity="0.8"
            />
            <!-- 中心十字 -->
            <line
              :x1="placedCircle(pt).cx - 2" :y1="placedCircle(pt).cy"
              :x2="placedCircle(pt).cx + 2" :y2="placedCircle(pt).cy"
              :stroke="pt.color" stroke-width="0.15"
            />
            <line
              :x1="placedCircle(pt).cx" :y1="placedCircle(pt).cy - 2"
              :x2="placedCircle(pt).cx" :y2="placedCircle(pt).cy + 2"
              :stroke="pt.color" stroke-width="0.15"
            />
            <text
              :x="placedCircle(pt).cx" :y="placedCircle(pt).cy - placedCircle(pt).ry - 1"
              text-anchor="middle" :fill="pt.color"
              font-size="3.5" font-weight="bold" class="point-label"
            >{{ pt.label }} ({{ pt.radius }}px)</text>
          </g>

          <!-- 悬停预览 -->
          <g v-if="previewCircle()">
            <ellipse
              :cx="previewCircle()!.cx"
              :cy="previewCircle()!.cy"
              :rx="previewCircle()!.rx"
              :ry="previewCircle()!.ry"
              :fill="previewCircle()!.color"
              opacity="0.2"
            />
            <ellipse
              :cx="previewCircle()!.cx"
              :cy="previewCircle()!.cy"
              :rx="previewCircle()!.rx"
              :ry="previewCircle()!.ry"
              fill="none"
              :stroke="previewCircle()!.color"
              stroke-width="0.2"
              stroke-dasharray="1"
              opacity="0.7"
            />
          </g>
        </svg>
      </div>

      <!-- 底部提示 -->
      <div v-if="analysisStore.nextPointConfig" class="placement-hint">
        放置
        <span :style="{ color: analysisStore.nextPointConfig.color, fontWeight: 'bold' }">
          {{ analysisStore.nextPointConfig.label }}
        </span>
        半径
        <strong>{{ analysisStore.nextPointConfig.id === 'aif' ? analysisStore.aifRadius : analysisStore.roiRadius }}px</strong>
        （{{ analysisStore.placedPoints.length + 1 }}/4）
      </div>
      <div v-else class="placement-hint placement-full">
        已放置全部 4 个点
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
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
  min-height: 400px;
}

.viewer-placeholder {
  position: absolute;
}

.image-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  width: 100%;
  overflow: hidden;
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

.point-label {
  paint-order: stroke;
  stroke: rgba(0, 0, 0, 0.8);
  stroke-width: 1px;
}

.placement-hint {
  padding: 6px 16px;
  background: rgba(0, 0, 0, 0.8);
  color: #fff;
  font-size: 13px;
  flex-shrink: 0;
}

.placement-full {
  color: rgba(255, 255, 255, 0.5);
}
</style>
