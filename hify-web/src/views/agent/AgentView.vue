<template>
  <div class="agent-view">
    <!-- 页面顶部 -->
    <div class="page-header">
      <div class="page-header-left">
        <h1 class="page-title">Agent 管理</h1>
        <p class="page-desc">创建和配置 AI Agent，绑定模型、知识库与工具</p>
      </div>
      <el-button type="primary" class="btn-add" @click="handleAdd">
        <el-icon><Plus /></el-icon>
        新建 Agent
      </el-button>
    </div>

    <!-- 表格 -->
    <div class="table-wrapper">
      <HifyTable ref="tableRef" :api="getAgentList">
        <el-table-column prop="name" label="名称" min-width="160" />
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="model_id" label="模型" width="160">
          <template #default="{ row }">
            <span class="model-label">{{ modelNameMap[row.model_id] ?? row.model_id }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="temperature" label="温度" width="90">
          <template #default="{ row }">
            <span class="temperature-value">{{ row.temperature?.toFixed(2) ?? '0.70' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="max_context_turns" label="上下文轮数" width="110">
          <template #default="{ row }">
            <span>{{ row.max_context_turns ?? 10 }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="enabled" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.enabled === 1 ? 'success' : 'info'" size="small" effect="plain">
              {{ row.enabled === 1 ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="知识库" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.knowledge_bases?.length" size="small" effect="plain">
              {{ row.knowledge_bases.length }}
            </el-tag>
            <span v-else class="text-tertiary">0</span>
          </template>
        </el-table-column>
        <el-table-column label="工具" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.tools?.length" size="small" effect="plain">
              {{ row.tools.length }}
            </el-tag>
            <span v-else class="text-tertiary">0</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170" class-name="col-created-at">
          <template #default="{ row }">
            {{ row.created_at }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button type="primary" text size="small" class="btn-edit" @click="handleEdit(row)">编辑</el-button>
              <el-button type="danger" text size="small" class="btn-delete" @click="handleDelete(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </HifyTable>
    </div>

    <!-- 表单弹窗 -->
    <HifyFormDialog
      ref="dialogRef"
      title="Agent"
      :rules="formRules"
      @submit="handleSubmit"
    >
      <template #default="{ formData: fd }">
        <el-form-item label="名称" prop="name">
          <el-input v-model="fd.name" placeholder="请输入 Agent 名称" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="fd.description" type="textarea" :rows="2" maxlength="500" show-word-limit placeholder="请输入 Agent 描述（可选）" />
        </el-form-item>
        <el-form-item label="模型" prop="model_id">
          <el-select v-model="fd.model_id" placeholder="请选择模型" style="width: 100%">
            <el-option-group
              v-for="group in groupedModels"
              :key="group.providerId"
              :label="group.providerName"
            >
              <el-option
                v-for="m in group.models"
                :key="m.id"
                :label="m.name"
                :value="m.id"
              />
            </el-option-group>
          </el-select>
        </el-form-item>
        <el-form-item label="系统提示词" prop="system_prompt">
          <el-input
            v-model="fd.system_prompt"
            type="textarea"
            :rows="5"
            placeholder="请输入系统提示词"
          />
        </el-form-item>
        <el-divider content-position="left">模型参数</el-divider>
        <el-form-item label="知识库" prop="knowledge_base_id">
          <el-select v-model="fd.knowledge_base_id" placeholder="暂不绑定" clearable style="width: 100%">
            <el-option
              v-for="kb in allKnowledgeBases"
              :key="kb.id"
              :label="kb.name"
              :value="kb.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="工作流" prop="workflow_id">
          <el-select v-model="fd.workflow_id" placeholder="暂不绑定" clearable style="width: 100%">
            <el-option
              v-for="wf in allWorkflows"
              :key="wf.id"
              :label="wf.name"
              :value="wf.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="温度" prop="temperature">
          <div class="slider-wrapper">
            <el-slider
              v-model="fd.temperature"
              :min="0"
              :max="1"
              :step="0.1"
              :show-tooltip="false"
              style="flex: 1"
            />
            <span class="slider-value">{{ (fd.temperature ?? 0.7).toFixed(2) }}</span>
          </div>
        </el-form-item>
        <el-form-item label="最大 Token" prop="max_tokens">
          <el-input-number v-model="fd.max_tokens" :min="1" :max="128000" style="width: 100%" />
        </el-form-item>
        <el-form-item label="上下文轮数" prop="max_context_turns">
          <el-input-number v-model="fd.max_context_turns" :min="1" :max="100" style="width: 100%" />
        </el-form-item>
        <el-form-item label="状态" prop="enabled">
          <el-select v-model="fd.enabled" style="width: 100%">
            <el-option label="启用" :value="1" />
            <el-option label="禁用" :value="0" />
          </el-select>
        </el-form-item>
      </template>
    </HifyFormDialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import HifyTable from '@/components/HifyTable.vue'
import HifyFormDialog from '@/components/HifyFormDialog.vue'
import { useConfirm } from '@/composables/useConfirm'
import { notifySuccess } from '@/utils/notify'
import { getAgentList, createAgent, updateAgent, deleteAgent } from '@/api/agent'
import { getProviderList } from '@/api/provider'
import { getModelList } from '@/api/model'
import { getKnowledgeBaseList } from '@/api/knowledge'
import { getWorkflowList } from '@/api/workflow'
import type { Agent, Model, ModelProvider, KnowledgeBase, Workflow } from '@/types/model'

// ── 模型列表（表单下拉用，按 Provider 分组）──────────────────
const allModels = ref<Model[]>([])
const allProviders = ref<ModelProvider[]>([])
const modelNameMap = ref<Record<number, string>>({})

interface GroupedModel {
  providerId: number
  providerName: string
  models: Model[]
}

const groupedModels = computed<GroupedModel[]>(() => {
  const groups: GroupedModel[] = []
  for (const p of allProviders.value) {
    const providerModels = allModels.value.filter(m => m.provider_id === p.id && m.status === 'enabled')
    if (providerModels.length > 0) {
      groups.push({
        providerId: p.id,
        providerName: p.name,
        models: providerModels,
      })
    }
  }
  return groups
})

const loadModels = async () => {
  try {
    const providersRes = await getProviderList({ page: 1, page_size: 100 })
    const providers = providersRes.list as ModelProvider[]
    allProviders.value = providers

    const models: Model[] = []
    const nameMap: Record<number, string> = {}
    for (const p of providers) {
      try {
        const res = await getModelList(p.id, { page: 1, page_size: 100 })
        for (const m of res.list) {
          models.push(m)
          nameMap[m.id] = m.name
        }
      } catch {
        // provider 下可能没有模型
      }
    }
    allModels.value = models
    modelNameMap.value = nameMap
  } catch {
    // ignore
  }
}

onMounted(loadModels)

// ── 知识库列表（表单下拉用）─────────────────────────────────
const allKnowledgeBases = ref<KnowledgeBase[]>([])

const loadKnowledgeBases = async () => {
  try {
    const res = await getKnowledgeBaseList({ page: 1, page_size: 100 })
    // 确保所有知识库 ID 都是 Number 类型
    const list = (res.list as KnowledgeBase[]).map(kb => ({
      ...kb,
      id: Number(kb.id)
    }))
    allKnowledgeBases.value = list
  } catch {
    // ignore
  }
}

onMounted(loadKnowledgeBases)

// ── 工作流列表（表单下拉用）─────────────────────────────────
const allWorkflows = ref<Workflow[]>([])

const loadWorkflows = async () => {
  try {
    const res = await getWorkflowList({ page: 1, page_size: 100 })
    const list = (res.list as Workflow[]).map(wf => ({
      ...wf,
      id: Number(wf.id)
    }))
    allWorkflows.value = list
  } catch {
    // ignore
  }
}

onMounted(loadWorkflows)

// ── 弹窗 ────────────────────────────────────────────────
const tableRef = ref()
const dialogRef = ref()
const editingAgent = ref<Agent | null>(null)

const formRules = {
  name:     [{ required: true, message: '请输入 Agent 名称', trigger: 'blur' }],
  model_id: [{ required: true, message: '请选择模型', trigger: 'change' }],
}

const handleAdd = () => {
  editingAgent.value = null
  dialogRef.value.open({
    temperature: 0.7,
    max_tokens: 2048,
    max_context_turns: 10,
    enabled: 1,
    knowledge_base_id: null,
    workflow_id: null,
  })
}

const handleEdit = (row: Agent) => {
  editingAgent.value = row

  // 取第一个知识库 ID，确保是 Number 类型
  let kbId: number | null = null
  if (row.knowledge_bases?.length && row.knowledge_bases[0]?.id != null) {
    kbId = Number(row.knowledge_bases[0].id)
  }

  dialogRef.value.open({
    name: row.name,
    description: (row as any).description ?? '',
    model_id: row.model_id,
    system_prompt: row.system_prompt,
    temperature: (row as any).temperature ?? 0.7,
    max_tokens: (row as any).max_tokens ?? 2048,
    max_context_turns: (row as any).max_context_turns ?? 10,
    enabled: (row as any).enabled ?? 1,
    knowledge_base_id: kbId,
    workflow_id: (row as any).workflow_id ?? null,
  })
}

const handleSubmit = async (formData: any) => {
  const payload = {
    name: formData.name,
    description: formData.description ?? '',
    model_id: formData.model_id,
    workflow_id: formData.workflow_id ?? null,
    system_prompt: formData.system_prompt ?? '',
    temperature: formData.temperature ?? 0.7,
    max_tokens: formData.max_tokens ?? 2048,
    max_context_turns: formData.max_context_turns ?? 10,
    enabled: formData.enabled ?? 1,
    knowledge_base_id: formData.knowledge_base_id ?? 0,
  }
  if (editingAgent.value) {
    await updateAgent(editingAgent.value.id, payload)
    notifySuccess('更新成功')
  } else {
    await createAgent(payload)
    notifySuccess('创建成功')
  }
  tableRef.value?.refresh()
}

// ── 删除 ────────────────────────────────────────────────
const handleDelete = (row: Agent) => {
  const deleteFn = useConfirm(
    `确认删除「${row.name}」？删除后无法恢复。`,
    async () => {
      await deleteAgent(row.id)
      tableRef.value?.refresh()
    },
    '删除成功',
  )
  deleteFn()
}
</script>

<style scoped>
.agent-view {
  max-width: 1200px;
}

/* ── 页面顶部 ─────────────────────────────────────────── */
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 24px;
}

.page-header-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
  line-height: 1.3;
}

.page-desc {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin: 0;
}

/* ── 新增按钮 ──────────────────────────────────────────── */
.btn-add {
  display: flex;
  align-items: center;
  gap: 6px;
  background: linear-gradient(135deg, var(--color-brand-500), var(--color-brand-600)) !important;
  border: none !important;
  font-weight: 500;
  padding: 10px 20px;
  border-radius: var(--radius-lg);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.35);
  transition: all var(--transition-normal);
  color: #fff;
}

.btn-add:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(99, 102, 241, 0.45);
  background: linear-gradient(135deg, var(--color-brand-600), var(--color-brand-700)) !important;
}

.btn-add .el-icon {
  font-size: 16px;
}

/* ── 表格 ─────────────────────────────────────────────── */
.table-wrapper {
  background: var(--bg-surface);
  border-radius: var(--radius-xl);
  padding: 20px;
  border: 1px solid var(--border-default);
  box-shadow: var(--shadow-sm);
}

.table-wrapper :deep(.el-table__row) {
  height: 52px;
}

.table-wrapper :deep(.el-table__header th) {
  background: var(--bg-elevated) !important;
  color: var(--text-secondary);
  font-weight: 600;
  font-size: var(--text-sm);
}

.table-wrapper :deep(.el-table__body tr:hover > td) {
  background: var(--bg-elevated) !important;
}

@media (max-width: 1200px) {
  .agent-view {
    --hide-extra-col: none;
  }
}

/* 操作列按钮 */
.action-buttons {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-edit {
  color: var(--color-brand-500) !important;
  font-weight: 500;
}

.btn-edit:hover {
  color: var(--color-brand-700) !important;
}

.btn-delete {
  color: var(--color-danger) !important;
}

.btn-delete:hover {
  color: #c53030 !important;
}

/* 分页器上方分割线 */
.table-wrapper :deep(.hify-table-pagination) {
  padding-top: 16px;
  margin-top: 16px;
  border-top: 1px solid var(--border-default);
}

/* 模型标签 */
.model-label {
  font-weight: 500;
  color: var(--text-primary);
}

/* 温度数值 */
.temperature-value {
  font-family: var(--font-mono);
  font-weight: 500;
  color: var(--text-primary);
}

/* 数量为 0 时的颜色 */
.text-tertiary {
  color: var(--text-tertiary);
}

/* 滑块容器 */
.slider-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.slider-value {
  font-family: var(--font-mono);
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  min-width: 40px;
  text-align: right;
}
</style>
