<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { api, RESTAURANT_TYPES } from '../api'
import { userStore } from '../stores/user'
import { toast } from '../stores/toast'

interface OptionGroupDraft {
  group: string // e.g. "口味" / "加購"
  type: 'radio' | 'checkbox' // 單選(口味) | 可多選(加購)
  choicesText: string // e.g. "原味,泰式,五辣" or "白飯加量+20,半熟蛋+15"
}
interface ItemDraft {
  name: string
  price: number
  optionGroups: OptionGroupDraft[]
}

const router = useRouter()
const name = ref('')
const phone = ref('')
const address = ref('')
const type = ref(RESTAURANT_TYPES[0])
const items = ref<ItemDraft[]>([])

function addItemRow() {
  items.value.push({ name: '', price: 0, optionGroups: [] })
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

async function submit() {
  if (!name.value.trim()) {
    toast('請輸入餐廳名稱')
    return
  }
  await api.createRestaurant({
    name: name.value,
    phone: phone.value,
    address: address.value,
    type: type.value,
    created_by: userStore.username,
    menu_items: items.value.map((it) => ({
      name: it.name || '未命名品項',
      price: it.price || 0,
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
  toast('餐廳已建立:' + name.value)
  router.push('/more')
}
</script>

<template>
  <div class="page-header">
    <router-link class="back" to="/more">←</router-link>
    <h1>建立新餐廳</h1>
  </div>

  <div class="disabled-feature"><span>📷 上傳菜單照片,AI 自動解析品項</span><span class="tag-phase">Phase 2</span></div>
  <div class="disabled-feature"><span>🗺️ 貼上 Google Maps 網址,AI 自動生成菜單</span><span class="tag-phase">Phase 3</span></div>
  <div class="disabled-feature"><span>🔗 串接 Uber Eats / foodpanda 生成菜單</span><span class="tag-phase">評估中</span></div>

  <section class="block">
    <h2>餐廳資料(手動輸入)</h2>
    <div class="card">
      <div class="form-group"><label>餐廳名稱</label><input v-model="name" placeholder="例:日式烤肉飯 南崬" /></div>
      <div class="form-group"><label>電話</label><input v-model="phone" placeholder="(03) 312-8111" /></div>
      <div class="form-group"><label>地址</label><input v-model="address" placeholder="桃園市蘆竹區..." /></div>
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
