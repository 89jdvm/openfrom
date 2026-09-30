/**
 * Optional fit notes with the visitor's own AI key. The key stays in memory, or in
 * sessionStorage if the visitor asks. Calls go straight from the browser to the provider.
 */
import { t } from './i18n';

export type Provider = 'openrouter' | 'gemini';
export interface NoteJob { title: string; org: string; summary: string; who: string }

let memoryKey = '';

export function getKey(): string {
  if (memoryKey) return memoryKey;
  try { return sessionStorage.getItem('openfrom.key') ?? ''; } catch { return ''; }
}

export function setKey(key: string, remember: boolean): void {
  memoryKey = key;
  try {
    if (remember) sessionStorage.setItem('openfrom.key', key);
    else sessionStorage.removeItem('openfrom.key');
  } catch { /* storage blocked */ }
}

function prompt(cv: string, jobs: NoteJob[], lang: 'en' | 'es'): string {
  const list = jobs.map((j, i) => `${i + 1}. ${j.title} at ${j.org || 'unknown employer'} (${j.who}). ${j.summary}`).join('\n');
  return `You help a job seeker judge fit. Write in ${lang === 'es' ? 'Spanish' : 'English'}.
For each numbered job, write one or two plain sentences: the strongest match between the CV and the job, then the biggest gap. No preamble.
Answer as a JSON array of strings, one per job, in order.

CV:
${cv.slice(0, 6000)}

Jobs:
${list}`;
}

function parseNotes(text: string, n: number): string[] {
  const m = text.match(/\[[\s\S]*\]/);
  if (m) {
    try {
      const arr = JSON.parse(m[0]);
      if (Array.isArray(arr)) return arr.slice(0, n).map((s) => String(s));
    } catch { /* fall through */ }
  }
  return text.split(/\n+\s*\d+[.)]\s*/).map((s) => s.trim()).filter(Boolean).slice(0, n);
}

export async function fitNotes(provider: Provider, key: string, model: string, cv: string, jobs: NoteJob[],
  lang: 'en' | 'es'): Promise<string[]> {
  const body = prompt(cv, jobs, lang);
  let r: Response;
  if (provider === 'openrouter') {
    r = await fetch('https://openrouter.ai/api/v1/chat/completions', {
      method: 'POST',
      headers: { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json', 'X-Title': 'openfrom' },
      body: JSON.stringify({ model, messages: [{ role: 'user', content: body }], temperature: 0.2 }),
    });
  } else {
    const m = model || 'gemini-2.5-flash';
    r = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(m)}:generateContent`, {
      method: 'POST',
      headers: { 'x-goog-api-key': key, 'Content-Type': 'application/json' },
      body: JSON.stringify({ contents: [{ parts: [{ text: body }] }], generationConfig: { temperature: 0.2 } }),
    });
  }
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(t('byok.err', { msg: String(j?.error?.message ?? r.status) }));
  const text = provider === 'openrouter'
    ? j?.choices?.[0]?.message?.content ?? ''
    : (j?.candidates?.[0]?.content?.parts ?? []).map((p: { text?: string }) => p.text ?? '').join('');
  return parseNotes(String(text), jobs.length);
}
