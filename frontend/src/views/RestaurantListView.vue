<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api, RESTAURANT_TYPES, type RestaurantSummary } from '../api'

const router = useRouter()
const restaurants = ref<RestaurantSummary[]>([])
const types = ref<string[]>(RESTAURANT_TYPES)
const q = ref('')
const activeType = ref<string | null>(null)

async function load() {
  restaurants.value = await api.listRestaurants(q.value, activeType.value || undefined)
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

  <div v-if="restaurants.length === 0" class="empty">找不到符合的餐廳</div>
  <div v-else v-for="r in restaurants" :key="r.id" class="card card-clickable" @click="openMenu(r.id)">
    <div>
      <div class="name">{{ r.name }}</div>
      <div class="sub">{{ r.type }} · {{ r.address }}</div>
    </div>
    <div class="chevron">›</div>
  </div>
</template>
