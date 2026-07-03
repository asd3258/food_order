<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { api, type HistoryEntry } from '../api'
import { userStore } from '../stores/user'
import { confirmAction } from '../stores/confirm'
import { toast } from '../stores/toast'
import { copyText } from '../share'

const entries = ref<HistoryEntry[]>([])
const expanded = reactive<Set<number>>(new Set())

async function load() {
  entries.value = await api.listHistory()
}
onMounted(load)

function toggle(id: number) {
  if (expanded.has(id)) expanded.delete(id)
  else expanded.add(id)
}

async function togglePayment(entry: HistoryEntry, user: string) {
  if (entry.initiator !== userStore.username) return
  await api.togglePayment(entry.id, user, userStore.username)
  load()
}

// v0.11: 「複製成文字」-- 整理成一段方便貼到 LINE/Teams 通知大家付款的純文字,
// 不用截圖或一個個念金額。
function buildHistoryText(h: HistoryEntry): string {
  const lines = [
    `${h.restaurant_name} - ${h.closed_date}`,
    `共 ${h.people_count} 人,合計 $${h.total_amount}`,
    '',
    ...h.lines.map((l) => `${l.item_label} x${l.quantity} - ${l.user} - $${l.amount}`),
    '',
    '收款狀態:',
    ...h.payments.map((p) => `${p.is_paid ? '✅' : '⬜'} ${p.user} $${p.total_amount}`),
  ]
  return lines.join('\n')
}
function copyHistoryText(h: HistoryEntry) {
  copyText(buildHistoryText(h), '已複製成文字,可以貼到 LINE/Teams 了')
}

// v0.7: 歷史清單 delete is admin-only.
async function removeEntry(entry: HistoryEntry) {
  const ok = await confirmAction(`確定要刪除「${entry.restaurant_name}」(${entry.closed_date}) 這筆歷史紀錄嗎?此動作無法復原。`)
  if (!ok) return
  await api.deleteHistory(entry.id, userStore.username)
  toast('已刪除歷史紀錄')
  load()
}
</script>

<template>
  <div class="page-header">
    <router-link class="back" to="/more">←</router-link>
    <h1>歷史訂單</h1>
  </div>

  <div v-if="!entries.length" class="empty">尚無歷史訂單</div>
  <div v-for="h in entries" :key="h.id" class="card history-card" :class="{ open: expanded.has(h.id) }">
    <div class="hc-head" @click="toggle(h.id)">
      <div>
        <div class="name" style="font-weight:600;font-size:14px;">{{ h.restaurant_name }}</div>
        <div class="sub" style="font-size:12px;color:var(--muted);">
          {{ h.closed_date }} · 發起者:{{ h.initiator }} · {{ h.people_count }}人 · 共 ${{ h.total_amount }} ·
          已收款 {{ h.payments.filter((p) => p.is_paid).length }}/{{ h.payments.length }}
        </div>
      </div>
      <span v-if="userStore.isAdmin" style="color:var(--danger);font-size:12px;cursor:pointer;margin-right:8px;align-self:center;" @click.stop="removeEntry(h)">刪除</span>
      <div class="chevron">▾</div>
    </div>
    <div class="hc-detail">
      <table class="stat-table">
        <tr><th>品項</th><th>人員</th><th>數量</th><th>金額</th></tr>
        <tr v-for="(l, i) in h.lines" :key="i">
          <td>{{ l.item_label }}</td><td>{{ l.user }}</td><td>{{ l.quantity }}</td><td>${{ l.amount }}</td>
        </tr>
      </table>
      <div class="menu-cat" style="margin-top:10px;font-size:12px;color:var(--muted);font-weight:600;">
        收款狀態({{ h.payments.filter((p) => p.is_paid).length }}/{{ h.payments.length }} 人)
      </div>
      <label v-for="p in h.payments" :key="p.user" class="payment-row">
        <input type="checkbox" :checked="p.is_paid" :disabled="h.initiator !== userStore.username" @change="togglePayment(h, p.user)" />
        <span class="puser">{{ p.user }}</span>
        <span class="pamt">${{ p.total_amount }}</span>
      </label>
      <button class="btn btn-secondary btn-full" style="margin-top:10px;" @click.stop="copyHistoryText(h)">📋 複製成文字</button>
    </div>
  </div>
</template>
