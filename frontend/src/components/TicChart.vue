<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { PlacedPoint } from '@/types'

use([LineChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const props = defineProps<{
  times: number[]
  ticCurves: Record<string, number[]>
  points: PlacedPoint[]
}>()

const option = computed(() => {
  const colorMap: Record<string, string> = {}
  for (const p of props.points) {
    colorMap[p.id] = p.color
  }

  return {
    tooltip: {
      trigger: 'axis' as const,
      formatter: (params: unknown) => {
        const arr = Array.isArray(params) ? params : [params]
        return (arr as Array<{ seriesName: string; value: [number, number] }>)
          .map((p) => `${p.seriesName}: ${p.value[1]?.toFixed(2)}`)
          .join('<br/>')
      },
    },
    legend: {
      data: Object.keys(props.ticCurves).map((k) => k.toUpperCase()),
      top: 8,
      textStyle: { fontSize: 12 },
    },
    grid: { top: 48, right: 24, bottom: 40, left: 56 },
    xAxis: {
      type: 'value' as const,
      name: '时间 (s)',
      nameLocation: 'center' as const,
      nameGap: 28,
      min: 0,
    },
    yAxis: {
      type: 'value' as const,
      name: '像素强度',
    },
    series: Object.entries(props.ticCurves).map(([key, values]) => ({
      name: key.toUpperCase(),
      type: 'line' as const,
      data: props.times.map((t, i) => [t, values[i]]),
      smooth: true,
      symbol: 'none' as const,
      lineStyle: { color: colorMap[key] || '#999', width: 2 },
      itemStyle: { color: colorMap[key] || '#999' },
    })),
  }
})
</script>

<template>
  <div class="tic-chart">
    <VChart v-if="props.times.length > 0" :option="option" autoresize />
    <n-empty v-else description="暂无 TIC 数据" />
  </div>
</template>

<style scoped>
.tic-chart {
  width: 100%;
  height: 100%;
  min-height: 300px;
}
</style>
