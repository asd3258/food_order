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

async function load() {
  // v0.12: ???蟡其?敺???撣貊?芸?,???迂??摨?銝恣????撠?蝭拚??
  // 憟??憟?頛?銝?擗輒皜??摨??隞亙?????
  restaurants.value = await api.listRestaurants(
    orderVoteFilters.q, orderVoteFilters.typeFilter || undefined, 'star', userStore.username || undefined)
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
  if (n === 0) return '隢??撱?
  if (n === 1) return '蝡?閮'
  return '?脰?擗輒?巨'
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
    await alertWarning('?芣迫??銝?拇?曉')
    return
  }
  if (ids.length === 1) {
    const order = await api.createOrder({ restaurant_id: ids[0], initiator: userStore.username, deadline_at: isoDeadline })
    toast('撌脤??箄???)
    router.push(`/orders/${order.id}`)
  } else if (ids.length > 1) {
    await api.createVote({ restaurant_ids: ids, initiator: userStore.username, deadline_at: isoDeadline })
    toast('撌脣遣蝡?蟡?)
    router.push('/')
  }
}
</script>

<template>
  <div class="page-header">
    <h1>???蟡?/h1>
  </div>

  <section class="block">
    <h2>?豢?擗輒</h2>
    <div class="search-row">
      <input v-model="orderVoteFilters.q" type="text" placeholder="??擗輒????蝔? />
    </div>
    <div class="type-filter-row">
      <span class="type-chip" :class="{ active: orderVoteFilters.typeFilter === '' }" @click="orderVoteFilters.typeFilter = ''">?券</span>
      <span v-for="t in types" :key="t.id" class="type-chip" :class="{ active: orderVoteFilters.typeFilter === t.name }" @click="orderVoteFilters.typeFilter = t.name">{{ t.name }}</span>
    </div>

    <div v-if="restaurants.length === 0" class="empty">?曆??啁泵??擗輒</div>
    <label v-else v-for="r in restaurants" :key="r.id" class="checkbox-item">
      <input type="checkbox" :checked="selected.has(r.id)" @change="toggle(r.id, ($event.target as HTMLInputElement).checked)" />
      <span class="cname">{{ r.name }} <span style="color:var(--muted);font-weight:400;font-size:11px;">({{ r.type }})</span><span v-if="r.is_favorite" class="fav-star-static">??/span></span>
    </label>

    <div class="deadline-row">
      <label>?芣迫??</label>
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

    <button v-if="userStore.can('???蟡?, 'create')" class="btn btn-primary btn-full" :disabled="buttonDisabled" @click="handleAction">{{ buttonLabel }}</button>
  </section>
</template>
