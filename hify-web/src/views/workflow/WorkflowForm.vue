<template>
  <div class="workflow-form-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>{{ isEdit ? '编辑工作流' : '新建工作流' }}</h2>
      <p class="page-desc">通过表单配置工作流的节点与连线，无需编写 JSON</p>
    </div>

    <div class="form-card">
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="80px"
        @submit.prevent="handleSubmit"
      >
        <!-- 基本信息 -->
        <el-form-item label="名称" prop="name">
          <el-input
            v-model="formData.name"
            placeholder="请输入工作流名称"
            maxlength="64"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="描述" prop="description">
          <el-input
            v-model="formData.description"
            type="textarea"
            :rows="2"
            placeholder="请输入描述（可选）"
            maxlength="256"
            show-word-limit
          />
        </el-form-item>

        <!-- 节点列表 -->
        <el-form-item label="节点配置">
          <div class="node-list">
            <div
              v-for="(node, index) in formData.nodes"
              :key="node.uid"
              class="node-card"
            >
              <div class="node-header">
                <span class="node-index">节点 {{ index + 1 }}</span>
                <div class="node-header-right">
                  <el-tag
                    :type="nodeTypeTagType(node.node_type)"
                    size="small"
                  >
                    {{ nodeTypeLabel(node.node_type) }}
                  </el-tag>
                  <el-button
                    v-if="node.node_type !== WorkflowNodeType.START && node.node_type !== WorkflowNodeType.END"
                    type="danger"
                    link
                    @click="removeNode(node.uid)"
                  >
                    删除
                  </el-button>
                </div>
              </div>

              <div class="node-body">
                <!-- 节点名称 -->
                <div class="node-field">
                  <label>节点名称</label>
                  <el-input
                    v-model="node.name"
                    :disabled="node.node_type === WorkflowNodeType.START || node.node_type === WorkflowNodeType.END"
                    placeholder="节点名称"
                    maxlength="32"
                  />
                </div>

                <!-- 节点类型 -->
                <div class="node-field">
                  <label>类型</label>
                  <el-select
                    v-model="node.node_type"
                    :disabled="node.node_type === WorkflowNodeType.START || node.node_type === WorkflowNodeType.END"
                    style="width: 100%"
                    @change="(val: WorkflowNodeType) => onNodeTypeChange(node, val)"
                  >
                    <el-option
                      v-for="t in editableNodeTypes"
                      :key="t.value"
                      :label="t.label"
                      :value="t.value"
                    />
                  </el-select>
                </div>

                <!-- LLM 节点配置 -->
                <template v-if="node.node_type === WorkflowNodeType.LLM">
                  <div class="node-field">
                    <label>模型 <span class="required">*</span></label>
                    <el-select
                      v-model="node.model_config_id"
                      placeholder="请选择模型"
                      style="width: 100%"
                    >
                      <el-option-group
                        v-for="g in modelGroups"
                        :key="g.providerName"
                        :label="g.providerName"
                      >
                        <el-option
                          v-for="m in g.models"
                          :key="m.id"
                          :label="`${m.name} (${m.model_id})`"
                          :value="m.id"
                        />
                      </el-option-group>
                    </el-select>
                  </div>
                  <div class="node-field">
                    <label>提示词 <span class="required">*</span></label>
                    <el-input
                      v-model="node.prompt"
                      type="textarea"
                      :rows="4"
                      placeholder="请输入提示词，可使用 {{start.userMessage}} 引用用户消息"
                    />
                  </div>
                </template>

                <!-- CONDITION 节点配置 -->
                <template v-if="node.node_type === WorkflowNodeType.CONDITION">
                  <div class="node-field">
                    <label>表达式 <span class="required">*</span></label>
                    <el-input
                      v-model="node.expression"
                      placeholder="例如：{{start.userMessage}} === 'help'"
                    />
                    <p class="field-hint">
                      表达式结果将用于条件分支路由。可使用 <code v-pre>{{node_key.variable}}</code> 引用上下文变量。
                    </p>
                  </div>
                </template>
              </div>
            </div>
          </div>

          <div class="add-node-area">
            <el-dropdown @command="addNode">
              <el-button type="primary" plain>
                + 添加节点
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item :command="WorkflowNodeType.LLM">LLM 节点</el-dropdown-item>
                  <el-dropdown-item :command="WorkflowNodeType.CONDITION">条件节点</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </el-form-item>

        <!-- 连线预览 -->
        <el-form-item label="连线预览">
          <div class="edge-preview">
            <template v-for="(edge, i) in formData.edges" :key="i">
              <div class="edge-row">
                <span class="edge-source">{{ getNodeLabel(edge.source_node_key) }}</span>
                <span class="edge-arrow">→</span>
                <span class="edge-target">{{ getNodeLabel(edge.target_node_key) }}</span>
                <el-tag
                  v-if="edge.condition"
                  size="small"
                  type="warning"
                  class="edge-condition"
                >
                  {{ edge.condition }}
                </el-tag>
              </div>
            </template>
            <p v-if="formData.edges.length === 0" class="edge-empty">
              连线将根据节点顺序自动生成
            </p>
          </div>
        </el-form-item>

        <!-- 操作按钮 -->
        <el-form-item>
          <div class="form-actions">
            <el-button @click="router.push('/workflows')">取消</el-button>
            <el-button type="primary" :loading="submitting" @click="handleSubmit">
              {{ isEdit ? '保存修改' : '创建工作流' }}
            </el-button>
          </div>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import type { FormInstance, FormRules } from 'element-plus'
