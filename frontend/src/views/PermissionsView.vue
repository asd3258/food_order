<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { api, type PermissionRule, type PermissionRuleUpdate } from '../api'
import { requireAdmin, requireLogin } from '../auth'
import { userStore } from '../stores/user'
import { confirmAction } from '../stores/confirm'
import { toast } from '../stores/toast'

const rules = ref<PermissionRule[]>([])
const loading = ref(true)

const showAddModal = ref(false)
const newRule = ref({
  module: '歷史訂單',
  role: 'other',
  can_create: '-',
  can_read: 'V',
  can_update: '-',
  can_delete: '-'
})

const editingId = ref<number | null>(null)
const editRuleDraft = ref<PermissionRuleUpdate>({
  can_create: '-', can_read: '-', can_update: '-', can_delete: '-'
})

async function load() {
  if (!requireLogin() || !requireAdmin()) return
  try {
    rules.value = await api.listPermissions(userStore.currentUser!.name)
  } catch {
    //
  } finally {
    loading.value = false
  }
}
onMounted(load)

async function createRule() {
  if (!requireLogin() || !requireAdmin()) return
  try {
    const created = await api.createPermission(newRule.value, userStore.currentUser!.name)
    rules.value.push(created)
    showAddModal.value = false
    toast('新增權限規則成功')
  } catch {
    //
  }
}

async function deleteRule(r: PermissionRule) {
  if (!requireLogin() || !requireAdmin()) return
  const ok = await confirmAction(`確定刪除 ${r.module} 對 ${r.role} 的權限規則嗎？`)
  if (!ok) return
  try {
    await api.deletePermission(r.id, userStore.currentUser!.name)
    rules.value = rules.value.filter(x => x.id !== r.id)
    toast('已刪除權限規則')
  } catch {
    //
  }
}

function startEdit(r: PermissionRule) {
  editingId.value = r.id
  editRuleDraft.value = {
    can_create: r.can_create,
    can_read: r.can_read,
    can_update: r.can_update,
    can_delete: r.can_delete
  }
}

async function saveEdit(r: PermissionRule) {
  if (!requireLogin() || !requireAdmin()) return
  try {
    const updated = await api.updatePermission(r.id, editRuleDraft.value, userStore.currentUser!.name)
    const idx = rules.value.findIndex(x => x.id === r.id)
    if (idx !== -1) {
      rules.value[idx] = updated
    }
    editingId.value = null
    toast('已儲存權限設定')
  } catch {
    //
  }
}

function cancelEdit() {
  editingId.value = null
}

const groupedRules = computed(() => {
  const groups: Record<string, PermissionRule[]> = {}
  for (const r of rules.value) {
    if (!groups[r.module]) groups[r.module] = []
    groups[r.module].push(r)
  }
  return groups
})
</script>

