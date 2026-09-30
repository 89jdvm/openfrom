/** Ranking jobs against a CV: model scores, or a keyword fallback (BM25 over titles and labels). */
import type { Data, Skill } from './data';

export interface Scored { idx: number; score: number; passage: number }

export function compileSkills(skills: Skill[]): { id: string; rx: RegExp }[] {
  return skills.map((s) => ({ id: s.id, rx: new RegExp(s.rx, s.id === 'r' ? '' : 'i') }));
}

export function cvSkills(text: string, compiled: { id: string; rx: RegExp }[]): Set<string> {
  return new Set(compiled.filter((s) => s.rx.test(text)).map((s) => s.id));
}

export function rankModel(best: Float32Array, which: Uint8Array): Scored[] {
  const out: Scored[] = [];
  for (let i = 0; i < best.length; i++) out.push({ idx: i, score: best[i], passage: which[i] });
  return out.sort((a, b) => b.score - a.score);
}

const STOP = new Set(('a an the and or of in to for with on at by from as is are be was were i me my we our you your ' +
  'this that it its have has had will would can could not no yes also more most than then there their they them he she ' +
  'y o de la el los las en con para por del al un una unos unas que se su sus es son fue como más muy mi mis yo nos ' +
  'experience experiencia years años work trabajo team equipo').split(' '));

export function tokens(s: string): string[] {
  return (s.toLowerCase().normalize('NFKD').replace(/[̀-ͯ]/g, '').match(/[a-z0-9+#]{2,}/g) || [])
    .filter((w) => !STOP.has(w));
}

/** BM25 over each job's title, role family, industry and skill names, in both languages. */
export class Keyword {
  private docs: Map<string, number>[] = [];
  private len: number[] = [];
  private df = new Map<string, number>();
  private avg = 1;

  constructor(data: Data) {
    const { jobs, meta, skills } = data;
    const skillName = new Map(skills.map((s) => [s.id, `${s.en} ${s.es}`]));
    for (let i = 0; i < jobs.n; i++) {
      const rf = meta.labels.rf[jobs.rf[i]] ?? ['', ''];
      const ind = meta.labels.ind[jobs.ind[i]] ?? ['', ''];
      const sk = jobs.sk[i] ? jobs.sk[i].split(',').map((s) => skillName.get(s) ?? '').join(' ') : '';
      const toks = tokens(`${jobs.title[i]} ${jobs.title[i]} ${rf.join(' ')} ${ind.join(' ')} ${sk}`);
      const tf = new Map<string, number>();
      for (const t of toks) tf.set(t, (tf.get(t) ?? 0) + 1);
      for (const t of tf.keys()) this.df.set(t, (this.df.get(t) ?? 0) + 1);
      this.docs.push(tf);
      this.len.push(toks.length);
    }
    this.avg = this.len.reduce((a, b) => a + b, 0) / Math.max(1, this.len.length);
  }

  rank(cv: string): Scored[] {
    const q = new Map<string, number>();
    for (const t of tokens(cv)) q.set(t, (q.get(t) ?? 0) + 1);
    const N = this.docs.length, k1 = 1.2, b = 0.75;
    const out: Scored[] = [];
    for (let i = 0; i < N; i++) {
      let s = 0;
      const tf = this.docs[i];
      for (const [t, qn] of q) {
        const f = tf.get(t);
        if (!f) continue;
        const idf = Math.log(1 + (N - (this.df.get(t) ?? 0) + 0.5) / ((this.df.get(t) ?? 0) + 0.5));
        s += idf * ((f * (k1 + 1)) / (f + k1 * (1 - b + (b * this.len[i]) / this.avg))) * Math.min(qn, 3);
      }
      out.push({ idx: i, score: s, passage: 0 });
    }
    return out.sort((a, b2) => b2.score - a.score);
  }
}

/** Short snippet of the CV passage that matched, cut at a word. */
export function snippet(passage: string, max = 110): string {
  const s = passage.replace(/\s+/g, ' ').trim();
  if (s.length <= max) return s;
  return s.slice(0, s.lastIndexOf(' ', max)).replace(/[,;:.-]+$/, '') + '…';
}