import { notifySuccess, notifyError } from '@/utils/notify'
import { getWorkflow, createWorkflow, updateWorkflow } from '@/api/workflow'
import { getProviderList } from '@/api/provider'
import { getModelList } from '@/api/model'
import type { ModelProvider, Model } from '@/types/model'
import { WorkflowNodeType } from '@/types/workflow'
import type { WorkflowFormNode, WorkflowFormEdge } from '@/types/workflow'

const props = defineProps<{
  workflowId?: number
}>()

const router = useRouter()
const route = useRoute()

const isEdit = computed(() => props.workflowId != null || route.params.id != null)
const workflowId = computed(() => props.workflowId ?? (route.params.id ? Number(route.params.id) : undefined))

// ── 表单状态 ──
const formRef = ref<FormInstance>()
const submitting = ref(false)

let uidCounter = 0
function nextUid(): string {
  return `node_${++uidCounter}`
}

function createNode(type: WorkflowNodeType, overrides: Partial<WorkflowFormNode> = {}): WorkflowFormNode {
  const key = type === WorkflowNodeType.START ? 'start'
    : type === WorkflowNodeType.END ? 'end'
    : `node_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`

  const name = type === WorkflowNodeType.START ? '开始'
    : type === WorkflowNodeType.END ? '结束'
    : type === WorkflowNodeType.LLM ? 'LLM 处理'
    : '条件判断'

  return {
    uid: nextUid(),
    node_key: key,
    name,
    node_type: type,
    config: {},
    ...overrides,
  }
}

const formData = reactive({
  name: '',
  description: '',
  nodes: [
    createNode(WorkflowNodeType.START),
    createNode(WorkflowNodeType.END),
  ] as WorkflowFormNode[],
  edges: [] as WorkflowFormEdge[],
})

const formRules: FormRules = {
  name: [
    { required: true, message: '请输入工作流名称', trigger: 'blur' },
  ],
}

// ── 可编辑的节点类型 ──
const editableNodeTypes = [
  { label: 'LLM 节点', value: WorkflowNodeType.LLM },
  { label: '条件节点', value: WorkflowNodeType.CONDITION },
]

// ── 模型加载 ──
interface ModelGroup {
  providerName: string
  models: Model[]
}
const modelGroups = ref<ModelGroup[]>([])

