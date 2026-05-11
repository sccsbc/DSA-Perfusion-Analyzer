<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  modelValue: number
  frameCount: number
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', v: number): void
}>()

function onSliderChange(v: number) {
  emit('update:modelValue', v)
}

const sliderMarks = computed(() => {
  if (props.frameCount <= 10) return undefined
  const marks: Record<number, string> = {}
  const step = Math.max(1, Math.floor(props.frameCount / 5))
  for (let i = 0; i < props.frameCount; i += step) {
    marks[i] = `${i + 1}`
  }
  return marks
})
</script>

<template>
  <div class="frame-navigator">
    <n-button
      :disabled="modelValue <= 0"
      @click="emit('update:modelValue', modelValue - 1)"
      size="small"
      secondary
    >
      ◀ 上一帧
    </n-button>

    <n-slider
      :value="modelValue"
      :min="0"
      :max="Math.max(0, frameCount - 1)"
      :step="1"
      :marks="sliderMarks"
      class="frame-slider"
      @update:value="onSliderChange"
    />

    <n-button
      :disabled="modelValue >= frameCount - 1"
      @click="emit('update:modelValue', modelValue + 1)"
      size="small"
      secondary
    >
      下一帧 ▶
    </n-button>

    <span class="frame-label">帧 {{ modelValue + 1 }} / {{ frameCount }}</span>
  </div>
</template>

<style scoped>
.frame-navigator {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 16px;
  background: var(--n-color-modal);
  border-radius: 8px;
}
.frame-slider {
  flex: 1;
  min-width: 150px;
}
.frame-label {
  font-size: 13px;
  color: var(--n-text-color-3);
  white-space: nowrap;
  min-width: 80px;
  text-align: center;
}
</style>
