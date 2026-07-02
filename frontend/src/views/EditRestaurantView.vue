<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, RESTAURANT_TYPES, type RestaurantDetail } from '../api'
import { confirmAction } from '../stores/confirm'
import { toast } from '../stores/toast'

const route = useRoute()
const router = useRouter()
const restaurantId = Number(route.params.id)

const name = ref('')
const phone = ref('')
const address = ref('')
const type = ref(RESTAURANT_TYPES[0])
const photos = ref<{ id?: number; image_url: string; caption: string; isNew?: boolean }[]>([])
const items = ref<{ id?: number; name: string; price: number }[]>([])
const fileInput = ref<HTMLInputElement | null>(null)

async function load() {
  const r: RestaurantDetail = await api.getRestaurantMenu(restaurantId)
  name.value = r.name
  phone.value = r.phone
  address.value = r.address
  type.value = r.type
  photos.value = r.photos.map((p) => ({ id: p.id, image_url: p.image_url, caption: p.caption }))
  items.value = r.menu_items.map((m) => ({ id: m.id, name: m.name, price: m.price }))
}
onMounted(load)

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
  items.value.push({ name: '', price: 0 })
}
function removeItemRow(index: number) {
  items.value.splice(index, 1)
}

async function save() {
  await api.updateRestaurant(restaurantId, {
    name: name.value,
    phone: phone.value,
    address: address.value,
    type: type.value,
    menu_items: items.value.map((it) => ({ name: it.name, price: it.price, options: [] })),
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
      <div class="form-group"><label>電話</label><input v-model="phone" /></div>
      <div class="form-group"><label>地址</label><input v-model="address" /></div>
      <div class="form-group">
        <label>餐廳類型</label>
        <select v-model="type">
          <option v-for="t in RESTAURANT_TYPES" :key="t" :value="t">{{ t }}</option>
        </select>
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
      <div v-for="(p, i) in photos" :key="p.id ?? 'new-' + i" class="photo-thumb">
        <img v-if="!p.image_url.startsWith('placeholder:')" :src="p.image_url" />
        <div v-else class="ph-ph" :style="{ background: p.image_url.replace('placeholder:', '') }">📷</div>
        <span class="ph-rm" @click="removePhoto(i)">×</span>
      </div>
    </div>
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
    </div>
  </section>

  <button class="btn btn-primary btn-full" @click="save">儲存變更</button>
</template>
