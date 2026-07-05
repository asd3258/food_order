<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, type OrderOut, type RestaurantDetail, type MenuItem, type StatRow } from '../api'
import { HOURS, MINUTES, formatDeadline, isoToParts, partsToIso, type DeadlineParts, defaultDeadline } from '../deadline'
import { userStore } from '../stores/user'
import { confirmAction, alertWarning } from '../stores/confirm'
import { toast } from '../stores/toast'
import { canWebShare, copyLink, copyText, shareLink } from '../share'
import { requireLogin } from '../auth'

const route = useRoute()
const router = useRouter()
const orderId = Number(route.params.id)

const order = ref<OrderOut | null>(null)
const restaurant = ref<RestaurantDetail | null>(null)
const stats = ref<StatRow[]>([])
const editDeadline = ref<DeadlineParts | null>(null)

// v0.11: 暺?皜?見靘?憿?蝯?頝?RestaurantMenuView ?霈?銝??,
// ?芸?憿??格??敺?
const groupedMenu = computed(() => {
  const items = restaurant.value?.menu_items || []
  const catOrder: string[] = []
  const groups: Record<string, MenuItem[]> = {}
  for (const m of items) {
    const cat = m.category?.trim() || '?芸?憿?
    if (!groups[cat]) {
      groups[cat] = []
      if (cat === '?芸?憿?) catOrder.push(cat)
      else catOrder.unshift(cat)
    }
    groups[cat].push(m)
  }
  const sorted = catOrder.filter((c) => c !== '?芸?憿?).concat(catOrder.includes('?芸?憿?) ? ['?芸?憿?] : [])
  return sorted.map((category) => {
    // 瘥??亙?券?憿?撠憭扳?摨?
    const sortedItems = groups[category].slice().sort((a, b) => a.price - b.price)
    return { category, items: sortedItems }
  })
})

// v0.12: ?寧 userStore.can 蝯曹??斗甈?
const isInitiator = computed(() => {
  if (!order.value) return false
  return userStore.can('閮', 'delete', order.value.initiator)
})
const canModify = computed(() => {
  if (!order.value) return false
  const canUpdate = userStore.can('閮', 'update', order.value.initiator)
  if (!canUpdate) return false
  if (!order.value.is_locked) return true
  return isInitiator.value
})
const myLines = computed(() => stats.value.filter((s) => s.user === userStore.username && !s.is_deleted))
const myTotal = computed(() => myLines.value.reduce((sum, l) => sum + l.amount, 0))
const attemptedSubmit = ref(false)
const isDeadlineInvalid = computed(() => {
  if (order.value?.is_locked) return false
  if (!attemptedSubmit.value) return false
  if (!editDeadline.value) return false
  return new Date(partsToIso(editDeadline.value)).getTime() < Date.now()
})

async function load() {
  try {
    order.value = await api.getOrder(orderId, userStore.username)
    restaurant.value = await api.getRestaurantMenu(order.value.restaurant_id)
    stats.value = await api.getOrderStats(orderId, userStore.username)
    if (order.value.deadline_at) {
      editDeadline.value = isoToParts(order.value.deadline_at)
    } else {
      editDeadline.value = defaultDeadline()
    }
  } catch (e: any) {
    router.push('/')
  }
}
let ws: WebSocket | null = null

onMounted(() => {
  load()
  
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  let wsUrl = ''
  if (import.meta.env.VITE_API_BASE) {
    const base = import.meta.env.VITE_API_BASE
    wsUrl = base.replace(/^http/, 'ws') + `/api/ws/orders/${orderId}`
  } else {
    wsUrl = `${protocol}//${window.location.host}/api/ws/orders/${orderId}`
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
  await api.updateOrderDeadline(orderId, isoDeadline, userStore.username)
  toast('撌脫?唳甇Ｘ???)
  load()
}

// ---- item customization sheet ----
const sheetOpen = ref(false)
const sheetItem = ref<MenuItem | null>(null)
const sheetChoices = ref<Record<string, string[]>>({})
const sheetQty = ref(1)

function openItemSheet(item: MenuItem) {
  if (!requireLogin()) return
  if (!canModify.value) {
    toast('甇方??桀歇?嚗瘜?擗?)
    return
  }
  sheetItem.value = item
  sheetChoices.value = {}
  for (const group of Array.from(new Set(item.options.map((o) => o.option_group)))) {
    const groupOptions = item.options.filter((o) => o.option_group === group)
    if (groupOptions[0]?.option_type === 'radio' && groupOptions.length) {
      sheetChoices.value[group] = [groupOptions[0].option_name]
    } else {
      sheetChoices.value[group] = []
    }
  }
  sheetQty.value = 1
  sheetOpen.value = true
}
function closeSheet() {
  sheetOpen.value = false
}
function groupsOf(item: MenuItem): { group: string; type: string; choices: typeof item.options }[] {
  const groups: Record<string, typeof item.options> = {}
  for (const o of item.options) {
    groups[o.option_group] = groups[o.option_group] || []
    groups[o.option_group].push(o)
  }
  return Object.entries(groups).map(([group, choices]) => ({ group, type: choices[0].option_type, choices }))
}
function onRadioPick(group: string, name: string) {
  sheetChoices.value[group] = [name]
}
function onCheckboxToggle(group: string, name: string, checked: boolean) {
  const list = new Set(sheetChoices.value[group] || [])
  if (checked) list.add(name)
  else list.delete(name)
  sheetChoices.value[group] = Array.from(list)
}
async function addToOrder() {
  if (!sheetItem.value) return
  const selected = Object.values(sheetChoices.value).flat()
  await api.addOrderItem(orderId, {
    user: userStore.username,
    menu_item_id: sheetItem.value.id,
    selected_options: selected,
    quantity: sheetQty.value,
  })
  closeSheet()
  toast('撌脣??交?????)
  stats.value = await api.getOrderStats(orderId)
}

async function removeMyLine(itemId: number) {
  await api.removeOwnItem(orderId, itemId, userStore.username)
  stats.value = await api.getOrderStats(orderId)
}

async function softDelete(itemId: number) {
  const ok = await confirmAction('蝣箏?閬?方府蝑????(撠誑?芷蝺?蝷?銝??迤蝘駁閮?)')
  if (!ok) return
  await api.softDeleteItem(orderId, itemId, userStore.username)
  toast('撌脣?方府蝑???隞亙?斤?璅內)')
  stats.value = await api.getOrderStats(orderId)
}

async function lockOrder() {
  const ok = await confirmAction('蝣箏?閬??桀???敺隞犖撠瘜脣??)
  if (!ok) return
  await api.lockOrder(orderId, userStore.username)
  toast('撌脤???)
  load()
}

async function unlockOrder() {
  const ok = await confirmAction('蝣箏?閬圾?日??桀??閫?敺隞犖撠隞仿脣??)
  if (!ok) return
  await api.unlockOrder(orderId, userStore.username)
  toast('撌脰圾?日???)
  load()
}

async function closeOrder() {
  const ok = await confirmAction('蝣箏?閬????桀??蝯梯?蝯?撠神?交風?脰??柴?)
  if (!ok) return
  await api.closeOrder(orderId, userStore.username)
  toast('撌脣?????)
  router.push('/')
}
async function deleteOrder() {
  const ok = await confirmAction('蝣箏?閬?斗迨閮??甇文?雿瘜儔??)
  if (!ok) return
  await api.deleteOrder(orderId, userStore.username)
  toast('撌脣?方???)
  router.push('/')
}

function mapUrl(r: RestaurantDetail): string {
  return 'https://www.google.com/maps/search/?api=1&query=' + encodeURIComponent(r.name + ' ' + r.address)
}

// v0.12: ??桐?憿 Google Maps ??????????賬?
function copyMapLink(r: RestaurantDetail) {
  copyText(mapUrl(r), '撌脰?鋆賢???')
}

const shareSupported = canWebShare()
function currentUrl(): string {
  return window.location.href
}
function doCopyLink() {
  copyLink(currentUrl())
}
function doShare() {
  const rname = restaurant.value?.name || '閮'
  shareLink(`閮${orderId} - ${rname}`, `銝韏瑁? ${rname} ??暺???脣?訾?閬???:`, currentUrl())
}
</script>

<template>
  <div class="page-header">
    <router-link class="back" to="/">??/router-link>
    <h1>{{ restaurant?.name || '暺?' }}</h1>
  </div>

  <template v-if="order && restaurant">
    <div class="btn-row">
      <button class="btn btn-secondary" @click="doCopyLink">?? 銴ˊ???</button>
      <button v-if="shareSupported" class="btn btn-secondary" @click="doShare">? ?澈</button>
    </div>

    <div v-if="!isInitiator" class="deadline-inline">
      <span>?芣迫??</span><strong>{{ order.deadline_at ? formatDeadline(order.deadline_at) : '(?芾身摰?' }}</strong>
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
      <button class="btn btn-secondary" style="flex:none;padding:7px 12px;" :disabled="order.is_locked" @click="updateDeadline">?湔</button>
    </div>

    <div v-if="isInitiator" class="btn-row">
      <button v-if="!order.is_locked" class="btn btn-secondary" @click="lockOrder">?</button>
      <button v-if="order.is_locked" class="btn btn-secondary" @click="unlockOrder">閫??</button>
      <button v-if="order.is_locked" class="btn btn-secondary" @click="closeOrder">摰?閮</button>
      <button class="btn btn-danger" @click="deleteOrder">?芷</button>
    </div>

    <div v-for="grp in groupedMenu" :key="grp.category">
      <div class="menu-cat" style="margin-top:14px;font-size:12px;color:var(--muted);font-weight:600;">{{ grp.category }}</div>
      <div v-for="m in grp.items" :key="m.id" class="menu-item" @click="openItemSheet(m)">
        <div>
          <div class="mi-name">{{ m.name }}</div>
          <div class="mi-price">${{ m.price }}</div>
        </div>
        <div class="plus-badge" v-if="canModify">+</div>
      </div>
    </div>

    <section class="block">
      <h2 class="h2-highlight">??閮</h2>
      <div class="card card-highlight">
        <div v-if="!myLines.length" class="empty">撠?豢???</div>
        <div v-else v-for="l in myLines" :key="l.item_id" class="cart-line">
          <span>{{ l.label }} ? {{ l.quantity }}</span>
          <span>${{ l.amount }} <span class="rm" v-if="canModify" @click="removeMyLine(l.item_id)">蝘駁</span></span>
        </div>
      </div>
      <div class="cart-bar">
        <span>撠?</span>
        <strong>${{ myTotal }}</strong>
      </div>
    </section>

    <section class="block">
      <h2>?桀???犖蝯梯?(敶蜇)</h2>
      <div class="card">
        <table class="stat-table">
          <tr><th>?? / ?賊?</th><th>鈭箏</th><th>?賊?</th><th>??</th></tr>
          <tr v-if="!stats.length"><td colspan="4" style="color:var(--muted);">撠鞈?</td></tr>
          <tr v-for="s in stats" :key="s.item_id" :style="s.is_deleted ? 'opacity:.5;text-decoration:line-through;' : ''">
            <td>{{ s.label }}</td>
            <td>{{ s.user }}</td>
            <td>{{ s.quantity }}</td>
            <td>
              ${{ s.amount }}
              <span v-if="!s.is_deleted && s.user !== userStore.username && isInitiator" class="rm" @click="softDelete(s.item_id)">?芷</span>
            </td>
          </tr>
        </table>
      </div>
    </section>

    <div class="btn-row">
      <button class="btn btn-secondary" @click="copyMapLink(restaurant)">?? 銴ˊ?啣????</button>
      <a class="btn btn-secondary" :href="mapUrl(restaurant)" target="_blank">?? ??Google Maps ??</a>
    </div>

    <div class="overlay" :class="{ active: sheetOpen }" @click.self="closeSheet">
      <div class="sheet" v-if="sheetItem">
        <h3>{{ sheetItem.name }}</h3>
        <div class="price">${{ sheetItem.price }} 韏?/div>

        <div v-if="!sheetItem.options.length" class="empty" style="text-align:left;padding:4px 0;">甇文??摰Ｚˊ?賊?</div>
        <div v-for="g in groupsOf(sheetItem)" :key="g.group">
          <div class="opt-group-title">{{ g.group }}{{ g.type === 'radio' ? '(?桅)' : '(?臬???' }}</div>
          <label v-for="c in g.choices" :key="c.option_name" class="opt-choice">
            <input
              v-if="g.type === 'radio'"
              type="radio"
              :name="g.group"
              :checked="sheetChoices[g.group]?.[0] === c.option_name"
              @change="onRadioPick(g.group, c.option_name)"
            />
            <input
              v-else
              type="checkbox"
              :checked="sheetChoices[g.group]?.includes(c.option_name)"
              @change="onCheckboxToggle(g.group, c.option_name, ($event.target as HTMLInputElement).checked)"
            />
            {{ c.option_name }}<template v-if="c.extra_price"> ({{ c.extra_price > 0 ? '+$' + c.extra_price : '-$' + (-c.extra_price) }})</template>
          </label>
        </div>

        <div class="qty-row">
          <span style="font-size:13px;color:var(--muted);">?賊?</span>
          <div class="qty-ctrl">
            <button @click="sheetQty = Math.max(1, sheetQty - 1)">??/button>
            <span>{{ sheetQty }}</span>
            <button @click="sheetQty += 1">+</button>
          </div>
        </div>

        <div class="sheet-actions">
          <button class="btn btn-secondary" @click="closeSheet">??</button>
          <button class="btn btn-primary" @click="addToOrder">???閮</button>
        </div>
      </div>
    </div>
  </template>
</template>
