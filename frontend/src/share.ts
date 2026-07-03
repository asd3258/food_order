import { toast } from './stores/toast'

export function canWebShare(): boolean {
  return typeof navigator !== 'undefined' && typeof navigator.share === 'function'
}

// v0.11: generic "copy arbitrary text to clipboard" -- copyLink() below is
// just this with a URL and a fixed toast message. Used for the 歷史訂單
// "複製成文字" button (a formatted 品項/金額/收款狀態 summary to paste into
// LINE/Teams), so the success/failure toast wording needed to be generic
// too instead of always saying "已複製連結".
export async function copyText(text: string, successMessage = '已複製', failureMessage = '複製失敗,請手動選取文字複製') {
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text)
    } else {
      // Fallback for browsers without the Clipboard API (some in-app/Teams
      // mobile webviews) -- select a hidden textarea and copy via execCommand.
      const el = document.createElement('textarea')
      el.value = text
      el.style.position = 'fixed'
      el.style.opacity = '0'
      document.body.appendChild(el)
      el.select()
      document.execCommand('copy')
      document.body.removeChild(el)
    }
    toast(successMessage)
  } catch {
    toast(failureMessage)
  }
}

export async function copyLink(url: string) {
  await copyText(url, '已複製連結', '複製失敗,請手動選取網址複製')
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
