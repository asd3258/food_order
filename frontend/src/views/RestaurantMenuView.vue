<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, type RestaurantDetail, type MenuItem, type OptionChoice, type Photo } from '../api'
import { userStore } from '../stores/user'
import ImageLightbox from '../components/ImageLightbox.vue'
import { copyText } from '../share'

const route = useRoute()
const router = useRouter()
const restaurant = ref<RestaurantDetail | null>(null)
const trackRef = ref<HTMLElement | null>(null)

// v0.10: 分類 grouping is back -- group items by category, keeping the
// order each category first appears in, with uncategorized items lumped
// under 未分類 at the end.
const groupedMenu = computed(() => {
  const items = restaurant.value?.menu_items || []
  const order: string[] = []
  const groups: Record<string, MenuItem[]> = {}
  for (const m of items) {
    const cat = m.category?.trim() || '未分類'
    if (!groups[cat]) {
      groups[cat] = []
      if (cat === '未分類') order.push(cat)
      else order.unshift(cat)
    }
    groups[cat].push(m)
  }
  // keep 未分類 last regardless of insertion order above
  const sorted = order.filter((c) => c !== '未分類').concat(order.includes('未分類') ? ['未分類'] : [])
  return sorted.map((category) => {
    return {
      category,
      items: groups[category].sort((a, b) => a.price - b.price)
    }
  })
})

const lightboxOpen = ref(false)
const lightboxPhoto = ref<Photo | null>(null)
function openLightbox(p: Photo) {
  lightboxPhoto.value = p
  lightboxOpen.value = true
}
function closeLightbox() {
  lightboxOpen.value = false
}

function flavorStr(options: OptionChoice[]): string {
  const groups = groupBy(options.filter((o) => o.option_type === 'radio'))
  if (Object.keys(groups).length === 0) return '無'
  return Object.values(groups).map((names) => names.join('/')).join(' | ')
}
function addonStr(options: OptionChoice[]): string {
  const groups = groupBy(options.filter((o) => o.option_type === 'checkbox'), true)
  if (Object.keys(groups).length === 0) return '無'
  return Object.values(groups).map((names) => names.join('/')).join(' | ')
}
function groupBy(options: OptionChoice[], withPrice = false): Record<string, string[]> {
  const out: Record<string, string[]> = {}
  for (const o of options) {
    out[o.option_group] = out[o.option_group] || []
    out[o.option_group].push(withPrice && o.extra_price ? `${o.option_name}(${o.extra_price > 0 ? '+$' + o.extra_price : '-$' + (-o.extra_price)})` : o.option_name)
  }
  return out
}

function mapUrl(r: RestaurantDetail): string {
  // v0.7: prefer the manually-entered Google Map 連結 (more accurate than a
  // generated search query) -- fall back to an auto-generated search URL
  // for restaurants that don't have one set yet.
  if (r.map_url && r.map_url.trim()) return r.map_url.trim()
  return 'https://www.google.com/maps/search/?api=1&query=' + encodeURIComponent(r.name + ' ' + r.address)
}

async function load() {
  restaurant.value = await api.getRestaurantMenu(Number(route.params.id))
}
onMounted(load)

function scrollCarousel(dir: number) {
  const el = trackRef.value
  if (!el) return
  el.scrollBy({ left: dir * el.clientWidth, behavior: 'smooth' })
}

function goEdit() {
  router.push(`/restaurants/${route.params.id}/edit`)
}

// v0.12: 原本單一顆「在 Google Maps 開啟」按鈕拆成兩個功能。
function copyMapLink(r: RestaurantDetail) {
  copyText(mapUrl(r), '已複製地圖連結')
}
</script>

<template>
  <div class="page-header">
    <router-link class="back" to="/restaurants">←</router-link>
    <h1>{{ restaurant?.name || '餐廳菜單' }}</h1>
  </div>

  <button v-if="restaurant && userStore.can('編輯餐廳資料', 'update', restaurant.created_by)" class="btn btn-secondary btn-full" style="margin-bottom:14px;" @click="goEdit">✏️ 編輯餐廳資料</button>

  <template v-if="restaurant">
    <template v-if="restaurant.menu_items.length">
      <div v-for="grp in groupedMenu" :key="grp.category">
        <div class="menu-cat" style="margin-top:14px;font-size:12px;color:var(--muted);font-weight:600;">{{ grp.category }}</div>
        <table class="stat-table" style="table-layout: fixed;">
          <tr>
            <th style="width: 40%;">品項名稱</th>
            <th style="width: 25%;">口味</th>
            <th style="width: 20%;">加購</th>
            <th style="width: 15%;">金額</th>
          </tr>
          <tr v-for="m in grp.items" :key="m.id">
            <td>{{ m.name }}</td>
            <td>{{ flavorStr(m.options) }}</td>
            <td>{{ addonStr(m.options) }}</td>
            <td>${{ m.price }}</td>
          </tr>
        </table>
      </div>
    </template>
    <div v-else class="empty">此餐廳尚未建立菜單</div>

    <div class="menu-cat" style="margin-top:16px;font-size:12px;color:var(--muted);font-weight:600;">餐廳照片</div>
    <div class="carousel">
      <div class="carousel-track" ref="trackRef">
        <div v-if="!restaurant.photos.length" class="carousel-slide" style="background:#999;">📷</div>
        <div v-for="p in restaurant.photos" :key="p.id" class="carousel-slide"
             :style="p.image_url.startsWith('placeholder:') ? { background: p.image_url.replace('placeholder:', '') } : {}"
             @click="openLightbox(p)">
          <img v-if="!p.image_url.startsWith('placeholder:')" :src="p.image_url" />
          <span v-else>📷</span>
          <span class="cap">{{ p.caption }}</span>
        </div>
      </div>
      <button class="carousel-arrow left" @click="scrollCarousel(-1)">‹</button>
      <button class="carousel-arrow right" @click="scrollCarousel(1)">›</button>
    </div>

    <ImageLightbox
      :visible="lightboxOpen"
      :image-url="lightboxPhoto?.image_url"
      :placeholder-color="lightboxPhoto?.image_url.startsWith('placeholder:') ? lightboxPhoto.image_url.replace('placeholder:', '') : null"
      :caption="lightboxPhoto?.caption"
      @close="closeLightbox"
    />

    <div class="menu-cat" style="font-size:12px;color:var(--muted);font-weight:600;">餐廳資訊</div>
    <div class="card">
      <div class="info-row"><span class="lbl">類型</span><span>{{ restaurant.type }}</span></div>
      <div class="info-row"><span class="lbl">地址</span><span>{{ restaurant.address }}</span></div>
      <div class="info-row"><span class="lbl">電話</span><span>{{ restaurant.phone }}</span></div>
      <div class="info-row" v-if="restaurant.hours"><span class="lbl">營業時間</span><span style="white-space:pre-line;">{{ restaurant.hours }}</span></div>
    </div>
    <div class="btn-row">
      <button class="btn btn-secondary" @click="copyMapLink(restaurant)">📋 複製地圖連結</button>
      <a class="btn btn-secondary" :href="mapUrl(restaurant)" target="_blank">📍 在 Google Maps 開啟</a>
    </div>
  </template>
</template>
