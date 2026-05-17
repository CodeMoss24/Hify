<template>
  <div class="app-wrapper">
    <!-- 侧边栏 -->
    <aside class="sidebar" :class="{ collapsed }">
      <!-- Logo 区 -->
      <div class="sidebar-logo">
        <div class="logo-icon">✦</div>
        <div v-if="!collapsed" class="logo-text">
          <span class="logo-name">Hify</span>
          <span class="logo-sub">AI Agent Platform</span>
        </div>
      </div>

      <!-- 菜单 -->
      <nav class="sidebar-nav">
        <div class="nav-section-title" v-if="!collapsed">导航</div>
        <router-link
          v-for="item in menuItems"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: isActive(item.path) }"
        >
          <el-icon class="nav-icon"><component :is="item.icon" /></el-icon>
          <span v-if="!collapsed" class="nav-label">{{ item.label }}</span>
          <span v-if="collapsed" class="nav-tooltip">{{ item.label }}</span>
        </router-link>
      </nav>

      <!-- 底部：折叠按钮 + 版本号 -->
      <div class="sidebar-footer">
        <button class="collapse-btn" @click="toggleCollapsed" :title="collapsed ? '展开' : '收起'">
          <el-icon><Expand v-if="collapsed" /><Fold v-else /></el-icon>
          <span v-if="!collapsed">收起</span>
        </button>
        <div v-if="!collapsed" class="version">v1.0.0</div>
      </div>
    </aside>

    <!-- 主内容区 -->
    <div class="main-wrapper">
      <!-- 顶栏 -->
      <header class="topbar">
        <div class="breadcrumb">
          <span class="breadcrumb-item">首页</span>
          <span class="breadcrumb-sep">/</span>
          <span class="breadcrumb-item current">{{ currentPageName }}</span>
        </div>
        <div class="user-info">
          <div class="user-avatar">
            <el-icon><UserFilled /></el-icon>
          </div>
          <span class="user-name">Admin</span>
        </div>
      </header>

      <!-- 内容区 -->
      <main class="content-area">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  ChatDotRound,
  Setting,
  User,
  Document,
  Share,
  Connection,
  Expand,
  Fold,
  UserFilled,
} from '@element-plus/icons-vue'

const collapsed = ref(false)
const route = useRoute()

const menuItems = [
  { path: '/chat',       label: '对话',       icon: ChatDotRound },
  { path: '/providers',  label: '模型管理',   icon: Setting },
  { path: '/agents',     label: 'Agent 管理',  icon: User },
  { path: '/knowledge', label: '知识库',     icon: Document },
  { path: '/workflows',  label: '工作流',     icon: Share },
  { path: '/mcp',        label: 'MCP',        icon: Connection },
]

const isActive = (path: string) => route.path.startsWith(path)

const currentPageName = computed(() => {
  const item = menuItems.find(m => route.path.startsWith(m.path))
  return item?.label ?? '首页'
})

const toggleCollapsed = () => { collapsed.value = !collapsed.value }
</script>

<style scoped>
/* ── 全局 wrapper ─────────────────────────────────────── */
.app-wrapper {
  display: flex;
  height: 100vh;
  overflow: hidden;
  font-family: var(--font-sans);
}

/* ── 侧边栏 ──────────────────────────────────────────── */
.sidebar {
  width: 240px;
  min-width: 240px;
  height: 100vh;
  background: var(--bg-sidebar);
  display: flex;
  flex-direction: column;
  transition: width var(--transition-normal), min-width var(--transition-normal);
  overflow: hidden;
  position: relative;
  z-index: 10;
}
.sidebar.collapsed {
  width: 64px;
  min-width: 64px;
}

/* Logo */
.sidebar-logo {
  height: 64px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  overflow: hidden;
}
.logo-icon {
  font-size: 22px;
  color: var(--color-brand-400);
  flex-shrink: 0;
  line-height: 1;
  filter: drop-shadow(0 0 8px rgba(99, 102, 241, 0.6));
}
.logo-text {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.logo-name {
  font-size: 18px;
  font-weight: 700;
  background: linear-gradient(135deg, #a5b4fc, #2dd4bf);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  line-height: 1.2;
  white-space: nowrap;
}
.logo-sub {
  font-size: 10px;
  color: var(--text-tertiary);
  white-space: nowrap;
  letter-spacing: 0.02em;
}

/* 导航 */
.sidebar-nav {
  flex: 1;
  padding: 12px 8px;
  overflow-y: auto;
  overflow-x: hidden;
}
.nav-section-title {
  font-size: var(--text-xs);
  font-weight: 600;
  color: rgba(255, 255, 255, 0.25);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 4px 12px 8px;
  white-space: nowrap;
}
.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  color: rgba(255, 255, 255, 0.55);
  font-size: var(--text-sm);
  font-weight: 450;
  text-decoration: none;
  cursor: pointer;
  transition: background var(--transition-fast), color var(--transition-fast);
  margin-bottom: 2px;
  white-space: nowrap;
  overflow: hidden;
}
.nav-item:hover {
  background: var(--bg-sidebar-hover);
  color: rgba(255, 255, 255, 0.9);
}
.nav-item.active {
  background: var(--bg-sidebar-active);
  color: #93c5fd;
}
.nav-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 60%;
  background: var(--color-brand-400);
  border-radius: 0 2px 2px 0;
  box-shadow: 0 0 8px rgba(99, 102, 241, 0.8);
}
.nav-icon {
  font-size: 16px;
  flex-shrink: 0;
  width: 20px;
}
.nav-label { flex: 1; }
.nav-tooltip {
  position: absolute;
  left: 64px;
  background: var(--bg-sidebar);
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: 6px 10px;
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  color: #fff;
  white-space: nowrap;
  z-index: 100;
  box-shadow: var(--shadow-lg);
}

/* 底部 */
.sidebar-footer {
  padding: 12px 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.collapse-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 8px 12px;
  background: transparent;
  border: none;
  border-radius: var(--radius-md);
  color: rgba(255, 255, 255, 0.4);
  font-size: var(--text-sm);
  cursor: pointer;
  transition: background var(--transition-fast), color var(--transition-fast);
}
.collapse-btn:hover {
  background: var(--bg-sidebar-hover);
  color: rgba(255, 255, 255, 0.8);
}
.version {
  text-align: center;
  font-size: var(--text-xs);
  color: rgba(255, 255, 255, 0.2);
  padding: 4px;
}

/* ── 主内容区 ─────────────────────────────────────────── */
.main-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--bg-base);
}

/* 顶栏 */
.topbar {
  height: 56px;
  min-height: 56px;
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-default);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  box-shadow: var(--shadow-xs);
  z-index: 5;
}
.breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--text-sm);
}
.breadcrumb-item { color: var(--text-tertiary); }
.breadcrumb-item.current { color: var(--text-primary); font-weight: 500; }
.breadcrumb-sep { color: var(--text-tertiary); }

.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
}
.user-avatar {
  width: 32px;
  height: 32px;
  background: var(--color-brand-100);
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-brand-600);
  font-size: 16px;
}
.user-name {
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--text-primary);
}

/* 内容区 */
.content-area {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}
</style>