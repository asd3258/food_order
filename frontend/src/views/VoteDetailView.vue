<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, type VoteBatchOut } from '../api'
import { HOURS, MINUTES, formatDeadline, isoToParts, partsToIso, type DeadlineParts } from '../deadline'
import { userStore } from '../stores/user'
import { confirmAction, alertWarning } from '../stores/confirm'
import { toast } from '../stores/toast'
import { canWebShare, copyLink, shareLink } from '../share'
import { requireLogin } from '../auth'

const route = useRoute()
const router = useRouter()
const batchId = Number(route.params.id)
const batch = ref<VoteBatchOut | null>(null)
const editDeadline = ref<DeadlineParts | null>(null)
const pendingSelection = ref<number | null>(null)

// v0.12: ?寧 userStore.can 蝯曹??斗甈?
const isInitiator = computed(() => {
  if (!batch.value) return false
  return userStore.can('?巨', 'delete', batch.value.initiator)
})

const attemptedSubmit = ref(false)
const isDeadlineInvalid = computed(() => {
  if (!attemptedSubmit.value) return false
  if (!editDeadline.value) return false
  return new Date(partsToIso(editDeadline.value)).getTime() < Date.now()
})

async function load() {
  batch.value = await api.getVote(batchId, userStore.username)
  pendingSelection.value = batch.value.my_selection
  editDeadline.value = isoToParts(batch.value.deadline_at)
}
let ws: WebSocket | null = null

onMounted(() => {
  load()
  
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  let wsUrl = ''
  if (import.meta.env.VITE_API_BASE) {
    const base = import.meta.env.VITE_API_BASE
    wsUrl = base.replace(/^http/, 'ws') + `/api/ws/votes/${batchId}`
  } else {
    wsUrl = `${protocol}//${window.location.host}/api/ws/votes/${batchId}`
  }

  ws = new WebSocket(wsUrl)
  ws.onmessage = (event) => {
    if (event.data === 'update') {
      load()
    }
  }
})

onUnmounted(() => {
  if (ws) {
    ws.close()
  }
})

async function updateDeadline() {
  if (!editDeadline.value) return
  attemptedSubmit.value = true
  const isoDeadline = partsToIso(editDeadline.value)
  if (new Date(isoDeadline).getTime() < Date.now()) {
    await alertWarning('?芣迫??銝?拇?曉')
    return
  }
  await api.updateVoteDeadline(batchId, isoDeadline, userStore.username)
  toast('撌脫?唳甇Ｘ???)
  load()
}

async function save() {
  if (!requireLogin()) return
  if (pendingSelection.value == null) {
    toast('隢??豢?銝摰園?撱?)
    return
  }
  await api.saveMyChoice(batchId, userStore.username, pendingSelection.value)
  toast('撌脤?摰?蟡?)
  load()
}
async function edit() {
  if (!requireLogin()) return
  // v0.5 behavior change: Edit now immediately clears the saved choice
  // (rather than just unlocking the radios while keeping the old pick) --
  // the vote stops counting toward the tally right away, and the user must
  // pick again and press Save to be counted.
  await api.clearMyChoice(batchId, userStore.username)
  toast('撌脫??斗???隢??圈?蒂??Save')
  load()
}

async function tally() {
  const ok = await confirmAction('蝣箏?閬?蟡典??撠??桀?蟡冽?擃?擗輒?芸?撱箇?閮??)
  if (!ok) return
  const order = await api.decideVote(batchId, userStore.username)
  toast('撌脤?蟡?撌脣遣蝡???)
  router.push(`/orders/${order.id}`)
}
async function remove() {
  const ok = await confirmAction('蝣箏?閬?斗迨?巨??甇文?雿瘜儔??)
  if (!ok) return
  await api.deleteVote(batchId, userStore.username)
  toast('撌脣?斗?蟡?)
  router.push('/')
}

const shareSupported = canWebShare()
function currentUrl(): string {
  return window.location.href
}
function doCopyLink() {
  copyLink(currentUrl())
}
function doShare() {
  const names = batch.value?.candidates.map((c) => c.restaurant_name).join('/') || ''
  shareLink(`?巨${batchId}`, `撟怠???蟡典?隞暻?${names}),暺???脣??`, currentUrl())
}
</script>

<template>
  <div class="page-header">
    <router-link class="back" to="/">??/router-link>
    <h1>?巨{{ batchId }}</h1>
  </div>

  <template v-if="batch">
    <div class="btn-row">
      <button class="btn btn-secondary" @click="doCopyLink">?? 銴ˊ???</button>
      <button v-if="shareSupported" class="btn btn-secondary" @click="doShare">? ?澈</button>
    </div>

    <div v-if="!isInitiator" class="deadline-inline">
      <span>?芣迫??</span><strong>{{ formatDeadline(batch.deadline_at) }}</strong>
    </div>
    <div v-else-if="editDeadline" class="deadline-inline">
      <span>?芣迫??</span>
      <input v-model="editDeadline.date" type="date" class="time-select" :class="{ 'input-invalid': isDeadlineInvalid }" />
      <select v-model.number="editDeadline.hour" class="time-select" :class="{ 'input-invalid': isDeadlineInvalid }">
        <option v-for="h in HOURS" :key="h" :value="h">{{ String(h).padStart(2, '0') }}</option>
      </select>
      <span>:</span>
      <select v-model.number="editDeadline.minute" class="time-select" :class="{ 'input-invalid': isDeadlineInvalid }">
        <option v-for="m in MINUTES" :key="m" :value="m">{{ String(m).padStart(2, '0') }}</option>
      </select>
      <button class="btn btn-secondary" style="flex:none;padding:7px 12px;" @click="updateDeadline">?湔</button>
    </div>

    <div v-if="isInitiator" class="btn-row">
      <button class="btn btn-primary" @click="tally">?巨</button>
      <button class="btn btn-danger" @click="remove">?芷</button>
    </div>

    <section class="block">
      <h2>?擗輒</h2>
      <div class="card">
        <label v-for="c in batch.candidates" :key="c.restaurant_id" class="checkbox-item" :style="batch.my_locked ? 'opacity:.55' : ''">
          <input
            type="radio"
            name="voteChoice"
            :value="c.restaurant_id"
            :checked="pendingSelection === c.restaurant_id"
            :disabled="batch.my_locked"
            @change="pendingSelection = c.restaurant_id"
          />
          <span class="cname">{{ c.restaurant_name }}</span>
          <span style="font-size:12px;color:var(--muted);background:#f0f0f0;padding:2px 8px;border-radius:10px;">{{ c.count }} 蟡?/span>
        </label>
        <div class="btn-row" style="margin-top:10px;margin-bottom:0;" v-if="userStore.can('?巨', 'update', batch.initiator)">
          <button v-if="!batch.my_locked" class="btn btn-primary" @click="save">Save</button>
          <button v-else class="btn btn-primary" @click="edit">Edit</button>
        </div>
      </div>
    </section>
  </template>
</template>
