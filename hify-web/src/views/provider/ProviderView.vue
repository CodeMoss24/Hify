<template>
  <div class="provider-view">
    <!-- 页面顶部 -->
    <div class="page-header">
      <div class="page-header-left">
        <h1 class="page-title">模型提供商管理</h1>
        <p class="page-desc">管理 AI 模型提供商配置与连接</p>
      </div>
      <el-button type="primary" class="btn-add" @click="handleAdd">
        <el-icon><Plus /></el-icon>
        新增提供商
      </el-button>
    </div>

    <!-- 表格 -->
    <div class="table-wrapper">
      <HifyTable ref="tableRef" :api="getProviderList">
        <el-table-column prop="name" label="名称" min-width="160" />
        <el-table-column prop="provider_type" label="类型" width="130">
          <template #default="{ row }">
            <span class="provider-type">{{ typeLabelMap[row.provider_type] ?? row.provider_type }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="base_url" label="Base URL" min-width="200" class-name="col-base-url">
          <template #default="{ row }">
            <span class="base-url-text">{{ row.base_url }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 'enabled' ? 'success' : 'info'" size="small" effect="plain">
              {{ row.status === 'enabled' ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="健康" width="90">
          <template #default="{ row }">
            <el-tag
              v-if="row.health"
              :type="healthTagType(row.health.status)"
              size="small"
              effect="plain"
            >
              {{ healthLabel(row.health.status) }}
            </el-tag>
            <el-tag v-else type="info" size="small" effect="plain">未知</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170" class-name="col-created-at">
          <template #default="{ row }">
            {{ row.created_at }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button type="primary" text size="small" class="btn-edit" @click="handleEdit(row)">编辑</el-button>
              <el-button
                text size="small"
                class="btn-test"
                :loading="testingId === row.id"
                @click="handleTestConnection(row)"
              >
                测试
              </el-button>
              <el-button type="danger" text size="small" class="btn-delete" @click="handleDelete(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </HifyTable>
    </div>

    <!-- 表单弹窗 -->
    <HifyFormDialog
      ref="dialogRef"
      title="模型提供商"
      :rules="formRules"
      @submit="handleSubmit"
    >
      <template #default="{ formData: fd }">
        <el-form-item label="名称" prop="name">
          <el-input v-model="fd.name" placeholder="请输入提供商名称" />
        </el-form-item>
        <el-form-item label="类型" prop="provider_type">
          <el-select v-model="fd.provider_type" placeholder="请选择类型" style="width: 100%">
            <el-option label="OpenAI" value="openai" />
            <el-option label="Claude (Anthropic)" value="anthropic" />
            <el-option label="OpenAI 兼容" value="openai_compatible" />
            <el-option label="Ollama" value="ollama" />
          </el-select>
        </el-form-item>
        <el-form-item label="API Key" prop="api_key">
          <el-input
            v-model="fd.api_key"
            :type="showApiKey ? 'text' : 'password'"
            placeholder="请输入 API Key（Ollama 可留空）"
            autocomplete="new-password"
          >
            <template #suffix>
              <el-button link class="btn-eye" @click="showApiKey = !showApiKey">
                <el-icon><View v-if="!showApiKey" /><Hide v-else /></el-icon>
              </el-button>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item label="Base URL" prop="base_url">
          <el-input v-model="fd.base_url" placeholder="https://api.openai.com/v1" />
        </el-form-item>
        <el-form-item v-if="fd.provider_type === 'openai_compatible'" label="测试模型">
          <el-input v-model="fd.test_model" placeholder="火山方舟填 endpoint_id，其他填模型名" />
        </el-form-item>
      </template>
    </HifyFormDialog>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, View, Hide } from '@element-plus/icons-vue'
import HifyTable from '@/components/HifyTable.vue'
import HifyFormDialog from '@/components/HifyFormDialog.vue'
import { useConfirm } from '@/composables/useConfirm'
import { notifySuccess } from '@/utils/notify'
import {
  getProviderList,
  createProvider,
  updateProvider,
  deleteProvider,
  testConnection,
} from '@/api/provider'
import type { ModelProvider, ProviderHealth } from '@/types/model'

// ── 类型映射 ────────────────────────────────────────────
const typeLabelMap: Record<string, string> = {
  openai:           'OpenAI',
  anthropic:        'Claude',
  openai_compatible: 'OpenAI 兼容',
  ollama:           'Ollama',
}

const healthTagType = (status: string) => {
  if (status === 'healthy') return 'success'
  if (status === 'unhealthy') return 'danger'
  return 'info'
}

const healthLabel = (status: string) => {
  if (status === 'healthy') return '正常'
  if (status === 'unhealthy') return '异常'
  return '未知'
}

// ── 弹窗 ────────────────────────────────────────────────
const tableRef = ref()
const dialogRef = ref()
const showApiKey = ref(false)
const editingProvider = ref<ModelProvider | null>(null)

const formRules = {
  name:          [{ required: true, message: '请输入提供商名称', trigger: 'blur' }],
  provider_type: [{ required: true, message: '请选择类型', trigger: 'change' }],
  base_url:      [{ required: true, message: '请输入 Base URL', trigger: 'blur' }],
}

const handleAdd = () => {
  editingProvider.value = null
  showApiKey.value = false
  dialogRef.value.open()
}

const handleEdit = (row: ModelProvider) => {
  editingProvider.value = row
  showApiKey.value = false
  const form = { ...row, test_model: row.extra_config?.test_model ?? '' }
  dialogRef.value.open(form)
}

const handleSubmit = async (formData: any) => {
  const { test_model, ...rest } = formData
  const payload: any = { ...rest }
  // openai_compatible 时把 test_model 放进 extra_config
  if (rest.provider_type === 'openai_compatible' && test_model) {
    payload.extra_config = { ...(rest.extra_config || {}), test_model }
  }
  if (editingProvider.value) {
    await updateProvider(editingProvider.value.id, payload)
    notifySuccess('更新成功')
  } else {
    await createProvider(payload)
    notifySuccess('创建成功')
  }
  tableRef.value?.refresh()
}

// ── 删除 ────────────────────────────────────────────────
const handleDelete = (row: ModelProvider) => {
  const deleteFn = useConfirm(
    `确认删除「${row.name}」？删除后无法恢复。`,
    async () => {
      await deleteProvider(row.id)
      tableRef.value?.refresh()
    },
    '删除成功',
  )
  deleteFn()
}

// ── 连通性测试 ──────────────────────────────────────────
const testingId = ref<number | null>(null)

const handleTestConnection = async (row: ModelProvider) => {
  testingId.value = row.id
  try {
    const result = await testConnection(row.id)
    if (result.success) {
      ElMessage.success(`连接成功 · 延迟 ${result.latency_ms}ms · 模型 ${result.model_count} 个`)
    } else {
      ElMessage.error(`连接失败 · ${result.error_message}`)
    }
  } catch {
    // axios interceptor 已提示
  } finally {
    testingId.value = null
  }
}
</script>

<style scoped>
.provider-view {
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

/* 表格行高 52px */
.table-wrapper :deep(.el-table__row) {
  height: 52px;
}

/* 表头背景 */
.table-wrapper :deep(.el-table__header th) {
  background: var(--bg-elevated) !important;
  color: var(--text-secondary);
  font-weight: 600;
  font-size: var(--text-sm);
}

/* 行 hover 微微变色 */
.table-wrapper :deep(.el-table__body tr:hover > td) {
  background: var(--bg-elevated) !important;
}

/* 响应式隐藏 Base URL 和创建时间列 */
.table-wrapper :deep(.col-base-url),
.table-wrapper :deep(.col-created-at) {
  display: var(--hide-extra-col, table-cell);
}

@media (max-width: 1200px) {
  .provider-view {
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

.btn-test {
  color: var(--color-brand-500) !important;
  font-weight: 500;
}

.btn-test:hover {
  color: var(--color-brand-700) !important;
}

.btn-delete {
  color: var(--color-danger) !important;
}

.btn-delete:hover {
  color: #c53030 !important;
}

/* password 显示切换按钮 */
.btn-eye {
  padding: 0 4px;
  color: var(--text-tertiary);
}

/* 分页器上方分割线 */
.table-wrapper :deep(.hify-table-pagination) {
  padding-top: 16px;
  margin-top: 16px;
  border-top: 1px solid var(--border-default);
}

/* provider type 文字 */
.provider-type {
  font-weight: 500;
  color: var(--text-primary);
}

/* Base URL monospace 字体 */
.base-url-text {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--text-secondary);
}
</style>
