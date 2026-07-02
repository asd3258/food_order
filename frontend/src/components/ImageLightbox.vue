<script setup lang="ts">
defineProps<{
  visible: boolean
  imageUrl?: string | null
  placeholderColor?: string | null
  emoji?: string | null
  caption?: string | null
}>()
const emit = defineEmits<{ close: [] }>()
</script>

<template>
  <div class="overlay lightbox-overlay" :class="{ active: visible }" @click="emit('close')">
    <div class="lightbox-inner">
      <img v-if="imageUrl && !imageUrl.startsWith('placeholder:')" :src="imageUrl" @click.stop />
      <div v-else class="lightbox-placeholder" :style="{ background: placeholderColor || '#999' }" @click.stop>
        <span>{{ emoji || '📷' }}</span>
      </div>
      <div v-if="caption" class="lightbox-caption">{{ caption }}</div>
      <button class="lightbox-close" @click="emit('close')">×</button>
    </div>
  </div>
</template>

<style scoped>
.lightbox-overlay {
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.85);
  z-index: 90;
}
.lightbox-inner {
  position: relative;
  max-width: 92vw;
  max-height: 86vh;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.lightbox-inner img {
  max-width: 92vw;
  max-height: 78vh;
  object-fit: contain;
  border-radius: 8px;
}
.lightbox-placeholder {
  width: min(92vw, 320px);
  height: min(78vh, 320px);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 72px;
  color: #fff;
}
.lightbox-caption {
  color: #fff;
  font-size: 13px;
  margin-top: 10px;
  text-align: center;
}
.lightbox-close {
  position: absolute;
  top: -14px;
  right: -14px;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: none;
  background: #fff;
  color: #242424;
  font-size: 18px;
  cursor: pointer;
}
</style>
