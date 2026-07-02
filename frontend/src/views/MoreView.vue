<script setup lang="ts">
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
  <router-link to="/manage-users" class="card nav-card" style="text-decoration:none;color:inherit;display:flex;">
    <span class="nc-ic">👥</span><span class="nc-name">管理使用者</span><span class="chevron">›</span>
  </router-link>
</template>
