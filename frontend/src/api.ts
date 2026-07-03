// Thin fetch wrapper for the FastAPI backend (see SPEC.md section 6 for the
// full endpoint list). Every mutating call that only the initiator may
// perform passes `acting_user` as a query param; the backend re-checks it
// server-side, so this is not a real auth layer -- see SPEC.md section 8
// item 1/3 for the identity/permission caveats already flagged in the spec.

import { toast } from './stores/toast'

// v0.10 follow-up: "" (relative /api/... path, same origin nginx proxies to
// the backend -- see nginx.conf) is now the production default so this
// works from the LAN, Tailscale, or anywhere else without rebuilding.
// Nullish-coalescing (not ||) because "" is a deliberate, valid value here
// -- only fall back to the localhost dev default when the var is truly
// unset (plain `npm run dev`, no .env).
const BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${BASE}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...init,
    })
  } catch (networkErr) {
    // fetch() throws (not a rejected HTTP status) when the request can't even
    // reach the server -- wrong host/port, DNS/hostname not resolvable from
    // this device, mixed content, CORS preflight rejected, etc. Without this,
    // a button click just does nothing with no visible feedback.
    toast(`連不上伺服器(${BASE})，請確認網址設定或網路連線`)
    throw networkErr
  }
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail || detail
    } catch {
      /* ignore */
    }
    toast(`操作失敗:${detail}`)
    throw new Error(detail)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

function qs(params: Record<string, string | number | boolean | undefined>): string {
  const usp = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== '') usp.set(k, String(v))
  }
  const s = usp.toString()
  return s ? `?${s}` : ''
}

export interface OptionChoice {
  option_group: string
  option_type: 'radio' | 'checkbox'
  option_name: string
  extra_price: number
}
export interface MenuItem {
  id: number
  name: string
  price: number
  category: string
  options: OptionChoice[]
}
export interface Photo {
  id: number
  image_url: string
  caption: string
  sort_order: number
}
export interface RestaurantSummary {
  id: number
  name: string
  type: string
  phone: string
  address: string
  created_at: string
  is_favorite: boolean
}
export interface RestaurantDetail extends RestaurantSummary {
  map_url: string
  hours: string
  menu_items: MenuItem[]
  photos: Photo[]
}
export interface AiMenuItemDraft {
  name: string
  price: number
  category: string
  options: OptionChoice[]
}
export interface PlaceInfo {
  name: string
  phone: string
  address: string
  hours: string
}
export interface CategorySuggestion {
  name: string
  category: string
}

export interface OrderItemRow {
  id: number
  user: string
  menu_item_id: number | null  // v0.12: null once the referenced MenuItem is deleted (ON DELETE SET NULL)
  selected_options: string[]
  quantity: number
  note: string
  is_deleted: boolean
}
export interface OrderOut {
  id: number
  restaurant_id: number
  initiator: string
  deadline_at: string
  status: string
  is_locked: boolean
  items: OrderItemRow[]
}
export interface StatRow {
  label: string
  user: string
  quantity: number
  amount: number
  item_id: number
  is_deleted: boolean
}
export interface VoteCandidate {
  restaurant_id: number
  restaurant_name: string
  count: number
}
export interface VoteBatchOut {
  id: number
  initiator: string
  deadline_at: string
  status: string
  candidates: VoteCandidate[]
  my_selection: number | null
  my_locked: boolean
}
export interface HistoryLine {
  item_label: string
  user: string
  quantity: number
  amount: number
}
export interface HistoryPayment {
  user: string
  total_amount: number
  is_paid: boolean
}
export interface UserProfile {
  id: number
  name: string
  order_count: number
  is_admin: boolean
  ui_mode: string
}
export interface HistoryEntry {
  id: number
  restaurant_name: string
  initiator: string
  closed_date: string
  people_count: number
  total_amount: number
  lines: HistoryLine[]
  payments: HistoryPayment[]
}
export interface PermissionRule {
  id: number
  module: string
  role: string
  can_create: string
  can_read: string
  can_update: string
  can_delete: string
}
export interface PermissionRuleUpdate {
  can_create: string
  can_read: string
  can_update: string
  can_delete: string
}

export const RESTAURANT_TYPES = ['便當', '飲料', '牛排', '義大利麵']

