<template>
  <div class="chat-view">
    <div class="chat-layout">
      <!-- 左侧：会话列表 -->
      <aside class="chat-sidebar">
        <div class="sidebar-header">
          <div class="agent-select-label">选择 Agent</div>
          <el-select
            v-model="selectedAgentId"
            placeholder="请选择一个 Agent"
            style="width: 100%; margin-bottom: 12px;"
            @change="handleAgentChange"
          >
            <el-option
              v-for="agent in availableAgents"
              :key="agent.id"
              :value="agent.id"
              :label="agent.name"
            >
              <div class="agent-option">
                <div class="agent-option-name">{{ agent.name }}</div>
                <div v-if="agent.description" class="agent-option-desc">{{ agent.description }}</div>
              </div>
            </el-option>
          </el-select>
          <el-button type="primary" class="new-chat-btn" @click="createNewConversation" :disabled="!selectedAgentId">
            <el-icon><Plus /></el-icon>
            新建对话
          </el-button>
        </div>
        <div class="conversation-list">
          <div
            v-for="conv in conversations"
            :key="conv.id"
            class="conversation-item"
            :class="{ active: currentConversationId === conv.id }"
            @click="selectConversation(conv.id)"
          >
            <div class="conv-main">
              <div class="conv-title">{{ conv.title }}</div>
              <div class="conv-preview">{{ conv.lastMessage || '暂无消息' }}</div>
            </div>
            <div
              class="delete-btn"
              @click.stop="deleteConversation(conv.id)"
            >
              <el-icon><Delete /></el-icon>
            </div>
          </div>
        </div>
      </aside>

      <!-- 右侧：聊天区域 -->
      <main class="chat-main">
        <!-- 消息区域 -->
        <div class="messages-container" ref="messagesContainerRef" @scroll="handleScroll">
          <div v-if="messages.length === 0" class="empty-state">
            <el-icon class="empty-icon"><ChatDotRound /></el-icon>
            <div class="empty-text">开始一段对话吧</div>
          </div>
          <div v-else class="messages-list">
            <div
              v-for="msg in messages"
              :key="msg.id"
              class="message-item"
              :class="msg.role"
            >
              <div class="message-avatar">
                <el-icon v-if="msg.role === 'user'"><User /></el-icon>
                <el-icon v-else><Promotion /></el-icon>
              </div>
              <div class="message-content">
                <div class="message-bubble" v-html="renderMarkdown(msg.content)"></div>
              </div>
            </div>

            <!-- AI 正在输入状态 -->
            <div v-if="isAiTyping" class="message-item assistant">
              <div class="message-avatar">
                <el-icon><Promotion /></el-icon>
              </div>
              <div class="message-content">
                <div class="message-bubble">
                  <span v-if="aiResponseContent">{{ aiResponseContent }}</span>
                  <span v-else class="typing-indicator">
                    <span class="dot"></span>
                    <span class="dot"></span>
                    <span class="dot"></span>
                  </span>
                </div>
              </div>
            </div>

            <!-- 错误提示 -->
            <div v-if="errorMessage" class="message-item assistant">
              <div class="message-avatar">
                <el-icon><Promotion /></el-icon>
              </div>
              <div class="message-content">
                <div class="message-bubble error">{{ errorMessage }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 输入区域 -->
        <div class="input-area">
          <div class="input-wrapper">
            <el-input
              v-model="inputContent"
              type="textarea"
              :rows="3"
              :disabled="isSending"
              placeholder="输入消息... (Enter 发送，Shift+Enter 换行)"
              @keydown="handleKeyDown"
              resize="none"
            />
            <div class="input-actions">
              <el-button type="primary" :loading="isSending" :disabled="!inputContent.trim() || !currentConversationId" @click="sendMessage">
                <el-icon><Promotion /></el-icon>
                发送
              </el-button>
            </div>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import { Plus, ChatDotRound, User, Promotion, Delete } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { marked } from 'marked'
import axios from 'axios'
import {
  getConversationList,
  createConversation,
  getConversationMessages,
  sendMessageStream,
  type Conversation,
  type Message,
} from '@/api/conversation'
import { getAgentList } from '@/api/agent'

// 状态
const conversations = ref<Conversation[]>([])
const messages = ref<Message[]>([])
const currentConversationId = ref<number | null>(null)
const currentAgentId = ref<number | null>(null)
const selectedAgentId = ref<number | null>(null)
const inputContent = ref('')
const isSending = ref(false)
const isAiTyping = ref(false)
const aiResponseContent = ref('')
const errorMessage = ref<string | null>(null)
const shouldAutoScroll = ref(true)
const availableAgents = ref<any[]>([]) // 可用的 agent 列表

const messagesContainerRef = ref<HTMLElement | null>(null)

// 初始化
onMounted(async () => {
  await loadAgents()
  if (availableAgents.value.length > 0) {
    selectedAgentId.value = availableAgents.value[0].id
  }
  await loadConversations()
  if (conversations.value.length > 0) {
    selectConversation(conversations.value[0].id)
  }
})

// Agent 变化时，更新当前选中的 Agent
function handleAgentChange() {
  // 可以在这里添加一些逻辑
}

// 加载可用的 agent 列表
async function loadAgents() {
  try {
    const res = await getAgentList({ page: 1, page_size: 100 })
    // 确保 id 是 number 类型
    availableAgents.value = (res.list || []).map((agent: any) => ({
      ...agent,
      id: Number(agent.id)
    }))
  } catch (e) {
    console.error('加载 agent 列表失败', e)
    ElMessage.error('请先创建一个 Agent')
  }
}

// Markdown 渲染
function renderMarkdown(content: string): string {
  if (!content) return ''
  return marked(content, { breaks: true, gfm: true }) as string
}

// 加载会话列表，同时转换后端字段名
async function loadConversations() {
  try {
    const res = await getConversationList({ page: 1, page_size: 100 })
    // 转换后端 snake_case 字段，并确保 id 是 number 类型
    conversations.value = (res.list || []).map((item: any) => ({
      id: Number(item.id),
      agent_id: Number(item.agent_id),
      title: item.title,
      status: item.status,
      createdAt: item.created_at,
      updatedAt: item.updated_at,
      lastMessage: item.last_message || '',
    }))
  } catch (e) {
    console.error('加载会话列表失败', e)
  }
}

// 创建新会话
async function createNewConversation() {
  if (!selectedAgentId.value) {
    ElMessage.error('请先选择一个 Agent')
    return
  }

  try {
    const conv = await createConversation(Number(selectedAgentId.value))
    // 转换字段
    const formattedConv: Conversation = {
      id: Number(conv.id),
      agent_id: Number(conv.agent_id),
      title: conv.title,
      status: conv.status,
      createdAt: conv.created_at || '',
      updatedAt: conv.updated_at || '',
      lastMessage: conv.last_message || '',
    }
    conversations.value.unshift(formattedConv)
    currentConversationId.value = formattedConv.id
    currentAgentId.value = selectedAgentId.value
    messages.value = []
    errorMessage.value = null
  } catch (e) {
    ElMessage.error('创建对话失败')
    console.error(e)
  }
}

// 选择会话
async function selectConversation(id: number) {
  if (currentConversationId.value === id) return

  // 找到选中的会话，设置对应的 agent_id
  const conv = conversations.value.find(c => c.id === id)
  if (conv) {
    currentAgentId.value = Number(conv.agent_id)
    selectedAgentId.value = Number(conv.agent_id)
  }

  currentConversationId.value = id
  errorMessage.value = null
  aiResponseContent.value = ''
  isAiTyping.value = false

  try {
    const msgs = await getConversationMessages(id)
    messages.value = msgs || []
    await nextTick()
    scrollToBottom()
  } catch (e) {
    console.error('加载消息失败', e)
    messages.value = []
  }
}

// 删除对话
async function deleteConversation(id: number) {
  try {
    console.log('准备删除对话，ID:', id)
    await ElMessageBox.confirm(
      '确定要删除这个对话吗？删除后无法恢复。',
      '删除对话',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'el-button--danger'
      }
    )

    console.log('调用删除 API')
    // 直接调用 axios 来避免拦截器的问题
    const response = await axios.delete(`/api/v1/conversations/${id}`)
    console.log('删除 API 响应:', response)

    // 不管返回什么，只要不是网络错误就认为成功
    ElMessage.success('删除成功')

    const wasSelected = currentConversationId.value === id

    // 刷新列表
    console.log('刷新对话列表')
    await loadConversations()

    // 如果删的是当前对话，自动选第一个（或清空）
    if (wasSelected) {
      if (conversations.value.length > 0) {
        selectConversation(conversations.value[0].id)
      } else {
        currentConversationId.value = null
        messages.value = []
      }
    }
  } catch (e) {
    console.log('删除出错:', e)
    if (e !== 'cancel') {
      // 检查错误响应，如果是状态码 200 也认为成功
      const error = e as any
      if (error?.response?.status === 200 || error?.code === 200) {
        ElMessage.success('删除成功')
        await loadConversations()
        return
      }
      console.error('删除失败', e)
      ElMessage.error('删除失败: ' + (error?.message || error?.response?.data?.message || '未知错误'))
    }
  }
}

