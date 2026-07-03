<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api, RESTAURANT_TYPES, type RestaurantSummary } from '../api'
import { requireLogin } from '../auth'

const router = useRouter()
const restaurants = ref<RestaurantSummary[]>([])
const types = ref<string[]>(RESTAURANT_TYPES)
const q = ref('')
const activeType = ref<string | null>(null)

// v0.11: 手動排序只在「完整清單、沒有篩選」時才有意義 -- 搜尋/類型篩選出來的
// 只是子集,順序移動了也不代表真正的全域順序,所以篩選中就不顯示上下移動按鈕。
const canReorder = computed(() => !q.value.trim() && !activeType.value)

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

// v0.11: 手動排序 -- 在記憶體裡先交換兩筆,再把整個清單的新順序送回後端存成
// sort_order。只在 canReorder(無篩選)時會顯示按鈕,所以這裡送出的一定是完整清單。
async function move(index: number, dir: -1 | 1) {
  if (!requireLogin()) return
  const target = index + dir
  if (target < 0 || target >= restaurants.value.length) return
  const list = restaurants.value
  ;[list[index], list[target]] = [list[target], list[index]]
  await api.reorderRestaurants(list.map((r) => r.id))
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

  <div v-if="canReorder" class="empty" style="text-align:left;font-size:11px;padding:4px 2px;">
    可以用左邊的 ▲▼ 調整餐廳排列順序(搜尋或篩選類型時會先隱藏)
  </div>

  <div v-if="restaurants.length === 0" class="empty">找不到符合的餐廳</div>
  <div v-else v-for="(r, i) in restaurants" :key="r.id" class="card card-clickable" style="align-items:center;" @click="openMenu(r.id)">
    <div v-if="canReorder" style="display:flex;flex-direction:column;gap:2px;margin-right:10px;" @click.stop>
      <button :disabled="i === 0" style="width:26px;height:22px;padding:0;border-radius:6px;border:1px solid var(--border);background:#f5f5f5;font-size:11px;" @click="move(i, -1)">▲</button>
      <button :disabled="i === restaurants.length - 1" style="width:26px;height:22px;padding:0;border-radius:6px;border:1px solid var(--border);background:#f5f5f5;font-size:11px;" @click="move(i, 1)">▼</button>
    </div>
    <div>
      <div class="name">{{ r.name }}</div>
      <div class="sub">{{ r.type }} · {{ r.address }}</div>
    </div>
    <div class="chevron">›</div>
  </div>
</template>
