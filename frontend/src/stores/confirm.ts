import { reactive } from 'vue'

export const confirmStore = reactive({
  visible: false,
  message: '',
  resolver: null as ((ok: boolean) => void) | null,
})

export function confirmAction(message: string): Promise<boolean> {
  confirmStore.message = message
  confirmStore.visible = true
  return new Promise((resolve) => {
    confirmStore.resolver = resolve
  })
}

export function resolveConfirm(ok: boolean) {
  confirmStore.visible = false
  if (confirmStore.resolver) confirmStore.resolver(ok)
  confirmStore.resolver = null
}
