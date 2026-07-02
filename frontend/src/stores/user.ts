import { reactive } from 'vue'
import { api } from '../api'
import { toast } from './toast'

function getClientId(): string {
  let id = localStorage.getItem('food_order_client_id')
  if (!id) {
    id = 'c_' + Math.random().toString(36).slice(2) + Date.now().toString(36)
    localStorage.setItem('food_order_client_id', id)
  }
  return id
}

// SPEC.md 4.1: a personalized link can carry `?name=` so the first person to
// open it gets their name pre-filled instead of typing it in manually.
// Whoever pastes the link into Teams (or a bot doing it later) is expected
// to append their own name once, e.g. .../?name=Tony%20Su -- this does NOT
// know who's clicking automatically, it just saves the sender a step.
function consumeNameFromUrl(): string | null {
  const url = new URL(window.location.href)
  const name = url.searchParams.get('name')
  if (!name || !name.trim()) return null
  // Strip it immediately so it doesn't linger in window.location.href --
  // otherwise the "複製連結"/"分享" buttons on Order/Vote detail pages would
  // keep re-broadcasting whoever's name happened to be in the URL when they
  // first opened the app.
  url.searchParams.delete('name')
  const cleaned = url.pathname + (url.search ? url.search : '') + url.hash
  window.history.replaceState({}, '', cleaned)
  return name.trim()
}

export const userStore = reactive({
  clientId: getClientId(),
  username: '訪客',
  async load() {
    const nameFromUrl = consumeNameFromUrl()
    if (nameFromUrl) {
      this.username = nameFromUrl
      try {
        await api.saveMe(this.clientId, nameFromUrl)
        toast(`已帶入名稱:${nameFromUrl}`)
      } catch {
        /* backend not reachable yet; keep the name locally, retry on next save */
      }
      return
    }
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
