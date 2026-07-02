<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import BottomNav from './components/BottomNav.vue'
import ConfirmDialog from './components/ConfirmDialog.vue'
import ToastMessage from './components/ToastMessage.vue'
import { userStore } from './stores/user'
import { toast } from './stores/toast'

const router = useRouter()
const nameInput = ref(userStore.username)

async function saveUsername() {
  const name = nameInput.value.trim()
  if (!name) return
  await userStore.save(name)
  toast('已儲存名稱:' + name)
}

router.afterEach(() => {
  nameInput.value = userStore.username
})
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="title">訂餐統計</div>
      <div class="username-row">
        <input v-model="nameInput" type="text" />
        <button @click="saveUsername">Save</button>
      </div>
    </header>

    <main class="content">
      <router-view />
    </main>

    <BottomNav />
    <ConfirmDialog />
    <ToastMessage />
  </div>
</template>
