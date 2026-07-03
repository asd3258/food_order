<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, type OrderOut, type RestaurantDetail, type MenuItem, type StatRow } from '../api'
import { HOURS, MINUTES, formatDeadline, isoToParts, partsToIso, type DeadlineParts } from '../deadline'
import { userStore } from '../stores/user'
import { confirmAction } from '../stores/confirm'
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

// v0.11: 點餐清單同樣依「分類」分組(跟 RestaurantMenuView 的唯讀菜單一致),
// 未分類項目排最後。
const groupedMenu = computed(() => {
  const items = restaurant.value?.menu_items || []
  const catOrder: string[] = []
  const groups: Record<string, MenuItem[]> = {}
  for (const m of items) {
    const cat = m.category?.trim() || '未分類'
    if (!groups[cat]) {
      groups[cat] = []
      if (cat === '未分類') catOrder.push(cat)
      else catOrder.unshift(cat)
    }
    groups[cat].push(m)
  }
  const sorted = catOrder.filter((c) => c !== '未分類').concat(catOrder.includes('未分類') ? ['未分類'] : [])
  return sorted.map((category) => ({ category, items: groups[category] }))
})

// v0.12: mike_admin 的權限跟發起者相同 -- 結單/刪除/改截止時間/軟刪除他人品項
// 這些按鈕,admin 帳號即使不是這筆訂單的發起者也要看得到(後端 orders.py 已經
// 放寬,前端這裡卻只看 initiator 字串比對,按鈕才一直沒出現)。
const isInitiator = computed(() => order.value?.initiator === userStore.username || userStore.isAdmin)
const myLines = computed(() => stats.value.filter((s) => s.user === userStore.username && !s.is_deleted))
const myTotal = computed(() => myLines.value.reduce((sum, l) => sum + l.amount, 0))

async function load() {
  try {
    order.value = await api.getOrder(orderId, userStore.username)
    restaurant.value = await api.getRestaurantMenu(order.value.restaurant_id)
    stats.value = await api.getOrderStats(orderId, userStore.username)
    editDeadline.value = isoToParts(order.value.deadline_at)
  } catch (e: any) {
    router.push('/')
  }
}
onMounted(load)

async function updateDeadline() {
  if (!editDeadline.value) return
  await api.updateOrderDeadline(orderId, partsToIso(editDeadline.value), userStore.username)
  toast('已更新截止時間')
  load()
}

// ---- item customization sheet ----
const sheetOpen = ref(false)
const sheetItem = ref<MenuItem | null>(null)
const sheetChoices = ref<Record<string, string[]>>({})
const sheetQty = ref(1)

function openItemSheet(item: MenuItem) {
  if (!requireLogin()) return
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
  toast('已加入我的訂單')
  stats.value = await api.getOrderStats(orderId)
}

async function removeMyLine(itemId: number) {
  await api.removeOwnItem(orderId, itemId, userStore.username)
  stats.value = await api.getOrderStats(orderId)
}

async function softDelete(itemId: number) {
  const ok = await confirmAction('確定要刪除該筆品項嗎?(將以刪除線標示,不會真正移除記錄)')
  if (!ok) return
  await api.softDeleteItem(orderId, itemId, userStore.username)
  toast('已刪除該筆品項(以刪除線標示)')
  stats.value = await api.getOrderStats(orderId)
}

async function lockOrder() {
  const ok = await confirmAction('確定要鎖定此訂單嗎?鎖定後其他人將無法進入。')
  if (!ok) return
  await api.lockOrder(orderId, userStore.username)
  toast('已鎖定訂單')
  load()
}

async function closeOrder() {
  const ok = await confirmAction('確定要保存到歷史紀錄嗎?統計結果將寫入歷史訂單。')
  if (!ok) return
  await api.closeOrder(orderId, userStore.username)
  toast('已保存到歷史紀錄')
  router.push('/')
}
async function deleteOrder() {
  const ok = await confirmAction('確定要刪除此訂單嗎?此動作無法復原。')
  if (!ok) return
  await api.deleteOrder(orderId, userStore.username)
  toast('已刪除訂單')
  router.push('/')
}

function mapUrl(r: RestaurantDetail): string {
  return 'https://www.google.com/maps/search/?api=1&query=' + encodeURIComponent(r.name + ' ' + r.address)
}

// v0.12: 原本單一顆「在 Google Maps 開啟」按鈕拆成兩個功能。
function copyMapLink(r: RestaurantDetail) {
  copyText(mapUrl(r), '已複製地圖連結')
}

