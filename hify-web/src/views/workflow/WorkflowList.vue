<template>
  <div class="workflow-list">
    <!-- 页面顶部 -->
    <div class="page-header">
      <div class="page-header-left">
        <h1 class="page-title">工作流管理</h1>
        <p class="page-desc">通过 JSON 配置创建自动化工作流，支持线性执行与条件分支</p>
      </div>
      <el-button type="primary" class="btn-add" @click="router.push('/workflows/create')">
        <el-icon><Plus /></el-icon>
        新建工作流
      </el-button>
    </div>

    <!-- 表格 -->
    <div class="table-wrapper">
      <HifyTable ref="tableRef" :api="fetchList" :immediate="true">
        <el-table-column prop="name" label="名称" min-width="180">
          <template #default="{ row }">
            <span class="wf-name">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small" effect="plain">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170" />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button type="danger" text size="small" class="btn-delete" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </HifyTable>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Plus } from '@element-plus/icons-vue'
import HifyTable from '@/components/HifyTable.vue'
import { useConfirm } from '@/composables/useConfirm'
import { getWorkflowList, deleteWorkflow } from '@/api/workflow'
import type { Workflow } from '@/types/model'
import type { PageResult, PageParams } from '@/types/api'

const router = useRouter()
const tableRef = ref()

const fetchList = (params: PageParams): Promise<PageResult<Workflow>> => {
  return getWorkflowList(params)
}

const statusTagType = (status: string) => {
  return status === 'ACTIVE' ? 'success' : 'info'
}

const statusLabel = (status: string) => {
  return status === 'ACTIVE' ? '已激活' : '草稿'
}

const handleDelete = (row: Workflow) => {
  const fn = useConfirm(
    `确认删除工作流「${row.name}」？删除后无法恢复。`,
    async () => {
      await deleteWorkflow(row.id)
      tableRef.value?.refresh()
    },
    '删除成功',
  )
  fn()
}
</script>

<style scoped>
.workflow-list {
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

.wf-name {
  font-weight: 500;
  color: var(--text-primary);
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
