export interface ModelProvider {
  id: number
  name: string
  provider_type: string
  base_url: string
  api_key?: string
  created_at: string
  updated_at: string
}

export interface Model {
  id: number
  provider_id: number
  name: string
  model_id: string
  created_at: string
  updated_at: string
}

export interface Agent {
  id: number
  name: string
  model_id: number
  system_prompt?: string
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
