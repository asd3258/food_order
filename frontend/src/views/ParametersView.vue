<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api, type RestaurantType } from '../api'
import { toast } from '../stores/toast'

const types = ref<RestaurantType[]>([])
const newTypeName = ref('')
const editingType = ref<RestaurantType | null>(null)

async function load() {
  types.value = await api.listRestaurantTypes()
}

onMounted(load)

async function addType() {
  if (!newTypeName.value.trim()) return
  try {
    await api.createRestaurantType({ name: newTypeName.value.trim() })
    newTypeName.value = ''
    toast('已新增類型')
    load()
  } catch (e: any) {
    // API client shows toast
  }
}

async function updateType() {
  if (!editingType.value || !editingType.value.name.trim()) return
  try {
    await api.updateRestaurantType(editingType.value.id, { name: editingType.value.name.trim() })
    editingType.value = null
    toast('已更新類型')
    load()
  } catch (e: any) {
    // API client shows toast
  }
}

async function deleteType(id: number) {
  if (!confirm('確定要刪除這個餐廳類型嗎？')) return
  try {
    await api.deleteRestaurantType(id)
    toast('已刪除類型')
    load()
  } catch (e: any) {
    // API client shows toast
  }
}
</script>

<template>
  <div class="page-header">
    <h1>參數維護</h1>
  </div>

  <div class="card">
    <h3>餐廳類型維護</h3>
    <div style="font-size:13px;color:var(--muted);margin-bottom:15px;">
      新增、修改或刪除餐廳分類標籤。注意：若類型正在被餐廳使用中，將無法刪除。
    </div>
    
    <div style="display:flex; gap:8px; margin-bottom: 20px;">
      <input v-model="newTypeName" placeholder="輸入新類型名稱 (例如: 韓式)" style="flex:1" @keyup.enter="addType" />
      <button class="btn btn-primary" @click="addType">新增</button>
    </div>

    <table v-if="types.length > 0" class="data-table">
      <thead>
        <tr>
          <th>類型名稱</th>
          <th style="width: 120px; text-align:right">操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="t in types" :key="t.id">
          <td>
            <template v-if="editingType?.id === t.id">
              <input v-model="editingType.name" @keyup.enter="updateType" />
            </template>
            <template v-else>
              {{ t.name }}
            </template>
          </td>
          <td class="td-actions">
            <template v-if="editingType?.id === t.id">
              <button class="btn btn-primary btn-sm" @click="updateType">儲存</button>
              <button class="btn btn-secondary btn-sm" @click="editingType = null">取消</button>
            </template>
            <template v-else>
              <button class="btn btn-secondary btn-sm" @click="editingType = { ...t }">編輯</button>
              <button class="btn btn-danger btn-sm" @click="deleteType(t.id)">刪除</button>
            </template>
          </td>
        </tr>
      </tbody>
    </table>
    <div v-else class="empty">目前沒有任何餐廳類型。</div>
  </div>
</template>

<style scoped>
.data-table {
  width: 100%;
  border-collapse: collapse;
}
.data-table th, .data-table td {
  padding: 8px;
  border-bottom: 1px solid var(--border);
  text-align: left;
}
.td-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  align-items: center;
}
.btn-sm {
  padding: 6px 12px !important;
  font-size: 13px !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  height: auto !important;
  line-height: 1 !important;
}
</style>
