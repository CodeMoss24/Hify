import { get, post, put, del } from '@/api'
import type { PageResult, PageParams } from '@/types/api'
import type { ModelProvider, ConnectionTestResult } from '@/types/model'

export function getProviderList(params: PageParams): Promise<PageResult<ModelProvider>> {
  return get('/v1/providers', params)
}

export function createProvider(data: Partial<ModelProvider>): Promise<ModelProvider> {
  return post('/v1/providers', data)
}

export function updateProvider(id: number, data: Partial<ModelProvider>): Promise<ModelProvider> {
  return put(`/v1/providers/${id}`, data)
}

export function deleteProvider(id: number): Promise<void> {
  return del(`/v1/providers/${id}`)
}

export function testConnection(id: number): Promise<ConnectionTestResult> {
  return post(`/v1/providers/${id}/test-connection`)
}
