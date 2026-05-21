<template>
  <div class="kb-view">
    <!-- 页面顶部 -->
    <div class="page-header">
      <div class="page-header-left">
        <h1 class="page-title">知识库管理</h1>
        <p class="page-desc">管理知识库与文档，为 Agent 提供 RAG 检索能力</p>
      </div>
      <el-button type="primary" class="btn-add" @click="handleAdd">
        <el-icon><Plus /></el-icon>
        新建知识库
      </el-button>
    </div>

    <!-- 搜索栏 -->
    <div class="search-bar">
      <el-input
        v-model="searchName"
        placeholder="搜索知识库名称"
        clearable
        prefix-icon="Search"
        style="width: 280px"
        @clear="handleSearch"
        @keyup.enter="handleSearch"
      />
      <el-button type="primary" plain @click="handleSearch">搜索</el-button>
    </div>

    <!-- 表格 -->
    <div class="table-wrapper">
      <HifyTable ref="tableRef" :api="fetchList" :immediate="true">
        <el-table-column prop="name" label="名称" min-width="180">
          <template #default="{ row }">
            <el-link type="primary" class="kb-name-link" @click="goDocuments(row)">
              {{ row.name }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="240">
          <template #default="{ row }">
            <span class="desc-text">{{ row.description || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="document_count" label="文档数量" width="110" align="center">
          <template #default="{ row }">
            <span class="doc-count">{{ row.document_count ?? 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170" />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button type="primary" text size="small" class="btn-edit" @click="handleEdit(row)">编辑</el-button>
              <el-button type="danger" text size="small" class="btn-delete" @click="handleDelete(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </HifyTable>
    </div>

    <!-- 新建/编辑弹窗 -->
    <HifyFormDialog
      ref="dialogRef"
      title="知识库"
      :rules="formRules"
      @submit="handleSubmit"
    >
      <template #default="{ formData: fd }">
        <el-form-item label="名称" prop="name">
          <el-input v-model="fd.name" placeholder="请输入知识库名称" maxlength="64" show-word-limit />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input
            v-model="fd.description"
            type="textarea"
            placeholder="请输入知识库描述（可选）"
            maxlength="256"
            show-word-limit
            :rows="3"
          />
        </el-form-item>
      </template>
    </HifyFormDialog>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Plus } from '@element-plus/icons-vue'
import HifyTable from '@/components/HifyTable.vue'
import HifyFormDialog from '@/components/HifyFormDialog.vue'
import { useConfirm } from '@/composables/useConfirm'
import { notifySuccess } from '@/utils/notify'
import {
  getKnowledgeBaseList,
  createKnowledgeBase,
  updateKnowledgeBase,
  deleteKnowledgeBase,
} from '@/api/knowledge'
import type { KnowledgeBase } from '@/types/model'
import type { PageResult, PageParams } from '@/types/api'

const router = useRouter()
const tableRef = ref()
const dialogRef = ref()
const editingKb = ref<KnowledgeBase | null>(null)
const searchName = ref('')

// ── 列表请求（带搜索） ─────────────────────────────────
const fetchList = (params: PageParams): Promise<PageResult<KnowledgeBase>> => {
  return getKnowledgeBaseList({ ...params, name: searchName.value || undefined })
}

const handleSearch = () => {
  tableRef.value?.refresh()
}

// ── 新建 / 编辑 ────────────────────────────────────────
const formRules = {
  name: [{ required: true, message: '请输入知识库名称', trigger: 'blur' }],
}

const handleAdd = () => {
  editingKb.value = null
  dialogRef.value.open()
}

const handleEdit = (row: KnowledgeBase) => {
  editingKb.value = row
  dialogRef.value.open({ name: row.name, description: row.description ?? '' })
}

const handleSubmit = async (formData: any) => {
  if (editingKb.value) {
    await updateKnowledgeBase(editingKb.value.id, formData)
    notifySuccess('更新成功')
  } else {
    await createKnowledgeBase(formData)
    notifySuccess('创建成功')
  }
  tableRef.value?.refresh()
}

// ── 删除 ────────────────────────────────────────────────
const handleDelete = (row: KnowledgeBase) => {
  const fn = useConfirm(
    `确认删除知识库「${row.name}」？其下所有文档将一并删除，无法恢复。`,
    async () => {
      await deleteKnowledgeBase(row.id)
      tableRef.value?.refresh()
    },
    '删除成功',
  )
  fn()
}

// ── 跳转文档管理 ────────────────────────────────────────
const goDocuments = (row: KnowledgeBase) => {
  router.push(`/knowledge-bases/${row.id}/documents`)
}
</script>

<style scoped>
.kb-view {
  max-width: 1200px;
}

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

/* ── 搜索栏 ──────────────────────────────────────────── */
.search-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
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

.kb-name-link {
  font-weight: 500;
  cursor: pointer;
}

.desc-text {
  color: var(--text-secondary);
  font-size: var(--text-sm);
}

.doc-count {
  font-family: var(--font-mono);
  font-weight: 500;
  color: var(--text-primary);
}

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

.table-wrapper :deep(.hify-table-pagination) {
  padding-top: 16px;
  margin-top: 16px;
  border-top: 1px solid var(--border-default);
}
</style>
