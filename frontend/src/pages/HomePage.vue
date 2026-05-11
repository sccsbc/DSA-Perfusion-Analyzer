<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { uploadDicom } from '@/api/dsaApi'
import { useStudyStore } from '@/stores/studyStore'

const router = useRouter()
const studyStore = useStudyStore()

const isUploading = ref(false)
const errorMsg = ref<string | null>(null)

async function handleUpload(options: { file: { file?: File; name?: string }; fileList: Array<{ file?: File }> }) {
  // Naive UI UploadFileInfo: file 是原生 File 对象，在 file.file 中
  const nativeFile = options.file?.file
  if (!nativeFile) return

  isUploading.value = true
  errorMsg.value = null

  try {
    const study = await uploadDicom(nativeFile)
    studyStore.setStudy(study)
    router.push(`/analysis/${study.study_id}`)
  } catch (err: unknown) {
    const detail = (err as { response?: { data?: { detail?: string } }; message?: string })?.response?.data?.detail
      || (err as Error).message
      || '上传失败，请重试'
    errorMsg.value = detail
  } finally {
    isUploading.value = false
  }
}

function handleRetry() {
  errorMsg.value = null
}
</script>

<template>
  <div class="home-page">
    <n-card class="upload-card" :bordered="true">
      <template #header>
        <div class="card-header">
          <n-icon size="28" color="#1890ff">
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>
            </svg>
          </n-icon>
          <div>
            <h2 class="card-title">DSA 灌注分析</h2>
            <p class="card-subtitle">数字减影血管造影灌注参数计算工具</p>
          </div>
        </div>
      </template>

      <!-- n-upload-dragger 必须包裹在 n-upload 内，不能独立使用 -->
      <n-upload
        accept=".dcm"
        :max="1"
        :disabled="isUploading"
        :default-upload="false"
        @change="handleUpload"
      >
        <n-upload-dragger>
          <div class="upload-content">
            <n-icon size="48" color="#999">
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM14 13v4h-4v-4H7l5-5 5 5h-3z"/>
              </svg>
            </n-icon>
            <p class="upload-text">点击或拖拽 DICOM 文件到此区域上传</p>
            <p class="upload-hint">支持 .dcm 单文件多帧 DICOM</p>
          </div>
        </n-upload-dragger>
      </n-upload>

      <div v-if="isUploading" class="status-overlay">
        <n-spin size="medium" />
        <p class="status-text">正在解析 DICOM 文件...</p>
      </div>

      <n-alert
        v-if="errorMsg"
        type="error"
        :bordered="false"
        class="error-alert"
      >
        <template #header>
          上传失败
        </template>
        {{ errorMsg }}
        <template #footer>
          <n-button size="small" @click="handleRetry">重试</n-button>
        </template>
      </n-alert>
    </n-card>
  </div>
</template>

<style scoped>
.home-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  padding: 24px;
}

.upload-card {
  width: 100%;
  max-width: 520px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 16px;
}

.card-title {
  margin: 0;
  font-size: 22px;
  font-weight: 600;
}

.card-subtitle {
  margin: 2px 0 0;
  font-size: 13px;
  color: var(--n-text-color-3);
}

.upload-content {
  padding: 32px 16px;
  text-align: center;
}

.upload-text {
  margin: 12px 0 4px;
  font-size: 15px;
  color: var(--n-text-color-2);
}

.upload-hint {
  margin: 0;
  font-size: 12px;
  color: var(--n-text-color-3);
}

.status-overlay {
  text-align: center;
  padding: 24px;
}

.status-text {
  margin-top: 12px;
  color: var(--n-text-color-3);
  font-size: 14px;
}

.error-alert {
  margin-top: 16px;
}
</style>