async function loadModels() {
  try {
    const providersRes = await getProviderList({ page: 1, page_size: 100 })
    const providers = providersRes.list as ModelProvider[]

    const groups: ModelGroup[] = []
    for (const p of providers) {
      try {
        const res = await getModelList(p.id, { page: 1, page_size: 100 })
        const enabled = res.list.filter(m => (m as any).enabled !== 0)
        if (enabled.length > 0) {
          groups.push({
            providerName: p.name,
            models: enabled,
          })
        }
      } catch {
        // provider 下可能没有模型
      }
    }
    modelGroups.value = groups
  } catch {
    // ignore
  }
}

// ── 节点类型显示 ──
function nodeTypeTagType(type: WorkflowNodeType): string {
  switch (type) {
    case WorkflowNodeType.START: return 'success'
    case WorkflowNodeType.END: return 'info'
    case WorkflowNodeType.LLM: return ''
    case WorkflowNodeType.CONDITION: return 'warning'
    default: return ''
  }
}

function nodeTypeLabel(type: WorkflowNodeType): string {
  switch (type) {
    case WorkflowNodeType.START: return '开始'
    case WorkflowNodeType.END: return '结束'
    case WorkflowNodeType.LLM: return 'LLM'
    case WorkflowNodeType.CONDITION: return '条件'
    default: return type
  }
}

// ── 节点操作 ──
function addNode(type: WorkflowNodeType) {
  const newNode = createNode(type)
  // 插入到 END 之前
  const endIndex = formData.nodes.length - 1
  formData.nodes.splice(endIndex, 0, newNode)
  rebuildEdges()
}

function removeNode(uid: string) {
  const index = formData.nodes.findIndex(n => n.uid === uid)
  if (index === -1) return
  const node = formData.nodes[index]
  if (node.node_type === WorkflowNodeType.START || node.node_type === WorkflowNodeType.END) return
  formData.nodes.splice(index, 1)
  rebuildEdges()
}

function onNodeTypeChange(node: WorkflowFormNode, _newType: WorkflowNodeType) {
  node.config = {}
  node.model_config_id = undefined
  node.prompt = undefined
  node.expression = undefined
}

// ── 连线 ──
function rebuildEdges() {
  const edges: WorkflowFormEdge[] = []
  for (let i = 0; i < formData.nodes.length - 1; i++) {
    const source = formData.nodes[i]
    const target = formData.nodes[i + 1]
    edges.push({
      source_node_key: source.node_key,
      target_node_key: target.node_key,
      condition: '',
    })
  }
  formData.edges = edges
}

function getNodeLabel(nodeKey: string): string {
  const node = formData.nodes.find(n => n.node_key === nodeKey)
  return node ? `${node.name} (${nodeKey})` : nodeKey
}

// ── 加载已有工作流（编辑模式）──
async function loadWorkflow() {
  if (!workflowId.value) return
  try {
    const wf = await getWorkflow(workflowId.value)
    formData.name = wf.name
    formData.description = wf.description || ''

    const nodes: WorkflowFormNode[] = (wf.nodes || []).map((n: any) => ({
      uid: nextUid(),
      node_key: n.node_key,
      name: n.name,
      node_type: n.node_type as WorkflowNodeType,
      model_config_id: n.config?.model_config_id,
      prompt: n.config?.prompt,
      expression: n.config?.expression,
      config: n.config || {},
    }))

    // 确保有 START 和 END
    const hasStart = nodes.some(n => n.node_type === WorkflowNodeType.START)
    const hasEnd = nodes.some(n => n.node_type === WorkflowNodeType.END)
    if (!hasStart) nodes.unshift(createNode(WorkflowNodeType.START))
    if (!hasEnd) nodes.push(createNode(WorkflowNodeType.END))

    formData.nodes = nodes

    // 加载已有连线
    formData.edges = (wf.edges || []).map((e: any) => ({
      source_node_key: e.source_node_key,
      target_node_key: e.target_node_key,
      condition: e.condition || '',
    }))
  } catch (e: any) {
    notifyError(e?.message || '加载工作流失败')
    router.push('/workflows')
  }
}