// 发送消息
async function sendMessage() {
  const content = inputContent.value.trim()
  if (!content || isSending.value) return
  if (!currentConversationId.value) {
    ElMessage.warning('请先选择或创建一个对话')
    return
  }

  // 1. 清空输入框，禁用发送按钮
  inputContent.value = ''
  isSending.value = true
  errorMessage.value = null

  // 2. 立即添加用户消息到界面
  const userMessage: Message = {
    id: Date.now(), // 临时ID
    conversationId: currentConversationId.value,
    role: 'user',
    content,
    finishReason: '',
    latencyMs: 0,
    createdAt: new Date().toISOString(),
  }
  messages.value.push(userMessage)

  // 3. 显示 AI 加载状态
  isAiTyping.value = true
  aiResponseContent.value = ''
  await nextTick()
  scrollToBottom()

  // 4. 流式接收 AI 响应
  let fullResponse = ''

  try {
    await sendMessageStream(
      currentConversationId.value,
      { content, stream: true },
      (event) => {
        if (event.type === 'delta') {
          fullResponse += event.content
          aiResponseContent.value = fullResponse
          if (shouldAutoScroll.value) {
            scrollToBottom()
          }
        } else if (event.type === 'done') {
          finishAiResponse(fullResponse)
        } else if (event.type === 'error') {
          handleAiError(event.content || '请求出错')
        }
      },
      (error) => {
        handleAiError(error.message || '网络请求失败')
      }
    )
  } catch (e) {
    handleAiError('请求失败')
  }
}

