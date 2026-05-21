<template>
  <div class="doc-view">
    <!-- 页面顶部 -->
    <div class="page-header">
      <div class="page-header-left">
        <el-button text class="btn-back" @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          返回知识库
        </el-button>
        <h1 class="page-title">{{ kbName }}</h1>
      </div>
      <el-button type="primary" class="btn-add" @click="uploadVisible = true">
        <el-icon><Upload /></el-icon>
        上传文档
      </el-button>
    </div>

    <!-- 表格 -->
    <div class="table-wrapper">
      <HifyTable ref="tableRef" :api="fetchList" :immediate="true">
        <el-table-column prop="name" label="文件名" min-width="220" />
        <el-table-column prop="size" label="文件大小" width="120" align="center">
          <template #default="{ row }">
            {{ formatSize(row.size) }}
          </template>
        </el-table-column>
        <el-table-column prop="chunk_count" label="分块数量" width="110" align="center">
          <template #default="{ row }">
            <span class="chunk-count">{{ row.chunk_count || 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="130" align="center">
          <template #default="{ row }">
            <el-tag
              :type="statusTagType(row.status)"
              size="small"
              effect="plain"
              :class="{ 'is-loading': row.status === 'processing' }"
            >
              <el-icon v-if="row.status === 'processing'" class="status-loading-icon"><Loading /></el-icon>
              {{ statusLabel(row.status) }}
            </el-tag>
            <el-tooltip
              v-if="row.status === 'failed' && row.error_message"
              :content="row.error_message"
              placement="top"
            >
              <el-icon class="error-tip-icon"><WarningFilled /></el-icon>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170" />
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button type="primary" text size="small" class="btn-chunk" @click="handleViewChunks(row)">
                查看分块
              </el-button>
              <el-button
                type="danger"
                text
                size="small"
                class="btn-delete"
                :disabled="row.status === 'processing'"
                @click="handleDelete(row)"
              >
                删除
              </el-button>
            </div>
          </template>
        </el-table-column>
      </HifyTable>
    </div>

    <!-- 上传弹窗 -->
    <el-dialog v-model="uploadVisible" title="上传文档" width="520px" :close-on-click-modal="false" destroy-on-close>
      <el-upload
        ref="uploadRef"
        class="doc-upload"
        drag
        multiple
        :auto-upload="false"
        :limit="5"
        accept=".txt,.md,.pdf"
        :on-exceed="handleExceed"
        :on-change="handleFileChange"
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">拖拽文件到此处，或 <em>点击上传</em></div>
        <template #tip>
          <div class="el-upload__tip">
            支持 TXT、MD、PDF 格式，单文件不超过 10MB，最多 5 个文件
          </div>
        </template>
      </el-upload>
      <template #footer>
        <el-button @click="uploadVisible = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="handleUpload">确认上传</el-button>
      </template>
    </el-dialog>

    <!-- 查看分块弹窗 -->
    <el-dialog v-model="chunkVisible" title="文档分块" width="700px" destroy-on-close>
      <div v-loading="chunkLoading" class="chunk-list">
        <div v-if="!chunkLoading && chunks.length === 0" class="chunk-empty">暂无分块数据</div>
        <div v-for="chunk in chunks" :key="chunk.id" class="chunk-item">
          <div class="chunk-header">
            <el-tag size="small" effect="plain" type="info">分块 #{{ chunk.chunk_index }}</el-tag>
          </div>
          <div class="chunk-content">
            <template v-if="expandedChunks.has(chunk.id)">
              {{ chunk.content }}
              <el-button type="primary" text size="small" @click="toggleChunk(chunk.id)">收起</el-button>
            </template>
            <template v-else>
              {{ truncateContent(chunk.content) }}
              <el-button
                v-if="chunk.content.length > 200"
                type="primary"
                text
                size="small"
                @click="toggleChunk(chunk.id)"
              >
                展开
              </el-button>
            </template>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="chunkVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { UploadFile, UploadInstance, UploadRawFile } from 'element-plus'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Upload, UploadFilled, Loading, WarningFilled } from '@element-plus/icons-vue'
import HifyTable from '@/components/HifyTable.vue'
import { useConfirm } from '@/composables/useConfirm'
import { notifySuccess } from '@/utils/notify'
import {
  getDocumentList,
  uploadDocument,
  getDocument,
  getDocumentChunks,
  deleteDocument,
} from '@/api/knowledge'
import type { Document, DocumentChunk } from '@/types/model'
import type { PageResult, PageParams } from '@/types/api'

const route = useRoute()
const router = useRouter()
const kbId = Number(route.params.kbId)
const kbName = ref('知识库')
const tableRef = ref()

// ── 列表 ────────────────────────────────────────────────
const fetchList = (params: PageParams): Promise<PageResult<Document>> => {
  return getDocumentList(kbId, params)
}

const goBack = () => {
  router.push('/knowledge-bases')
}

// ── 状态显示 ────────────────────────────────────────────
const statusTagType = (status: string) => {
  switch (status) {
    case 'pending': return 'info'
    case 'processing': return ''
    case 'done': return 'success'
    case 'failed': return 'danger'
    default: return 'info'
  }
}

const statusLabel = (status: string) => {
  switch (status) {
    case 'pending': return '待处理'
    case 'processing': return '处理中'
    case 'done': return '已完成'
    case 'failed': return '失败'
    default: return status
  }
}

const formatSize = (bytes: number) => {
  if (bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return (bytes / Math.pow(1024, i)).toFixed(i > 0 ? 1 : 0) + ' ' + units[i]
}

// ── 上传 ────────────────────────────────────────────────
const uploadVisible = ref(false)
const uploading = ref(false)
const uploadRef = ref<UploadInstance>()
const pendingFiles = ref<UploadRawFile[]>([])

const handleFileChange = (file: UploadFile) => {
  if (!file.raw) return
  if (file.raw.size > 10 * 1024 * 1024) {
    ElMessage.warning(`文件「${file.name}」超过 10MB，已跳过`)
    uploadRef.value?.handleRemove(file)
    return
  }
  if (!pendingFiles.value.find(f => f.uid === file.raw!.uid)) {
    pendingFiles.value.push(file.raw)
  }
}

const handleExceed = () => {
  ElMessage.warning('最多同时上传 5 个文件')
}

const handleUpload = async () => {
  if (pendingFiles.value.length === 0) {
    ElMessage.warning('请选择要上传的文件')
    return
  }
  uploading.value = true
  let successCount = 0
  const pollingIds: number[] = []

  for (const file of pendingFiles.value) {
    try {
      const fd = new FormData()
      fd.append('file', file)
      const doc = await uploadDocument(kbId, fd)
      successCount++
      // 上传成功后开始轮询
      const pollId = startPolling(doc.id)
      if (pollId) pollingIds.push(pollId)
    } catch {
      // axios interceptor 已提示
    }
  }

  uploading.value = false
  uploadVisible.value = false
  pendingFiles.value = []
  uploadRef.value?.clearFiles()

  if (successCount > 0) {
    notifySuccess(`成功上传 ${successCount} 个文件`)
    tableRef.value?.refresh()
  }
}

// ── 轮询 ────────────────────────────────────────────────
const pollingTimers = new Map<number, ReturnType<typeof setInterval>>()

const startPolling = (docId: number): number | null => {
  if (pollingTimers.has(docId)) return null
  const timer = setInterval(async () => {
    try {
      const doc = await getDocument(docId)
      if (doc.status === 'done' || doc.status === 'failed') {
        stopPolling(docId)
        tableRef.value?.refresh()
      }
    } catch {
      stopPolling(docId)
    }
  }, 3000)
  pollingTimers.set(docId, timer)
  return docId
}

const stopPolling = (docId: number) => {
  const timer = pollingTimers.get(docId)
  if (timer) {
    clearInterval(timer)
    pollingTimers.delete(docId)
  }
}

const stopAllPolling = () => {
  for (const [id] of pollingTimers) {
    stopPolling(id)
  }
}

onUnmounted(() => {
  stopAllPolling()
})

// ── 删除 ────────────────────────────────────────────────
const handleDelete = (row: Document) => {
  const fn = useConfirm(
    `确认删除文档「${row.name}」？删除后无法恢复。`,
    async () => {
      await deleteDocument(row.id)
      tableRef.value?.refresh()
    },
    '删除成功',
  )
  fn()
}

// ── 查看分块 ────────────────────────────────────────────
const chunkVisible = ref(false)
const chunkLoading = ref(false)
const chunks = ref<DocumentChunk[]>([])
const expandedChunks = ref(new Set<number>())

const handleViewChunks = async (row: Document) => {
  chunkVisible.value = true
  chunkLoading.value = true
  chunks.value = []
  expandedChunks.value.clear()
  try {
    const res = await getDocumentChunks(row.id, { page: 1, page_size: 100 })
    chunks.value = res.list
  } catch {
    // axios interceptor 已提示
  } finally {
    chunkLoading.value = false
  }
}

const truncateContent = (text: string) => {
  return text.length > 200 ? text.slice(0, 200) + '...' : text
}

const toggleChunk = (id: number) => {
  if (expandedChunks.value.has(id)) {
    expandedChunks.value.delete(id)
  } else {
    expandedChunks.value.add(id)
  }
}

// ── 初始化：获取知识库名称 ─────────────────────────────
onMounted(async () => {
  try {
    const { getKnowledgeBaseList } = await import('@/api/knowledge')
    const res = await getKnowledgeBaseList({ page: 1, page_size: 1, name: undefined })
    // 从列表中找到对应的知识库
    const found = res.list?.find((kb: any) => kb.id === kbId)
    if (found) {
      kbName.value = found.name
    }
  } catch {
    // ignore
  }
})
</script>

<style scoped>
.doc-view {
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
  gap: 6px;
}

.btn-back {
  padding: 0;
  color: var(--text-secondary);
  font-size: var(--text-sm);
  margin-bottom: 2px;
}

.btn-back:hover {
  color: var(--color-brand-500);
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
  line-height: 1.3;
}

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

.chunk-count {
  font-family: var(--font-mono);
  font-weight: 500;
  color: var(--text-primary);
}

/* 状态 loading 动画 */
.status-loading-icon {
  animation: spin 1s linear infinite;
  margin-right: 4px;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}

/* failed 状态错误提示图标 */
.error-tip-icon {
  color: var(--color-danger);
  margin-left: 4px;
  cursor: help;
  font-size: 14px;
  vertical-align: middle;
}

.action-buttons {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-chunk {
  color: var(--color-brand-500) !important;
  font-weight: 500;
}

.btn-chunk:hover {
  color: var(--color-brand-700) !important;
}

.btn-delete {
  color: var(--color-danger) !important;
}

.btn-delete:hover {
  color: #c53030 !important;
}

.table-wrapper :deep(.hify-table-pagination) {
  padding-top: 16px;
  margin-top: 16px;
  border-top: 1px solid var(--border-default);
}

/* ── 上传弹窗 ────────────────────────────────────────── */
.doc-upload :deep(.el-upload-dragger) {
  border-radius: var(--radius-lg);
  padding: 30px 20px;
}

.doc-upload :deep(.el-upload) {
  width: 100%;
}

/* ── 分块弹窗 ────────────────────────────────────────── */
.chunk-list {
  max-height: 500px;
  overflow-y: auto;
}

.chunk-empty {
  text-align: center;
  color: var(--text-tertiary);
  padding: 40px 0;
  font-size: var(--text-sm);
}

.chunk-item {
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: 12px 16px;
  margin-bottom: 10px;
}

.chunk-item:last-child {
  margin-bottom: 0;
}

.chunk-header {
  margin-bottom: 8px;
}

.chunk-content {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
