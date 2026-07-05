<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import { toast } from '../stores/toast'
import { userStore } from '../stores/user'
import { alertWarning } from '../stores/confirm'

const router = useRouter()
const currentEmail = ref('')
const hasPassword = ref(false)

const emailInput = ref('')
const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')

const updatingEmail = ref(false)
const updatingPassword = ref(false)
const emailInvalid = ref(false)

async function load() {
  if (!userStore.isLoggedIn) {
    router.replace('/login')
    return
  }
  try {
    const info = await api.getMyInfo(userStore.username)
    currentEmail.value = info.email || ''
    emailInput.value = info.email || ''
    hasPassword.value = info.has_password
  } catch (e) {
    //
  }
}
onMounted(load)

async function updateEmail() {
  emailInvalid.value = false
  if (!emailInput.value.trim()) {
    toast('請輸入 Email')
    return
  }
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailInput.value.trim())) {
    toast('請輸入有效的 Email 格式')
    return
  }
  
  updatingEmail.value = true
  try {
    const res = await api.updateEmail(userStore.username, emailInput.value.trim())
    toast(res.message)
    currentEmail.value = emailInput.value.trim()
  } catch {
    //
  } finally {
    updatingEmail.value = false
  }
}

async function updatePassword() {
  emailInvalid.value = false
  
  if (!emailInput.value.trim()) {
    emailInvalid.value = true
    toast('變更密碼前請先設定 Email')
    return
  }
  
  if (emailInput.value.trim() !== currentEmail.value) {
    emailInvalid.value = true
    await alertWarning('輸入的 Email 與目前設定不同，請先點擊「儲存 Email」進行變更')
    return
  }
  
  if (hasPassword.value && !currentPassword.value) {
    toast('請輸入目前密碼')
    return
  }
  if (!newPassword.value || !confirmPassword.value) {
    toast('請輸入新密碼與確認密碼')
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    toast('新密碼與確認密碼不相符')
    return
  }
  
  updatingPassword.value = true
  try {
    const res = await api.updatePassword(userStore.username, currentPassword.value, newPassword.value)
    toast(res.message)
    hasPassword.value = true
    currentPassword.value = ''
    newPassword.value = ''
    confirmPassword.value = ''
  } catch {
    //
  } finally {
    updatingPassword.value = false
  }
}
</script>

<template>
  <div class="page-header">
    <router-link class="back" to="/more">←</router-link>
    <h1>帳號管理</h1>
  </div>

  <section class="block card">
    <h2>Email 設定</h2>
    <div class="form-group">
      <input v-model="emailInput" type="email" placeholder="輸入您的 Email" :class="{ 'time-select-invalid': emailInvalid }" />
      <small style="color: var(--text-muted); display: block; margin-top: 4px;">
        用於找回密碼
      </small>
    </div>
    <button class="btn btn-primary" :disabled="updatingEmail" @click="updateEmail">
      {{ updatingEmail ? '儲存中...' : '儲存 Email' }}
    </button>
  </section>

  <section class="block card">
    <h2>變更密碼</h2>
    <div v-if="hasPassword" class="form-group">
      <input v-model="currentPassword" type="password" placeholder="目前密碼" />
    </div>
    <div class="form-group">
      <input v-model="newPassword" type="password" placeholder="新密碼" />
    </div>
    <div class="form-group">
      <input v-model="confirmPassword" type="password" placeholder="確認新密碼" />
    </div>
    <button class="btn btn-primary" :disabled="updatingPassword" @click="updatePassword">
      {{ updatingPassword ? '變更中...' : '變更密碼' }}
    </button>
  </section>
</template>
