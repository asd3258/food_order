import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './style.css'
import { userStore } from './stores/user'

const app = createApp(App)
app.use(router)
app.mount('#app')

userStore.load()
