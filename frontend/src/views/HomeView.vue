<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api, type HistoryEntry, type HistoryLine, type OrderOut, type VoteBatchOut } from '../api'
import { formatDeadline } from '../deadline'
import { userStore } from '../stores/user'
import { toast } from '../stores/toast'

const router = useRouter()
const orders = ref<OrderOut[]>([])
const votes = ref<VoteBatchOut[]>([])
const restaurantNames = ref<Record<number, string>>({})
const todayHistory = ref<HistoryEntry[]>([])

// 本地日期 YYYY-MM-DD,對應後端 closed_date 格式
function todayStr() {
  const d = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

function sortedLines(lines: HistoryLine[]) {
  return [...lines].sort((a, b) => a.user.localeCompare(b.user) || a.item_label.localeCompare(b.item_label))
}

async function load() {
  const [o, v, restaurants, history] = await Promise.all([
    api.listOrders('open'),
    api.listVotes('open,failed'),
    api.listRestaurants(),
    api.listHistory(),
  ])
  const today = todayStr()
  todayHistory.value = history.filter((h) => h.closed_date === today).sort((a, b) => a.id - b.id)
  // v0.12: 依訂單/投票編號由小到大排序(訂單1,訂單2,訂單4...),不依賴資料庫
  // 回傳的預設順序。
  orders.value = [...o].sort((a, b) => a.id - b.id)
  votes.value = [...v].sort((a, b) => a.id - b.id)
  restaurantNames.value = Object.fromEntries(restaurants.map((r) => [r.id, r.name]))
}

let ws: WebSocket | null = null

onMounted(() => {
  load()
  
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  let wsUrl = ''
  if (import.meta.env.VITE_API_BASE) {
    const base = import.meta.env.VITE_API_BASE
    wsUrl = base.replace(/^http/, 'ws') + `/api/ws/home`
  } else {
    wsUrl = `${protocol}//${window.location.host}/api/ws/home`
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

function openOrder(o: OrderOut) {
  router.push(`/orders/${o.id}`)
}
function openVote(id: number) {
  router.push(`/votes/${id}`)
}
</script>

<template>
  <section class="block">
    <h2>當前已發起訂單</h2>
    <div v-if="orders.length === 0" class="empty">目前沒有訂單</div>
    <div v-else v-for="o in orders" :key="o.id" class="card card-clickable" :class="{ 'card-mine': o.initiator === userStore.username }" @click="openOrder(o)">
      <div>
        <div class="name">
          訂單{{ o.id }} <span v-if="o.is_locked">🔒</span> · {{ restaurantNames[o.restaurant_id] || '未知餐廳' }}
        </div>
        <div class="sub">
          發起者:{{ o.initiator }} 截止時間:
          <span :class="{ 'text-danger': o.is_locked }">
            {{ o.deadline_at ? formatDeadline(o.deadline_at) : '(未設定)' }}
            <template v-if="o.is_locked">(已截止)</template>
          </span>
        </div>
      </div>
      <div class="chevron">›</div>
    </div>
  </section>

  <section class="block">
    <h2>目前投票中</h2>
    <div v-if="votes.length === 0" class="empty">目前沒有投票</div>
    <div v-else v-for="v in votes" :key="v.id" class="card card-clickable" :class="{ 'card-mine': v.initiator === userStore.username }" @click="openVote(v.id)">
      <div>
        <div class="name">投票{{ v.id }} {{ v.candidates.map((c) => c.restaurant_name).join('/') }}</div>
        <div class="sub">
          發起者:{{ v.initiator }} 截止時間:
          <span :class="{ 'text-danger': v.status === 'failed' }">
            {{ formatDeadline(v.deadline_at) }}
            <template v-if="v.status === 'failed'">(已截止, ERR:票數相同)</template>
          </span>
        </div>
      </div>
      <div class="chevron">›</div>
    </div>
  </section>

  <section class="block">
    <h2>今日歷史訂單</h2>
    <div v-if="todayHistory.length === 0" class="empty">今天尚無歷史訂單</div>
    <div v-else v-for="h in todayHistory" :key="h.id" class="card today-history">
      <div class="name">{{ h.restaurant_name }}</div>
      <table class="stat-table">
        <tr>
          <th>品項</th>
          <th>人員</th>
          <th>數量</th>
          <th>金額</th>
        </tr>
        <tr v-for="l in sortedLines(h.lines)" :key="l.id">
          <td>{{ l.item_label }}</td>
          <td>{{ l.user }}</td>
          <td>{{ l.quantity }}</td>
          <td>${{ l.amount }}</td>
        </tr>
      </table>
    </div>
  </section>
</template>

<style scoped>
.today-history {
  display: block;
}
.today-history .name {
  margin-bottom: 6px;
  font-weight: 600;
  font-size: 15px;
}
</style>
