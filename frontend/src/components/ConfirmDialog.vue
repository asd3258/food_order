<script setup lang="ts">
import { confirmStore, resolveConfirm } from '../stores/confirm'
</script>

<template>
  <div class="overlay" :class="{ active: confirmStore.visible }" @click.self="resolveConfirm(false)">
    <div class="sheet confirm-box">
      <p id="confirmMessage">{{ confirmStore.message }}</p>
      <div class="sheet-actions">
        <button class="btn btn-secondary" @click="resolveConfirm(false)">No</button>
        <button class="btn btn-primary" @click="resolveConfirm(true)">Yes</button>
      </div>
    </div>
  </div>
</template>
