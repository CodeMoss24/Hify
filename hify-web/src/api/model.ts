import { get } from '@/api'
import type { PageResult, PageParams } from '@/types/api'
import type { Model } from '@/types/model'

export function getModelList(providerId: number, params?: PageParams): Promise<PageResult<Model>> {
  return get(`/v1/providers/${providerId}/models`, params)
}

export function getModel(id: number): Promise<Model> {
  return get(`/v1/models/${id}`)
}
