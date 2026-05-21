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
      path: '/knowledge-bases',
      name: 'KnowledgeBases',
      component: () => import('@/views/knowledge/KnowledgeBaseList.vue'),
    },
    {
      path: '/knowledge-bases/:kbId/documents',
      name: 'KnowledgeBaseDocuments',
      component: () => import('@/views/knowledge/DocumentList.vue'),
    },
    {
      path: '/workflows',
      name: 'Workflows',
      component: () => import('@/views/workflow/WorkflowList.vue'),
    },
    {
      path: '/workflows/create',
      name: 'WorkflowCreate',
      component: () => import('@/views/workflow/WorkflowCreate.vue'),
    },
    {
      path: '/mcp',
      name: 'Mcp',
      component: () => import('@/views/mcp/McpView.vue'),
    },
    {
      path: '/mcp/:id',
      name: 'McpDetail',
      component: () => import('@/views/mcp/McpDetailView.vue'),
    },
  ],
})

export default router
