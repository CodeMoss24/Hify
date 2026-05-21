<template>
  <div class="mcp-detail">
    <!-- 返回 + 标题 -->
    <div class="page-header">
      <div class="page-header-left">
        <el-button text class="btn-back" @click="router.push('/mcp')">
          <el-icon><ArrowLeft /></el-icon> 返回列表
        </el-button>
        <h1 class="page-title">{{ server?.name ?? 'MCP Server' }}</h1>
        <p class="page-desc">{{ server?.url ?? '' }}</p>
      </div>
      <div class="page-header-right">
        <el-tag :type="server?.enabled ? 'success' : 'info'" size="small" effect="plain">
          {{ server?.enabled ? '启用' : '禁用' }}
        </el-tag>
      </div>
    </div>

    <!-- Tabs -->
    <el-tabs v-model="activeTab" class="detail-tabs">
      <!-- ── 工具列表 Tab ── -->
      <el-tab-pane label="工具列表" name="tools">
        <div class="tab-toolbar">
          <el-button
            type="primary"
            plain
            :loading="testing"
            @click="handleTestConnection"
          >
            <el-icon><Connection /></el-icon>
            测试连通性
          </el-button>
          <span class="tool-count-label">共 {{ tools.length }} 个工具</span>
        </div>
        <div v-if="tools.length" class="tool-grid">
          <div v-for="tool in tools" :key="tool.id" class="tool-card" @click="goDebug(tool)">
            <div class="tool-card-header">
              <span class="tool-card-name">{{ tool.name }}</span>
              <el-icon class="tool-card-arrow"><ArrowRight /></el-icon>
            </div>
            <div class="tool-card-desc">{{ tool.description || '无描述' }}</div>
          </div>
        </div>
        <el-empty v-else description="暂无工具，点击「测试连通性」拉取" />
      </el-tab-pane>

      <!-- ── 调试工具 Tab ── -->
      <el-tab-pane label="调试工具" name="debug">
        <div class="debug-layout">
          <!-- 左侧：工具列表 -->
          <div class="debug-sidebar">
            <div class="debug-sidebar-title">选择工具</div>
            <div v-if="tools.length" class="debug-tool-list">
              <div
                v-for="tool in tools"
                :key="tool.id"
                class="debug-tool-item"
                :class="{ active: selectedTool?.id === tool.id }"
                @click="selectTool(tool)"
              >
                <span class="debug-tool-name">{{ tool.name }}</span>
              </div>
            </div>
            <el-empty v-else description="暂无工具" :image-size="60" />
          </div>

          <!-- 右侧：参数 + 结果 -->
          <div class="debug-main">
            <template v-if="selectedTool">
              <!-- 工具描述 -->
              <div class="debug-tool-desc">{{ selectedTool.description }}</div>

              <!-- 参数表单 -->
              <div class="debug-form">
                <div class="debug-form-title">参数</div>
                <el-form label-width="120px" size="default">
                  <el-form-item
                    v-for="field in formFields"
                    :key="field.key"
                    :label="field.key"
                    :required="field.required"
                  >
                    <el-input
                      v-if="field.type === 'string'"
                      v-model="formValues[field.key]"
                      :placeholder="field.description || field.key"
                    />
                    <el-input-number
                      v-else-if="field.type === 'integer'"
                      v-model="formValues[field.key]"
                      :placeholder="field.description || field.key"
                      controls-position="right"
                      style="width: 100%"
                    />
                  </el-form-item>
                  <el-form-item v-if="formFields.length === 0">
                    <span class="no-params">该工具无需参数</span>
                  </el-form-item>
                  <el-form-item>
                    <el-button
                      type="primary"
                      :loading="debugging"
                      @click="handleDebug"
                    >
                      {{ debugging ? '调用中...' : '调用工具' }}
                    </el-button>
                  </el-form-item>
                </el-form>
              </div>

              <!-- 结果区 -->
              <div v-if="debugResult" class="debug-result">
                <div class="debug-result-header">
                  <span class="debug-result-label">返回结果</span>
                  <el-tag size="small" effect="plain" type="info">
                    耗时 {{ debugResult.elapsed_ms }}ms
                  </el-tag>
                </div>
                <pre class="debug-result-content">{{ formatResult(debugResult.result) }}</pre>
              </div>

              <!-- 历史记录 -->
              <div v-if="history.length" class="debug-history">
                <div class="debug-history-title">最近调用（{{ history.length }}/5）</div>
                <div
                  v-for="(record, idx) in history"
                  :key="idx"
                  class="debug-history-item"
                >
                  <div class="history-meta">
                    <span class="history-tool">{{ record.tool }}</span>
                    <span class="history-time">{{ record.elapsed_ms }}ms</span>
                  </div>
                  <pre class="history-content">{{ formatResult(record.result) }}</pre>
                </div>
              </div>
            </template>
            <div v-else class="debug-placeholder">
              <el-icon :size="32" color="var(--text-tertiary)"><Monitor /></el-icon>
              <p>从左侧选择一个工具开始调试</p>
            </div>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, ArrowRight, Connection, Monitor } from '@element-plus/icons-vue'
