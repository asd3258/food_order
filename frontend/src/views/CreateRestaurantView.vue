<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import { userStore } from '../stores/user'
import { toast } from '../stores/toast'
import { requireLogin } from '../auth'
import { optionsToGroups } from '../menuDraft'
import { compressImage } from '../imageCompressor'

interface OptionGroupDraft {
  group: string // e.g. "口味" / "加購"
  type: 'radio' | 'checkbox' // 單選(口味) | 可多選(加購)
  choicesText: string // e.g. "原味,泰式,五辣" or "白飯加量+20,半熟蛋+15"
}
interface ItemDraft {
  name: string
  price: number
  category: string
  optionGroups: OptionGroupDraft[]
}

const router = useRouter()
const name = ref('')
const mapUrl = ref('')
const phone = ref('')
const address = ref('')
const hours = ref('')
const selectedTypes = ref<string[]>([])
const types = ref<{ id: number, name: string }[]>([])
const items = ref<ItemDraft[]>([])
const parsingMenu = ref(false)
const fetchingPlace = ref(false)
const menuFileInput = ref<HTMLInputElement | null>(null)

async function loadTypes() {
  try {
    types.value = await api.listRestaurantTypes()
    if (types.value.length > 0) {
      selectedTypes.value = [types.value[0].name]
    }
  } catch (e) {
    // keep the static fallback if the backend isn't reachable yet
  }
}
onMounted(loadTypes)

// v0.10: "AI 自動生成菜單" -- merges what used to be two separate disabled
// placeholders (上傳菜單照片 AI 解析品項 / 貼上 Google Maps 網址 AI 生成菜單)
// into one section with two independent triggers:
//   1. 上傳照片 -> vision AI extracts 品項清單 (v0.9, unchanged)
//   2. 讀取店家資訊 -> Google Places API fills 電話/地址/營業時間 from the
//      Google Map 連結 above (v0.10). Does NOT touch menu items -- Google's
//      official API has no way to fetch "the menu photos" reliably (see
//      app/places.py's docstring), so that direction only works via manual
//      photo upload.
function triggerMenuUpload() {
  menuFileInput.value?.click()
}
function handleMenuPhoto(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  
  parsingMenu.value = true
  compressImage(file)
    .then(async (dataUrl) => {
      try {
        const parsed = await api.parseMenuPhoto(dataUrl)
        if (!parsed.length) {
          toast('AI 沒有從照片中辨識出品項,請確認照片清晰或改用手動輸入')
        } else {
          for (const it of parsed) {
            items.value.push({ name: it.name, price: it.price, category: it.category || '', optionGroups: optionsToGroups(it.options) })
          }
          toast(`AI 已辨識出 ${parsed.length} 個品項,請檢查並修正後再建立餐廳`)
        }
      } catch {
        // api.ts already toasted the backend's error detail
      } finally {
        parsingMenu.value = false
      }
    })
    .catch(() => {
      toast('圖片處理失敗，請換一張圖片再試')
      parsingMenu.value = false
    })
    
  input.value = ''
}

async function fetchPlaceInfo() {
  if (!mapUrl.value.trim()) {
    toast('請先輸入 Google Map 連結')
    return
  }
  fetchingPlace.value = true
  try {
    const info = await api.fetchPlaceInfo(mapUrl.value.trim())
    if (info.name && !name.value.trim()) name.value = info.name
    if (info.phone) phone.value = info.phone
    if (info.address) address.value = info.address
    if (info.hours) hours.value = info.hours
    toast('已從 Google Map 讀取店名/電話/地址/營業時間,請檢查後再建立餐廳')
  } catch {
    // api.ts already toasted the backend's error detail (缺金鑰/找不到地點等)
  } finally {
    fetchingPlace.value = false
  }
}

function addItemRow() {
  items.value.push({ name: '', price: 0, category: '', optionGroups: [] })
}
function removeItemRow(i: number) {
  items.value.splice(i, 1)
}
function addOptionGroup(i: number) {
  items.value[i].optionGroups.push({ group: '口味', type: 'radio', choicesText: '' })
}
function removeOptionGroup(i: number, gi: number) {
  items.value[i].optionGroups.splice(gi, 1)
}

