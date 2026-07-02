import { toast } from './stores/toast'

export function canWebShare(): boolean {
  return typeof navigator !== 'undefined' && typeof navigator.share === 'function'
}

export async function copyLink(url: string) {
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(url)
    } else {
      // Fallback for browsers without the Clipboard API (some in-app/Teams
      // mobile webviews) -- select a hidden textarea and copy via execCommand.
      const el = document.createElement('textarea')
      el.value = url
      el.style.position = 'fixed'
      el.style.opacity = '0'
      document.body.appendChild(el)
      el.select()
      document.execCommand('copy')
      document.body.removeChild(el)
    }
    toast('已複製連結')
  } catch {
    toast('複製失敗,請手動選取網址複製')
  }
}

export async function shareLink(title: string, text: string, url: string) {
  if (canWebShare()) {
    try {
      await navigator.share({ title, text, url })
    } catch (err) {
      // AbortError just means the user closed the native share sheet --
      // not an actual failure, so don't show an error toast for that.
      if ((err as Error)?.name !== 'AbortError') {
        toast('分享取消或失敗,改用複製連結試試')
      }
    }
  } else {
    await copyLink(url)
  }
}
