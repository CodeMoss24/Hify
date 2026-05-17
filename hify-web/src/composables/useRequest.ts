import { ref } from 'vue'
import type { PageResult, PageParams } from '@/types/api'

export interface TableColumn<T = any> {
  label: string
  prop?: keyof T | string
  width?: string | number
  slot?: string
}

interface UseRequestOptions<T, P extends PageParams = PageParams> {
  api: (params: P) => Promise<PageResult<T>>
  defaultParams?: P
}

export function useRequest<T, P extends PageParams = PageParams>(
  options: UseRequestOptions<T, P>,
) {
  const { api, defaultParams } = options

  const data = ref<T[]>([])
  const loading = ref(false)
  const error = ref<Error | null>(null)

  const execute = async (params?: P) => {
    loading.value = true
    error.value = null
    try {
      const res = await api((params ?? defaultParams) as P)
      data.value = res.list
      return res
    } catch (e) {
      error.value = e instanceof Error ? e : new Error(String(e))
      throw e
    } finally {
      loading.value = false
    }
  }

  return { data, loading, error, execute }
}