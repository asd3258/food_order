import { reactive } from 'vue'
import { api } from '../api'
import { toast } from './toast'

const STORAGE_KEY = 'food_order_user_id'
// v0.11: 大字模式 -- 這個 key 只是「開機時先套用,避免閃一下正常字級再變大」的
// 本地快取,實際的偏好是跟著帳號存在後端(users.ui_mode),見 restore()/loginAs()。
const UI_MODE_KEY = 'food_order_ui_mode'

/** Toggles the `large-mode` class on <html> -- see style.css for the actual
 * font-size/icon overrides. Exported so main.ts can apply the last-known
 * mode synchronously before the user profile round-trip resolves. */
export function applyUiModeClass(mode: string) {
  document.documentElement.classList.toggle('large-mode', mode === 'large')
}

export function initUiModeFromStorage() {
  applyUiModeClass(localStorage.getItem(UI_MODE_KEY) || 'normal')
}

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
  uiMode: 'normal' as string,  // v0.11: "normal" | "large" -- 大字模式,跟著帳號走
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
      this.uiMode = profile.ui_mode || 'normal'
      applyUiModeClass(this.uiMode)
      localStorage.setItem(UI_MODE_KEY, this.uiMode)
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
    this.uiMode = profile.ui_mode || 'normal'
    applyUiModeClass(this.uiMode)
    localStorage.setItem(STORAGE_KEY, String(profile.id))
    localStorage.setItem(UI_MODE_KEY, this.uiMode)
    toast(`已登入:${profile.name}`)
  },

  /** v0.11: 「其他功能」的大字模式切換 -- 立即套用(不用重整頁面),同時存回本地
   * 快取跟後端的使用者帳號,下次不管在哪台裝置登入都會直接套用。 */
  async setUiMode(mode: string) {
    this.uiMode = mode
    applyUiModeClass(mode)
    localStorage.setItem(UI_MODE_KEY, mode)
    if (this.userId) {
      await api.updateUiMode(this.userId, mode)
    }
  },

  logout() {
    this.userId = null
    this.username = ''
    this.isAdmin = false
    localStorage.removeItem(STORAGE_KEY)
  },
})
