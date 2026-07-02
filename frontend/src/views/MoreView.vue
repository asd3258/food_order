<script setup lang="ts">
import { userStore } from '../stores/user'
</script>

<template>
  <div class="page-header">
    <h1>其他功能</h1>
  </div>
  <router-link to="/history" class="card nav-card" style="text-decoration:none;color:inherit;display:flex;">
    <span class="nc-ic">🕘</span><span class="nc-name">歷史訂單</span><span class="chevron">›</span>
  </router-link>
  <router-link to="/create-restaurant" class="card nav-card" style="text-decoration:none;color:inherit;display:flex;">
    <span class="nc-ic">➕</span><span class="nc-name">建立餐廳</span><span class="chevron">›</span>
  </router-link>
  <!-- v0.7: 管理使用者 is admin-only now -- hidden entirely for regular users. -->
  <router-link v-if="userStore.isAdmin" to="/manage-users" class="card nav-card" style="text-decoration:none;color:inherit;display:flex;">
    <span class="nc-ic">👥</span><span class="nc-name">管理使用者</span><span class="chevron">›</span>
  </router-link>
</template>
