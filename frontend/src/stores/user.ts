import { reactive } from 'vue'
import { api } from '../api'

function getClientId(): string {
  let id = localStorage.getItem('food_order_client_id')
  if (!id) {
    id = 'c_' + Math.random().toString(36).slice(2) + Date.now().toString(36)
    localStorage.setItem('food_order_client_id', id)
  }
  return id
}

export const userStore = reactive({
  clientId: getClientId(),
  username: '訪客',
  async load() {
    try {
      const me = await api.getMe(this.clientId)
      this.username = me.display_name
    } catch {
      /* backend not reachable yet; keep default */
    }
  },
  async save(name: string) {
    this.username = name
    await api.saveMe(this.clientId, name)
  },
})
