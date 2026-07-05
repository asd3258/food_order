<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import { toast } from '../stores/toast'
import { userStore } from '../stores/user'

const router = useRouter()
const name = ref('')
const email = ref('')
const tempCode = ref('')
const countdown = ref(0)
const sending = ref(false)
const loggingIn = ref(false)
const emailInvalid = ref(false)

async function sendCode() {
  emailInvalid.value = false
  if (!name.value.trim() || !email.value.trim()) {
    if (!email.value.trim()) emailInvalid.value = true
    toast('請輸入帳號與 Email')
    return
  }
  
  // Basic email format check
  if (!/^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(email.value)) {
    emailInvalid.value = true
    toast('請輸入有效的 Email 格式')
    return
  }
  
  sending.value = true
  try {
    const res = await api.forgotPassword(name.value.trim(), email.value.trim())
    toast(res.message)
    // Start countdown
    countdown.value = 30
    const timer = setInterval(() => {
      countdown.value--
      if (countdown.value <= 0) {
        clearInterval(timer)
      }
    }, 1000)
  } catch (err: any) {
    // API already toasts the error
  } finally {
    sending.value = false
  }
}

async function loginWithCode() {
  if (!tempCode.value.trim()) {
    toast('請輸入臨時密碼')
    return
  }
  if (!name.value.trim()) {
    toast('請輸入帳號')
    return
  }
  
  loggingIn.value = true
  try {
    await userStore.loginAs(name.value.trim(), tempCode.value.trim())
    router.push('/')
  } catch (err: any) {
    // error handled by api/store
  } finally {
    loggingIn.value = false
  }
}
</script>

<template>
  <div class="page-header">
    <router-link class="back" to="/login">←</router-link>
    <h1>忘記密碼</h1>
  </div>

  <div class="card">
    <div class="form-group">
      <input v-model="name" type="text" placeholder="請輸入帳號" required />
    </div>
    <div class="form-group">
      <input v-model="email" type="email" placeholder="請輸入 Email" required :class="{ 'time-select-invalid': emailInvalid }" />
    </div>
    <button class="btn btn-secondary btn-full" :disabled="countdown > 0 || sending || !name || !email" @click="sendCode">
      {{ countdown > 0 ? `請稍候 ${countdown} 秒` : (sending ? '發送中...' : '寄送臨時密碼') }}
    </button>
    
    <hr style="border:none;border-top:1px solid var(--border);margin:18px 0;" />
    
    <div class="form-group">
      <input v-model="tempCode" type="text" placeholder="請輸入臨時密碼" required @keyup.enter="loginWithCode" />
    </div>
    <button class="btn btn-primary btn-full" :disabled="!tempCode || loggingIn" @click="loginWithCode">
      {{ loggingIn ? '登入中...' : '登入' }}
    </button>
  </div>
</template>