<template>
  <div class="page-header">
    <h1>權限維護</h1>
    <button class="btn btn-primary" @click="showAddModal = true">+ 新增權限規則</button>
  </div>

  <div v-if="loading" class="empty">讀取中...</div>
  <div v-else-if="!rules.length" class="empty">沒有任何權限規則</div>
  <div v-else style="display:flex;flex-direction:column;gap:24px;padding-bottom:80px;">
    <div v-for="(moduleRules, moduleName) in groupedRules" :key="moduleName" class="card">
      <h3 style="margin-top:0;margin-bottom:12px;border-bottom:1px solid var(--border);padding-bottom:8px;">{{ moduleName }}</h3>
      <table style="width:100%;border-collapse:collapse;font-size:14px;text-align:center;">
        <thead>
          <tr style="border-bottom:1px solid var(--border);">
            <th style="padding:8px;text-align:left;">角色/使用者</th>
            <th style="padding:8px;">新增</th>
            <th style="padding:8px;">查看</th>
            <th style="padding:8px;">修改</th>
            <th style="padding:8px;">刪除</th>
            <th style="padding:8px;text-align:right;">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in moduleRules" :key="r.id" style="border-bottom:1px solid var(--border);">
            <td style="padding:8px;text-align:left;">
              <span class="badge" :class="{
                'badge-admin': r.role === 'admin',
                'badge-owner': r.role === 'owner',
                'badge-other': r.role === 'other'
              }">{{ r.role }}</span>
            </td>

            <template v-if="editingId === r.id">
              <td style="padding:8px;">
                <select v-model="editRuleDraft.can_create">
                  <option value="V">V</option>
                  <option value="X">X</option>
                  <option value="-">-</option>
                </select>
              </td>
              <td style="padding:8px;">
                <select v-model="editRuleDraft.can_read">
                  <option value="V">V</option>
                  <option value="X">X</option>
                  <option value="-">-</option>
                </select>
              </td>
              <td style="padding:8px;">
                <select v-model="editRuleDraft.can_update">
                  <option value="V">V</option>
                  <option value="X">X</option>
                  <option value="-">-</option>
                </select>
              </td>
              <td style="padding:8px;">
                <select v-model="editRuleDraft.can_delete">
                  <option value="V">V</option>
                  <option value="X">X</option>
                  <option value="-">-</option>
                </select>
              </td>
              <td style="padding:8px;text-align:right;">
                <button class="btn btn-primary" style="padding:4px 8px;font-size:12px;margin-right:4px;" @click="saveEdit(r)">儲存</button>
                <button class="btn btn-secondary" style="padding:4px 8px;font-size:12px;" @click="cancelEdit">取消</button>
              </td>
            </template>

            <template v-else>
              <td style="padding:8px;" :style="{ color: r.can_create === 'V' ? 'var(--brand)' : 'var(--muted)' }">{{ r.can_create }}</td>
              <td style="padding:8px;" :style="{ color: r.can_read === 'V' ? 'var(--brand)' : 'var(--muted)' }">{{ r.can_read }}</td>
              <td style="padding:8px;" :style="{ color: r.can_update === 'V' ? 'var(--brand)' : 'var(--muted)' }">{{ r.can_update }}</td>
              <td style="padding:8px;" :style="{ color: r.can_delete === 'V' ? 'var(--brand)' : 'var(--muted)' }">{{ r.can_delete }}</td>
              <td style="padding:8px;text-align:right;">
                <button class="btn btn-secondary" style="padding:4px 8px;font-size:12px;margin-right:4px;" @click="startEdit(r)">編輯</button>
                <button class="btn btn-danger" style="padding:4px 8px;font-size:12px;" @click="deleteRule(r)" :disabled="['admin','owner','other'].includes(r.role)">刪除</button>
              </td>
            </template>
          </tr>
        </tbody>
      </table>
    </div>
  </div>

  <!-- Add Modal -->
  <div v-if="showAddModal" class="modal-backdrop" @click.self="showAddModal = false">
    <div class="modal">
      <h2>新增權限規則</h2>
      <div class="form-group">
        <label>模組 (Module)</label>
        <select v-model="newRule.module">
          <option value="歷史訂單">歷史訂單</option>
          <option value="建立餐廳">建立餐廳</option>
          <option value="權限維護">權限維護</option>
          <option value="編輯餐廳資料">編輯餐廳資料</option>
          <option value="開單與投票">開單與投票</option>
          <option value="訂單">訂單</option>
          <option value="投票">投票</option>
        </select>
      </div>
      <div class="form-group">
        <label>角色 (Role)</label>
        <input v-model="newRule.role" placeholder="admin, owner, other, 或特定使用者名稱" />
      </div>
      <div class="form-group">
        <label>新增 (Create)</label>
        <select v-model="newRule.can_create">
          <option value="V">V</option>
          <option value="X">X</option>
          <option value="-">-</option>
        </select>
      </div>
      <div class="form-group">
        <label>查看 (Read)</label>
        <select v-model="newRule.can_read">
          <option value="V">V</option>
          <option value="X">X</option>
          <option value="-">-</option>
        </select>
      </div>
      <div class="form-group">
        <label>修改 (Update)</label>
        <select v-model="newRule.can_update">
          <option value="V">V</option>
          <option value="X">X</option>
          <option value="-">-</option>
        </select>
      </div>
      <div class="form-group">
        <label>刪除 (Delete)</label>
        <select v-model="newRule.can_delete">
          <option value="V">V</option>
          <option value="X">X</option>
          <option value="-">-</option>
        </select>
      </div>
      <div style="display:flex;gap:12px;margin-top:20px;">
        <button class="btn btn-secondary btn-full" @click="showAddModal = false">取消</button>
        <button class="btn btn-primary btn-full" @click="createRule">新增</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.badge {
  display: inline-block;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
  background: var(--surface);
  color: var(--text);
  border: 1px solid var(--border);
}
.badge-admin { background: #fee2e2; color: #991b1b; border-color: #fca5a5; }
.badge-owner { background: #dbeafe; color: #1e3a8a; border-color: #bfdbfe; }
.badge-other { background: #f3f4f6; color: #374151; border-color: #d1d5db; }
</style>
