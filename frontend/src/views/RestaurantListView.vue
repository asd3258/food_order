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

async function load() {
  restaurants.value = await api.listRestaurants(
    restaurantListFilters.q, restaurantListFilters.typeFilter || undefined, restaurantListFilters.sort, userStore.username || undefined)
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
