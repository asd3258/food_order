<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, type VoteBatchOut } from '../api'
import { HOURS, MINUTES, formatDeadline, isoToParts, partsToIso, type DeadlineParts } from '../deadline'
import { userStore } from '../stores/user'
import { confirmAction } from '../stores/confirm'
import { toast } from '../stores/toast'
import { canWebShare, copyLink, shareLink } from '../share'
import { requireLogin } from '../auth'

const route = useRoute()
const router = useRouter()
const batchId = Number(route.params.id)
const batch = ref<VoteBatchOut | null>(null)
const editDeadline = ref<DeadlineParts | null>(null)
const pendingSelection = ref<number | null>(null)

const isInitiator = computed(() => batch.value?.initiator === userStore.username)

async function load() {
  batch.value = await api.getVote(batchId, userStore.username)
  pendingSelection.value = batch.value.my_selection
  editDeadline.value = isoToParts(batch.value.deadline_at)
}
onMounted(load)

async function updateDeadline() {
  if (!editDeadline.value) return
  await api.updateVoteDeadline(batchId, partsToIso(editDeadline.value), userStore.username)
  toast('已更新截止時間')
  load()
}

async function save() {
  if (!requireLogin()) return
  if (pendingSelection.value == null) {
    toast('請先選擇一家餐廳')
    return
  }
  await api.saveMyChoice(batchId, userStore.username, pendingSelection.value)
  toast('已鎖定投票')
  load()
}
async function edit() {
  if (!requireLogin()) return
  // v0.5 behavior change: Edit now immediately clears the saved choice
  // (rather than just unlocking the radios while keeping the old pick) --
  // the vote stops counting toward the tally right away, and the user must
  // pick again and press Save to be counted.
  await api.clearMyChoice(batchId, userStore.username)
  toast('已清除您的選擇,請重新選擇並按 Save')
  load()
}

async function tally() {
  const ok = await confirmAction('確定要開票嗎?將依目前票數最高的餐廳自動建立訂單。')
  if (!ok) return
  const order = await api.decideVote(batchId, userStore.username)
  toast('已開票,已建立訂單')
  router.push(`/orders/${order.id}`)
}
async function remove() {
  const ok = await confirmAction('確定要刪除此投票嗎?此動作無法復原。')
  if (!ok) return
  await api.deleteVote(batchId, userStore.username)
  toast('已刪除投票')
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
  shareLink(`投票${batchId}`, `幫忙投一票吃什麼(${names}),點連結進去選:`, currentUrl())
}
</script>

<template>
  <div class="page-header">
    <router-link class="back" to="/">←</router-link>
    <h1>投票{{ batchId }}</h1>
  </div>

  <template v-if="batch">
    <div class="btn-row">
      <button class="btn btn-secondary" @click="doCopyLink">🔗 複製連結</button>
      <button v-if="shareSupported" class="btn btn-secondary" @click="doShare">📤 分享</button>
    </div>

    <div v-if="!isInitiator" class="deadline-inline">
      <span>截止時間</span><strong>{{ formatDeadline(batch.deadline_at) }}</strong>
    </div>
    <div v-else-if="editDeadline" class="deadline-inline">
      <span>截止時間</span>
      <input v-model="editDeadline.date" type="date" class="time-select" />
      <select v-model.number="editDeadline.hour" class="time-select">
        <option v-for="h in HOURS" :key="h" :value="h">{{ String(h).padStart(2, '0') }}</option>
      </select>
      <span>:</span>
      <select v-model.number="editDeadline.minute" class="time-select">
        <option v-for="m in MINUTES" :key="m" :value="m">{{ String(m).padStart(2, '0') }}</option>
      </select>
      <button class="btn btn-secondary" style="flex:none;padding:7px 12px;" @click="updateDeadline">更新</button>
    </div>

    <div v-if="isInitiator" class="btn-row">
      <button class="btn btn-primary" @click="tally">開票</button>
      <button class="btn btn-danger" @click="remove">刪除</button>
    </div>

    <section class="block">
      <h2>候選餐廳</h2>
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
          <span style="font-size:12px;color:var(--muted);background:#f0f0f0;padding:2px 8px;border-radius:10px;">{{ c.count }} 票</span>
        </label>
        <div class="btn-row" style="margin-top:10px;margin-bottom:0;">
          <button v-if="!batch.my_locked" class="btn btn-primary" @click="save">Save</button>
          <button v-else class="btn btn-primary" @click="edit">Edit</button>
        </div>
      </div>
    </section>
  </template>
</template>
