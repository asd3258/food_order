import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  // v0.12: without this, switching routes keeps whatever scroll position the
  // PREVIOUS page was at -- if you'd scrolled down on Home then tapped
  // "餐廳清單" in the bottom nav, the new page renders already scrolled down
  // (looks like "the screen gets pushed down"). Mobile browsers tend to mask
  // this (shorter lists, overlay scrollbars, address-bar auto-hide), so it's
  // mostly only noticeable on desktop -- but the fix applies everywhere.
  scrollBehavior() {
    return { top: 0 }
  },
  routes: [
    { path: '/', name: 'home', component: () => import('./views/HomeView.vue') },
    { path: '/restaurants', name: 'restaurantList', component: () => import('./views/RestaurantListView.vue') },
    { path: '/restaurants/:id', name: 'restaurantMenu', component: () => import('./views/RestaurantMenuView.vue') },
    { path: '/restaurants/:id/edit', name: 'editRestaurant', component: () => import('./views/EditRestaurantView.vue') },
    { path: '/order-vote', name: 'orderVote', component: () => import('./views/OrderVoteView.vue') },
    { path: '/votes/:id', name: 'voteDetail', component: () => import('./views/VoteDetailView.vue') },
    { path: '/orders/:id', name: 'orderDetail', component: () => import('./views/OrderDetailView.vue') },
    { path: '/more', name: 'more', component: () => import('./views/MoreView.vue') },
    { path: '/parameters', name: 'parameters', component: () => import('./views/ParametersView.vue') },
    { path: '/create-restaurant', name: 'createRestaurant', component: () => import('./views/CreateRestaurantView.vue') },
    { path: '/history', name: 'history', component: () => import('./views/HistoryView.vue') },
    { path: '/login', name: 'login', component: () => import('./views/LoginView.vue') },
    { path: '/manage-users', name: 'manageUsers', component: () => import('./views/ManageUsersView.vue') },
    { path: '/permissions', name: 'permissions', component: () => import('./views/PermissionsView.vue') },
  ],
})

export default router
