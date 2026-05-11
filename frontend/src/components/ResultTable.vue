<script setup lang="ts">
import { computed } from 'vue'
import type { AnalyzeResponse } from '@/types'
import type { DataTableColumn } from 'naive-ui'

const props = defineProps<{
  results: AnalyzeResponse | null
}>()

interface RowData {
  key: string
  region: string
  ttp: number
  auc: number
  washInSlope: number
  peak: number
  dsaCbf: number | null
  dsaCbv: number | null
  dsaMtt: number | null
  dsaTmax: number | null
}

const columns: DataTableColumn<RowData>[] = [
  { title: '区域', key: 'region', width: 80, fixed: 'left' },
  { title: 'TTP (s)', key: 'ttp', render: (_row: RowData) => _row.ttp.toFixed(2) },
  { title: 'AUC', key: 'auc', render: (_row: RowData) => _row.auc.toFixed(1) },
  { title: 'Wash-in Slope', key: 'washInSlope', render: (_row: RowData) => _row.washInSlope.toFixed(2) },
  { title: 'DSA-CBF', key: 'dsaCbf', render: (_row: RowData) => _row.dsaCbf != null ? _row.dsaCbf.toFixed(4) : '--' },
  { title: 'DSA-CBV', key: 'dsaCbv', render: (_row: RowData) => _row.dsaCbv != null ? _row.dsaCbv.toFixed(4) : '--' },
  { title: 'DSA-MTT (s)', key: 'dsaMtt', render: (_row: RowData) => _row.dsaMtt != null ? _row.dsaMtt.toFixed(2) : '--' },
  { title: 'DSA-Tmax (s)', key: 'dsaTmax', render: (_row: RowData) => _row.dsaTmax != null ? _row.dsaTmax.toFixed(2) : '--' },
]

const rows = computed<RowData[]>(() => {
  if (!props.results) return []
  const data: RowData[] = []
  for (const [key, region] of Object.entries(props.results.regions)) {
    const tic = region.tic_parameters
    const dec = region.deconvolution_parameters
    data.push({
      key,
      region: key.toUpperCase(),
      ttp: tic.ttp,
      auc: tic.auc,
      washInSlope: tic.wash_in_slope,
      peak: tic.peak,
      dsaCbf: dec?.dsa_cbf ?? null,
      dsaCbv: dec?.dsa_cbv ?? null,
      dsaMtt: dec?.dsa_mtt ?? null,
      dsaTmax: dec?.dsa_tmax ?? null,
    })
  }
  return data
})
</script>

<template>
  <div class="result-table">
    <n-data-table
      v-if="rows.length > 0"
      :columns="columns"
      :data="rows"
      :bordered="true"
      :single-line="false"
      size="small"
      :row-class-name="(row: RowData) => row.key === 'aif' ? 'aif-row' : ''"
    />
    <n-empty v-else description="暂无分析结果，请先放置 AIF/ROI 选点并点击分析" />
  </div>
</template>

<style scoped>
.result-table {
  width: 100%;
  height: 100%;
  overflow: auto;
}
:deep(.aif-row) {
  background: rgba(255, 0, 0, 0.05);
}
</style>