function finishAiResponse(content: string) {
  if (currentConversationId.value) {
    const aiMessage: Message = {
      id: Date.now() + 1,
      conversationId: currentConversationId.value,
      role: 'assistant',
      content,
      finishReason: 'stop',
      latencyMs: 0,
      createdAt: new Date().toISOString(),
    }
    messages.value.push(aiMessage)
  }

  isAiTyping.value = false
  isSending.value = false
  aiResponseContent.value = ''

  // 刷新会话列表以更新 lastMessage
  loadConversations()

  nextTick(scrollToBottom)
}

function handleAiError(message: string) {
  errorMessage.value = message
  isAiTyping.value = false
  isSending.value = false
  nextTick(scrollToBottom)
}

// 键盘事件
function handleKeyDown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

// 滚动控制
function handleScroll(e: Event) {
  const container = e.target as HTMLElement
  const { scrollTop, clientHeight, scrollHeight } = container
  shouldAutoScroll.value = scrollTop + clientHeight >= scrollHeight - 100
}

function scrollToBottom() {
  if (messagesContainerRef.value) {
    const container = messagesContainerRef.value
    container.scrollTop = container.scrollHeight
  }
}
</script>

<style scoped>
.chat-view {
  height: 100%;
  padding: 0;
}

.chat-layout {
  display: flex;
  height: calc(100vh - 56px);
  margin: -24px;
}