// ── 提交 ──
function buildSubmitData() {
  const nodes = formData.nodes.map((n, i) => ({
    node_key: n.node_key,
    name: n.name,
    node_type: n.node_type,
    config: buildNodeConfig(n),
    position_x: i * 200,
    position_y: 0,
  }))

  const edges = formData.edges.map(e => ({
    source_node_key: e.source_node_key,
    target_node_key: e.target_node_key,
    condition: e.condition,
  }))

  return { nodes, edges }
}

function buildNodeConfig(node: WorkflowFormNode): Record<string, any> {
  switch (node.node_type) {
    case WorkflowNodeType.LLM:
      return {
        model_config_id: node.model_config_id,
        prompt: node.prompt || '',
        output_variable: 'llm_output',
      }
    case WorkflowNodeType.CONDITION:
      return {
        expression: node.expression || '',
        output_variable: 'condition_result',
      }
    default:
      return {}
  }
}

function validateNodes(): string | null {
  for (const node of formData.nodes) {
    if (node.node_type === WorkflowNodeType.LLM) {
      if (!node.model_config_id) {
        return `节点「${node.name}」的模型不能为空`
      }
      if (!node.prompt || !node.prompt.trim()) {
        return `节点「${node.name}」的提示词不能为空`
      }
    }
    if (node.node_type === WorkflowNodeType.CONDITION) {
      if (!node.expression || !node.expression.trim()) {
        return `节点「${node.name}」的表达式不能为空`
      }
    }
  }
  return null
}

async function handleSubmit() {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
  } catch {
    return
  }

  const nodeError = validateNodes()
  if (nodeError) {
    notifyError(nodeError)
    return
  }

  rebuildEdges()

  submitting.value = true
  try {
    const data = buildSubmitData()
    const payload = {
      name: formData.name,
      description: formData.description,
      ...data,
    }

    if (isEdit.value && workflowId.value) {
      await updateWorkflow(workflowId.value, payload as any)
      notifySuccess('工作流已更新')
    } else {
      await createWorkflow(payload as any)
      notifySuccess('工作流已创建')
    }
    router.push('/workflows')
  } catch (e: any) {
    notifyError(e?.message || '保存失败')
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  loadModels()
  rebuildEdges()
  if (isEdit.value) {
    loadWorkflow()
  }
})
</script>

<style scoped>
.workflow-form-page {
  max-width: 900px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;
}

.page-header h2 {
  margin: 0 0 8px;
  font-size: 24px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.page-desc {
  margin: 0;
  color: var(--el-text-color-secondary);
  font-size: 14px;
}

.form-card {
  background: #fff;
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  padding: 32px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

/* ── 节点列表 ── */
.node-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
}

.node-card {
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  padding: 16px;
  background: var(--el-fill-color-lighter);
}

.node-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.node-index {
  font-weight: 600;
  font-size: 14px;
  color: var(--el-text-color-primary);
}

.node-header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.node-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.node-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.node-field label {
  font-size: 13px;
  color: var(--el-text-color-regular);
  font-weight: 500;
}

.node-field .required {
  color: var(--el-color-danger);
}

.field-hint {
  margin: 2px 0 0;
  font-size: 12px;
  color: var(--el-text-color-placeholder);
}

.field-hint code {
  background: var(--el-fill-color);
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 12px;
}

/* ── 添加节点 ── */
.add-node-area {
  margin-top: 12px;
}

/* ── 连线预览 ── */
.edge-preview {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

.edge-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--el-fill-color-lighter);
  border-radius: 6px;
  font-size: 13px;
}

.edge-source,
.edge-target {
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.edge-arrow {
  color: var(--el-color-primary);
  font-weight: 700;
  font-size: 16px;
}

.edge-condition {
  margin-left: auto;
}

.edge-empty {
  color: var(--el-text-color-placeholder);
  font-size: 13px;
}

/* ── 表单操作 ── */
.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  width: 100%;
}
</style>
