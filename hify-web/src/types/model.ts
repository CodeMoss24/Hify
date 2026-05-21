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
  document_count?: number
  created_at: string
  updated_at: string
}

export interface Document {
  id: number
  knowledge_base_id: number
  name: string
  size: number
  status: string
  error_message: string
  chunk_count: number
  created_at: string
  updated_at: string
}

export interface DocumentChunk {
  id: number
  document_id: number
  content: string
  chunk_index: number
  vector_id: string
  created_at: string
  updated_at: string
}

export interface McpServer {
  id: number
  name: string
  url: string
  enabled: boolean
  created_at: string
  updated_at: string
}

export interface McpTool {
  id: number
  server_id: number
  name: string
  description: string
  input_schema: string
}

export interface McpConnectionTestResult {
  success: boolean
  tool_count: number
  tools: McpTool[]
  error_message: string
}

export interface McpServerDetail {
  server: McpServer
  tools: McpTool[]
}

export interface McpDebugResult {
  result: string
  elapsed_ms: number
}

export interface WorkflowNode {
  node_key: string
  name: string
  node_type: string
  config: Record<string, any>
  position_x: number
  position_y: number
}

export interface WorkflowEdge {
  source_node_key: string
  target_node_key: string
  condition: string
}

export interface Workflow {
  id: number
  name: string
  description: string
  status: string
  nodes: WorkflowNode[]
  edges: WorkflowEdge[]
  config: any
  created_at: string
  updated_at: string
}
