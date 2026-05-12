<template>
  <div class="provider-view">
    <el-alert v-if="status" :type="status === 'connected' ? 'success' : 'error'" :title="message" show-icon />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getHealth } from '@/api/health'

const status = ref<'connected' | 'disconnected' | ''>('')
const message = ref('')

onMounted(async () => {
  try {
    await getHealth()
    status.value = 'connected'
    message.value = '后端已连接：Hify is running'
  } catch {
    status.value = 'disconnected'
    message.value = '后端未连接'
  }
})
</script>
