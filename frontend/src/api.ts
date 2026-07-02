// Thin fetch wrapper for the FastAPI backend (see SPEC.md section 6 for the
// full endpoint list). Every mutating call that only the initiator may
// perform passes `acting_user` as a query param; the backend re-checks it
// server-side, so this is not a real auth layer -- see SPEC.md section 8
// item 1/3 for the identity/permission caveats already flagged in the spec.

import { toast } from './stores/toast'

const BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

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
}
export interface RestaurantDetail extends RestaurantSummary {
  map_url: string
  menu_items: MenuItem[]
  photos: Photo[]
}
export interface OrderItemRow {
  id: number
  user: string
  menu_item_id: number
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

export const RESTAURANT_TYPES = ['便當', '飲料', '牛排', '義大利麵']

export const api = {
  // Users
  getMe: (clientId: string) => request<{ client_id: string; display_name: string }>(
    `/api/users/me${qs({ client_id: clientId })}`),
  saveMe: (clientId: string, displayName: string) => request(`/api/users/me`, {
    method: 'PUT', body: JSON.stringify({ client_id: clientId, display_name: displayName }),
  }),

  // Restaurants
  listRestaurants: (q?: string, type?: string) => request<RestaurantSummary[]>(
    `/api/restaurants${qs({ q, type })}`),
  getRestaurantMenu: (id: number) => request<RestaurantDetail>(`/api/restaurants/${id}/menu`),
  createRestaurant: (payload: any) => request<RestaurantDetail>('/api/restaurants', {
    method: 'POST', body: JSON.stringify(payload),
  }),
  updateRestaurant: (id: number, payload: any) => request<RestaurantDetail>(`/api/restaurants/${id}`, {
    method: 'PUT', body: JSON.stringify(payload),
  }),
  uploadPhoto: (id: number, imageUrl: string, caption = '') => request<Photo>(
    `/api/restaurants/${id}/photos`, { method: 'POST', body: JSON.stringify({ image_url: imageUrl, caption }) }),
  deletePhoto: (id: number, photoId: number) => request<void>(
    `/api/restaurants/${id}/photos/${photoId}`, { method: 'DELETE' }),

  // Orders
  listOrders: (status = 'open') => request<OrderOut[]>(`/api/orders${qs({ status })}`),
  createOrder: (payload: { restaurant_id: number; initiator: string; deadline_at: string; source_vote_batch_id?: number }) =>
    request<OrderOut>('/api/orders', { method: 'POST', body: JSON.stringify(payload) }),
  getOrder: (id: number) => request<OrderOut>(`/api/orders/${id}`),
  getOrderStats: (id: number) => request<StatRow[]>(`/api/orders/${id}/stats`),
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
  deleteOrder: (orderId: number, actingUser: string) => request<void>(
    `/api/orders/${orderId}${qs({ acting_user: actingUser })}`, { method: 'DELETE' }),

  // Votes
  listVotes: (status = 'open') => request<VoteBatchOut[]>(`/api/votes${qs({ status })}`),
  createVote: (payload: { restaurant_ids: number[]; initiator: string; deadline_at: string }) =>
    request<VoteBatchOut>('/api/votes', { method: 'POST', body: JSON.stringify(payload) }),
  getVote: (id: number, user?: string) => request<VoteBatchOut>(`/api/votes/${id}${qs({ user })}`),
  saveMyChoice: (batchId: number, user: string, restaurantId: number) => request(
    `/api/votes/${batchId}/my-choice`, { method: 'PUT', body: JSON.stringify({ user, restaurant_id: restaurantId }) }),
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
}
