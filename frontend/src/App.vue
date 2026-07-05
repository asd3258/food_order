<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import BottomNav from './components/BottomNav.vue'
import ConfirmDialog from './components/ConfirmDialog.vue'
import ToastMessage from './components/ToastMessage.vue'
import { userStore } from './stores/user'
import { toast } from './stores/toast'

const router = useRouter()
const route = useRoute()

// Bug fix: the lockout overlay used to render on *every* route while logged
// out -- including /login itself, since logging in hasn't happened yet at
// that point. That trapped the user: the overlay sat on top of the login
// form/button with a higher z-index, so nothing under it was clickable and
// there was no way to actually finish logging in. The overlay must not
// cover the login screen.
const showLockout = computed(() => !userStore.isLoggedIn && !['login', 'forgotPassword'].includes(route.name as string))

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
      <div v-if="showLockout" class="lockout-overlay" @click="goLogin">
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
