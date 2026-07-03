<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api, RESTAURANT_TYPES, type RestaurantSummary } from '../api'

const router = useRouter()
const restaurants = ref<RestaurantSummary[]>([])
const types = ref<string[]>(RESTAURANT_TYPES)
const q = ref('')
const activeType = ref<string | null>(null)
// v0.11: 取代手動拖曳排序 -- 固定兩個排序方式,"created_desc"(預設,建立時間新到
// 舊)或 "name"(名稱排序)。
const sort = ref<'created_desc' | 'name'>('created_desc')

async function load() {
  restaurants.value = await api.listRestaurants(q.value, activeType.value || undefined, sort.value)
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

function setSort(s: 'created_desc' | 'name') {
  sort.value = s
  load()
}

function openMenu(id: number) {
  router.push(`/restaurants/${id}`)
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
    <span class="type-chip" :class="{ active: sort === 'created_desc' }" @click="setSort('created_desc')">建立時間(新到舊)</span>
    <span class="type-chip" :class="{ active: sort === 'name' }" @click="setSort('name')">名稱排序</span>
  </div>

  <div v-if="restaurants.length === 0" class="empty">找不到符合的餐廳</div>
  <div v-else v-for="r in restaurants" :key="r.id" class="card card-clickable" style="align-items:center;" @click="openMenu(r.id)">
    <div>
      <div class="name">{{ r.name }}</div>
      <div class="sub">{{ r.type }} · {{ r.address }}</div>
    </div>
    <div class="chevron">›</div>
  </div>
</template>
