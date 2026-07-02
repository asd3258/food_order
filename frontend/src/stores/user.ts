import { reactive } from 'vue'
import { api } from '../api'
import { toast } from './toast'

const STORAGE_KEY = 'food_order_user_id'

// SPEC.md 4.1: a personalized link can carry `?name=` so the first person to
// open it gets logged in automatically instead of using the login screen.
// Whoever pastes the link into Teams (or a bot doing it later) is expected
// to append their own name once, e.g. .../?name=Tony%20Su -- this does NOT
// know who's clicking automatically, it just saves the sender a step; it
// reuses the same login-or-create endpoint as the manual login screen.
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
  userId: null as number | null,
  username: '',
  isAdmin: false,
  get isLoggedIn(): boolean {
    return this.userId !== null
  },

  /** Called once on app startup. Restores a previous login from
   * localStorage (re-validating against the backend, in case that person
   * was renamed or removed via 管理使用者), or auto-logs-in from a
   * `?name=` link. */
  async restore() {
    const nameFromUrl = consumeNameFromUrl()
    if (nameFromUrl) {
      await this.loginAs(nameFromUrl)
      return
    }
    const stored = localStorage.getItem(STORAGE_KEY)
    if (!stored) return
    try {
      const profile = await api.getUser(Number(stored))
      this.userId = profile.id
      this.username = profile.name
      this.isAdmin = profile.is_admin
    } catch {
      // Deleted from the roster, or backend not reachable yet -- fall back
      // to logged-out rather than silently acting as a name that no longer
      // exists.
      localStorage.removeItem(STORAGE_KEY)
    }
  },

  /** Logs in as `name` -- finds the existing roster entry (case-insensitive)
   * or creates a new one. Used by both the free-text login field and by
   * clicking a name in the 快速登入 list. */
  async loginAs(name: string) {
    const profile = await api.loginOrCreateUser(name)
    this.userId = profile.id
    this.username = profile.name
    this.isAdmin = profile.is_admin
    localStorage.setItem(STORAGE_KEY, String(profile.id))
    toast(`已登入:${profile.name}`)
  },

  logout() {
    this.userId = null
    this.username = ''
    this.isAdmin = false
    localStorage.removeItem(STORAGE_KEY)
  },
})
