// Mirrors backend/app/validators.py (v0.8) -- this only gives instant
// feedback before the API call; the backend re-checks regardless, since a
// name could be submitted directly against the API without going through
// this frontend at all.
//
// Two rules:
// 1. Reserved prefixes: nobody can self-register/rename into admin*, root*,
//    ubuntu*, sysop*, sysadmin* (case-insensitive).
// 2. Injection prevention via allow-list (not blacklist): a name may only
//    contain letters (any language), digits, spaces, and -_. -- anything
//    else (<, >, ;, ', ", backtick, /, \, ...) is rejected.

export const RESERVED_PREFIXES = ['admin', 'root', 'ubuntu', 'sysop', 'sysadmin']

// \p{L}=any letter, \p{N}=any digit, unicode-aware. 1-30 chars.
const NAME_PATTERN = /^[\p{L}\p{N}_\-. ]{1,30}$/u

/** Returns an error message if `name` is invalid, or null if it's fine. */
export function validateUserName(name: string): string | null {
  const cleaned = name.trim()
  if (!cleaned) return '請輸入使用者名稱'
  if (!NAME_PATTERN.test(cleaned)) {
    return '名稱包含不允許的字元,只能使用中文/英文/數字/空格與 - _ .,且長度需在30字以內'
  }
  const lower = cleaned.toLowerCase()
  for (const prefix of RESERVED_PREFIXES) {
    if (lower.startsWith(prefix)) return `不可使用「${prefix}」開頭的名稱,請改用其他名稱`
  }
  return null
}
