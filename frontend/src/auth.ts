import router from './router'
import { userStore } from './stores/user'
import { toast } from './stores/toast'

/** Call at the top of any action that needs an identity (ordering, voting,
 * creating/editing a restaurant, toggling a payment, ...). Returns false and
 * redirects to the login screen if nobody's logged in, so callers can just
 * `if (!requireLogin()) return`. */
export function requireLogin(): boolean {
  if (userStore.isLoggedIn) return true
  toast('請先登入')
  router.push('/login')
  return false
}

/** v0.7: gate for admin-only actions (管理使用者, 刪除歷史訂單). Note this is a
 * UI convenience only -- the backend re-checks is_admin on every admin-gated
 * endpoint, since acting_user is just a string the client controls. */
export function requireAdmin(): boolean {
  if (userStore.isAdmin) return true
  toast('只有管理者帳號可以使用此功能')
  return false
}
