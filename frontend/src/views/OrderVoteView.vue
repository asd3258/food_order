<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api, RESTAURANT_TYPES, type RestaurantSummary } from '../api'
import { HOURS, MINUTES, defaultDeadline, partsToIso, type DeadlineParts } from '../deadline'
import { userStore } from '../stores/user'
import { toast } from '../stores/toast'
import { requireLogin } from '../auth'

const router = useRouter()
const restaurants = ref<RestaurantSummary[]>([])
const q = ref('')
const activeType = ref<string | null>(null)
const selected = ref<Set<number>>(new Set())
const deadline = ref<DeadlineParts>(defaultDeadline())

async function load() {
  restaurants.value = await api.listRestaurants(q.value, activeType.value || undefined)
}
onMounted(load)
watch(q, load)

function toggleType(t: string) {
  activeType.value = activeType.value === t ? null : t
  load()
}

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

async function handleAction() {
  if (!requireLogin()) return
  const ids = Array.from(selected.value)
  const isoDeadline = partsToIso(deadline.value)
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
      <input v-model="q" type="text" placeholder="搜尋餐廳或品項名稱" />
    </div>
    <div class="type-filter-row">
      <span
        v-for="t in RESTAURANT_TYPES"
        :key="t"
        class="type-chip"
        :class="{ active: activeType === t }"
        @click="toggleType(t)"
      >{{ t }}</span>
    </div>

    <div v-if="restaurants.length === 0" class="empty">找不到符合的餐廳</div>
    <label v-else v-for="r in restaurants" :key="r.id" class="checkbox-item">
      <input type="checkbox" :checked="selected.has(r.id)" @change="toggle(r.id, ($event.target as HTMLInputElement).checked)" />
      <span class="cname">{{ r.name }} <span style="color:var(--muted);font-weight:400;font-size:11px;">({{ r.type }})</span></span>
    </label>

    <div class="deadline-row">
      <label>截止時間</label>
      <div class="deadline-inline" style="margin-bottom:0;">
        <input v-model="deadline.date" type="date" class="time-select" />
        <select v-model.number="deadline.hour" class="time-select">
          <option v-for="h in HOURS" :key="h" :value="h">{{ String(h).padStart(2, '0') }}</option>
        </select>
        <span>:</span>
        <select v-model.number="deadline.minute" class="time-select">
          <option v-for="m in MINUTES" :key="m" :value="m">{{ String(m).padStart(2, '0') }}</option>
        </select>
      </div>
    </div>

    <button class="btn btn-primary btn-full" :disabled="buttonDisabled" @click="handleAction">{{ buttonLabel }}</button>
  </section>
</template>
