import { ElMessage } from 'element-plus'

type NotifyType = 'success' | 'error' | 'warning' | 'info'

const defaultDuration = 2000

function notify(type: NotifyType, message: string, duration = defaultDuration) {
  ElMessage({
    type,
    message,
    duration,
    showClose: false,
  })
}

export const notifySuccess = (message: string, duration = defaultDuration) =>
  notify('success', message, duration)

export const notifyError = (message: string, duration = defaultDuration) =>
  notify('error', message, duration)

export const notifyWarning = (message: string, duration = defaultDuration) =>
  notify('warning', message, duration)