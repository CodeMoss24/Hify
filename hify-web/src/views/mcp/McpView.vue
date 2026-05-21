<template>
  <div class="mcp-view">
    <!-- 页面顶部 -->
    <div class="page-header">
      <div class="page-header-left">
        <h1 class="page-title">MCP Server 管理</h1>
        <p class="page-desc">管理 MCP 工具服务器，测试连通性并自动发现工具</p>
      </div>
      <el-button type="primary" class="btn-add" @click="handleAdd">
        <el-icon><Plus /></el-icon>
        新增 Server
      </el-button>
    </div>

    <!-- 表格 -->
    <div class="table-wrapper">
      <HifyTable ref="tableRef" :api="getMcpServerList" @load="onTableLoad">
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="expand-content">
              <div class="expand-title">已发现工具</div>
              <div v-if="toolLoadingMap[row.id]" class="expand-loading">
                <el-icon class="is-loading"><Loading /></el-icon> 加载中...
              </div>
              <div v-else-if="toolMap[row.id]?.length" class="tool-list">
                <div v-for="tool in toolMap[row.id]" :key="tool.id" class="tool-item">
                  <div class="tool-header">
                    <span class="tool-name">{{ tool.name }}</span>
                  </div>
                  <div class="tool-desc">{{ tool.description }}</div>
                </div>
              </div>
              <div v-else class="expand-empty">
                暂无工具，点击「测试」按钮连通后自动拉取
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="名称" min-width="160" />
        <el-table-column prop="url" label="URL" min-width="260" class-name="col-url">
          <template #default="{ row }">
            <span class="url-text">{{ row.url }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="enabled" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.enabled ? 'success' : 'info'" size="small" effect="plain">
              {{ row.enabled ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="工具数" width="80">
          <template #default="{ row }">
            <span class="tool-count">{{ toolMap[row.id]?.length ?? '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170" class-name="col-created-at">
          <template #default="{ row }">
            {{ row.created_at }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button type="primary" text size="small" class="btn-detail" @click="router.push(`/mcp/${row.id}`)">详情</el-button>
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
      title="MCP Server"
      :rules="formRules"
      @submit="handleSubmit"
    >
      <template #default="{ formData: fd }">
        <el-form-item label="名称" prop="name">
          <el-input v-model="fd.name" placeholder="请输入 Server 名称" />
        </el-form-item>
        <el-form-item label="URL" prop="url">
          <el-input v-model="fd.url" placeholder="http://localhost:8000/api/v1/mcp-refund" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="fd.enabled" />
        </el-form-item>
      </template>
    </HifyFormDialog>

    <!-- 连通性测试结果弹窗 -->
    <el-dialog
      v-model="testResultVisible"
      title="连通性测试结果"
      width="560px"
      destroy-on-close
    >
      <div v-if="testResult" class="test-result">
        <div class="test-result-header">
          <el-tag :type="testResult.success ? 'success' : 'danger'" size="large" effect="plain">
            {{ testResult.success ? '连接成功' : '连接失败' }}
          </el-tag>
          <span v-if="testResult.success" class="test-result-count">
            发现 {{ testResult.tool_count }} 个工具
          </span>
          <span v-else class="test-result-error">{{ testResult.error_message }}</span>
        </div>
        <div v-if="testResult.success && testResult.tools?.length" class="test-tools">
          <div v-for="tool in testResult.tools" :key="tool.id" class="test-tool-item">
            <div class="test-tool-name">{{ tool.name }}</div>
            <div class="test-tool-desc">{{ tool.description }}</div>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus, Loading } from '@element-plus/icons-vue'
import HifyTable from '@/components/HifyTable.vue'
import HifyFormDialog from '@/components/HifyFormDialog.vue'
import { useConfirm } from '@/composables/useConfirm'
import { notifySuccess } from '@/utils/notify'
import {
  getMcpServerList,
  getMcpServer,
  createMcpServer,
  updateMcpServer,
  deleteMcpServer,
  testMcpConnection,
} from '@/api/mcp'
import type { McpServer, McpTool, McpConnectionTestResult } from '@/types/model'

const router = useRouter()

// ── 工具列表缓存 ────────────────────────────────────────
const toolMap = reactive<Record<number, McpTool[]>>({})
const toolLoadingMap = reactive<Record<number, boolean>>({})

const onTableLoad = async (rows: McpServer[]) => {
  for (const row of rows) {
    if (!toolMap[row.id]) {
      loadTools(row.id)
    }
  }
}

const loadTools = async (serverId: number) => {
  toolLoadingMap[serverId] = true
  try {
    const detail = await getMcpServer(serverId)
    toolMap[serverId] = detail.tools
  } catch {
    toolMap[serverId] = []
  } finally {
    toolLoadingMap[serverId] = false
  }
}

// ── 弹窗 ────────────────────────────────────────────────
const tableRef = ref()
const dialogRef = ref()
const editingServer = ref<McpServer | null>(null)

const formRules = {
  name: [{ required: true, message: '请输入 Server 名称', trigger: 'blur' }],
  url:  [{ required: true, message: '请输入 Server URL', trigger: 'blur' }],
}

const handleAdd = () => {
  editingServer.value = null
  dialogRef.value.open({ enabled: true })
}

const handleEdit = (row: McpServer) => {
  editingServer.value = row
  dialogRef.value.open({ ...row })
}

const handleSubmit = async (formData: any) => {
  const payload = { name: formData.name, url: formData.url, enabled: !!formData.enabled }
  if (editingServer.value) {
    await updateMcpServer(editingServer.value.id, payload)
    notifySuccess('更新成功')
  } else {
    await createMcpServer(payload)
    notifySuccess('创建成功')
  }
  tableRef.value?.refresh()
}

// ── 删除 ────────────────────────────────────────────────
const handleDelete = (row: McpServer) => {
  const deleteFn = useConfirm(
    `确认删除「${row.name}」？删除后无法恢复。`,
    async () => {
      await deleteMcpServer(row.id)
      delete toolMap[row.id]
      tableRef.value?.refresh()
    },
    '删除成功',
  )
  deleteFn()
}

// ── 连通性测试 ──────────────────────────────────────────
const testingId = ref<number | null>(null)
const testResultVisible = ref(false)
const testResult = ref<McpConnectionTestResult | null>(null)

const handleTestConnection = async (row: McpServer) => {
  testingId.value = row.id
  try {
    const result = await testMcpConnection(row.id)
    testResult.value = result
    testResultVisible.value = true
    if (result.success) {
      toolMap[row.id] = result.tools
      ElMessage.success(`连接成功，发现 ${result.tool_count} 个工具`)
    } else {
      ElMessage.error(`连接失败：${result.error_message}`)
    }
  } catch {
    // axios interceptor 已提示
  } finally {
    testingId.value = null
  }
}
</script>

<style scoped>
.mcp-view {
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

.table-wrapper :deep(.col-url),
.table-wrapper :deep(.col-created-at) {
  display: var(--hide-extra-col, table-cell);
}

@media (max-width: 1200px) {
  .mcp-view {
    --hide-extra-col: none;
  }
}

/* 操作列按钮 */
.action-buttons {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-detail {
  color: var(--color-brand-500) !important;
  font-weight: 500;
}

.btn-detail:hover {
  color: var(--color-brand-700) !important;
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

/* 分页器 */
.table-wrapper :deep(.hify-table-pagination) {
  padding-top: 16px;
  margin-top: 16px;
  border-top: 1px solid var(--border-default);
}

/* URL monospace */
.url-text {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--text-secondary);
}

/* 工具数 */
.tool-count {
  font-weight: 600;
  color: var(--text-primary);
}

/* ── 展开行 ────────────────────────────────────────────── */
.expand-content {
  padding: 12px 20px 16px 56px;
}

.expand-title {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 10px;
}

.expand-loading {
  font-size: var(--text-sm);
  color: var(--text-tertiary);
  display: flex;
  align-items: center;
  gap: 6px;
}

.expand-empty {
  font-size: var(--text-sm);
  color: var(--text-tertiary);
}

.tool-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.tool-item {
  background: var(--bg-elevated);
  border-radius: var(--radius-md);
  padding: 10px 14px;
  border: 1px solid var(--border-default);
}

.tool-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.tool-name {
  font-weight: 600;
  font-size: var(--text-sm);
  color: var(--color-brand-600);
  font-family: var(--font-mono);
}

.tool-desc {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  line-height: 1.5;
}

/* ── 测试结果弹窗 ─────────────────────────────────────── */
.test-result {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.test-result-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.test-result-count {
  font-size: var(--text-sm);
  color: var(--text-primary);
  font-weight: 500;
}

.test-result-error {
  font-size: var(--text-sm);
  color: var(--color-danger);
}

.test-tools {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 360px;
  overflow-y: auto;
}

.test-tool-item {
  background: var(--bg-elevated);
  border-radius: var(--radius-md);
  padding: 10px 14px;
  border: 1px solid var(--border-default);
}

.test-tool-name {
  font-weight: 600;
  font-size: var(--text-sm);
  color: var(--color-brand-600);
  font-family: var(--font-mono);
  margin-bottom: 4px;
}

.test-tool-desc {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  line-height: 1.5;
}
</style>
