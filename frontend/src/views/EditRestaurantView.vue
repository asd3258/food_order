<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, RESTAURANT_TYPES, type RestaurantDetail, type MenuItem } from '../api'
import { confirmAction } from '../stores/confirm'
import { toast } from '../stores/toast'
import ImageLightbox from '../components/ImageLightbox.vue'
import { requireLogin } from '../auth'

interface OptionGroupDraft {
  group: string
  type: 'radio' | 'checkbox'
  choicesText: string
}
interface ItemDraft {
  id?: number
  name: string
  price: number
  optionGroups: OptionGroupDraft[]
}

const route = useRoute()
const router = useRouter()
const restaurantId = Number(route.params.id)

const name = ref('')
const mapUrl = ref('')
const phone = ref('')
const address = ref('')
const type = ref(RESTAURANT_TYPES[0])
const customType = ref('') // v0.7: 餐廳類型 manual entry, overrides the dropdown when filled
const types = ref<string[]>(RESTAURANT_TYPES)
const photos = ref<{ id?: number; image_url: string; caption: string; isNew?: boolean }[]>([])
const items = ref<ItemDraft[]>([])
const fileInput = ref<HTMLInputElement | null>(null)

async function loadTypes() {
  try {
    types.value = await api.listRestaurantTypes()
  } catch {
    // keep the static fallback if the backend isn't reachable yet
  }
}

const lightboxOpen = ref(false)
const lightboxPhoto = ref<{ image_url: string; caption: string } | null>(null)
function openLightbox(p: { image_url: string; caption: string }) {
  lightboxPhoto.value = p
  lightboxOpen.value = true
}
function closeLightbox() {
  lightboxOpen.value = false
}

// Turn the flat MenuItemOption[] the backend returns back into editable
// group rows -- inverse of parseChoices() below. Groups are kept in the
// order their first option appeared.
function groupsFromMenuItem(m: MenuItem): OptionGroupDraft[] {
  const order: string[] = []
  const byGroup: Record<string, { type: 'radio' | 'checkbox'; choices: string[] }> = {}
  for (const o of m.options) {
    if (!byGroup[o.option_group]) {
      byGroup[o.option_group] = { type: o.option_type as 'radio' | 'checkbox', choices: [] }
      order.push(o.option_group)
    }
    byGroup[o.option_group].choices.push(o.extra_price ? `${o.option_name}+${o.extra_price}` : o.option_name)
  }
  return order.map((group) => ({ group, type: byGroup[group].type, choicesText: byGroup[group].choices.join(',') }))
}
function parseChoices(text: string): { option_name: string; extra_price: number }[] {
  return text
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)
    .map((entry) => {
      const m = entry.match(/^(.+?)\+(\d+)$/)
      if (m) return { option_name: m[1].trim(), extra_price: parseInt(m[2], 10) }
      return { option_name: entry, extra_price: 0 }
    })
}

async function load() {
  const r: RestaurantDetail = await api.getRestaurantMenu(restaurantId)
  name.value = r.name
  mapUrl.value = r.map_url || ''
  phone.value = r.phone
  address.value = r.address
  type.value = r.type
  photos.value = r.photos.map((p) => ({ id: p.id, image_url: p.image_url, caption: p.caption }))
  items.value = r.menu_items.map((m) => ({ id: m.id, name: m.name, price: m.price, optionGroups: groupsFromMenuItem(m) }))
}
onMounted(load)
onMounted(loadTypes)

function triggerUpload() {
  fileInput.value?.click()
}
function handleFile(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = () => {
    photos.value.push({ image_url: String(reader.result), caption: file.name, isNew: true })
    toast('已加入圖片,按「儲存變更」後才會真正上傳')
  }
  reader.readAsDataURL(file)
  input.value = ''
}
async function removePhoto(index: number) {
  const ok = await confirmAction('確定要刪除這張圖片嗎?')
  if (!ok) return
  const photo = photos.value[index]
  if (photo.id) {
    await api.deletePhoto(restaurantId, photo.id)
  }
  photos.value.splice(index, 1)
  toast('已刪除圖片')
}

function addItemRow() {
  items.value.push({ name: '', price: 0, optionGroups: [] })
}
function removeItemRow(index: number) {
  items.value.splice(index, 1)
}
function addOptionGroup(i: number) {
  items.value[i].optionGroups.push({ group: '口味', type: 'radio', choicesText: '' })
}
function removeOptionGroup(i: number, gi: number) {
  items.value[i].optionGroups.splice(gi, 1)
}

