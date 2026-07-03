<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api, type OrderOut, type VoteBatchOut } from '../api'
import { formatDeadline } from '../deadline'
import { userStore } from '../stores/user'
import { toast } from '../stores/toast'

const router = useRouter()
const orders = ref<OrderOut[]>([])
const votes = ref<VoteBatchOut[]>([])
const restaurantNames = ref<Record<number, string>>({})

async function load() {
  const [o, v, restaurants] = await Promise.all([
    api.listOrders('open'),
    api.listVotes('open'),
    api.listRestaurants(),
  ])
  // v0.12: 依訂單/投票編號由小到大排序(訂單1,訂單2,訂單4...),不依賴資料庫
  // 回傳的預設順序。
  orders.value = [...o].sort((a, b) => a.id - b.id)
  votes.value = [...v].sort((a, b) => a.id - b.id)
  restaurantNames.value = Object.fromEntries(restaurants.map((r) => [r.id, r.name]))
}

onMounted(load)

function openOrder(o: OrderOut) {
  if (o.is_locked && o.initiator !== userStore.username && !userStore.isAdmin) {
    toast('此訂單已鎖定，只有發起者或管理員可以進入')
    return
  }
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
    <div v-else v-for="o in orders" :key="o.id" class="card card-clickable" @click="openOrder(o)">
      <div>
        <div class="name">訂單{{ o.id }} <span v-if="o.is_locked">🔒</span> · {{ restaurantNames[o.restaurant_id] || '未知餐廳' }}</div>
        <div class="sub">發起者:{{ o.initiator }} 截止時間:{{ formatDeadline(o.deadline_at) }}</div>
      </div>
      <div class="chevron">›</div>
    </div>
  </section>

  <section class="block">
    <h2>目前投票中</h2>
    <div v-if="votes.length === 0" class="empty">目前沒有投票</div>
    <div v-else v-for="v in votes" :key="v.id" class="card card-clickable" @click="openVote(v.id)">
      <div>
        <div class="name">投票{{ v.id }} {{ v.candidates.map((c) => c.restaurant_name).join('/') }}</div>
        <div class="sub">發起者:{{ v.initiator }} 截止時間:{{ formatDeadline(v.deadline_at) }}</div>
      </div>
      <div class="chevron">›</div>
    </div>
  </section>
</template>
