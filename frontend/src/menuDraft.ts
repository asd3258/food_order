import type { OptionChoice } from './api'

export interface OptionGroupDraft {
  group: string // e.g. "口味" / "加購"
  type: 'radio' | 'checkbox'
  choicesText: string // e.g. "原味,泰式,五辣" or "白飯加量+20,半熟蛋+15"
}

/** Turns a flat OptionChoice[] (what the backend stores/returns, and what
 * the AI menu-parser returns too) into the editable "group" rows used by
 * the 品項清單 forms on Create/EditRestaurantView. Inverse of each view's
 * local parseChoices(). Shared so the AI-parsed drafts and the
 * already-saved items round-trip through the exact same logic. */
export function optionsToGroups(options: OptionChoice[]): OptionGroupDraft[] {
  const order: string[] = []
  const byGroup: Record<string, { type: 'radio' | 'checkbox'; choices: string[] }> = {}
  for (const o of options) {
    if (!byGroup[o.option_group]) {
      byGroup[o.option_group] = { type: o.option_type, choices: [] }
      order.push(o.option_group)
    }
    byGroup[o.option_group].choices.push(o.extra_price ? `${o.option_name}+${o.extra_price}` : o.option_name)
  }
  return order.map((group) => ({ group, type: byGroup[group].type, choicesText: byGroup[group].choices.join(',') }))
}
