import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './style.css'
import { initUiModeFromStorage, userStore } from './stores/user'

// v0.11: 大字模式 -- 在 Vue 掛載前就先套用上次記住的模式,避免畫面先閃一下標準
// 字級再變大;真正的帳號偏好會在 userStore.restore() 裡用後端資料覆蓋一次確認。
initUiModeFromStorage()

const app = createApp(App)
app.use(router)
app.mount('#app')

userStore.restore()
