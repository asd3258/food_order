<script setup lang="ts">
import { toastStore } from '../stores/toast'
</script>

<template>
  <div class="toast" :class="{ show: toastStore.visible }">{{ toastStore.message }}</div>
</template>
