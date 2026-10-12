<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, type OrderOut, type RestaurantDetail, type MenuItem, type Photo, type StatRow } from '../api'
import { HOURS, MINUTES, formatDeadline, isoToParts, partsToIso, type DeadlineParts, defaultDeadline } from '../deadline'
import { userStore } from '../stores/user'
import { confirmAction, alertWarning } from '../stores/confirm'
import { toast } from '../stores/toast'
import { canWebShare, copyLink, copyText, shareLink } from '../share'
import { requireLogin } from '../auth'
import ImageLightbox from '../components/ImageLightbox.vue'

const route = useRoute()
const router = useRouter()
const orderId = Number(route.params.id)

const order = ref<OrderOut | null>(null)
const restaurant = ref<RestaurantDetail | null>(null)
const stats = ref<StatRow[]>([])
const editDeadline = ref<DeadlineParts | null>(null)
const photoTrackRef = ref<HTMLElement | null>(null)
const lightboxOpen = ref(false)
const lightboxPhoto = ref<Photo | null>(null)

function scrollPhotos(dir: number) {
  const track = photoTrackRef.value
  if (track) track.scrollBy({ left: dir * track.clientWidth, behavior: 'smooth' })
}
function openPhoto(photo: Photo) {
  lightboxPhoto.value = photo
  lightboxOpen.value = true
}
function closePhoto() {
  lightboxOpen.value = false
}

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
  return sorted.map((category) => {
    // 每個類別內用金額(小到大排序)
    const sortedItems = groups[category].slice().sort((a, b) => a.price - b.price)
    return { category, items: sortedItems }
  })
})

// v0.12: 改用 userStore.can 統一判斷權限
const isInitiator = computed(() => {
  if (!order.value) return false
  return userStore.can('訂單', 'delete', order.value.initiator)
})
const canModify = computed(() => {
  if (!order.value) return false
  const canUpdate = userStore.can('訂單', 'update', order.value.initiator)
  if (!canUpdate) return false
  if (!order.value.is_locked) return true
  return isInitiator.value
})
// v0.19: 「已售完」標記 -- 只在訂單還開著時能改,權限跟鎖單/結單一樣是
// 訂單建立者 & admin(後端用 check_permission(訂單, delete) 再驗一次)。
const canMarkSoldOut = computed(() => !!order.value && order.value.status === 'open' && isInitiator.value)
const soldOutItemIds = computed(
  () => new Set((order.value?.sold_outs || []).filter((s) => !s.option_name).map((s) => s.menu_item_id)),
)
const soldOutOptionKeys = computed(
  () => new Set(
    (order.value?.sold_outs || [])
      .filter((s) => s.option_name)
      .map((s) => `${s.menu_item_id}|${s.option_group}|${s.option_name}`),
  ),
)
function isItemSoldOut(item: MenuItem): boolean {
  return soldOutItemIds.value.has(item.id)
}
function isOptionSoldOut(item: MenuItem, group: string, name: string): boolean {
  return soldOutOptionKeys.value.has(`${item.id}|${group}|${name}`)
}
async function toggleItemSoldOut(item: MenuItem) {
  if (!order.value) return
  const marks = await api.toggleSoldOut(
    orderId,
    { menu_item_id: item.id, sold_out: !isItemSoldOut(item) },
    userStore.username,
  )
  order.value.sold_outs = marks
  toast(isItemSoldOut(item) ? `已標記「${item.name}」售完` : `已恢復供應「${item.name}」`)
}
async function toggleOptionSoldOut(item: MenuItem, group: string, name: string) {
  if (!order.value) return
  const marks = await api.toggleSoldOut(
    orderId,
    { menu_item_id: item.id, option_group: group, option_name: name, sold_out: !isOptionSoldOut(item, group, name) },
    userStore.username,
  )
  order.value.sold_outs = marks
  toast(isOptionSoldOut(item, group, name) ? `已標記「${name}」售完` : `已恢復供應「${name}」`)
}

