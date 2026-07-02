<script setup lang="ts">
import { confirmStore, resolveConfirm } from '../stores/confirm'
</script>

<template>
  <div class="overlay" :class="{ active: confirmStore.visible }" @click.self="resolveConfirm(false)">
    <div class="sheet confirm-box">
      <p id="confirmMessage">{{ confirmStore.message }}</p>
      <div class="sheet-actions">
        <template v-if="confirmStore.mode === 'alert'">
          <button class="btn btn-primary" style="width:100%;" @click="resolveConfirm(true)">知道了</button>
        </template>
        <template v-else>
          <button class="btn btn-secondary" @click="resolveConfirm(false)">No</button>
          <button class="btn btn-primary" @click="resolveConfirm(true)">Yes</button>
        </template>
      </div>
    </div>
  </div>
</template>
