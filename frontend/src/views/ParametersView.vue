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

  <div class="card type-manager-card">
    <div class="type-manager-head">
      <div>
        <h3>餐廳類型維護</h3>
        <p>新增、修改或刪除餐廳分類標籤。正在被餐廳使用中的類型無法刪除。</p>
      </div>
      <span class="type-count">{{ types.length }} 種</span>
    </div>
    
    <div class="add-type-row">
      <input v-model="newTypeName" placeholder="輸入新類型名稱 (例如: 韓式)" @keyup.enter="addType" />
      <button class="btn btn-primary" @click="addType">新增</button>
    </div>

    <div v-if="types.length > 0" class="type-list">
      <div v-for="t in types" :key="t.id" class="type-row">
        <div class="type-main">
          <span class="type-dot"></span>
          <div class="type-name-wrap">
            <template v-if="editingType?.id === t.id">
              <input class="type-edit-input" v-model="editingType.name" @keyup.enter="updateType" />
            </template>
            <template v-else>
              <span class="type-name">{{ t.name }}</span>
            </template>
          </div>
        </div>
        <div class="type-actions">
          <template v-if="editingType?.id === t.id">
            <button class="btn btn-primary btn-sm" @click="updateType">儲存</button>
            <button class="btn btn-secondary btn-sm" @click="editingType = null">取消</button>
          </template>
          <template v-else>
            <button class="btn btn-secondary btn-sm" @click="editingType = { ...t }">編輯</button>
            <button class="btn btn-danger btn-sm" @click="deleteType(t.id)">刪除</button>
          </template>
        </div>
      </div>
    </div>
    <div v-else class="empty">目前沒有任何餐廳類型。</div>
  </div>
</template>

<style scoped>
.type-manager-card {
  padding: 18px;
}
.type-manager-head {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: flex-start;
  margin-bottom: 16px;
}
.type-manager-head h3 {
  margin: 0 0 8px;
  font-size: 18px;
}
.type-manager-head p {
  margin: 0;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.6;
}
.type-count {
  flex-shrink: 0;
  color: var(--brand);
  background: #eceaf9;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  padding: 5px 10px;
}
.add-type-row {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}
.add-type-row input,
.type-edit-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 10px;
  font-size: 14px;
  font-family: inherit;
}
.add-type-row input {
  flex: 1;
  min-width: 0;
}
.type-list {
  display: grid;
  gap: 8px;
}
.type-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: #fff;
}
.type-main {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex: 1;
}
.type-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--brand);
  box-shadow: 0 0 0 4px #eceaf9;
  flex-shrink: 0;
}
.type-name-wrap {
  min-width: 0;
  flex: 1;
}
.type-name {
  display: block;
  font-size: 15px;
  font-weight: 700;
  overflow-wrap: anywhere;
}
.type-actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}
.btn-sm {
  padding: 7px 10px;
  font-size: 12px;
  border-radius: 8px;
}
@media (max-width: 430px) {
  .type-manager-card {
    padding: 14px;
  }
  .add-type-row {
    flex-direction: column;
  }
  .type-row {
    align-items: stretch;
    flex-direction: column;
  }
  .type-actions {
    display: grid;
    grid-template-columns: 1fr 1fr;
  }
}
</style>
