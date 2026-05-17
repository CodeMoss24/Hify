<template>
  <div class="hify-table">
    <el-table
      v-loading="loading"
      :data="tableData"
      stripe
      border
      :row-class-name="() => 'hify-table-row'"
      style="width: 100%"
    >
      <slot />
      <template #empty>
        <el-empty description="暂无数据" />
      </template>
    </el-table>

    <div v-if="showPagination" class="hify-table-pagination">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="currentPageSize"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        :background="true"
        layout="total, sizes, prev, pager, next"
        @current-change="handlePageChange"
        @size-change="handleSizeChange"
      />
    </div>
  </div>
</template>

<script setup lang="ts" generic="T extends Record<string, any>">
import { ref, onMounted, watch } from 'vue'
import type { PageResult, PageParams } from '@/types/api'

export interface HifyTableProps<T> {
  columns?: never
  api: (params: PageParams) => Promise<PageResult<T>>
  showPagination?: boolean
  immediate?: boolean
}

const props = withDefaults(defineProps<HifyTableProps<T>>(), {
  showPagination: true,
  immediate: true,
})

const emit = defineEmits<{
  (e: 'load', data: T[]): void
}>()

const loading = ref(false)
const tableData = ref<T[]>([])
const total = ref(0)
const currentPage = ref(1)
const currentPageSize = ref(20)

const loadData = async () => {
  if (!props.api) return
  loading.value = true
  try {
    const res = await props.api({ page: currentPage.value, page_size: currentPageSize.value })
    tableData.value = res.list
    total.value = res.total
    emit('load', res.list)
  } finally {
    loading.value = false
  }
}

const handlePageChange = () => loadData()
const handleSizeChange = () => {
  currentPage.value = 1
  loadData()
}

const refresh = () => {
  currentPage.value = 1
  return loadData()
}

defineExpose({ refresh })

onMounted(() => {
  if (props.immediate) loadData()
})
</script>

<style scoped>
.hify-table {
  width: 100%;
}

.hify-table :deep(.hify-table-row) {
  font-size: var(--text-sm);
}

.hify-table :deep(.el-table__empty-text) {
  padding: 40px 0;
  color: var(--text-tertiary);
}

.hify-table-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>