const myLines = computed(() => stats.value.filter((s) => s.user === userStore.username && !s.is_deleted))
const myTotal = computed(() => myLines.value.reduce((sum, l) => sum + l.amount, 0))
const allTotal = computed(() => stats.value.filter((s) => !s.is_deleted).reduce((sum, s) => sum + s.amount, 0))
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
    await alertWarning('截止時間不能早於現在')
    return
  }
  await api.updateOrderDeadline(orderId, isoDeadline, userStore.username)
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
  if (isItemSoldOut(item)) {
    toast(`「${item.name}」已售完`)
    return
  }
  if (!canModify.value) {
    toast('此訂單已鎖單，無法點餐')
    return
  }
  sheetItem.value = item
  sheetChoices.value = {}
  for (const group of Array.from(new Set(item.options.map((o) => o.option_group)))) {
    const groupOptions = item.options.filter((o) => o.option_group === group)
    // 單選群組的預設值要跳過已售完的選項,免得一打開就選到不能點的東西。
    const firstAvailable = groupOptions.find((o) => !isOptionSoldOut(item, group, o.option_name))
    if (groupOptions[0]?.option_type === 'radio' && firstAvailable) {
      sheetChoices.value[group] = [firstAvailable.option_name]
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
  const item = sheetItem.value
  if (isItemSoldOut(item)) {
    await alertWarning(`「${item.name}」已售完`)
    closeSheet()
    return
  }
  const selected = Object.values(sheetChoices.value).flat()
  // 彈層開著的時候別人可能剛把某個選項標成售完(WebSocket 會即時更新反灰狀態),
  // 送出前再擋一次;後端也會再驗一次。
  const soldOutPick = Object.entries(sheetChoices.value)
    .flatMap(([group, names]) => names.map((name) => ({ group, name })))
    .find(({ group, name }) => isOptionSoldOut(item, group, name))
  if (soldOutPick) {
    await alertWarning(`選項「${soldOutPick.name}」已售完,請改選其他選項`)
    return
  }
  const extraPrice = selected.reduce((sum, name) =>
    sum + (item.options.find(option => option.option_name === name)?.extra_price || 0), 0)
  const amount = (item.price + extraPrice) * sheetQty.value
  if (!Number.isFinite(amount) || Math.abs(amount - Math.round(amount)) > 1e-8) {
    await alertWarning(`品項總價不能有小數點（目前為 ${Number(amount.toFixed(8))} 元），請調整數量或選項，使總價為整數。`)
    return
  }
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
  const ok = await confirmAction('確定要鎖單嗎?鎖單後其他人將無法進入。')
  if (!ok) return
  await api.lockOrder(orderId, userStore.username)
  toast('已鎖單')
  load()
}

async function unlockOrder() {
  const ok = await confirmAction('確定要解除鎖單嗎?解除後其他人將可以進入。')
  if (!ok) return
  await api.unlockOrder(orderId, userStore.username)
  toast('已解除鎖單')
  load()
}

async function closeOrder() {
  const ok = await confirmAction('確定要完成訂單嗎?統計結果將寫入歷史訂單。')
  if (!ok) return
  await api.closeOrder(orderId, userStore.username)
  toast('已完成訂單')
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

const sortedStats = computed(() => {
  return [...stats.value].sort((a, b) => {
    return (
      a.user.localeCompare(b.user) ||
      a.label.localeCompare(b.label) ||
      b.quantity - a.quantity ||
      b.amount - a.amount
    )
  })
})

function getItemStats() {
  const counts: Record<string, number> = {}
  for (const s of stats.value) {
    if (s.is_deleted) continue
    counts[s.label] = (counts[s.label] || 0) + s.quantity
  }
  return Object.entries(counts)
    .map(([label, count]) => ({ label, count }))
    .sort((a, b) => b.count - a.count)
}

function getTotalItemCount() {
  return stats.value.filter(s => !s.is_deleted).reduce((sum, s) => sum + s.quantity, 0)
}

type LabelPart = { text: string; temperatureTone: 'warm' | 'hot' | null }

function temperatureOptionNames(stat: StatRow): string[] {
  const orderItem = order.value?.items.find((item) => item.id === stat.item_id)
  if (!orderItem?.menu_item_id) return []

  const menuItem = restaurant.value?.menu_items.find((item) => item.id === orderItem.menu_item_id)
  if (!menuItem) return []

  return menuItem.options
    .filter((option) => option.option_group.trim() === '溫度')
    .filter((option) => orderItem.selected_options.includes(option.option_name))
    .map((option) => option.option_name)
    .filter((name) => name.includes('溫') || name.includes('熱'))
    .sort((a, b) => b.length - a.length)
}

function labelParts(stat: StatRow): LabelPart[] {
  const optionNames = temperatureOptionNames(stat)
  if (!optionNames.length) return [{ text: stat.label, temperatureTone: null }]

  const parts: LabelPart[] = []
  let cursor = 0
  while (cursor < stat.label.length) {
    let matchIndex = -1
    let matchName = ''
    for (const name of optionNames) {
      const index = stat.label.indexOf(name, cursor)
      if (index !== -1 && (matchIndex === -1 || index < matchIndex)) {
        matchIndex = index
        matchName = name
      }
    }
    if (matchIndex === -1) {
      parts.push({ text: stat.label.slice(cursor), temperatureTone: null })
      break
    }
    if (matchIndex > cursor) parts.push({ text: stat.label.slice(cursor, matchIndex), temperatureTone: null })
    parts.push({
      text: matchName,
      temperatureTone: matchName.includes('熱') ? 'hot' : 'warm',
    })
    cursor = matchIndex + matchName.length
  }
  return parts
}
</script>

<template>
  <div class="page-header">
    <router-link class="back" to="/">←</router-link>
    <h1>{{ restaurant?.name || '點餐' }}</h1>
  </div>

  <template v-if="order && restaurant">
    <div class="btn-row">
      <button class="btn btn-secondary" @click="copyMapLink(restaurant)">📋 複製地圖連結</button>
      <a class="btn btn-secondary" :href="mapUrl(restaurant)" target="_blank">📍 在 Google Maps 開啟</a>
    </div>

    <div v-if="!isInitiator" class="deadline-inline">
      <span>截止時間</span><strong>{{ order.deadline_at ? formatDeadline(order.deadline_at) : '(未設定)' }}</strong>
      <button class="btn btn-secondary" @click="doCopyLink">🔗 複製訂單連結</button>
    </div>
    <div v-else-if="editDeadline" class="deadline-inline">
      <span>截止時間</span>
      <input v-model="editDeadline.date" type="date" class="time-select" :class="{ 'input-invalid': isDeadlineInvalid }" />
      <select v-model.number="editDeadline.hour" class="time-select" :class="{ 'input-invalid': isDeadlineInvalid }">
        <option v-for="h in HOURS" :key="h" :value="h">{{ String(h).padStart(2, '0') }}</option>
      </select>
      <span>:</span>
      <select v-model.number="editDeadline.minute" class="time-select" :class="{ 'input-invalid': isDeadlineInvalid }">
        <option v-for="m in MINUTES" :key="m" :value="m">{{ String(m).padStart(2, '0') }}</option>
      </select>
      <button class="btn btn-secondary" style="flex:none;padding:7px 12px;" :disabled="order.is_locked" @click="updateDeadline">更新</button>
      <button class="btn btn-secondary" @click="doCopyLink">🔗 複製訂單連結</button>
    </div>

    <div v-if="shareSupported" class="btn-row">
      <button class="btn btn-secondary" @click="doShare">📤 分享</button>
    </div>

    <div v-if="isInitiator" class="btn-row">
      <button v-if="!order.is_locked" class="btn btn-secondary" @click="lockOrder">鎖單</button>
      <button v-if="order.is_locked" class="btn btn-secondary" @click="unlockOrder">解除鎖單</button>
      <button v-if="order.is_locked" class="btn btn-secondary" @click="closeOrder">完成訂單</button>
      <button class="btn btn-danger" @click="deleteOrder">刪除</button>
    </div>

    <div class="menu-cat" style="font-size:12px;color:var(--muted);font-weight:600;">餐廳圖片</div>
    <div class="carousel order-photo-carousel">
      <div ref="photoTrackRef" class="carousel-track">
        <div v-if="!restaurant.photos.length" class="carousel-slide" style="background:#999;">📷</div>
        <div
          v-for="photo in restaurant.photos"
          :key="photo.id"
          class="carousel-slide"
          :style="photo.image_url.startsWith('placeholder:') ? { background: photo.image_url.replace('placeholder:', '') } : {}"
          @click="openPhoto(photo)"
        >
          <img v-if="!photo.image_url.startsWith('placeholder:')" :src="photo.image_url" :alt="photo.caption || `${restaurant.name} 餐廳圖片`" />
          <span v-else>📷</span>
          <span v-if="photo.caption" class="cap">{{ photo.caption }}</span>
        </div>
      </div>
      <button class="carousel-arrow left" @click="scrollPhotos(-1)">‹</button>
      <button class="carousel-arrow right" @click="scrollPhotos(1)">›</button>
    </div>

    <ImageLightbox
      :visible="lightboxOpen"
      :image-url="lightboxPhoto?.image_url"
      :placeholder-color="lightboxPhoto?.image_url.startsWith('placeholder:') ? lightboxPhoto.image_url.replace('placeholder:', '') : null"
      :caption="lightboxPhoto?.caption"
      @close="closePhoto"
    />

    <div v-for="grp in groupedMenu" :key="grp.category">
      <div class="menu-cat" style="margin-top:14px;font-size:12px;color:var(--muted);font-weight:600;">{{ grp.category }}</div>
      <div
        v-for="m in grp.items"
        :key="m.id"
        class="menu-item"
        :class="{ 'is-sold-out': isItemSoldOut(m) }"
        @click="openItemSheet(m)"
      >
        <div>
          <div class="mi-name">
            <span class="mi-label">{{ m.name }}</span>
            <span v-if="isItemSoldOut(m)" class="sold-out-badge">已售完</span>
          </div>
          <div class="mi-price">${{ m.price }}</div>
        </div>
        <div class="mi-actions">
          <button
            v-if="canMarkSoldOut"
            type="button"
            class="soldout-btn"
            :class="{ active: isItemSoldOut(m) }"
            @click.stop="toggleItemSoldOut(m)"
          >{{ isItemSoldOut(m) ? '恢復供應' : '標記售完' }}</button>
          <div class="plus-badge" v-if="canModify && !isItemSoldOut(m)">+</div>
        </div>
      </div>
    </div>

    <section class="block">
      <h2 class="h2-highlight">我的訂單</h2>
      <div class="card card-highlight">
        <div v-if="!myLines.length" class="empty">尚未選擇品項</div>
        <div v-else v-for="l in myLines" :key="l.item_id" class="cart-line">
          <span>{{ l.label }} × {{ l.quantity }}</span>
          <span>${{ l.amount }} <span class="rm" v-if="canModify" @click="removeMyLine(l.item_id)">移除</span></span>
        </div>
      </div>
      <div class="cart-bar">
        <span>小計</span>
        <strong>${{ myTotal }}</strong>
      </div>
    </section>

    <section class="block">
      <h2>目前所有人統計(彙總)</h2>
      <div class="card">
        <table class="stat-table">
          <tr><th>品項 / 選項</th><th>人員</th><th>數量</th><th>金額</th></tr>
          <tr v-if="!sortedStats.length"><td colspan="4" style="color:var(--muted);">尚無資料</td></tr>
          <tr v-for="s in sortedStats" :key="s.item_id" :style="s.is_deleted ? 'opacity:.5;text-decoration:line-through;' : ''">
            <td>
              <template v-for="(part, index) in labelParts(s)" :key="index">
                <span :class="part.temperatureTone ? `temperature-${part.temperatureTone}` : undefined">{{ part.text }}</span>
              </template>
            </td>
            <td>{{ s.user }}</td>
            <td>{{ s.quantity }}</td>
            <td>
              ${{ s.amount }}
              <span v-if="!s.is_deleted && s.user !== userStore.username && isInitiator" class="rm" @click="softDelete(s.item_id)">刪除</span>
            </td>
          </tr>
          <tr style="font-weight: 600; background-color: var(--bg); border-top: 1px solid var(--border);">
            <td colspan="3">總金額</td>
            <td>${{ allTotal }}</td>
          </tr>
        </table>
        
        <div class="menu-cat" style="margin-top:16px;font-size:12px;color:var(--muted);font-weight:600;">
          品項統計(總共{{ getTotalItemCount() }}個)
        </div>
        <table class="stat-table" style="margin-top:4px;">
          <tr>
            <th>品項</th>
            <th style="text-align: right; width: 60px;">總數</th>
          </tr>
          <tr v-for="stat in getItemStats()" :key="stat.label">
            <td>{{ stat.label }}</td>
            <td style="text-align: right;">{{ stat.count }}</td>
          </tr>
          <tr style="font-weight: 600; background-color: var(--bg); border-top: 1px solid var(--border);">
            <td>總共</td>
            <td style="text-align: right;">{{ getTotalItemCount() }}</td>
          </tr>
        </table>
      </div>
    </section>

    <!-- v0.21: teleported to <body>. This overlay used to live inside
         main.content, and on iOS Safari a scroll container with
         -webkit-overflow-scrolling:touch becomes the containing block for
         position:fixed descendants -- so the sheet was boxed into the
         content area and the bottom nav drew over its action buttons. -->
    <Teleport to="body">
    <div class="overlay" :class="{ active: sheetOpen }" @click.self="closeSheet">
      <div class="sheet order-item-sheet" v-if="sheetItem">
        <h3>{{ sheetItem.name }}</h3>
        <div class="price">${{ sheetItem.price }} 起</div>

        <div v-if="!sheetItem.options.length" class="empty" style="text-align:left;padding:4px 0;">此品項無客製選項</div>
        <div v-for="g in groupsOf(sheetItem)" :key="g.group">
          <div class="opt-group-title">{{ g.group }}{{ g.type === 'radio' ? '(單選)' : '(可多選)' }}</div>
          <label
            v-for="c in g.choices"
            :key="c.option_name"
            class="opt-choice"
            :class="{ 'is-sold-out': isOptionSoldOut(sheetItem, g.group, c.option_name) }"
          >
            <input
              v-if="g.type === 'radio'"
              type="radio"
              :name="g.group"
              :disabled="isOptionSoldOut(sheetItem, g.group, c.option_name)"
              :checked="sheetChoices[g.group]?.[0] === c.option_name"
              @change="onRadioPick(g.group, c.option_name)"
            />
            <input
              v-else
              type="checkbox"
              :disabled="isOptionSoldOut(sheetItem, g.group, c.option_name)"
              :checked="sheetChoices[g.group]?.includes(c.option_name)"
              @change="onCheckboxToggle(g.group, c.option_name, ($event.target as HTMLInputElement).checked)"
            />
            <span class="opt-label">{{ c.option_name }}<template v-if="c.extra_price"> ({{ c.extra_price > 0 ? '+$' + c.extra_price : '-$' + (-c.extra_price) }})</template></span>
            <span v-if="isOptionSoldOut(sheetItem, g.group, c.option_name)" class="sold-out-badge">已售完</span>
            <button
              v-if="canMarkSoldOut"
              type="button"
              class="soldout-btn"
              :class="{ active: isOptionSoldOut(sheetItem, g.group, c.option_name) }"
              @click.prevent.stop="toggleOptionSoldOut(sheetItem, g.group, c.option_name)"
            >{{ isOptionSoldOut(sheetItem, g.group, c.option_name) ? '恢復供應' : '標記售完' }}</button>
          </label>
        </div>

        <div class="qty-row">
          <span class="qty-label">數量</span>
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
    </Teleport>
  </template>
</template>