import { getMcpServer, testMcpConnection, debugMcpTool } from '@/api/mcp'
import type { McpServer, McpTool, McpDebugResult } from '@/types/model'

const route = useRoute()
const router = useRouter()
const serverId = Number(route.params.id)

const server = ref<McpServer | null>(null)
const tools = ref<McpTool[]>([])
const activeTab = ref('tools')
const testing = ref(false)

const loadDetail = async () => {
  try {
    const detail = await getMcpServer(serverId)
    server.value = detail.server
    tools.value = detail.tools
  } catch {
    ElMessage.error('加载 Server 详情失败')
  }
}

onMounted(loadDetail)

// ── 连通性测试 ──────────────────────────────────────────
const handleTestConnection = async () => {
  testing.value = true
  try {
    const result = await testMcpConnection(serverId)
    if (result.success) {
      ElMessage.success(`连接成功，发现 ${result.tool_count} 个工具`)
      tools.value = result.tools
    } else {
      ElMessage.error(`连接失败：${result.error_message}`)
    }
  } catch {
    // interceptor handled
  } finally {
    testing.value = false
  }
}

// ── 工具列表 → 调试 ────────────────────────────────────
const goDebug = (tool: McpTool) => {
  selectTool(tool)
  activeTab.value = 'debug'
}

// ── 调试相关 ────────────────────────────────────────────
const selectedTool = ref<McpTool | null>(null)
const formValues = reactive<Record<string, any>>({})
const debugging = ref(false)
const debugResult = ref<McpDebugResult | null>(null)
const history = ref<Array<{ tool: string; result: string; elapsed_ms: number }>>([])

interface FormField {
  key: string
  type: string
  required: boolean
  description: string
}

const formFields = computed<FormField[]>(() => {
  if (!selectedTool.value?.input_schema) return []
  try {
    const schema = JSON.parse(selectedTool.value.input_schema)
    const props = schema.properties ?? {}
    const required = new Set(schema.required ?? [])
    return Object.entries(props).map(([key, def]: [string, any]) => ({
      key,
      type: def.type ?? 'string',
      required: required.has(key),
      description: def.description ?? '',
    }))
  } catch {
    return []
  }
})

const selectTool = (tool: McpTool) => {
  selectedTool.value = tool
  debugResult.value = null
  // 重置表单
  Object.keys(formValues).forEach(k => delete formValues[k])
  formFields.value.forEach(f => {
    formValues[f.key] = f.type === 'integer' ? undefined : ''
  })
}

const handleDebug = async () => {
  if (!selectedTool.value) return
  debugging.value = true
  try {
    // 收集参数，过滤掉空字符串的 optional 字段
    const args: Record<string, any> = {}
    for (const f of formFields.value) {
      const val = formValues[f.key]
      if (val !== '' && val !== undefined && val !== null) {
        args[f.key] = val
      }
    }
    const result = await debugMcpTool(serverId, selectedTool.value.name, args)
    debugResult.value = result
    // 加入历史（最多 5 条）
    history.value.unshift({
      tool: selectedTool.value.name,
      result: result.result,
      elapsed_ms: result.elapsed_ms,
    })
    if (history.value.length > 5) {
      history.value = history.value.slice(0, 5)
    }
  } catch {
    // interceptor handled
  } finally {
    debugging.value = false
  }
}

const formatResult = (text: string): string => {
  try {
    return JSON.stringify(JSON.parse(text), null, 2)
  } catch {
    return text
  }
}

