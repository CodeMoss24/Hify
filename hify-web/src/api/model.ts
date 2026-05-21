import { get, post, put, del } from '@/api'
import type { PageResult, PageParams } from '@/types/api'
import type { Model } from '@/types/model'

export function getModelList(providerId: number, params?: PageParams): Promise<PageResult<Model>> {
  return get(`/v1/providers/${providerId}/models`, params)
}

export function getModel(id: number): Promise<Model> {
  return get(`/v1/models/${id}`)
}

export function createModel(data: Partial<Model>): Promise<Model> {
  return post('/v1/models', data)
}

export function updateModel(id: number, data: Partial<Model>): Promise<Model> {
  return put(`/v1/models/${id}`, data)
}

export function deleteModel(id: number): Promise<void> {
  return del(`/v1/models/${id}`)
}
