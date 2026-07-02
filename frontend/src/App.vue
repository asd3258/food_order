<script setup lang="ts">
import { useRouter } from 'vue-router'
import BottomNav from './components/BottomNav.vue'
import ConfirmDialog from './components/ConfirmDialog.vue'
import ToastMessage from './components/ToastMessage.vue'
import { userStore } from './stores/user'
import { toast } from './stores/toast'

const router = useRouter()

function goLogin() {
  router.push('/login')
}
function logout() {
  const name = userStore.username
  userStore.logout()
  toast(`已登出:${name}`)
}
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="title">訂餐統計</div>
      <div class="login-bar">
        <template v-if="userStore.isLoggedIn">
          <span class="login-status">使用者:{{ userStore.username }}</span>
          <button @click="logout">登出</button>
        </template>
        <template v-else>
          <span class="login-status login-status-warn">尚未登入</span>
          <button @click="goLogin">登入</button>
        </template>
      </div>
    </header>

    <div class="content-wrap">
      <main class="content">
        <router-view />
      </main>
      <!-- v0.7: logged-out users can still switch bottom-nav tabs, but can't
           click into any content -- this overlay sits on top of (only) the
           content area and routes any click to the login screen. -->
      <div v-if="!userStore.isLoggedIn" class="lockout-overlay" @click="goLogin">
        <div class="lockout-box">
          <p>請先登入才能使用</p>
          <button class="btn btn-primary" @click.stop="goLogin">登入</button>
        </div>
      </div>
    </div>

    <BottomNav />
    <ConfirmDialog />
    <ToastMessage />
  </div>
</template>
