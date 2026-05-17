import { get, post, put, del } from '@/api'
import type { PageResult, PageParams } from '@/types/api'
import type { Agent } from '@/types/model'

export function getAgentList(params: PageParams): Promise<PageResult<Agent>> {
  return get('/v1/agents', params)
}

export function getAgent(id: number): Promise<Agent> {
  return get(`/v1/agents/${id}`)
}

export function createAgent(data: Partial<Agent>): Promise<Agent> {
  return post('/v1/agents', data)
}

export function updateAgent(id: number, data: Partial<Agent>): Promise<Agent> {
  return put(`/v1/agents/${id}`, data)
}

export function deleteAgent(id: number): Promise<void> {
  return del(`/v1/agents/${id}`)
}

export function bindKnowledgeBase(agentId: number, kbId: number): Promise<void> {
  return post(`/v1/agents/${agentId}/knowledge-bases`, { knowledge_base_id: kbId })
}

export function unbindKnowledgeBase(agentId: number, kbId: number): Promise<void> {
  return del(`/v1/agents/${agentId}/knowledge-bases/${kbId}`)
}

export function bindTool(agentId: number, toolId: number): Promise<void> {
  return post(`/v1/agents/${agentId}/tools`, { mcp_tool_id: toolId })
}

export function unbindTool(agentId: number, toolId: number): Promise<void> {
  return del(`/v1/agents/${agentId}/tools/${toolId}`)
}
