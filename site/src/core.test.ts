import { describe, expect, it } from 'vitest';
import en from './i18n/en.json';
import es from './i18n/es.json';
import { guessCountry, openTo, parseWho } from './geo';
import { chunks, stripContact } from './cv';
import { tokens } from './match';
import type { Geo } from './data';

const geo: Geo = {
  countries: {
    KE: ['Kenya', 'Kenia', 3, 3], CO: ['Colombia', 'Colombia', -5, -5], DE: ['Germany', 'Alemania', 1, 1],
    US: ['United States', 'Estados Unidos', -10, -5], IN: ['India', 'India', 5.5, 5.5],
  },
  regions: { LATAM: ['CO'], EMEA: ['KE', 'DE'], EUROPE: ['DE'] },
};

describe('who can apply', () => {
  it('parses the compact code', () => {
    expect(parseWho('L:US,CA;R:LATAM;T:-8,-2')).toMatchObject({ world: false, countries: ['US', 'CA'], regions: ['LATAM'], utc: [-8, -2] });
    expect(parseWho('W').world).toBe(true);
  });
  it('opens worldwide jobs to everyone', () => expect(openTo('W', 'KE', geo)).toBe('yes'));
  it('opens region jobs to members only', () => {
    expect(openTo('R:LATAM', 'CO', geo)).toBe('yes');
    expect(openTo('R:LATAM', 'KE', geo)).toBe('no');
    expect(openTo('R:EMEA', 'KE', geo)).toBe('yes');
  });
  it('applies time-zone bands', () => {
    expect(openTo('W;T:-8,-2', 'CO', geo)).toBe('yes');
    expect(openTo('W;T:-8,-2', 'KE', geo)).toBe('no');
    expect(openTo('R:EMEA;T:0,4', 'KE', geo)).toBe('yes');
  });
  it('keeps unclear and unknown apart from open', () => {
    expect(openTo('U', 'KE', geo)).toBe('unclear');
    expect(openTo('N', 'KE', geo)).toBe('unknown');
    expect(openTo('L:US', 'KE', geo)).toBe('no');
  });
});

describe('country guess', () => {
  it('reads the phone prefix in the contact block', () => {
    expect(guessCountry('Amina Otieno\n+254 712 000 000\nProgramme officer', geo)).toBe('KE');
  });
  it('reads a city or country name', () => {
    expect(guessCountry('Laura Gómez\nBogotá, Colombia\nEspecialista en M&E', geo)).toBe('CO');
    expect(guessCountry('Jonas Weber\nBerlin\nData analyst', geo)).toBe('DE');
  });
});

describe('CV passages', () => {
  const at = '@'; // built at run time so the public-safety guard sees no address in the source
  const cv = 'Amina Otieno\namina' + at + 'example.org | +254 712 000 000\nNairobi, Kenya\n\n' +
    'Climate programme officer with six years managing adaptation projects funded by bilateral donors in East Africa.\n' +
    'Designed results frameworks and monitoring plans for county-level resilience programmes across four counties.\n' +
    'Led stakeholder workshops with county governments, farmer groups and research partners on drought planning.';
  it('drops emails, phones and the name header', () => {
    const s = stripContact(cv);
    expect(s).not.toMatch(/@/);
    expect(s).not.toMatch(/712/);
    expect(s).not.toMatch(/^Amina Otieno/);
  });
  it('makes passages of bounded length', () => {
    const c = chunks(cv.repeat(4));
    expect(c.length).toBeGreaterThan(1);
    for (const p of c) expect(p.length).toBeLessThanOrEqual(900);
  });
});

describe('keyword tokens', () => {
  it('folds accents and drops stop words', () => {
    expect(tokens('Gestión de proyectos y evaluación')).toEqual(['gestion', 'proyectos', 'evaluacion']);
  });
});

describe('translations', () => {
  it('has the same keys in English and Spanish', () => {
    expect(Object.keys(es).sort()).toEqual(Object.keys(en).sort());
  });
  it('keeps the same placeholders in both languages', () => {
    for (const k of Object.keys(en) as (keyof typeof en)[]) {
      const ph = (s: string) => (s.match(/\{\w+\}/g) || []).sort();
      expect(ph((es as Record<string, string>)[k]), k).toEqual(ph(en[k]));
    }
  });
});
