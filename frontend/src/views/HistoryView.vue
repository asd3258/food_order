<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { api, type HistoryEntry } from '../api'
import { userStore } from '../stores/user'

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
    </div>
  </div>
</template>