/* 左侧会话列表 */
.chat-sidebar {
  width: 280px;
  min-width: 280px;
  background: var(--bg-surface);
  border-right: 1px solid var(--border-default);
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid var(--border-subtle);
}

.agent-select-label {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-bottom: 6px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.agent-option {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.agent-option-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.agent-option-desc {
  font-size: 12px;
  color: var(--text-tertiary);
}

.new-chat-btn {
  width: 100%;
}

.conversation-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.conversation-item {
  padding: 10px 12px;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background var(--transition-fast);
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.conversation-item:hover {
  background: var(--bg-elevated);
}

.conversation-item:hover .delete-btn {
  opacity: 1;
}

.conversation-item.active {
  background: var(--color-brand-50);
  border: 1px solid var(--color-brand-200);
}

.conv-main {
  flex: 1;
  min-width: 0;
}

.conv-title {
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.conv-preview {
  font-size: 11px;
  color: var(--text-tertiary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.delete-btn {
  opacity: 0;
  padding: 4px;
  transition: opacity var(--transition-fast);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  cursor: pointer;
  color: var(--color-danger);
}

.delete-btn:hover {
  background: rgba(239, 68, 68, 0.1);
}

/* 右侧聊天区 */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: var(--bg-base);
}

/* 消息区域 */
.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-tertiary);
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.5;
}

.empty-text {
  font-size: var(--text-lg);
}

.messages-list {
  max-width: 900px;
  margin: 0 auto;
}

/* 消息项 */
.message-item {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.message-item.user {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.message-item.user .message-avatar {
  background: var(--color-brand-500);
  color: white;
}

.message-item.assistant .message-avatar {
  background: var(--bg-elevated);
  color: var(--color-brand-500);
}

.message-content {
  max-width: 70%;
}

.message-bubble {
  padding: 12px 16px;
  border-radius: var(--radius-lg);
  font-size: var(--text-base);
  line-height: 1.6;
  word-wrap: break-word;
}

.message-item.user .message-bubble {
  background: var(--bg-sidebar);
  color: var(--text-inverse);
}

.message-item.assistant .message-bubble {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  color: var(--text-primary);
}

.message-bubble.error {
  color: var(--color-danger);
  border-color: var(--color-danger);
  background: #fef2f2;
}

/* Markdown 内容样式 */
.message-bubble :deep(p) {
  margin-bottom: 8px;
}
.message-bubble :deep(p:last-child) {
  margin-bottom: 0;
}
.message-bubble :deep(code) {
  background: rgba(0, 0, 0, 0.05);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: var(--font-mono);
  font-size: 0.9em;
}
.message-item.user .message-bubble :deep(code) {
  background: rgba(255, 255, 255, 0.15);
}
.message-bubble :deep(pre) {
  background: rgba(0, 0, 0, 0.05);
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 8px 0;
}
.message-item.user .message-bubble :deep(pre) {
  background: rgba(255, 255, 255, 0.1);
}
.message-bubble :deep(pre code) {
  background: transparent;
  padding: 0;
}
.message-bubble :deep(ul), .message-bubble :deep(ol) {
  margin: 8px 0;
  padding-left: 20px;
}
.message-bubble :deep(li) {
  margin-bottom: 4px;
}

/* 输入动画 */
.typing-indicator {
  display: inline-flex;
  gap: 4px;
  padding: 4px 0;
}

.typing-indicator .dot {
  width: 8px;
  height: 8px;
  background: var(--text-tertiary);
  border-radius: 50%;
  animation: typing 1.4s infinite ease-in-out;
}

.typing-indicator .dot:nth-child(1) { animation-delay: 0s; }
.typing-indicator .dot:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator .dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing {
  0%, 80%, 100% { transform: scale(0.8); opacity: 0.5; }
  40% { transform: scale(1); opacity: 1; }
}

/* 输入区域 */
.input-area {
  padding: 16px 24px 24px;
  background: var(--bg-surface);
  border-top: 1px solid var(--border-default);
}

.input-wrapper {
  max-width: 900px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.input-actions {
  display: flex;
  justify-content: flex-end;
}
</style>
