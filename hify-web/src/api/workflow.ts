import { get, post, del } from '@/api'
import type { PageResult, PageParams } from '@/types/api'
import type { Workflow } from '@/types/model'

export function getWorkflowList(params: PageParams): Promise<PageResult<Workflow>> {
  return get('/v1/workflows', params)
}

export function createWorkflow(data: Partial<Workflow>): Promise<Workflow> {
  return post('/v1/workflows', data)
}

export function deleteWorkflow(id: number): Promise<void> {
  return del(`/v1/workflows/${id}`)
}
