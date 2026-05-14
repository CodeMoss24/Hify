import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/chat',
    },
    {
      path: '/chat',
      name: 'Chat',
      component: () => import('@/views/chat/ChatView.vue'),
    },
    {
      path: '/providers',
      name: 'Providers',
      component: () => import('@/views/provider/ProviderView.vue'),
    },
    {
      path: '/agents',
      name: 'Agents',
      component: () => import('@/views/agent/AgentView.vue'),
    },
    {
      path: '/knowledge',
      name: 'Knowledge',
      component: () => import('@/views/knowledge/KnowledgeView.vue'),
    },
    {
      path: '/workflows',
      name: 'Workflows',
      component: () => import('@/views/workflow/WorkflowView.vue'),
    },
    {
      path: '/mcp',
      name: 'Mcp',
      component: () => import('@/views/mcp/McpView.vue'),
    },
  ],
})

export default router