// 从工具列表 Tab 切到调试 Tab 时自动选中第一个（如果未选）
watch(activeTab, (tab) => {
  if (tab === 'debug' && !selectedTool.value && tools.value.length) {
    selectTool(tools.value[0])
  }
})
</script>

<style scoped>
.mcp-detail {
  max-width: 1200px;
}

/* ── 页面顶部 ─────────────────────────────────────────── */
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 20px;
}

.page-header-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.page-header-right {
  display: flex;
  align-items: center;
  padding-top: 28px;
}

.btn-back {
  color: var(--text-secondary) !important;
  font-size: var(--text-sm);
  padding: 0 0 4px 0;
  margin-bottom: 4px;
}

.btn-back:hover {
  color: var(--color-brand-500) !important;
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
  font-family: var(--font-mono);
}

/* ── Tabs ─────────────────────────────────────────────── */
.detail-tabs {
  background: var(--bg-surface);
  border-radius: var(--radius-xl);
  padding: 20px;
  border: 1px solid var(--border-default);
  box-shadow: var(--shadow-sm);
}

.detail-tabs :deep(.el-tabs__header) {
  margin-bottom: 20px;
}

/* ── 工具列表 Tab ─────────────────────────────────────── */
.tab-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.tool-count-label {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.tool-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}

.tool-card {
  background: var(--bg-elevated);
  border-radius: var(--radius-md);
  padding: 14px 16px;
  border: 1px solid var(--border-default);
  cursor: pointer;
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.tool-card:hover {
  border-color: var(--color-brand-300);
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.12);
}

.tool-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.tool-card-name {
  font-weight: 600;
  font-size: var(--text-sm);
  color: var(--color-brand-600);
  font-family: var(--font-mono);
}

.tool-card-arrow {
  color: var(--text-tertiary);
  font-size: 14px;
}

.tool-card-desc {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* ── 调试 Tab ─────────────────────────────────────────── */
.debug-layout {
  display: flex;
  gap: 20px;
  min-height: 400px;
}

.debug-sidebar {
  width: 220px;
  min-width: 220px;
  border-right: 1px solid var(--border-default);
  padding-right: 16px;
}

.debug-sidebar-title {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 10px;
}

.debug-tool-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.debug-tool-item {
  padding: 8px 12px;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background var(--transition-fast), color var(--transition-fast);
  font-size: var(--text-sm);
  color: var(--text-primary);
}

.debug-tool-item:hover {
  background: var(--bg-elevated);
}

.debug-tool-item.active {
  background: var(--color-brand-100);
  color: var(--color-brand-600);
  font-weight: 600;
}

.debug-tool-name {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
}

.debug-main {
  flex: 1;
  min-width: 0;
}

.debug-tool-desc {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  line-height: 1.6;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border-default);
}

.debug-form {
  margin-bottom: 20px;
}

.debug-form-title {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 12px;
}

.no-params {
  font-size: var(--text-sm);
  color: var(--text-tertiary);
}

/* ── 调试结果 ─────────────────────────────────────────── */
.debug-result {
  margin-bottom: 20px;
}

.debug-result-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.debug-result-label {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-primary);
}

.debug-result-content {
  background: var(--bg-elevated);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: 14px 16px;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  line-height: 1.6;
  color: var(--text-primary);
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 300px;
  overflow-y: auto;
  margin: 0;
}

/* ── 历史记录 ─────────────────────────────────────────── */
.debug-history {
  border-top: 1px solid var(--border-default);
  padding-top: 16px;
}

.debug-history-title {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 10px;
}

.debug-history-item {
  background: var(--bg-elevated);
  border-radius: var(--radius-md);
  padding: 10px 14px;
  border: 1px solid var(--border-default);
  margin-bottom: 8px;
}

.history-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.history-tool {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--color-brand-600);
}

.history-time {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

.history-content {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  line-height: 1.5;
  color: var(--text-secondary);
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 120px;
  overflow-y: auto;
  margin: 0;
}

/* ── 占位 ─────────────────────────────────────────────── */
.debug-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  gap: 12px;
  color: var(--text-tertiary);
}

.debug-placeholder p {
  font-size: var(--text-sm);
  margin: 0;
}
</style>
