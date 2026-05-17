export interface ProviderHealth {
  status: 'healthy' | 'unhealthy' | 'unknown'
  last_check_at: number
  response_time_ms: number
  consecutive_failures: number
  last_error: string
}

export interface ModelProvider {
  id: number
  name: string
  provider_type: string
  base_url: string
  api_key?: string
  extra_config?: Record<string, any> | null
  status: string
  health?: ProviderHealth | null
  created_at: string
  updated_at: string
}

export interface ConnectionTestResult {
  success: boolean
  latency_ms: number
  model_count: number
  error_message: string
}

export interface Model {
  id: number
  provider_id: number
  name: string
  model_id: string
  status: string
  capabilities: string
  created_at: string
  updated_at: string
}

export interface KnowledgeBaseItem {
  id: number
  name: string
}

export interface ToolItem {
  id: number
  name: string
}

export interface Agent {
  id: number
  name: string
  description: string
  model_id: number
  system_prompt: string
  temperature: number
  max_tokens: number
  max_context_turns: number
  enabled: number
  knowledge_bases: KnowledgeBaseItem[]
  tools: ToolItem[]
  created_at: string
  updated_at: string
}

export interface Conversation {
  id: number
  agent_id: number
  title: string
  created_at: string
  updated_at: string
}

export interface Message {
  id: number
  conversation_id: number
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export interface KnowledgeBase {
  id: number
  name: string
  description?: string
  created_at: string
  updated_at: string
}

export interface Document {
  id: number
  knowledge_base_id: number
  name: string
  size: number
  status: string
  created_at: string
  updated_at: string
}

export interface McpServer {
  id: number
  name: string
  url: string
  created_at: string
  updated_at: string
}

export interface Workflow {
  id: number
  name: string
  config: any
  created_at: string
  updated_at: string
}
