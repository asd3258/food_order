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
