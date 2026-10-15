/**
 * Derives a stable output key from a display name. German umlauts are written
 * out rather than dropped, preserving readable keys for German source labels.
 */

/** Allows letters, numbers and underscores, but no leading number. */
export const IDENTIFIER = /^[a-zA-Z_][a-zA-Z0-9_]*$/

const UMLAUTS: Record<string, string> = {
  ä: 'ae',
  ö: 'oe',
  ü: 'ue',
  ß: 'ss',
}

/** “Rechnungsbetrag netto” becomes `rechnungsbetrag_netto`. */
export function keyFrom(displayName: string): string {
  const raw = displayName
    .toLowerCase()
    .replace(/[äöüß]/g, (z) => UMLAUTS[z] ?? z)
    // Reduce remaining diacritics such as é and ç to their base letters.
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')

  if (!raw) return 'value'
  return /^\d/.test(raw) ? `v_${raw}` : raw
}

/** Returns an unused key so one result value cannot silently replace another. */
export function freeKey(displayName: string, used: Iterable<string>): string {
  const taken = new Set(used)
  const base = keyFrom(displayName)
  if (!taken.has(base)) return base

  let n = 2
  while (taken.has(`${base}_${n}`)) n++
  return `${base}_${n}`
}
