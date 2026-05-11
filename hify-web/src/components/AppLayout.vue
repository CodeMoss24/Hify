<template>
  <el-container class="app-container">
    <el-aside :width="collapsed ? '64px' : '200px'" class="app-aside">
      <div class="logo">{{ collapsed ? 'H' : 'Hify' }}</div>
      <el-menu
        :default-active="$route.name as string"
        :collapse="collapsed"
        router
        class="app-menu"
      >
        <el-menu-item index="/chat">
          <el-icon><ChatDotRound /></el-icon>
          <template #title>对话</template>
        </el-menu-item>
        <el-menu-item index="/providers">
          <el-icon><Connection /></el-icon>
          <template #title>模型</template>
        </el-menu-item>
        <el-menu-item index="/agents">
          <el-icon><User /></el-icon>
          <template #title>Agent</template>
        </el-menu-item>
        <el-menu-item index="/knowledge">
          <el-icon><Document /></el-icon>
          <template #title>知识库</template>
        </el-menu-item>
        <el-menu-item index="/workflows">
          <el-icon><Operation /></el-icon>
          <template #title>工作流</template>
        </el-menu-item>
        <el-menu-item index="/mcp">
          <el-icon><Box /></el-icon>
          <template #title>MCP</template>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="app-header">
        <el-icon class="collapse-btn" @click="toggleCollapsed"><Expand v-if="collapsed" /><Fold v-else /></el-icon>
        <div class="header-title">{{ $route.name }}</div>
      </el-header>
      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { useAppStore } from '@/stores/app'
import { ChatDotRound, Connection, User, Document, Operation, Box, Expand, Fold } from '@element-plus/icons-vue'
import { useRoute } from 'vue-router'

const store = useAppStore()
const $route = useRoute()
const { collapsed, toggleCollapsed } = store
</script>

<style scoped>
.app-container {
  height: 100%;
}

.app-aside {
  background: #304156;
  transition: width 0.3s;
  overflow: hidden;
}

.logo {
  height: 60px;
  line-height: 60px;
  text-align: center;
  color: #fff;
  font-size: 20px;
  font-weight: bold;
  background: #263445;
}

.app-menu {
  border-right: none;
  background: #304156;
}

.app-menu:not(.el-menu--collapse) {
  width: 200px;
}

:deep(.el-menu) {
  background: #304156;
}

:deep(.el-menu-item) {
  color: #bfcbd9;
}

:deep(.el-menu-item:hover),
:deep(.el-menu-item.is-active) {
  background: #263445;
  color: #409eff;
}

.app-header {
  display: flex;
  align-items: center;
  padding: 0 16px;
  background: #fff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
}

.collapse-btn {
  font-size: 20px;
  cursor: pointer;
  margin-right: 16px;
}

.header-title {
  font-size: 16px;
  font-weight: 500;
}

.app-main {
  background: #f5f7fa;
  padding: 16px;
}
</style>