const shareSupported = canWebShare()
function currentUrl(): string {
  return window.location.href
}
function doCopyLink() {
  copyLink(currentUrl())
}
function doShare() {
  const rname = restaurant.value?.name || '訂單'
  shareLink(`訂單${orderId} - ${rname}`, `一起訂 ${rname} 吧,點連結進去選你要的品項:`, currentUrl())
}
</script>

<template>
  <div class="page-header">
    <router-link class="back" to="/">←</router-link>
    <h1>{{ restaurant?.name || '點餐' }}</h1>
  </div>

  <template v-if="order && restaurant">
    <div class="btn-row">
      <button class="btn btn-secondary" @click="doCopyLink">🔗 複製連結</button>
      <button v-if="shareSupported" class="btn btn-secondary" @click="doShare">📤 分享</button>
    </div>

    <div v-if="!isInitiator" class="deadline-inline">
      <span>截止時間</span><strong>{{ formatDeadline(order.deadline_at) }}</strong>
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
      <button v-if="!order.is_locked" class="btn btn-secondary" @click="lockOrder">鎖定</button>
      <button class="btn btn-secondary" @click="closeOrder">保存到歷史紀錄</button>
      <button class="btn btn-danger" @click="deleteOrder">刪除</button>
    </div>

    <div v-for="grp in groupedMenu" :key="grp.category">
      <div class="menu-cat" style="margin-top:14px;font-size:12px;color:var(--muted);font-weight:600;">{{ grp.category }}</div>
      <div v-for="m in grp.items" :key="m.id" class="menu-item" @click="openItemSheet(m)">
        <div>
          <div class="mi-name">{{ m.name }}</div>
          <div class="mi-price">${{ m.price }}</div>
        </div>
        <div class="plus-badge">+</div>
      </div>
    </div>

    <section class="block">
      <h2 class="h2-highlight">我的訂單</h2>
      <div class="card card-highlight">
        <div v-if="!myLines.length" class="empty">尚未選擇品項</div>
        <div v-else v-for="l in myLines" :key="l.item_id" class="cart-line">
          <span>{{ l.label }} × {{ l.quantity }}</span>
          <span>${{ l.amount }} <span class="rm" @click="removeMyLine(l.item_id)">移除</span></span>
        </div>
      </div>
      <div class="cart-bar">
        <span>小計</span>
        <strong>${{ myTotal }}</strong>
      </div>
    </section>

    <section class="block" v-if="isInitiator">
      <h2>目前所有人統計(彙總)</h2>
      <div class="card">
        <table class="stat-table">
          <tr><th>品項 / 選項</th><th>人員</th><th>數量</th><th>金額</th></tr>
          <tr v-if="!stats.length"><td colspan="4" style="color:var(--muted);">尚無資料</td></tr>
          <tr v-for="s in stats" :key="s.item_id" :style="s.is_deleted ? 'opacity:.5;text-decoration:line-through;' : ''">
            <td>{{ s.label }}</td>
            <td>{{ s.user }}</td>
            <td>{{ s.quantity }}</td>
            <td>
              ${{ s.amount }}
              <span v-if="!s.is_deleted && s.user !== userStore.username" class="rm" @click="softDelete(s.item_id)">刪除</span>
            </td>
          </tr>
        </table>
      </div>
    </section>

    <div class="btn-row">
      <button class="btn btn-secondary" @click="copyMapLink(restaurant)">📋 複製地圖連結</button>
      <a class="btn btn-secondary" :href="mapUrl(restaurant)" target="_blank">📍 在 Google Maps 開啟</a>
    </div>

    <div class="overlay" :class="{ active: sheetOpen }" @click.self="closeSheet">
      <div class="sheet" v-if="sheetItem">
        <h3>{{ sheetItem.name }}</h3>
        <div class="price">${{ sheetItem.price }} 起</div>

        <div v-if="!sheetItem.options.length" class="empty" style="text-align:left;padding:4px 0;">此品項無客製選項</div>
        <div v-for="g in groupsOf(sheetItem)" :key="g.group">
          <div class="opt-group-title">{{ g.group }}{{ g.type === 'radio' ? '(單選)' : '(可多選)' }}</div>
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
            {{ c.option_name }}<template v-if="c.extra_price"> (+${{ c.extra_price }})</template>
          </label>
        </div>

        <div class="qty-row">
          <span style="font-size:13px;color:var(--muted);">數量</span>
          <div class="qty-ctrl">
            <button @click="sheetQty = Math.max(1, sheetQty - 1)">−</button>
            <span>{{ sheetQty }}</span>
            <button @click="sheetQty += 1">+</button>
          </div>
        </div>

        <div class="sheet-actions">
          <button class="btn btn-secondary" @click="closeSheet">取消</button>
          <button class="btn btn-primary" @click="addToOrder">加入我的訂單</button>
        </div>
      </div>
    </div>
  </template>
</template>
