import { get, post, put, del } from '@/api'
import type { PageResult, PageParams } from '@/types/api'
import type { McpServer, McpServerDetail, McpConnectionTestResult, McpDebugResult } from '@/types/model'

export function getMcpServerList(params: PageParams): Promise<PageResult<McpServer>> {
  return get('/v1/mcp-servers', params)
}

export function getMcpServer(id: number): Promise<McpServerDetail> {
  return get(`/v1/mcp-servers/${id}`)
}

export function createMcpServer(data: Partial<McpServer>): Promise<McpServer> {
  return post('/v1/mcp-servers', data)
}

export function updateMcpServer(id: number, data: Partial<McpServer>): Promise<McpServer> {
  return put(`/v1/mcp-servers/${id}`, data)
}

export function deleteMcpServer(id: number): Promise<void> {
  return del(`/v1/mcp-servers/${id}`)
}

export function testMcpConnection(id: number): Promise<McpConnectionTestResult> {
  return post(`/v1/mcp-servers/${id}/test-connection`)
}

export function debugMcpTool(id: number, tool_name: string, arguments_: Record<string, any>): Promise<McpDebugResult> {
  return post(`/v1/mcp-servers/${id}/debug`, { tool_name, arguments: arguments_ })
}
