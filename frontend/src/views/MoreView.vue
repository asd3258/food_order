<script setup lang="ts">
import { userStore } from '../stores/user'
import { requireLogin } from '../auth'

// v0.11: 大字模式 -- 立即套用 + 存回帳號,下次登入(不管哪台裝置)直接沿用。
function setUiMode(mode: string) {
  if (!requireLogin()) return
  userStore.setUiMode(mode)
}
</script>

<template>
  <div class="page-header">
    <h1>其他功能</h1>
  </div>

  <div class="card">
    <div style="font-size:13px;color:var(--muted);margin-bottom:10px;">🔎 顯示模式(大字模式,圖示與文字都會放大)</div>
    <div class="btn-row">
      <button class="btn" :class="userStore.uiMode === 'large' ? 'btn-secondary' : 'btn-primary'" @click="setUiMode('normal')">標準模式</button>
      <button class="btn" :class="userStore.uiMode === 'large' ? 'btn-primary' : 'btn-secondary'" @click="setUiMode('large')">大字模式</button>
    </div>
  </div>

  <router-link to="/manage-account" class="card nav-card" style="text-decoration:none;color:inherit;display:flex;">
    <span class="nc-ic">👤</span><span class="nc-name">帳號管理</span><span class="chevron">›</span>
  </router-link>
  <router-link v-if="userStore.can('歷史訂單', 'read')" to="/history" class="card nav-card" style="text-decoration:none;color:inherit;display:flex;">
    <span class="nc-ic">🕘</span><span class="nc-name">歷史訂單</span><span class="chevron">›</span>
  </router-link>
  <router-link v-if="userStore.can('建立餐廳', 'create')" to="/create-restaurant" class="card nav-card" style="text-decoration:none;color:inherit;display:flex;">
    <span class="nc-ic">➕</span><span class="nc-name">建立餐廳</span><span class="chevron">›</span>
  </router-link>
  <!-- v0.7: 管理使用者 is admin-only now -- hidden entirely for regular users. -->
  <router-link v-if="userStore.isAdmin" to="/manage-users" class="card nav-card" style="text-decoration:none;color:inherit;display:flex;">
    <span class="nc-ic">👥</span><span class="nc-name">管理使用者</span><span class="chevron">›</span>
  </router-link>
  <router-link v-if="userStore.can('權限維護', 'read')" to="/permissions" class="card nav-card" style="text-decoration:none;color:inherit;display:flex;">
    <span class="nc-ic">🛡️</span><span class="nc-name">權限維護</span><span class="chevron">›</span>
  </router-link>
  <router-link v-if="userStore.isAdmin" to="/parameters" class="card nav-card" style="text-decoration:none;color:inherit;display:flex;">
    <span class="nc-ic">⚙️</span><span class="nc-name">參數維護</span><span class="chevron">›</span>
  </router-link>
</template>
