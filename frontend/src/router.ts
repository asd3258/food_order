import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: () => import('./views/HomeView.vue') },
    { path: '/restaurants', name: 'restaurantList', component: () => import('./views/RestaurantListView.vue') },
    { path: '/restaurants/:id', name: 'restaurantMenu', component: () => import('./views/RestaurantMenuView.vue') },
    { path: '/restaurants/:id/edit', name: 'editRestaurant', component: () => import('./views/EditRestaurantView.vue') },
    { path: '/order-vote', name: 'orderVote', component: () => import('./views/OrderVoteView.vue') },
    { path: '/votes/:id', name: 'voteDetail', component: () => import('./views/VoteDetailView.vue') },
    { path: '/orders/:id', name: 'orderDetail', component: () => import('./views/OrderDetailView.vue') },
    { path: '/more', name: 'more', component: () => import('./views/MoreView.vue') },
    { path: '/create-restaurant', name: 'createRestaurant', component: () => import('./views/CreateRestaurantView.vue') },
    { path: '/history', name: 'history', component: () => import('./views/HistoryView.vue') },
  ],
})

export default router
