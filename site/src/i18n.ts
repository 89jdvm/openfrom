import en from './i18n/en.json';
import es from './i18n/es.json';

export type Lang = 'en' | 'es';
const DICTS: Record<Lang, Record<string, string>> = { en, es };
let lang: Lang = 'en';

export function detectLang(): Lang {
  try {
    const saved = localStorage.getItem('openfrom.lang');
    if (saved === 'en' || saved === 'es') return saved;
  } catch { /* storage blocked: fall through */ }
  return (navigator.languages || [navigator.language]).some((l) => l?.toLowerCase().startsWith('es')) ? 'es' : 'en';
}

export function setLang(l: Lang, remember = true): void {
  lang = l;
  document.documentElement.lang = l;
  if (remember) {
    try { localStorage.setItem('openfrom.lang', l); } catch { /* ignore */ }
  }
}

export const getLang = (): Lang => lang;

/** Translate a key, filling {placeholders}. Falls back to English, then the key. */
export function t(key: string, vars: Record<string, string | number> = {}): string {
  const s = DICTS[lang][key] ?? DICTS.en[key] ?? key;
  return s.replace(/\{(\w+)\}/g, (_, k) => (k in vars ? String(vars[k]) : `{${k}}`));
}

export function fmtNum(n: number): string {
  return new Intl.NumberFormat(lang === 'es' ? 'es' : 'en').format(Math.round(n));
}

export function fmtDate(iso: string, withYear = false): string {
  if (!iso) return '';
  const d = new Date(iso + 'T12:00:00Z');
  return new Intl.DateTimeFormat(lang === 'es' ? 'es' : 'en-GB', {
    day: 'numeric', month: 'short', ...(withYear ? { year: 'numeric' } : {}), timeZone: 'UTC',
  }).format(d);
}

export function listJoin(items: string[]): string {
  if (items.length <= 1) return items[0] ?? '';
  if (items.length <= 3) {
    return t('who.and', { a: items.slice(0, -1).join(', '), b: items[items.length - 1] });
  }
  return t('who.more', { list: items.slice(0, 3).join(', '), n: items.length - 3 });
}

/** Apply translations to static markup carrying data-i18n attributes. */
export function applyStatic(root: ParentNode = document): void {
  root.querySelectorAll<HTMLElement>('[data-i18n]').forEach((el) => { el.textContent = t(el.dataset.i18n!); });
  root.querySelectorAll<HTMLTextAreaElement>('[data-i18n-ph]').forEach((el) => { el.placeholder = t(el.dataset.i18nPh!); });
  root.querySelectorAll<HTMLElement>('[data-i18n-label]').forEach((el) => { el.setAttribute('aria-label', t(el.dataset.i18nLabel!)); });
}
