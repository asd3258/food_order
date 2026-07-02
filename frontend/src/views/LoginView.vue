<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api, type UserProfile } from '../api'
import { userStore } from '../stores/user'
import { alertWarning } from '../stores/confirm'
import { validateUserName } from '../validate'

const router = useRouter()
const nameInput = ref('')
const quickSearch = ref('')
const users = ref<UserProfile[]>([])

async function load() {
  // Backend already sorts by order_count desc, name asc (SPEC: 依歷史訂單次數排序).
  users.value = await api.listUsers()
}
onMounted(load)

// v0.7: admin accounts (e.g. admin_mike) don't show up in 快速登入 -- they can
// still log in by typing the name into the free-text field above.
const visibleUsers = computed(() => users.value.filter((u) => !u.is_admin))

const filteredUsers = computed(() => {
  const q = quickSearch.value.trim().toLowerCase()
  if (!q) return visibleUsers.value
  return visibleUsers.value.filter((u) => u.name.toLowerCase().includes(q))
})

async function loginWithInput() {
  const name = nameInput.value.trim()
  if (!name) return
  // v0.8: only validate names that don't already exist -- matches the
  // backend, which lets logging in as an existing (pre-check) name through
  // regardless, and only enforces the reserved-prefix/allow-list rules when
  // actually creating a brand-new roster entry.
  const isExisting = users.value.some((u) => u.name.toLowerCase() === name.toLowerCase())
  if (!isExisting) {
    const err = validateUserName(name)
    if (err) {
      await alertWarning(err)
      return
    }
  }
  await userStore.loginAs(name)
  router.push('/')
}
async function quickLogin(u: UserProfile) {
  await userStore.loginAs(u.name)
  router.push('/')
}
</script>

<template>
  <div class="page-header">
    <router-link class="back" to="/">←</router-link>
    <h1>登入</h1>
  </div>

  <div class="card">
    <div class="form-group">
      <input v-model="nameInput" type="text" placeholder="使用者名稱" @keyup.enter="loginWithInput" />
    </div>
    <button class="btn btn-primary btn-full" @click="loginWithInput">登入 &amp; 自動建立</button>
  </div>

  <hr style="border:none;border-top:1px solid var(--border);margin:18px 0;" />

  <section class="block">
    <h2>快速登入</h2>
    <div class="search-row">
      <input v-model="quickSearch" type="text" placeholder="搜尋" />
    </div>

    <div v-if="!filteredUsers.length" class="empty">找不到符合的使用者</div>
    <div v-else v-for="u in filteredUsers" :key="u.id" class="quick-login-item" @click="quickLogin(u)">
      <span class="qname">{{ u.name }}</span>
      <span v-if="u.order_count > 0" class="qcount">{{ u.order_count }} 次</span>
    </div>
  </section>
</template>
