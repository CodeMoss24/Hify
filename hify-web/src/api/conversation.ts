import { get, post } from '@/api'
import type { PageResult, PageParams } from '@/types/api'

export interface Conversation {
  id: number
  agent_id: number
  title: string
  status: string
  updatedAt: string
  createdAt: string
  lastMessage?: string
  last_message?: string
}

export interface Message {
  id: number
  conversationId: number
  role: 'user' | 'assistant'
  content: string
  finishReason: string
  latencyMs: number
  createdAt: string
}

export interface SendMessageRequest {
  content: string
  stream?: boolean
}

export interface SSEDeltaEvent {
  type: 'delta'
  content: string
}

export interface SSEDoneEvent {
  type: 'done'
  finishReason: string
  latencyMs: number
  conversationId?: number
}

export interface SSEErrorEvent {
  type: 'error'
  content: string
}

export type SSEEvent = SSEDeltaEvent | SSEDoneEvent | SSEErrorEvent

export function getConversationList(params?: PageParams): Promise<PageResult<Conversation>> {
  return get('/v1/conversations', params)
}

export function createConversation(agentId?: number): Promise<Conversation> {
  return post('/v1/conversations', { agent_id: agentId || 1 }) // 默认 agent_id=1
}

export async function getConversationMessages(id: number): Promise<Message[]> {
  const res = await get<PageResult<Message>>(`/v1/conversations/${id}/messages`, { page: 1, page_size: 100 })
  // 后端返回 PageResult，取出 list 字段并转换字段名（snake_case -> camelCase）
  if (res && res.list) {
    return res.list.map((item: any) => ({
      id: item.id,
      conversationId: item.conversation_id,
      role: item.role,
      content: item.content,
      finishReason: item.finish_reason,
      latencyMs: item.latency_ms,
      createdAt: item.created_at,
    }))
  }
  return []
}

export async function sendMessageStream(
  id: number,
  data: SendMessageRequest,
  onEvent: (event: SSEEvent) => void,
  onError: (error: Error) => void
): Promise<void> {
  try {
    const response = await fetch(`/api/v1/conversations/${id}/messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    })

    if (!response.ok) {
      throw new Error(`请求失败: ${response.status}`)
    }

    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('无法读取响应流')
    }

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        const trimmedLine = line.trim()
        if (!trimmedLine || !trimmedLine.startsWith('data: ')) continue

        const dataStr = trimmedLine.slice(6).trim()
        if (!dataStr || dataStr === '[DONE]') continue

        try {
          const event = JSON.parse(dataStr) as SSEEvent
          onEvent(event)
        } catch (e) {
          console.warn('解析SSE事件失败:', dataStr, e)
        }
      }
    }
  } catch (error) {
    onError(error instanceof Error ? error : new Error(String(error)))
  }
}
