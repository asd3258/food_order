import { reactive } from 'vue'

export const toastStore = reactive({
  message: '',
  visible: false,
})

let timer: ReturnType<typeof setTimeout> | null = null

export function toast(message: string) {
  toastStore.message = message
  toastStore.visible = true
  if (timer) clearTimeout(timer)
  timer = setTimeout(() => {
    toastStore.visible = false
  }, 1800)
}
