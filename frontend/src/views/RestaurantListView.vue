<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api, RESTAURANT_TYPES, type RestaurantSummary } from '../api'
import { userStore } from '../stores/user'
import { requireLogin } from '../auth'

const router = useRouter()
const restaurants = ref<RestaurantSummary[]>([])
const types = ref<string[]>(RESTAURANT_TYPES)
const q = ref('')
const activeType = ref<string | null>(null)
// v0.12: 新增 "star"(★常用優先,再依名稱)當預設排序,取代原本的 created_desc
// 預設;原本兩個排序("created_desc"/"name")邏輯不變,只是變成第 2、3 個選項。
const sort = ref<'star' | 'created_desc' | 'name'>('star')

async function load() {
  restaurants.value = await api.listRestaurants(
    q.value, activeType.value || undefined, sort.value, userStore.username || undefined)
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
watch(q, load)

function toggleType(t: string) {
  activeType.value = activeType.value === t ? null : t
  load()
}

function setSort(s: 'star' | 'created_desc' | 'name') {
  sort.value = s
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
    <input v-model="q" type="text" placeholder="搜尋餐廳或品項名稱" />
  </div>
  <div class="type-filter-row">
    <span
      v-for="t in types"
      :key="t"
      class="type-chip"
      :class="{ active: activeType === t }"
      @click="toggleType(t)"
    >{{ t }}</span>
  </div>
  <div class="type-filter-row">
    <span class="type-chip" :class="{ active: sort === 'star' }" @click="setSort('star')">預設排序</span>
    <span class="type-chip" :class="{ active: sort === 'name' }" @click="setSort('name')">名稱排序</span>
    <span class="type-chip" :class="{ active: sort === 'created_desc' }" @click="setSort('created_desc')">建立時間(新到舊)</span>
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
