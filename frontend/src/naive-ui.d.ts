/** Naive UI 全局组件类型声明 */
import type { MessageApiInjection } from 'naive-ui'

declare global {
  interface Window {
    $message?: MessageApiInjection
  }
}

export {}
