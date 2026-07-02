<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api, type UserProfile } from '../api'
import { userStore } from '../stores/user'
import { confirmAction } from '../stores/confirm'
import { toast } from '../stores/toast'

const users = ref<UserProfile[]>([])
const editingId = ref<number | null>(null)
const editingName = ref('')

async function load() {
  users.value = await api.listUsers()
}
onMounted(load)

function startEdit(u: UserProfile) {
  editingId.value = u.id
  editingName.value = u.name
}
function cancelEdit() {
  editingId.value = null
  editingName.value = ''
}
async function saveEdit() {
  if (editingId.value == null) return
  const name = editingName.value.trim()
  if (!name) {
    toast('請輸入使用者名稱')
    return
  }
  const wasCurrentUser = userStore.userId === editingId.value
  await api.renameUser(editingId.value, name)
  if (wasCurrentUser) userStore.username = name
  cancelEdit()
  toast('已更新名稱')
  load()
}

async function removeUser(u: UserProfile) {
  const ok = await confirmAction(`確定要刪除使用者「${u.name}」嗎?過去的訂單/投票/歷史紀錄不會被刪除,只是這個人不會再出現在快速登入清單。`)
  if (!ok) return
  await api.deleteUser(u.id)
  if (userStore.userId === u.id) {
    userStore.logout()
    toast(`已刪除並登出:${u.name}`)
  } else {
    toast(`已刪除使用者:${u.name}`)
  }
  load()
}
</script>

<template>
  <div class="page-header">
    <router-link class="back" to="/more">←</router-link>
    <h1>管理使用者</h1>
  </div>

  <div v-if="!users.length" class="empty">尚無使用者</div>
  <div v-for="u in users" :key="u.id" class="manage-user-row">
    <template v-if="editingId === u.id">
      <input v-model="editingName" type="text" style="flex:1;padding:8px 10px;border:1px solid var(--border);border-radius:8px;font-size:14px;" @keyup.enter="saveEdit" />
      <span class="mlink" @click="saveEdit">儲存</span>
      <span class="mlink" @click="cancelEdit">取消</span>
    </template>
    <template v-else>
      <span class="mname">{{ u.name }}</span>
      <span v-if="u.order_count > 0" style="font-size:11px;color:var(--muted);">{{ u.order_count }} 次</span>
      <span class="mlink" @click="startEdit(u)">改名</span>
      <span class="mlink danger" @click="removeUser(u)">刪除</span>
    </template>
  </div>
</template>
