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
  residueFunctions: Record<string, number[]>
  points: PlacedPoint[]
}>()

const option = computed(() => {
  const colorMap: Record<string, string> = {}
  for (const p of props.points) {
    if (p.id !== 'aif') colorMap[p.id] = p.color
  }

  return {
    tooltip: {
      trigger: 'axis' as const,
      formatter: (params: unknown) => {
        const arr = Array.isArray(params) ? params : [params]
        return (arr as Array<{ seriesName: string; value: [number, number] }>)
          .map((p) => `${p.seriesName}: ${p.value[1]?.toFixed(4)}`)
          .join('<br/>')
      },
    },
    legend: {
      data: Object.keys(props.residueFunctions).map((k) => k.toUpperCase()),
      top: 8,
      textStyle: { fontSize: 12 },
    },
    grid: { top: 48, right: 24, bottom: 40, left: 64 },
    xAxis: {
      type: 'value' as const,
      name: '时间 (s)',
      nameLocation: 'center' as const,
      nameGap: 28,
      min: 0,
    },
    yAxis: {
      type: 'value' as const,
      name: 'Flow-scaled Residue k(t)',
    },
    series: Object.entries(props.residueFunctions).map(([key, values]) => ({
      name: key.toUpperCase(),
      type: 'line' as const,
      data: props.times.map((t, i) => [t, values[i]]),
      smooth: true,
      symbol: 'none' as const,
      lineStyle: { color: colorMap[key] || '#999', width: 2 },
      itemStyle: { color: colorMap[key] || '#999' },
      markPoint: {
        data: [
          {
            type: 'max' as const,
            name: '峰值',
            symbolSize: 8,
            itemStyle: { color: colorMap[key] || '#999' },
          },
        ],
        label: { fontSize: 10, formatter: '{c}' },
      },
    })),
  }
})
</script>

<template>
  <div class="residue-chart">
    <VChart v-if="props.times.length > 0 && Object.keys(props.residueFunctions).length > 0" :option="option" autoresize />
    <n-empty v-else description="暂无 Residue Function 数据，请先运行分析" />
  </div>
</template>

<style scoped>
.residue-chart {
  width: 100%;
  height: 100%;
  min-height: 300px;
}
</style>
