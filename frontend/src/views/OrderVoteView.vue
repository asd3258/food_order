<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api, type RestaurantSummary, type RestaurantType } from '../api'
import { HOURS, MINUTES, defaultDeadline, partsToIso, type DeadlineParts } from '../deadline'
import { userStore } from '../stores/user'
import { orderVoteFilters } from '../stores/filters'
import { toast } from '../stores/toast'
import { alertWarning } from '../stores/confirm'
import { requireLogin } from '../auth'

const router = useRouter()
const restaurants = ref<RestaurantSummary[]>([])
const types = ref<RestaurantType[]>([])
const selected = ref<Set<number>>(new Set())
const deadline = ref<DeadlineParts>(defaultDeadline())

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
  const arr = orderVoteFilters.daysFilter
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
  return orderVoteFilters.daysFilter.includes(realVal)
}

async function load() {
  // v0.12: 開單與投票一律依「★常用優先,再依名稱」排序,不管有沒有搜尋/篩選都
  // 套用同一套邏輯(不像餐廳清單有排序按鈕可以切換)。
  const daysStr = orderVoteFilters.daysFilter.length > 0 ? orderVoteFilters.daysFilter.join(',') : undefined
  restaurants.value = await api.listRestaurants(
    orderVoteFilters.q, orderVoteFilters.typeFilter || undefined, 'star', userStore.username || undefined, daysStr)
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
watch(() => orderVoteFilters.q, load)
watch(() => orderVoteFilters.typeFilter, load)

function toggle(id: number, checked: boolean) {
  const s = new Set(selected.value)
  if (checked) s.add(id)
  else s.delete(id)
  selected.value = s
}

const buttonLabel = computed(() => {
  const n = selected.value.size
  if (n === 0) return '請選擇餐廳'
  if (n === 1) return '立即開出訂單'
  return '進行餐廳投票'
})
const buttonDisabled = computed(() => selected.value.size === 0)

const attemptedSubmit = ref(false)
const isDeadlineInvalid = computed(() => {
  if (!attemptedSubmit.value) return false
  return new Date(partsToIso(deadline.value)).getTime() < Date.now()
})

async function handleAction() {
  if (!requireLogin()) return
  attemptedSubmit.value = true
  const ids = Array.from(selected.value)
  const isoDeadline = partsToIso(deadline.value)
  if (new Date(isoDeadline).getTime() < Date.now()) {
    await alertWarning('截止時間不能早於現在')
    return
  }
  if (ids.length === 1) {
    const order = await api.createOrder({ restaurant_id: ids[0], initiator: userStore.username, deadline_at: isoDeadline })
    toast('已開出訂單')
    router.push(`/orders/${order.id}`)
  } else if (ids.length > 1) {
    await api.createVote({ restaurant_ids: ids, initiator: userStore.username, deadline_at: isoDeadline })
    toast('已建立投票')
    router.push('/')
  }
}
</script>

<template>
  <div class="page-header">
    <h1>開單與投票</h1>
  </div>

  <section class="block">
    <h2>選擇餐廳</h2>
    <div class="search-row">
      <input v-model="orderVoteFilters.q" type="text" placeholder="搜尋餐廳或品項名稱" />
    </div>
    <div class="type-filter-row">
      <span class="type-chip" :class="{ active: orderVoteFilters.typeFilter === '' }" @click="orderVoteFilters.typeFilter = ''">全部</span>
      <span v-for="t in types" :key="t.id" class="type-chip" :class="{ active: orderVoteFilters.typeFilter === t.name }" @click="orderVoteFilters.typeFilter = t.name">{{ t.name }}</span>
    </div>
    <div class="type-filter-row">
      <span v-for="d in DAYS_OF_WEEK" :key="d.val" class="type-chip" :class="{ active: isDayFilterActive(d.val) }" @click="toggleDayFilter(d.val)">
        {{ d.label }}
      </span>
    </div>

    <div v-if="restaurants.length === 0" class="empty">找不到符合的餐廳</div>
    <label v-else v-for="r in restaurants" :key="r.id" class="checkbox-item">
      <input type="checkbox" :checked="selected.has(r.id)" @change="toggle(r.id, ($event.target as HTMLInputElement).checked)" />
      <span class="cname">{{ r.name }} <span style="color:var(--muted);font-weight:400;font-size:11px;">({{ r.type }})</span><span v-if="r.is_favorite" class="fav-star-static">★</span></span>
    </label>

    <div class="deadline-row">
      <label>截止時間</label>
      <div class="deadline-inline" style="margin-bottom:0;">
        <input v-model="deadline.date" type="date" class="time-select" :class="{ 'input-invalid': isDeadlineInvalid }" />
        <select v-model.number="deadline.hour" class="time-select" :class="{ 'input-invalid': isDeadlineInvalid }">
          <option v-for="h in HOURS" :key="h" :value="h">{{ String(h).padStart(2, '0') }}</option>
        </select>
        <span>:</span>
        <select v-model.number="deadline.minute" class="time-select" :class="{ 'input-invalid': isDeadlineInvalid }">
          <option v-for="m in MINUTES" :key="m" :value="m">{{ String(m).padStart(2, '0') }}</option>
        </select>
      </div>
    </div>

    <button v-if="userStore.can('開單與投票', 'create')" class="btn btn-primary btn-full" :disabled="buttonDisabled" @click="handleAction">{{ buttonLabel }}</button>
  </section>
</template>
