export const WorkflowNodeType = {
  START: 'START',
  END: 'END',
  LLM: 'LLM',
  CONDITION: 'CONDITION',
  API_CALL: 'API_CALL',
} as const

export type WorkflowNodeType = (typeof WorkflowNodeType)[keyof typeof WorkflowNodeType]

export interface WorkflowFormNode {
  uid: string
  node_key: string
  name: string
  node_type: WorkflowNodeType
  model_config_id?: number
  prompt?: string
  expression?: string
  config: Record<string, any>
}

export interface WorkflowFormEdge {
  source_node_key: string
  target_node_key: string
  condition: string
}

export interface WorkflowFormData {
  name: string
  description: string
  nodes: WorkflowFormNode[]
  edges: WorkflowFormEdge[]
}