// "原味,泰式,五辣" -> 3 choices, extra_price 0
// "白飯加量+20,半熟蛋+15,去冰" -> 去冰 also extra_price 0 (no "+數字" suffix)
function parseChoices(text: string, basePrice: number): { option_name: string; extra_price: number }[] {
  return text
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)
    .map((entry) => {
      const m = entry.match(/^(.+?)([-+/*])([\d.]+)$/)
      if (m) {
        const name = m[1].trim()
        const op = m[2]
        const val = parseFloat(m[3])
        let extra = 0
        if (op === '+') extra = val
        else if (op === '-') extra = -val
        else if (op === '*') extra = parseFloat(((basePrice * val) - basePrice).toFixed(1))
        else if (op === '/') extra = parseFloat(((basePrice / val) - basePrice).toFixed(1))
        return { option_name: name, extra_price: extra }
      }
      return { option_name: entry, extra_price: 0 }
    })
}

async function submit() {
  if (!requireLogin()) return
  if (!name.value.trim()) {
    toast('請輸入餐廳名稱')
    return
  }
  const finalType = selectedTypes.value.join(',')
  if (!finalType) {
    alert('請至少選擇一個餐廳類型')
    return
  }
  await api.createRestaurant({
    name: name.value,
    phone: phone.value,
    address: address.value,
    map_url: mapUrl.value,
    hours: hours.value,
    type: finalType,
    created_by: userStore.username,
    menu_items: items.value.map((it) => ({
      name: it.name || '未命名品項',
      price: it.price || 0,
      category: it.category || '',
      options: it.optionGroups.flatMap((g) =>
        parseChoices(g.choicesText, it.price || 0).map((c) => ({
          option_group: g.group || '選項',
          option_type: g.type,
          option_name: c.option_name,
          extra_price: c.extra_price,
        })),
      ),
    })),
  })
  toast('餐廳已建立:' + name.value)
  router.push('/more')
}
</script>

<template>
  <div class="page-header">
    <router-link class="back" to="/more">←</router-link>
    <h1>建立新餐廳</h1>
  </div>

  <section class="block">
    <h2>AI 自動生成菜單</h2>
    <div class="card">
      <div class="form-group">
        <label>Google Map 連結</label>
        <input v-model="mapUrl" placeholder="https://maps.app.goo.gl/..." />
      </div>
      <button class="btn btn-secondary btn-full" :disabled="fetchingPlace || !mapUrl.trim()" @click="fetchPlaceInfo">
        {{ fetchingPlace ? '讀取中...' : '📍 從 Google Map 讀取店名/電話/地址/營業時間' }}
      </button>
    </div>
    <div class="card" style="display:flex;align-items:center;justify-content:space-between;gap:10px;">
      <span style="font-size:13px;">📷 上傳菜單照片,AI 自動解析品項</span>
      <button class="btn btn-secondary" :disabled="parsingMenu" @click="triggerMenuUpload">
        {{ parsingMenu ? 'AI 辨識中...' : '上傳照片' }}
      </button>
    </div>
    <input ref="menuFileInput" type="file" accept="image/*" style="display:none;" @change="handleMenuPhoto" />
  </section>

  <section class="block">
    <h2>餐廳資料(手動輸入)</h2>
    <div class="card">
      <div class="form-group"><label>餐廳名稱</label><input v-model="name" placeholder="例:日式烤肉飯 南崬" /></div>
      <div class="form-group"><label>電話</label><input v-model="phone" placeholder="(03) 312-8111" /></div>
      <div class="form-group"><label>地址</label><input v-model="address" placeholder="桃園市蘆竹區..." /></div>
      <div class="form-group">
        <label>營業時間</label>
        <textarea v-model="hours" rows="4" placeholder="例:&#10;星期一至五 11:00–14:00, 17:00–20:30&#10;星期六日 公休"></textarea>
      </div>
      <div class="form-group restaurant-type-field">
        <div class="field-head">
          <label>餐廳類型</label>
          <span>{{ selectedTypes.length ? `已選 ${selectedTypes.length} 種` : '至少選 1 種' }}</span>
        </div>
        <div class="type-picker">
          <label
            v-for="t in types"
            :key="t.id"
            class="type-option"
            :class="{ selected: selectedTypes.includes(t.name) }"
          >
            <input type="checkbox" :value="t.name" v-model="selectedTypes" />
            <span class="checkmark"></span>
            <span class="type-option-name">{{ t.name }}</span>
          </label>
        </div>
      </div>
    </div>
  </section>

  <section class="block">
    <h2>
      品項清單
      <span style="color:var(--brand);font-weight:600;cursor:pointer;" @click="addItemRow">+ 新增品項</span>
    </h2>
    <div v-if="!items.length" class="empty">尚未新增品項,點右上「+ 新增品項」</div>
    <div v-for="(it, i) in items" :key="i" class="item-row">
      <div class="item-row-head">
        <strong style="font-size:13px;">品項 {{ i + 1 }}</strong>
        <span class="rm" @click="removeItemRow(i)">刪除</span>
      </div>
      <div class="form-group"><label>名稱</label><input v-model="it.name" /></div>
      <div class="form-group"><label>分類</label><input v-model="it.category" placeholder="例:主餐/飲料/小菜" /></div>
      <div class="form-group"><label>價格</label><input v-model.number="it.price" type="number" /></div>

      <div style="margin-top:8px;">
        <div
          v-for="(g, gi) in it.optionGroups"
          :key="gi"
          style="background:#f7f7fb;border:1px solid var(--border);border-radius:8px;padding:8px;margin-bottom:8px;"
        >
          <div class="item-row-head" style="margin-bottom:6px;">
            <strong style="font-size:12px;color:var(--muted);">選項群組 {{ gi + 1 }}</strong>
            <span class="rm" @click="removeOptionGroup(i, gi)">刪除群組</span>
          </div>
          <div class="form-group">
            <label>群組名稱(例:口味 / 加購)</label>
            <input v-model="g.group" placeholder="口味" />
          </div>
          <div class="form-group">
            <label>選擇方式</label>
            <select v-model="g.type">
              <option value="radio">單選(例如口味)</option>
              <option value="checkbox">可多選(例如加購)</option>
            </select>
          </div>
          <div class="form-group">
            <label>選項內容(用逗號分開;要加價的用「名稱+金額」,例:白飯加量+20)</label>
            <input v-model="g.choicesText" placeholder="原味,泰式,五辣" />
          </div>
        </div>
        <span style="color:var(--brand);font-weight:600;cursor:pointer;font-size:13px;" @click="addOptionGroup(i)">
          + 新增選項群組(口味/加購)
        </span>
      </div>
    </div>
  </section>

  <button class="btn btn-primary btn-full" @click="submit">建立餐廳</button>
</template>

<style scoped>
.field-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}
.field-head label {
  margin: 0;
}
.field-head span {
  color: var(--muted);
  font-size: 12px;
}
.type-picker {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(118px, 1fr));
  gap: 8px;
}
.type-option {
  position: relative;
  display: flex;
  align-items: center;
  gap: 9px;
  min-height: 44px;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: #fff;
  color: var(--text);
  cursor: pointer;
  transition: border-color .15s ease, background .15s ease, color .15s ease;
}
.type-option input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}
.checkmark {
  width: 18px;
  height: 18px;
  border: 2px solid #c7c5d8;
  border-radius: 6px;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  background: #fff;
}
.checkmark::after {
  content: "";
  width: 8px;
  height: 5px;
  border-left: 2px solid #fff;
  border-bottom: 2px solid #fff;
  transform: rotate(-45deg) translate(1px, -1px);
  opacity: 0;
}
.type-option.selected {
  border-color: var(--brand);
  background: #f0efff;
  color: var(--brand);
  font-weight: 700;
}
.type-option.selected .checkmark {
  border-color: var(--brand);
  background: var(--brand);
}
.type-option.selected .checkmark::after {
  opacity: 1;
}
.type-option-name {
  min-width: 0;
  overflow-wrap: anywhere;
}
:global(html.large-mode) .field-head span {
  font-size: 14px;
}
:global(html.large-mode) .type-option {
  min-height: 50px;
  font-size: 16px;
}
:global(html.large-mode) .checkmark {
  width: 22px;
  height: 22px;
}
</style>
