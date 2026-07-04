import { reactive } from 'vue'

export const restaurantListFilters = reactive({
  q: '',
  typeFilter: '',
  sort: 'star' as 'star' | 'created_desc' | 'name'
})

export function resetFilters() {
  restaurantListFilters.q = ''
  restaurantListFilters.typeFilter = ''
  restaurantListFilters.sort = 'star'
}
