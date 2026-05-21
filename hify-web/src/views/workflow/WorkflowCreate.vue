<template>
  <div class="workflow-create">
    <!-- 页面顶部 -->
    <div class="page-header">
      <div class="page-header-left">
        <h1 class="page-title">新建工作流</h1>
        <p class="page-desc">通过 JSON 配置定义工作流的节点与连线</p>
      </div>
    </div>

    <!-- 表单 -->
    <div class="form-card">
      <el-form ref="formRef" :model="formData" :rules="formRules" label-width="100px" label-position="top">
        <el-form-item label="名称" prop="name">
          <el-input v-model="formData.name" placeholder="请输入工作流名称" maxlength="64" show-word-limit />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="formData.description" placeholder="请输入工作流描述（可选）" maxlength="256" show-word-limit />
        </el-form-item>
        <el-form-item label="工作流 JSON" prop="configJson">
          <el-input
            v-model="formData.configJson"
            type="textarea"
            :rows="20"
            placeholder="请输入工作流 JSON 配置"
            class="json-textarea"
          />
          <div class="json-actions">
            <el-button size="small" @click="formatJson">格式化</el-button>
          </div>
        </el-form-item>
        <el-form-item>
          <div class="form-actions">
            <el-button @click="router.push('/workflows')">取消</el-button>
            <el-button type="primary" :loading="submitting" @click="handleSubmit">创建</el-button>
          </div>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import type { FormInstance, FormRules } from 'element-plus'
import { notifySuccess, notifyError } from '@/utils/notify'
import { createWorkflow } from '@/api/workflow'

const router = useRouter()
const formRef = ref<FormInstance>()
const submitting = ref(false)

const PLACEHOLDER_JSON = JSON.stringify(
  {
    nodes: [
      { node_key: 'start', name: '开始', node_type: 'START', config: {}, position_x: 0, position_y: 0 },
      { node_key: 'llm', name: 'LLM 处理', node_type: 'LLM', config: { model_config_id: 1, prompt: '你好', output_variable: 'llm_output' }, position_x: 200, position_y: 0 },
      { node_key: 'end', name: '结束', node_type: 'END', config: {}, position_x: 400, position_y: 0 },
    ],
    edges: [
      { source_node_key: 'start', target_node_key: 'llm', condition: '' },
      { source_node_key: 'llm', target_node_key: 'end', condition: '' },
    ],
  },
  null,
  2,
)

const formData = reactive({
  name: '',
  description: '',
  configJson: PLACEHOLDER_JSON,
})

const formRules: FormRules = {
  name: [{ required: true, message: '请输入工作流名称', trigger: 'blur' }],
  configJson: [
    { required: true, message: '请输入工作流 JSON 配置', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (!value) return callback()
        try {
          JSON.parse(value)
          callback()
        } catch {
          callback(new Error('JSON 格式不合法，请检查后重试'))
        }
      },
      trigger: 'blur',
    },
  ],
}

const formatJson = () => {
  try {
    const parsed = JSON.parse(formData.configJson)
    formData.configJson = JSON.stringify(parsed, null, 2)
  } catch {
    notifyError('JSON 格式不合法，无法格式化')
  }
}

const handleSubmit = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  let parsed: any
  try {
    parsed = JSON.parse(formData.configJson)
  } catch {
    notifyError('JSON 格式不合法，请检查后重试')
    return
  }

  submitting.value = true
  try {
    await createWorkflow({
      name: formData.name,
      description: formData.description || '',
      nodes: parsed.nodes ?? [],
      edges: parsed.edges ?? [],
    })
    notifySuccess('创建成功')
    router.push('/workflows')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.workflow-create {
  max-width: 800px;
}

.page-header {
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

.form-card {
  background: var(--bg-surface);
  border-radius: var(--radius-xl);
  padding: 28px;
  border: 1px solid var(--border-default);
  box-shadow: var(--shadow-sm);
}

.json-textarea :deep(.el-textarea__inner) {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: 1.6;
}

.json-actions {
  margin-top: 8px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 8px;
}
</style>
