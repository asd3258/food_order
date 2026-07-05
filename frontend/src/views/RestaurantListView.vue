<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api, type RestaurantSummary, type RestaurantType } from '../api'
import { userStore } from '../stores/user'
import { restaurantListFilters } from '../stores/filters'
import { requireLogin } from '../auth'

const router = useRouter()
const restaurants = ref<RestaurantSummary[]>([])
const types = ref<RestaurantType[]>([])

const DAYS_OF_WEEK = [
  { val: 0, label: '今天' },
  { val: 1, label: '一' },
  { val: 2, label: '二' },
  { val: 3, label: '三' },
  { val: 4, label: '四' },
  { val: 5, label: '五' },
  { val: 6, label: '六' },
  { val: 7, label: '日' }
]

function toggleDayFilter(val: number) {
  const arr = restaurantListFilters.daysFilter
  const today = new Date().getDay()
  const realVal = val === 0 ? today : (val === 7 ? 0 : val)
  
  const idx = arr.indexOf(realVal)
  if (idx !== -1) {
    arr.splice(idx, 1)
  } else {
    arr.push(realVal)
  }
  load()
}

function isDayFilterActive(val: number) {
  const today = new Date().getDay()
  const realVal = val === 0 ? today : (val === 7 ? 0 : val)
  return restaurantListFilters.daysFilter.includes(realVal)
}

async function load() {
  const daysStr = restaurantListFilters.daysFilter.length > 0 ? restaurantListFilters.daysFilter.join(',') : undefined
  restaurants.value = await api.listRestaurants(
    restaurantListFilters.q, restaurantListFilters.typeFilter || undefined, restaurantListFilters.sort, userStore.username || undefined, daysStr)
}
async function loadTypes() {
  try {
    types.value = await api.listRestaurantTypes()
  } catch {
    // keep the static fallback if the backend isn't reachable yet
  }
}

onMounted(load)
onMounted(loadTypes)

watch(() => restaurantListFilters.q, load)
watch(() => restaurantListFilters.typeFilter, load)

function setSort(s: 'star' | 'created_desc' | 'name') {
  restaurantListFilters.sort = s
  load()
}

function openMenu(id: number) {
  router.push(`/restaurants/${id}`)
}

// v0.12: ★常用 -- by user 記錄,點擊不導頁(card 本身可點進菜單頁)。
async function toggleFavorite(r: RestaurantSummary) {
  if (!requireLogin()) return
  if (r.is_favorite) {
    await api.removeFavorite(r.id, userStore.username)
    r.is_favorite = false
  } else {
    await api.addFavorite(r.id, userStore.username)
    r.is_favorite = true
  }
}
</script>

<template>
  <div class="page-header">
    <h1>餐廳清單</h1>
  </div>
  <div class="search-row">
    <input v-model="restaurantListFilters.q" type="text" placeholder="搜尋餐廳或品項名稱" />
  </div>
  <div class="type-filter-row">
    <span class="type-chip" :class="{ active: restaurantListFilters.typeFilter === '' }" @click="restaurantListFilters.typeFilter = ''">全部</span>
    <span v-for="t in types" :key="t.id" class="type-chip" :class="{ active: restaurantListFilters.typeFilter === t.name }" @click="restaurantListFilters.typeFilter = t.name">{{ t.name }}</span>
  </div>
  <div class="type-filter-row">
    <span v-for="d in DAYS_OF_WEEK" :key="d.val" class="type-chip" :class="{ active: isDayFilterActive(d.val) }" @click="toggleDayFilter(d.val)">
      {{ d.label }}
    </span>
  </div>
  <div class="type-filter-row">
    <span class="type-chip" :class="{ active: restaurantListFilters.sort === 'star' }" @click="setSort('star')">預設排序</span>
    <span class="type-chip" :class="{ active: restaurantListFilters.sort === 'name' }" @click="setSort('name')">名稱排序</span>
    <span class="type-chip" :class="{ active: restaurantListFilters.sort === 'created_desc' }" @click="setSort('created_desc')">建立時間(新到舊)</span>
  </div>

  <div v-if="restaurants.length === 0" class="empty">找不到符合的餐廳</div>
  <div v-else v-for="r in restaurants" :key="r.id" class="card card-clickable" style="align-items:center;" @click="openMenu(r.id)">
    <span class="fav-star" @click.stop="toggleFavorite(r)">{{ r.is_favorite ? '★' : '☆' }}</span>
    <div style="flex:1;">
      <div class="name">{{ r.name }}</div>
      <div class="sub">{{ r.type }} · {{ r.address }}</div>
    </div>
    <div class="chevron">›</div>
  </div>
</template>
