<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, type RestaurantDetail, type OptionChoice, type Photo } from '../api'
import ImageLightbox from '../components/ImageLightbox.vue'

const route = useRoute()
const router = useRouter()
const restaurant = ref<RestaurantDetail | null>(null)
const trackRef = ref<HTMLElement | null>(null)

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
    out[o.option_group].push(withPrice && o.extra_price ? `${o.option_name}${o.extra_price}` : o.option_name)
  }
  return out
}

function mapUrl(r: RestaurantDetail): string {
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
</script>

<template>
  <div class="page-header">
    <router-link class="back" to="/restaurants">←</router-link>
    <h1>{{ restaurant?.name || '餐廳菜單' }}</h1>
  </div>

  <button class="btn btn-secondary btn-full" style="margin-bottom:14px;" @click="goEdit">✏️ 編輯餐廳資料</button>

  <template v-if="restaurant">
    <table class="stat-table" v-if="restaurant.menu_items.length">
      <tr><th>品項名稱</th><th>口味</th><th>加購</th><th>金額</th></tr>
      <tr v-for="m in restaurant.menu_items" :key="m.id">
        <td>{{ m.name }}</td>
        <td>{{ flavorStr(m.options) }}</td>
        <td>{{ addonStr(m.options) }}</td>
        <td>${{ m.price }}</td>
      </tr>
    </table>
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
    </div>
    <a class="btn btn-secondary btn-full" :href="mapUrl(restaurant)" target="_blank">📍 在 Google Maps 開啟</a>
  </template>
</template>
