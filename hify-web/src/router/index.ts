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
      component: () => import('@/views/ChatView.vue'),
    },
    {
      path: '/providers',
      name: 'Providers',
      component: () => import('@/views/ProvidersView.vue'),
    },
    {
      path: '/agents',
      name: 'Agents',
      component: () => import('@/views/AgentsView.vue'),
    },
    {
      path: '/knowledge',
      name: 'Knowledge',
      component: () => import('@/views/KnowledgeView.vue'),
    },
    {
      path: '/workflows',
      name: 'Workflows',
      component: () => import('@/views/WorkflowsView.vue'),
    },
    {
      path: '/mcp',
      name: 'Mcp',
      component: () => import('@/views/McpView.vue'),
    },
  ],
})

export default router
