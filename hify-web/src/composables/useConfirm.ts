import { ElMessageBox, ElMessage } from 'element-plus'

/**
 * 删除确认 composable
 * 一行代码完成：确认框 → 调接口 → 提示成功
 *
 * @param confirmText 确认框文案（如 "删除后无法恢复，确认删除该 Provider？"）
 * @param apiMethod 需要执行的 async API 方法
 * @param successText 成功提示文字，默认 "删除成功"
 */
export function useConfirm<T = void>(
  confirmText: string,
  apiMethod: () => Promise<T>,
  successText = '删除成功',
) {
  return async () => {
    await ElMessageBox.confirm(confirmText, '确认操作', {
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
      type: 'warning',
      confirmButtonClass: 'el-button--danger',
    })
    await apiMethod()
    ElMessage.success({ message: successText, duration: 2000 })
  }
}