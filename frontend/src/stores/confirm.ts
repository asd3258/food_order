import { reactive } from 'vue'

export const confirmStore = reactive({
  visible: false,
  message: '',
  mode: 'confirm' as 'confirm' | 'alert',
  resolver: null as ((ok: boolean) => void) | null,
})

export function confirmAction(message: string): Promise<boolean> {
  confirmStore.message = message
  confirmStore.mode = 'confirm'
  confirmStore.visible = true
  return new Promise((resolve) => {
    confirmStore.resolver = resolve
  })
}

/** v0.8: a single-button "警告視窗" for validation failures (reserved names,
 * disallowed characters, ...) that deserve more attention than a toast. */
export function alertWarning(message: string): Promise<void> {
  confirmStore.message = message
  confirmStore.mode = 'alert'
  confirmStore.visible = true
  return new Promise((resolve) => {
    confirmStore.resolver = () => resolve()
  })
}

export function resolveConfirm(ok: boolean) {
  confirmStore.visible = false
  if (confirmStore.resolver) confirmStore.resolver(ok)
  confirmStore.resolver = null
}
