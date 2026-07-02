// Deadline helpers shared by Order & Vote / Vote Detail / Order Detail.
// Mirrors the picker logic from wireframe.html: a native date input + an
// hour (0-23) dropdown + a minute dropdown restricted to 5-minute steps.

export const HOURS = Array.from({ length: 24 }, (_, i) => i)
export const MINUTES = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]

export interface DeadlineParts {
  date: string // YYYY-MM-DD
  hour: number
  minute: number
}

export function defaultDeadline(): DeadlineParts {
  const d = new Date(Date.now() + 10 * 60000)
  const minute = MINUTES.reduce((best, m) =>
    Math.abs(m - d.getMinutes()) < Math.abs(best - d.getMinutes()) ? m : best, MINUTES[0])
  return { date: toDateStr(d), hour: d.getHours(), minute }
}

export function toDateStr(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

export function partsToIso(parts: DeadlineParts): string {
  // Local time, no timezone suffix; the backend stores naive datetimes.
  return `${parts.date}T${String(parts.hour).padStart(2, '0')}:${String(parts.minute).padStart(2, '0')}:00`
}

export function isoToParts(iso: string): DeadlineParts {
  const d = new Date(iso)
  return { date: toDateStr(d), hour: d.getHours(), minute: d.getMinutes() }
}

export function formatDeadline(iso: string): string {
  const d = new Date(iso)
  return `${d.getFullYear()}/${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}
