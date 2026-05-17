<template>
  <el-dialog
    v-model="_visible"
    :title="dialogTitle"
    :width="width"
    :close-on-click-modal="false"
    destroy-on-close
  >
    <el-form
      ref="formRef"
      :model="formData"
      :rules="rules"
      :label-width="labelWidth"
      :disabled="submitting"
    >
      <slot :form-data="formData" :mode="editMode ? 'edit' : 'create'" />
    </el-form>

    <template #footer>
      <el-button @click="handleCancel" :disabled="submitting">取消</el-button>
      <el-button type="primary" @click="handleSubmit" :loading="submitting">
        {{ editMode ? '保存' : '创建' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts" generic="T extends Record<string, any>">
import { ref, computed, watch } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'

export interface HifyFormDialogProps {
  title: string
  width?: string | number
  rules?: FormRules
  labelWidth?: string | number
}

const props = withDefaults(defineProps<HifyFormDialogProps>(), {
  width: '520px',
  labelWidth: 120,
})

const emit = defineEmits<{
  (e: 'submit', data: T): Promise<void>
}>()

const formRef = ref<FormInstance>()
const formData = ref<Partial<T>>({})
const submitting = ref(false)
const _visible = ref(false)
const editData = ref<T | null>(null)

const dialogTitle = computed(() => {
  const base = editMode.value ? '编辑' : '新建'
  return `${base}${props.title}`
})

const editMode = computed(() => !!editData.value)

/**
 * 打开弹窗
 * @param data 传入则为编辑模式（回填表单），不传则为新增模式（清空表单）
 */
const open = (data?: T) => {
  editData.value = data ?? null
  if (data) {
    formData.value = { ...data }
  } else {
    formData.value = {}
  }
  _visible.value = true
}

const handleClose = () => {
  formRef.value?.resetFields()
  formData.value = {}
  editData.value = null
}

const handleCancel = () => {
  _visible.value = false
}

const handleSubmit = async () => {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
    submitting.value = true
    await emit('submit', formData.value as T)
    _visible.value = false
  } catch {
    // validation failed — keep dialog open
  } finally {
    submitting.value = false
  }
}

watch(_visible, (val) => {
  if (!val) handleClose()
})

defineExpose({ open })
</script>