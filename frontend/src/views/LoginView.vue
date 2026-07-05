<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api, type UserProfile } from '../api'
import { userStore } from '../stores/user'
import { alertWarning, confirmAction } from '../stores/confirm'
import { validateUserName } from '../validate'

const router = useRouter()
const nameInput = ref('')
const passwordInput = ref('')
const quickSearch = ref('')
const users = ref<UserProfile[]>([])

async function load() {
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

// v0.12: 快速登入不再依訂單次數排序 -- 改成純文字排序,並用開頭 1 個字當分組
// 標題(像通訊錄一樣),方便人數變多時快速找到人。
function groupLetter(name: string): string {
  const first = Array.from(name.trim())[0] || '#'
  return first.toUpperCase()
}
const groupedUsers = computed(() => {
  const sorted = [...filteredUsers.value].sort((a, b) => a.name.localeCompare(b.name, 'zh-Hant'))
  const groups: { letter: string; users: typeof sorted }[] = []
  for (const u of sorted) {
    const letter = groupLetter(u.name)
    let g = groups.find((g) => g.letter === letter)
    if (!g) {
      g = { letter, users: [] }
      groups.push(g)
    }
    g.users.push(u)
  }
  return groups.sort((a, b) => a.letter.localeCompare(b.letter, 'zh-Hant'))
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
  await userStore.loginAs(name, passwordInput.value || undefined)
  router.push('/')
}
// v0.12: 快速登入清單一鍵登入很容易手滑點錯人,加一個 Yes/No 確認,選 Yes 才
// 真的登入。
async function quickLogin(u: UserProfile) {
  // If the user has a password, we need to prompt for it in a real app,
  // but since we only know if they have a password by attempting login,
  // we'll try without password, if it fails with "請輸入密碼", we prompt.
  const ok = await confirmAction(`確定要以「${u.name}」的身分登入嗎?`)
  if (!ok) return
  
  try {
    await userStore.loginAs(u.name)
    router.push('/')
  } catch (err: any) {
    if (err.message === '請輸入密碼' || err.message === '密碼錯誤') {
      const pwd = prompt(`請輸入「${u.name}」的密碼:`)
      if (pwd === null) return // cancelled
      try {
        await userStore.loginAs(u.name, pwd)
        router.push('/')
      } catch {
        // toast already shown by api.ts
      }
    }
  }
}
</script>

<template>
  <div class="page-header">
    <router-link class="back" to="/">←</router-link>
    <h1>登入</h1>
  </div>

  <div class="card">
    <div class="form-group">
      <input v-model="nameInput" type="text" placeholder="使用者名稱 (必填)" />
    </div>
    <div class="form-group">
      <input v-model="passwordInput" type="password" placeholder="密碼 (首次登入可輸入以設定密碼)" @keyup.enter="loginWithInput" />
    </div>
    <button class="btn btn-primary btn-full" @click="loginWithInput">登入 &amp; 自動建立</button>
    <div style="margin-top: 12px; text-align: center; font-size: 14px;">
      <router-link to="/forgot-password" style="color: var(--brand);">忘記密碼?</router-link>
    </div>
  </div>

  <hr style="border:none;border-top:1px solid var(--border);margin:18px 0;" />

  <section class="block">
    <h2>快速登入</h2>
    <div class="search-row">
      <input v-model="quickSearch" type="text" placeholder="搜尋" />
    </div>

    <div v-if="!filteredUsers.length" class="empty">找不到符合的使用者</div>
    <template v-else v-for="g in groupedUsers" :key="g.letter">
      <div class="quick-login-group-header">{{ g.letter }}</div>
      <div v-for="u in g.users" :key="u.id" class="quick-login-item" @click="quickLogin(u)">
        <span class="qname">{{ u.name }}</span>
      </div>
    </template>
  </section>
</template>