export const api = {
  // Users (v0.6: shared roster / login-as picker, not a per-browser profile)
  listUsers: () => request<UserProfile[]>('/api/users'),
  getUser: (id: number) => request<UserProfile>(`/api/users/${id}`),
  loginOrCreateUser: (name: string) => request<UserProfile>('/api/users', {
    method: 'POST', body: JSON.stringify({ name }),
  }),
  renameUser: (id: number, name: string, actingUser: string) => request<UserProfile>(
    `/api/users/${id}${qs({ acting_user: actingUser })}`, {
      method: 'PATCH', body: JSON.stringify({ name }),
    }),
  deleteUser: (id: number, actingUser: string) => request<void>(
    `/api/users/${id}${qs({ acting_user: actingUser })}`, { method: 'DELETE' }),
  // v0.11: 大字模式偏好跟著帳號走 -- 不用 admin 權限,任何人都能改自己的。
  updateUiMode: (id: number, uiMode: string) => request<UserProfile>(
    `/api/users/${id}/ui-mode`, { method: 'PATCH', body: JSON.stringify({ ui_mode: uiMode }) }),

  // Restaurants
  // v0.12: `sort` -- "star"(★常用優先,新增,見 RestaurantListView.vue 的
  // 「預設排序」與 OrderVoteView.vue)、"created_desc"(建立時間新到舊)、
  // "name"(名稱排序);`user` 用來算 is_favorite 跟 star 排序的依據。
  listRestaurants: (q?: string, type?: string, sort?: string, user?: string) => request<RestaurantSummary[]>(
    `/api/restaurants${qs({ q, type, sort, user })}`),
  listRestaurantTypes: () => request<string[]>('/api/restaurants/types'),
  addFavorite: (id: number, user: string) => request<{ is_favorite: boolean }>(
    `/api/restaurants/${id}/favorite${qs({ user })}`, { method: 'POST' }),
  removeFavorite: (id: number, user: string) => request<{ is_favorite: boolean }>(
    `/api/restaurants/${id}/favorite${qs({ user })}`, { method: 'DELETE' }),
  getRestaurantMenu: (id: number) => request<RestaurantDetail>(`/api/restaurants/${id}/menu`),
  createRestaurant: (payload: any) => request<RestaurantDetail>('/api/restaurants', {
    method: 'POST', body: JSON.stringify(payload),
  }),
  updateRestaurant: (id: number, payload: any, actingUser: string) => request<RestaurantDetail>(`/api/restaurants/${id}${qs({ acting_user: actingUser })}`, {
    method: 'PUT', body: JSON.stringify(payload),
  }),
  deleteRestaurant: (id: number, actingUser: string) => request<void>(`/api/restaurants/${id}${qs({ acting_user: actingUser })}`, { method: 'DELETE' }),
  // v0.9: AI 菜單解析 -- send a photo (data URL), get back draft items to
  // review/edit before actually creating the restaurant. Gemini-first,
  // OpenAI-fallback happens entirely on the backend.
  parseMenuPhoto: (imageUrl: string) => request<AiMenuItemDraft[]>('/api/restaurants/parse-menu', {
    method: 'POST', body: JSON.stringify({ image_url: imageUrl }),
  }),
  // v0.10: reads phone/address/營業時間 off a Google Maps listing (Places API).
  fetchPlaceInfo: (mapUrl: string) => request<PlaceInfo>('/api/restaurants/fetch-place-info', {
    method: 'POST', body: JSON.stringify({ map_url: mapUrl }),
  }),
  // v0.10: "AI自動分類品項類型" -- suggestions only, doesn't write anything.
  classifyCategories: (itemNames: string[]) => request<CategorySuggestion[]>('/api/restaurants/classify-categories', {
    method: 'POST', body: JSON.stringify({ item_names: itemNames }),
  }),
  uploadPhoto: (id: number, imageUrl: string, caption = '') => request<Photo>(
    `/api/restaurants/${id}/photos`, { method: 'POST', body: JSON.stringify({ image_url: imageUrl, caption }) }),
  deletePhoto: (id: number, photoId: number) => request<void>(
    `/api/restaurants/${id}/photos/${photoId}`, { method: 'DELETE' }),

  // Orders
  listOrders: (status = 'open') => request<OrderOut[]>(`/api/orders${qs({ status })}`),
  createOrder: (payload: { restaurant_id: number; initiator: string; deadline_at: string; source_vote_batch_id?: number }) =>
    request<OrderOut>('/api/orders', { method: 'POST', body: JSON.stringify(payload) }),
  getOrder: (id: number, user?: string) => request<OrderOut>(`/api/orders/${id}${qs({ user })}`),
  getOrderStats: (id: number, user?: string) => request<StatRow[]>(`/api/orders/${id}/stats${qs({ user })}`),
  addOrderItem: (orderId: number, payload: any) => request<OrderItemRow>(
    `/api/orders/${orderId}/items`, { method: 'POST', body: JSON.stringify(payload) }),
  removeOwnItem: (orderId: number, itemId: number, user: string) => request<void>(
    `/api/orders/${orderId}/items/${itemId}${qs({ user })}`, { method: 'DELETE' }),
  softDeleteItem: (orderId: number, itemId: number, actingUser: string) => request<OrderItemRow>(
    `/api/orders/${orderId}/items/${itemId}/soft-delete${qs({ acting_user: actingUser })}`, { method: 'PATCH' }),
  updateOrderDeadline: (orderId: number, deadlineAt: string, actingUser: string) => request<OrderOut>(
    `/api/orders/${orderId}/deadline${qs({ acting_user: actingUser })}`,
    { method: 'PATCH', body: JSON.stringify({ deadline_at: deadlineAt }) }),
  closeOrder: (orderId: number, actingUser: string) => request<HistoryEntry>(
    `/api/orders/${orderId}/close${qs({ acting_user: actingUser })}`, { method: 'POST' }),
  lockOrder: (orderId: number, actingUser: string) => request<OrderOut>(
    `/api/orders/${orderId}/lock${qs({ acting_user: actingUser })}`, { method: 'PATCH' }),
  unlockOrder: (orderId: number, actingUser: string) => request<OrderOut>(
    `/api/orders/${orderId}/unlock${qs({ acting_user: actingUser })}`, { method: 'PATCH' }),
  deleteOrder: (orderId: number, actingUser: string) => request<void>(
    `/api/orders/${orderId}${qs({ acting_user: actingUser })}`, { method: 'DELETE' }),

  // Votes
  listVotes: (status = 'open') => request<VoteBatchOut[]>(`/api/votes${qs({ status })}`),
  createVote: (payload: { restaurant_ids: number[]; initiator: string; deadline_at: string }) =>
    request<VoteBatchOut>('/api/votes', { method: 'POST', body: JSON.stringify(payload) }),
  getVote: (id: number, user?: string) => request<VoteBatchOut>(`/api/votes/${id}${qs({ user })}`),
  saveMyChoice: (batchId: number, user: string, restaurantId: number) => request(
    `/api/votes/${batchId}/my-choice`, { method: 'PUT', body: JSON.stringify({ user, restaurant_id: restaurantId }) }),
  clearMyChoice: (batchId: number, user: string) => request<void>(
    `/api/votes/${batchId}/my-choice${qs({ user })}`, { method: 'DELETE' }),
  updateVoteDeadline: (batchId: number, deadlineAt: string, actingUser: string) => request<VoteBatchOut>(
    `/api/votes/${batchId}/deadline${qs({ acting_user: actingUser })}`,
    { method: 'PATCH', body: JSON.stringify({ deadline_at: deadlineAt }) }),
  decideVote: (batchId: number, actingUser: string) => request<OrderOut>(
    `/api/votes/${batchId}/decide${qs({ acting_user: actingUser })}`, { method: 'POST' }),
  deleteVote: (batchId: number, actingUser: string) => request<void>(
    `/api/votes/${batchId}${qs({ acting_user: actingUser })}`, { method: 'DELETE' }),

  // History
  listHistory: () => request<HistoryEntry[]>('/api/orders/history'),
  togglePayment: (historyId: number, user: string, actingUser: string) => request<HistoryPayment>(
    `/api/orders/history/${historyId}/payments/${encodeURIComponent(user)}${qs({ acting_user: actingUser })}`,
    { method: 'PATCH' }),
  deleteHistory: (historyId: number, actingUser: string) => request<void>(
    `/api/orders/history/${historyId}${qs({ acting_user: actingUser })}`, { method: 'DELETE' }),

  // Permissions
  listPermissions: (actingUser: string) => request<PermissionRule[]>(`/api/permissions${qs({ acting_user: actingUser })}`),
  createPermission: (payload: any, actingUser: string) => request<PermissionRule>(`/api/permissions${qs({ acting_user: actingUser })}`, {
    method: 'POST', body: JSON.stringify(payload)
  }),
  updatePermission: (id: number, payload: PermissionRuleUpdate, actingUser: string) => request<PermissionRule>(
    `/api/permissions/${id}${qs({ acting_user: actingUser })}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deletePermission: (id: number, actingUser: string) => request<void>(
    `/api/permissions/${id}${qs({ acting_user: actingUser })}`, { method: 'DELETE' }),
}