async function save() {
  if (!requireLogin()) return
  const finalType = customType.value.trim() || type.value
  await api.updateRestaurant(restaurantId, {
    name: name.value,
    phone: phone.value,
    address: address.value,
    map_url: mapUrl.value,
    type: finalType,
    menu_items: items.value.map((it) => ({
      name: it.name,
      price: it.price,
      options: it.optionGroups.flatMap((g) =>
        parseChoices(g.choicesText).map((c) => ({
          option_group: g.group || '選項',
          option_type: g.type,
          option_name: c.option_name,
          extra_price: c.extra_price,
        })),
      ),
    })),
  })
  for (const p of photos.value) {
    if (p.isNew) {
      await api.uploadPhoto(restaurantId, p.image_url, p.caption)
    }
  }
  toast('餐廳資料已更新')
  router.push(`/restaurants/${restaurantId}`)
}

function cancel() {
  router.push(`/restaurants/${restaurantId}`)
}

async function removeRestaurant() {
  if (!requireLogin()) return
  const ok = await confirmAction(`確定要刪除「${name.value}」這間餐廳嗎?菜單/照片會一併刪除,此動作無法復原。`)
  if (!ok) return
  try {
    await api.deleteRestaurant(restaurantId)
  } catch {
    // api.ts already toasts the backend's error detail (e.g. "此餐廳目前有
    // 進行中的訂單...") -- nothing else to do here.
    return
  }
  toast('已刪除餐廳:' + name.value)
  router.push('/restaurants')
}
</script>

<template>
  <div class="page-header">
    <a class="back" href="#" @click.prevent="cancel">←</a>
    <h1>編輯餐廳</h1>
  </div>

  <section class="block">
    <h2>餐廳資料</h2>
    <div class="card">
      <div class="form-group"><label>餐廳名稱</label><input v-model="name" /></div>
      <div class="form-group"><label>Google Map 連結</label><input v-model="mapUrl" placeholder="https://maps.app.goo.gl/..." /></div>
      <div class="form-group"><label>電話</label><input v-model="phone" /></div>
      <div class="form-group"><label>地址</label><input v-model="address" /></div>
      <div class="form-group">
        <label>餐廳類型</label>
        <select v-model="type">
          <option v-for="t in types" :key="t" :value="t">{{ t }}</option>
        </select>
      </div>
      <div class="form-group">
        <label>或手動輸入新類型(填了會取代上面的選擇)</label>
        <input v-model="customType" placeholder="例:火鍋" />
      </div>
    </div>
  </section>

  <section class="block">
    <h2>
      餐廳照片
      <span style="color:var(--brand);font-weight:600;cursor:pointer;" @click="triggerUpload">+ 上傳圖片</span>
    </h2>
    <input ref="fileInput" type="file" accept="image/*" style="display:none;" @change="handleFile" />
    <div v-if="!photos.length" class="empty">尚未上傳照片</div>
    <div v-else style="display:flex;flex-wrap:wrap;gap:8px;">
      <div v-for="(p, i) in photos" :key="p.id ?? 'new-' + i" class="photo-thumb" style="cursor:pointer;" @click="openLightbox(p)">
        <img v-if="!p.image_url.startsWith('placeholder:')" :src="p.image_url" />
        <div v-else class="ph-ph" :style="{ background: p.image_url.replace('placeholder:', '') }">📷</div>
        <span class="ph-rm" @click.stop="removePhoto(i)">×</span>
      </div>
    </div>

    <ImageLightbox
      :visible="lightboxOpen"
      :image-url="lightboxPhoto?.image_url"
      :placeholder-color="lightboxPhoto?.image_url.startsWith('placeholder:') ? lightboxPhoto.image_url.replace('placeholder:', '') : null"
      :caption="lightboxPhoto?.caption"
      @close="closeLightbox"
    />
  </section>

  <section class="block">
    <h2>
      品項清單
      <span style="color:var(--brand);font-weight:600;cursor:pointer;" @click="addItemRow">+ 新增品項</span>
    </h2>
    <div v-if="!items.length" class="empty">尚未新增品項</div>
    <div v-for="(it, i) in items" :key="it.id ?? 'new-' + i" class="item-row">
      <div class="item-row-head">
        <strong style="font-size:13px;">品項 {{ i + 1 }}</strong>
        <span class="rm" @click="removeItemRow(i)">刪除</span>
      </div>
      <div class="form-group"><label>名稱</label><input v-model="it.name" /></div>
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

  <button class="btn btn-primary btn-full" @click="save">儲存變更</button>
  <button class="btn btn-danger btn-full" style="margin-top:10px;" @click="removeRestaurant">🗑️ 刪除餐廳</button>
</template>
