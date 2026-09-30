/** Loads the nightly data files and gives typed access to jobs and vectors. */

export interface Jobs {
  n: number;
  sources: string[];
  title: string[]; org: string[]; url: string[]; src: number[]; posted: string[]; loc: string[];
  w: string[]; pay: (number[] | 0)[]; rf: string[]; ind: string[]; sen: string[]; eng: string[]; emp: string[];
  sk: string[]; imp: number[]; sum: string[];
}

export interface Meta {
  built: string; date: string; n: number;
  sources: { id: string; name: string; url: string; jobs: number }[];
  model: { name: string; revision: string; dtype: string; dim: number };
  labels: Record<'rf' | 'ind' | 'sen' | 'eng' | 'emp', Record<string, [string, string]>>;
}

export interface Geo {
  countries: Record<string, [string, string, number, number]>;
  regions: Record<string, string[]>;
}

export interface Skill { id: string; en: string; es: string; rx: string }

export interface Quality {
  fields?: Record<string, { agreement: number; baseline: number; n: number; approximate?: boolean }>;
}

export interface Market { n: number; worldwide_share: number; scope: Record<string, number>; impact: number }

export interface Data {
  jobs: Jobs; meta: Meta; geo: Geo; skills: Skill[]; quality: Quality; market: Market;
  vectors?: { q: Int8Array; scale: Float32Array; dim: number };
}

const base = new URL('./data/', document.baseURI).href;

async function json<T>(name: string): Promise<T> {
  const r = await fetch(base + name, { cache: 'no-cache' });
  if (!r.ok) throw new Error(`${name}: ${r.status}`);
  return r.json() as Promise<T>;
}

export async function loadData(): Promise<Data> {
  const [jobs, meta, geo, skills, quality, market] = await Promise.all([
    json<Jobs>('jobs.json'), json<Meta>('meta.json'), json<Geo>('geo.json'),
    json<Skill[]>('skills.json'), json<Quality>('quality.json'), json<Market>('market.json'),
  ]);
  return { jobs, meta, geo, skills, quality, market };
}

/** vectors.bin: N x dim int8 values, then N float32 scales. */
export async function loadVectors(n: number, dim: number): Promise<{ q: Int8Array; scale: Float32Array; dim: number }> {
  const r = await fetch(base + 'vectors.bin', { cache: 'no-cache' });
  if (!r.ok) throw new Error(`vectors.bin: ${r.status}`);
  const buf = await r.arrayBuffer();
  const q = new Int8Array(buf, 0, n * dim);
  const scale = new Float32Array(buf.slice(n * dim, n * dim + n * 4));
  return { q, scale, dim };
}
