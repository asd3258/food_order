<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const activeTab = computed(() => {
  const name = String(route.name || '')
  if (['home', 'orderDetail', 'voteDetail'].includes(name)) return 'home'
  if (['restaurantList', 'restaurantMenu', 'editRestaurant'].includes(name)) return 'list'
  if (name === 'orderVote') return 'vote'
  if (['more', 'history', 'createRestaurant'].includes(name)) return 'more'
  return ''
})
</script>

<template>
  <nav class="bottomnav">
    <router-link to="/" :class="{ active: activeTab === 'home' }"><span class="ic">🏠</span>首頁</router-link>
    <router-link to="/restaurants" :class="{ active: activeTab === 'list' }"><span class="ic">📋</span>餐廳清單</router-link>
    <router-link to="/order-vote" :class="{ active: activeTab === 'vote' }"><span class="ic">🗳️</span>開單與投票</router-link>
    <router-link to="/more" :class="{ active: activeTab === 'more' }"><span class="ic">⋯</span>其他功能</router-link>
  </nav>
</template>
