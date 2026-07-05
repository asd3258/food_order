import { reactive } from 'vue'

export const restaurantListFilters = reactive({
  q: '',
  typeFilter: '',
  daysFilter: [] as number[],
  sort: 'star' as 'star' | 'created_desc' | 'name'
})

export const orderVoteFilters = reactive({
  q: '',
  typeFilter: '',
  daysFilter: [] as number[],
})

export function resetFilters() {
  restaurantListFilters.q = ''
  restaurantListFilters.typeFilter = ''
  restaurantListFilters.daysFilter = []
  restaurantListFilters.sort = 'star'
  orderVoteFilters.q = ''
  orderVoteFilters.typeFilter = ''
  orderVoteFilters.daysFilter = []
}
