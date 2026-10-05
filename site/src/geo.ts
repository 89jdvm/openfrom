/** Who can apply, from the compact code built each night, and a country guess from CV text. */
import type { Geo } from './data';

export type Open = 'yes' | 'no' | 'unclear' | 'unknown';

export interface Who {
  world: boolean; countries: string[]; regions: string[]; utc: [number, number] | null; code: string;
  /** Set when the code is X:…, which means every known country except these. */
  except: string[] | null;
}

/** Parse "W", "U", "N", "L:US,CA;R:LATAM;T:-8,-2" or "X:CU,KP" (see build_site_data.w_code). */
export function parseWho(code: string): Who {
  const w: Who = { world: false, countries: [], regions: [], utc: null, code, except: null };
  for (const part of code.split(';')) {
    if (part === 'W') w.world = true;
    else if (part.startsWith('L:')) w.countries = part.slice(2).split(',');
    else if (part.startsWith('X:')) w.except = part.slice(2).split(',').filter(Boolean);
    else if (part.startsWith('R:')) w.regions = part.slice(2).split(',');
    else if (part.startsWith('T:')) {
      const [a, b] = part.slice(2).split(',').map(Number);
      w.utc = [a, b];
    }
  }
  return w;
}

/** Can someone living in `country` take this job? Mirrors who_can_apply.open_to. */
export function openTo(code: string, country: string, geo: Geo): Open {
  if (code === 'U') return 'unclear';
  if (code === 'N') return 'unknown';
  const w = parseWho(code);
  if (!w.world) {
    const inList = (w.except ? !w.except.includes(country) : w.countries.includes(country))
      || w.regions.some((r) => geo.regions[r]?.includes(country));
    if (!inList) return 'no';
  }
  if (w.utc) {
    const c = geo.countries[country];
    if (!c) return 'no';
    const [lo, hi] = w.utc;
    if (!(c[3] >= lo && c[2] <= hi)) return 'no';
  }
  return 'yes';
}

const PHONE_PREFIX: Record<string, string> = {
  '+1': 'US', '+44': 'GB', '+49': 'DE', '+33': 'FR', '+34': 'ES', '+39': 'IT', '+31': 'NL', '+32': 'BE', '+41': 'CH',
  '+43': 'AT', '+351': 'PT', '+353': 'IE', '+45': 'DK', '+46': 'SE', '+47': 'NO', '+358': 'FI', '+48': 'PL',
  '+52': 'MX', '+54': 'AR', '+55': 'BR', '+56': 'CL', '+57': 'CO', '+51': 'PE', '+593': 'EC', '+598': 'UY',
  '+595': 'PY', '+591': 'BO', '+58': 'VE', '+506': 'CR', '+507': 'PA', '+502': 'GT', '+503': 'SV', '+504': 'HN',
  '+505': 'NI', '+53': 'CU', '+254': 'KE', '+255': 'TZ', '+256': 'UG', '+250': 'RW', '+251': 'ET', '+234': 'NG',
  '+233': 'GH', '+27': 'ZA', '+20': 'EG', '+212': 'MA', '+216': 'TN', '+221': 'SN', '+225': 'CI', '+237': 'CM',
  '+91': 'IN', '+92': 'PK', '+880': 'BD', '+94': 'LK', '+977': 'NP', '+62': 'ID', '+63': 'PH', '+60': 'MY',
  '+65': 'SG', '+66': 'TH', '+84': 'VN', '+86': 'CN', '+81': 'JP', '+82': 'KR', '+61': 'AU', '+64': 'NZ',
  '+971': 'AE', '+966': 'SA', '+972': 'IL', '+90': 'TR', '+380': 'UA', '+40': 'RO', '+30': 'GR', '+36': 'HU',
  '+420': 'CZ',
};

const CITY: Record<string, string> = {
  nairobi: 'KE', mombasa: 'KE', kisumu: 'KE', bogotá: 'CO', bogota: 'CO', medellín: 'CO', medellin: 'CO', cali: 'CO',
  barranquilla: 'CO', cartagena: 'CO', quito: 'EC', guayaquil: 'EC', cuenca: 'EC', lima: 'PE', berlin: 'DE',
  munich: 'DE', münchen: 'DE', hamburg: 'DE', frankfurt: 'DE', cologne: 'DE', köln: 'DE', london: 'GB', madrid: 'ES',
  barcelona: 'ES', paris: 'FR', amsterdam: 'NL', lisbon: 'PT', lisboa: 'PT', 'mexico city': 'MX', cdmx: 'MX',
  'ciudad de méxico': 'MX', 'buenos aires': 'AR', santiago: 'CL', 'são paulo': 'BR', 'sao paulo': 'BR',
  lagos: 'NG', accra: 'GH', kampala: 'UG', kigali: 'RW', 'addis ababa': 'ET', 'dar es salaam': 'TZ',
  johannesburg: 'ZA', 'cape town': 'ZA', manila: 'PH', 'new delhi': 'IN', delhi: 'IN', mumbai: 'IN',
  bangalore: 'IN', bengaluru: 'IN', toronto: 'CA', vancouver: 'CA', 'new york': 'US', 'san francisco': 'US',
};

/** Guess where the CV's owner lives: the contact block first (phone prefix, city, country), then the whole text. */
export function guessCountry(text: string, geo: Geo): string | null {
  const head = text.slice(0, 700);
  const phone = head.match(/\+\d{1,3}(?=[\s\d().-]{6,})/g);
  if (phone) {
    for (const p of phone) {
      for (const len of [4, 3, 2]) {
        const hit = PHONE_PREFIX[p.slice(0, len)];
        if (hit) return hit;
      }
    }
  }
  const names: [string, string][] = [];
  for (const [code, [en, es]] of Object.entries(geo.countries)) {
    names.push([en.toLowerCase(), code], [es.toLowerCase(), code]);
  }
  for (const [city, code] of Object.entries(CITY)) names.push([city, code]);
  names.sort((a, b) => b[0].length - a[0].length);
  const find = (s: string): string | null => {
    const low = s.toLowerCase();
    let best: [number, string] | null = null;
    for (const [name, code] of names) {
      if (name.length < 4) continue;
      const i = low.search(new RegExp(`(^|[^a-zà-ÿ])${name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}($|[^a-zà-ÿ])`));
      if (i >= 0 && (!best || i < best[0])) best = [i, code];
    }
    return best ? best[1] : null;
  };
  return find(head) ?? find(text.slice(0, 4000));
}

export function countryName(code: string, geo: Geo, lang: 'en' | 'es'): string {
  const c = geo.countries[code];
  return c ? (lang === 'es' ? c[1] : c[0]) : code;
}
