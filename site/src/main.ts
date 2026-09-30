import './styles.css';
import { applyStatic, detectLang, fmtDate, fmtNum, getLang, listJoin, setLang, t, type Lang } from './i18n';
import { loadData, type Data } from './data';
import { countryName, guessCountry, openTo, parseWho } from './geo';
import { chunks, CvError, readFile, stripContact, wordCount } from './cv';
import { Embedder } from './embed';
import { compileSkills, cvSkills, Keyword, rankModel, snippet, type Scored } from './match';
import { renderMarket } from './market';
import { fitNotes, getKey, setKey, type Provider } from './byok';
import { $, esc, safeUrl } from './ui';

const ATS = new Set(['greenhouse', 'lever', 'ashby', 'recruitee']);
const PAGE = 50;

interface Result {
  ranked: Scored[];
  passages: string[];
  country: string;
  open: Uint8Array;        // 1 = open to the visitor
  status: string[];        // per job: yes / no / unclear / unknown
  cvSkills: Set<string>;
  mode: 'model' | 'quick';
  shown: number;
  notes: Map<number, string>;
}

let data: Data | null = null;
let result: Result | null = null;
let embedder: Embedder | null = null;
let vectorsLoaded = false;
let keyword: Keyword | null = null;
let skillRx: ReturnType<typeof compileSkills> = [];
let countryTouched = false;
const filters = { impact: false, role: '', level: '', pay: false, closed: false };

/* ---------- preferences ---------- */

function initTheme(): void {
  let saved: string | null = null;
  try { saved = localStorage.getItem('openfrom.theme'); } catch { /* blocked */ }
  if (saved === 'light' || saved === 'dark') document.documentElement.dataset.theme = saved;
  updateThemeButton();
  $('#theme').addEventListener('click', () => {
    const now = currentTheme() === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = now;
    try { localStorage.setItem('openfrom.theme', now); } catch { /* blocked */ }
    updateThemeButton();
  });
}
function currentTheme(): 'light' | 'dark' {
  const set = document.documentElement.dataset.theme;
  if (set === 'light' || set === 'dark') return set;
  return matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}
function updateThemeButton(): void {
  $('#theme').textContent = currentTheme() === 'dark' ? t('theme.light') : t('theme.dark');
}

function applyLang(l: Lang, remember = true): void {
  setLang(l, remember);
  applyStatic();
  const b = $('#lang');
  b.textContent = t('lang.other');
  b.setAttribute('aria-label', t('lang.otherName'));
  updateThemeButton();
  if (data) {
    renderStats();
    fillCountries();
    renderAbout();
  }
  if (result) renderResults();
  else renderBefore();
}

/* ---------- tabs ---------- */

function initTabs(): void {
  const tabs = [...document.querySelectorAll<HTMLButtonElement>('[role="tab"]')];
  const select = (tab: HTMLButtonElement, focus = false) => {
    for (const x of tabs) {
      const on = x === tab;
      x.setAttribute('aria-selected', String(on));
      x.tabIndex = on ? 0 : -1;
      $(`#panel-${x.dataset.tab}`).hidden = !on;
    }
    const about = tab.dataset.tab === 'about';
    for (const id of ['#tool', '.intro']) $(id).hidden = about;
    if (about) $('#status').hidden = true;
    else if ($('#status-text').textContent) $('#status').hidden = false;
    if (focus) tab.focus();
  };
  tabs.forEach((tab, i) => {
    tab.addEventListener('click', () => select(tab));
    tab.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
        e.preventDefault();
        select(tabs[(i + (e.key === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length], true);
      }
    });
  });
}

/* ---------- status line ---------- */

function status(text: string, kind: 'info' | 'error' = 'info', progress: number | null = null): void {
  const box = $('#status');
  box.hidden = !text;
  box.classList.toggle('error', kind === 'error');
  $('#status-text').textContent = text;
  $('#progress').hidden = progress === null;
  if (progress !== null) $('#progress-bar').style.width = `${Math.round(progress * 100)}%`;
}

/* ---------- data-driven chrome ---------- */

function renderStats(): void {
  if (!data) return;
  $('#stats').textContent = t('stats', {
    n: fmtNum(data.jobs.n), s: data.meta.sources.length, date: fmtDate(data.meta.date, true),
    ww: Math.max(1, Math.round(data.market.worldwide_share * 100)),
  });
}

function fillCountries(): void {
  if (!data) return;
  const sel = $<HTMLSelectElement>('#country');
  const cur = sel.value;
  const lang = getLang();
  const opts = Object.keys(data.geo.countries)
    .map((c) => [c, countryName(c, data!.geo, lang)] as const)
    .sort((a, b) => a[1].localeCompare(b[1], lang));
  sel.innerHTML = `<option value="">${esc(t('country.pick'))}</option>` +
    opts.map(([c, n]) => `<option value="${c}">${esc(n)}</option>`).join('');
  sel.value = cur;
}

function maybeGuessCountry(text: string): void {
  if (!data || countryTouched) return;
  const g = guessCountry(text, data.geo);
  if (g) {
    $<HTMLSelectElement>('#country').value = g;
    $('#country-hint').hidden = false;
  }
}

function slowDevice(): boolean {
  const c = (navigator as unknown as { connection?: { saveData?: boolean; effectiveType?: string } }).connection;
  const mem = (navigator as unknown as { deviceMemory?: number }).deviceMemory;
  return !!(c?.saveData || /(^|-)2g|3g/.test(c?.effectiveType ?? '') || (mem !== undefined && mem < 4) ||
    matchMedia('(max-width: 640px)').matches);
}

/* ---------- CV input ---------- */

function initInput(): void {
  const text = $<HTMLTextAreaElement>('#cv-text');
  const file = $<HTMLInputElement>('#cv-file');
  const drop = $('#drop');
  let timer = 0;
  text.addEventListener('input', () => {
    clearTimeout(timer);
    timer = window.setTimeout(() => maybeGuessCountry(text.value), 400);
  });
  const load = async (f: File) => {
    status(t('status.parsing'));
    try {
      const s = await readFile(f);
      text.value = s.trim();
      $('#file-name').textContent = t('cv.loaded', { name: f.name, words: fmtNum(wordCount(s)) });
      maybeGuessCountry(s);
      status('');
    } catch (e) {
      status(t(e instanceof CvError && e.code === 'pdf' ? 'err.pdf' : 'err.file'), 'error');
    }
  };
  file.addEventListener('change', () => { if (file.files?.[0]) void load(file.files[0]); });
  drop.addEventListener('dragover', (e) => { e.preventDefault(); drop.classList.add('over'); });
  drop.addEventListener('dragleave', () => drop.classList.remove('over'));
  drop.addEventListener('drop', (e) => {
    e.preventDefault();
    drop.classList.remove('over');
    const f = e.dataTransfer?.files?.[0];
    if (f) void load(f);
  });
  $('#country').addEventListener('change', () => {
    countryTouched = true;
    $('#country-hint').hidden = true;
  });
  if (slowDevice()) {
    $('#slow-hint').hidden = false;
    $<HTMLInputElement>('input[name="mode"][value="quick"]').checked = true;
  }
  $('#tool').addEventListener('submit', (e) => { e.preventDefault(); void run(); });
}

/* ---------- matching ---------- */

async function ensureModel(): Promise<void> {
  if (!data) return;
  embedder ??= new Embedder();
  status(t('status.modelStart'), 'info', 0);
  await embedder.init((loaded, total) => {
    if (total > 0) {
      status(t('status.model', { done: fmtNum(loaded / 1e6), total: fmtNum(total / 1e6) }), 'info', loaded / total);
    }
  });
  if (!vectorsLoaded) {
    const r = await fetch(new URL('./data/vectors.bin', document.baseURI), { cache: 'no-cache' });
    if (!r.ok) throw new Error('vectors');
    await embedder.setVectors(await r.arrayBuffer(), data.jobs.n);
    vectorsLoaded = true;
  }
}

let rfModel: { cls: string[]; b: number[]; coef: number[][] } | null = null;

/** Per job: the probability that the CV belongs to the job's role family (softmax of the trained model). */
async function rolePrior(v: Float32Array): Promise<Float32Array> {
  const n = data!.jobs.n;
  const out = new Float32Array(n);
  try {
    rfModel ??= await (await fetch(new URL('./data/rfmodel.json', document.baseURI))).json();
  } catch {
    return out;
  }
  const m = rfModel!;
  const logits = m.coef.map((row, c) => row.reduce((s, x, d) => s + x * v[d], m.b[c]));
  const mx = Math.max(...logits);
  const ex = logits.map((l) => Math.exp(l - mx));
  const sum = ex.reduce((a, b) => a + b, 0);
  const p = new Map(m.cls.map((c, i) => [c, ex[i] / sum]));
  for (let i = 0; i < n; i++) out[i] = p.get(data!.jobs.rf[i]) ?? 0;
  return out;
}

async function run(): Promise<void> {
  if (!data) return;
  const cv = $<HTMLTextAreaElement>('#cv-text').value.trim();
  const country = $<HTMLSelectElement>('#country').value;
  const words = wordCount(cv);
  if (!cv) { status(t('err.empty'), 'error'); $('#cv-text').focus(); return; }
  if (!country) { status(t('err.country'), 'error'); $('#country').focus(); return; }
  const mode = ($<HTMLInputElement>('input[name="mode"]:checked').value as 'model' | 'quick');
  const go = $<HTMLButtonElement>('#go');
  go.disabled = true;
  try {
    let ranked: Scored[];
    let passages: string[] = [];
    if (mode === 'model') {
      try {
        await ensureModel();
      } catch {
        status(t('err.model'), 'error');
        return;
      }
      passages = chunks(cv);
      if (!passages.length) passages = [cv.slice(0, 600)];
      status(t('status.matching', { n: fmtNum(data.jobs.n) }));
      const body = stripContact(cv).slice(0, 1500);
      const all = await embedder!.embed([...passages.map((p) => 'query: ' + p), 'query: ' + body, 'passage: ' + body]);
      const vecs = all.slice(0, passages.length);
      const prior = await rolePrior(all[all.length - 1]);
      const { best, which } = await embedder!.score(vecs, all[all.length - 2], prior);
      ranked = rankModel(best, which);
    } else {
      status(t('status.matching', { n: fmtNum(data.jobs.n) }));
      keyword ??= new Keyword(data);
      ranked = keyword.rank(cv);
    }
    const n = data.jobs.n;
    const open = new Uint8Array(n);
    const st: string[] = new Array(n);
    for (let i = 0; i < n; i++) {
      st[i] = openTo(data.jobs.w[i], country, data.geo);
      open[i] = st[i] === 'yes' ? 1 : 0;
    }
    result = { ranked, passages, country, open, status: st, cvSkills: cvSkills(cv, skillRx), mode, shown: PAGE, notes: new Map() };
    const openCount = open.reduce((a, b) => a + b, 0);
    status(t('status.done', { n: fmtNum(openCount), country: countryName(country, data.geo, getLang()) }));
    if (words < 60) status(t('err.short', { words }), 'error');
    renderResults();
    $('#panel-matches').scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
  } finally {
    go.disabled = false;
  }
}

/* ---------- results ---------- */

function whoChip(i: number): string {
  if (!data || !result) return '';
  const code = data.jobs.w[i];
  const s = result.status[i];
  const lang = getLang();
  if (s === 'unclear') return `<span class="who unsure">${esc(t('who.unclear'))}</span>`;
  if (s === 'unknown') return `<span class="who unsure">${esc(t('who.unknown'))}</span>`;
  const w = parseWho(code);
  const tz = w.utc ? ` · ${t('who.tz', { band: fmtBand(w.utc) })}` : '';
  if (s === 'yes') {
    const label = w.world && !w.utc ? t('who.world') : t('who.you', { country: countryName(result.country, data.geo, lang) });
    return `<span class="who open">${esc(label + tz)}</span>`;
  }
  const places = [...w.countries.map((c) => countryName(c, data!.geo, lang)), ...w.regions.map((r) => t(`region.${r}`))];
  return `<span class="who closed">${esc(places.length ? t('who.only', { places: listJoin(places) }) : t('who.tz', { band: fmtBand(w.utc ?? [0, 0]) }).trim())}${esc(places.length ? tz : '')}</span>`;
}

function fmtBand([a, b]: number[]): string {
  const f = (x: number) => (x >= 0 ? '+' : '−') + Math.abs(x);
  return a === b ? f(a) : t('who.range', { a: f(a), b: f(b) });
}

function payText(i: number): string {
  const p = data!.jobs.pay[i];
  if (!Array.isArray(p)) return `<span class="job-pay none">${esc(t('card.noPay'))}</span>`;
  const [lo, hi] = p;
  const txt = lo === hi ? t('card.payOne', { lo: fmtNum(lo) }) : t('card.pay', { lo: fmtNum(lo), hi: fmtNum(hi) });
  return `<span class="job-pay num">${esc(txt)}</span>`;
}

function sourceName(i: number): string {
  const { jobs, meta } = data!;
  const id = jobs.sources[jobs.src[i]];
  if (ATS.has(id)) return jobs.org[i] || meta.sources.find((s) => s.id === id)?.name || id;
  return meta.sources.find((s) => s.id === id)?.name ?? id;
}

function visible(): number[] {
  if (!data || !result) return [];
  const { jobs } = data;
  const out: number[] = [];
  for (const r of result.ranked) {
    const i = r.idx;
    if (!filters.closed && result.status[i] !== 'yes') continue;
    if (filters.impact && !jobs.imp[i]) continue;
    if (filters.role && jobs.rf[i] !== filters.role) continue;
    if (filters.level && jobs.sen[i] !== filters.level) continue;
    if (filters.pay && !Array.isArray(jobs.pay[i])) continue;
    if (result.mode === 'quick' && r.score <= 0) break;
    out.push(i);
  }
  return out;
}

function card(i: number, rank: Scored | undefined): string {
  const { jobs, meta } = data!;
  const L = getLang() === 'es' ? 1 : 0;
  const closed = result!.status[i] !== 'yes';
  const meta1 = [jobs.org[i], jobs.posted[i] ? t('card.posted', { date: fmtDate(jobs.posted[i]) }) : '']
    .filter(Boolean).map(esc).join(' · ');
  let why = '';
  if (result!.mode === 'model' && rank && result!.passages[rank.passage]) {
    why = t('card.why', { text: snippet(result!.passages[rank.passage]) });
  }
  const skillName = new Map(data!.skills.map((s) => [s.id, L ? s.es : s.en]));
  const shared = (jobs.sk[i] ? jobs.sk[i].split(',') : []).filter((s) => result!.cvSkills.has(s)).slice(0, 3)
    .map((s) => skillName.get(s) ?? s);
  if (shared.length) why += (why ? ' ' : '') + t('card.shared', { skills: listJoin(shared) });
  const rf = meta.labels.rf[jobs.rf[i]]?.[L] ?? '';
  const note = result!.notes.get(i);
  return `<li class="job${closed ? ' closed' : ''}">
    <div>
      <h3 class="job-title"><a href="${esc(safeUrl(jobs.url[i]))}" target="_blank" rel="noopener noreferrer">${esc(jobs.title[i])}</a></h3>
      <p class="job-meta">${meta1}</p>
      ${whoChip(i)}${jobs.imp[i] ? `<span class="tag">${esc(t('card.impact'))}</span>` : ''}${rf ? `<span class="tag">${esc(rf)}</span>` : ''}
      ${why ? `<p class="job-why">${esc(why)}</p>` : ''}
      ${jobs.sum[i] ? `<p class="job-sum">${esc(jobs.sum[i])}</p>` : ''}
      ${note ? `<p class="ai-note">${esc(note)}</p>` : ''}
    </div>
    <div class="job-side">
      ${payText(i)}
      <a class="job-link" href="${esc(safeUrl(jobs.url[i]))}" target="_blank" rel="noopener noreferrer">${esc(t('card.view', { source: sourceName(i) }))} ↗</a>
    </div>
  </li>`;
}

function renderBefore(): void {
  $('#panel-matches').innerHTML = '';
  $('#panel-market').innerHTML = `<p class="empty">${esc(t('m.before'))}</p>`;
}

function renderResults(): void {
  if (!data || !result) return;
  const root = $('#panel-matches');
  const { jobs, meta } = data;
  const L = getLang() === 'es' ? 1 : 0;
  const cname = countryName(result.country, data.geo, getLang());
  const openCount = result.open.reduce((a, b) => a + b, 0);
  const list = visible();
  const shown = list.slice(0, result.shown);
  const rankOf = new Map(result.ranked.map((r) => [r.idx, r]));
  const roles = [...new Set(jobs.rf)].sort((a, b) => (meta.labels.rf[a]?.[L] ?? a).localeCompare(meta.labels.rf[b]?.[L] ?? b));
  const levels = ['INTERN', 'JUNIOR', 'MID', 'SENIOR', 'LEAD'];
  const k = Math.min(PAGE, list.length);
  root.innerHTML = `
    <p class="summary">${t(result.mode === 'model' ? 'sum.results' : 'sum.resultsQuick', {
      open: fmtNum(openCount), n: fmtNum(jobs.n), country: esc(cname), k: fmtNum(k) })}${filters.closed ? ' ' + esc(t('sum.closed')) : ''}</p>
    <div class="filters" role="group" aria-label="Filters">
      <label class="check"><input type="checkbox" id="f-impact" ${filters.impact ? 'checked' : ''}> ${esc(t('f.impact'))}</label>
      <label class="check"><span class="sr">${esc(t('f.role'))}</span>
        <select id="f-role" aria-label="${esc(t('f.role'))}"><option value="">${esc(t('f.allRoles'))}</option>
        ${roles.map((r) => `<option value="${r}" ${filters.role === r ? 'selected' : ''}>${esc(meta.labels.rf[r]?.[L] ?? r)}</option>`).join('')}</select></label>
      <label class="check"><select id="f-level" aria-label="${esc(t('f.level'))}"><option value="">${esc(t('f.allLevels'))}</option>
        ${levels.map((r) => `<option value="${r}" ${filters.level === r ? 'selected' : ''}>${esc(meta.labels.sen[r]?.[L] ?? r)}</option>`).join('')}</select></label>
      <label class="check"><input type="checkbox" id="f-pay" ${filters.pay ? 'checked' : ''}> ${esc(t('f.pay'))}</label>
      <label class="check"><input type="checkbox" id="f-closed" ${filters.closed ? 'checked' : ''}> ${esc(t('f.closed'))}</label>
      <span class="count num" aria-live="polite">${esc(t('f.count', { n: fmtNum(shown.length) }))}</span>
    </div>
    ${shown.length ? `<ol class="jobs">${shown.map((i) => card(i, rankOf.get(i))).join('')}</ol>` : `<p class="empty">${esc(t('empty.filters'))}</p>`}
    ${list.length > shown.length ? `<p class="more"><button class="secondary" id="more">${esc(t('more'))}</button></p>` : ''}
    ${renderByok()}`;
  root.querySelector('.sr')?.remove();
  const bind = (id: string, key: keyof typeof filters, prop: 'checked' | 'value') => {
    root.querySelector<HTMLInputElement>(`#${id}`)!.addEventListener('change', (e) => {
      (filters as Record<string, unknown>)[key] = (e.target as HTMLInputElement)[prop];
      result!.shown = PAGE;
      renderResults();
      root.querySelector<HTMLElement>(`#${id}`)?.focus();
    });
  };
  bind('f-impact', 'impact', 'checked');
  bind('f-role', 'role', 'value');
  bind('f-level', 'level', 'value');
  bind('f-pay', 'pay', 'checked');
  bind('f-closed', 'closed', 'checked');
  root.querySelector('#more')?.addEventListener('click', () => { result!.shown += 25; renderResults(); });
  bindByok(root, shown.filter((i) => result!.status[i] === 'yes').slice(0, 10));

  // Market map: the three role families most common among the closest open jobs.
  const top = result.ranked.filter((r) => result!.open[r.idx]).slice(0, 60);
  const fam = new Map<string, number>();
  top.forEach((r, j) => fam.set(jobs.rf[r.idx], (fam.get(jobs.rf[r.idx]) ?? 0) + 1 / (1 + j / 20)));
  let families = [...fam].sort((a, b) => b[1] - a[1]).slice(0, 3).map(([f]) => f);
  if (!families.length) families = result.ranked.slice(0, 30).map((r) => jobs.rf[r.idx]).filter((f, i, a) => a.indexOf(f) === i).slice(0, 3);
  renderMarket($('#panel-market'), data, result.country, cname, result.open, families, result.cvSkills);
}

/* ---------- bring your own key ---------- */

function renderByok(): string {
  const key = getKey();
  return `<details class="byok" id="byok"><summary>${esc(t('byok.title'))}</summary><div class="byok-body">
    <p class="warn">${esc(t('byok.warn'))}</p>
    <label class="label" for="byok-provider">${esc(t('byok.provider'))}</label>
    <select id="byok-provider"><option value="openrouter">OpenRouter</option><option value="gemini">Google Gemini</option></select>
    <label class="label" for="byok-key">${esc(t('byok.key'))}</label>
    <input type="password" id="byok-key" autocomplete="off" value="${esc(key)}">
    <p class="hint">${esc(t('byok.keyHint'))}</p>
    <label class="check"><input type="checkbox" id="byok-remember"> ${esc(t('byok.remember'))}</label>
    <label class="label" for="byok-model">${esc(t('byok.model'))}</label>
    <input type="text" id="byok-model" value="google/gemini-2.5-flash" spellcheck="false">
    <div><button class="secondary" id="byok-run" type="button">${esc(t('byok.run'))}</button></div>
    <p class="hint" id="byok-status" aria-live="polite"></p>
  </div></details>`;
}

function bindByok(root: HTMLElement, top: number[]): void {
  const prov = root.querySelector<HTMLSelectElement>('#byok-provider')!;
  const model = root.querySelector<HTMLInputElement>('#byok-model')!;
  prov.addEventListener('change', () => { model.value = prov.value === 'gemini' ? 'gemini-2.5-flash' : 'google/gemini-2.5-flash'; });
  root.querySelector('#byok-run')!.addEventListener('click', async () => {
    const out = root.querySelector<HTMLElement>('#byok-status')!;
    const key = root.querySelector<HTMLInputElement>('#byok-key')!.value.trim();
    if (!key) { out.textContent = t('byok.needKey'); return; }
    setKey(key, root.querySelector<HTMLInputElement>('#byok-remember')!.checked);
    out.textContent = t('byok.working', { n: top.length });
    try {
      const { jobs } = data!;
      const notes = await fitNotes(prov.value as Provider, key, model.value.trim(), $<HTMLTextAreaElement>('#cv-text').value,
        top.map((i) => ({ title: jobs.title[i], org: jobs.org[i], summary: jobs.sum[i], who: jobs.w[i] })), getLang());
      top.forEach((i, j) => { if (notes[j]) result!.notes.set(i, notes[j]); });
      renderResults();
      const done = $('#byok-status');
      if (done) done.textContent = t('byok.done', { n: top.length });
    } catch (e) {
      out.textContent = String((e as Error).message);
    }
  });
}

/* ---------- about ---------- */

function renderAbout(): void {
  if (!data) return;
  const q = data.quality.fields ?? {};
  const order = ['role_family', 'industry', 'seniority', 'engagement', 'employer_type'];
  const pct = (x: number) => `${Math.round(x * 100)}%`;
  const rows = order.filter((f) => q[f]).map((f) =>
    `<tr><td>${esc(t(`field.${f}`))}${q[f].approximate ? ` <span class="tag">${esc(t('card.approx'))}</span>` : ''}</td><td class="n">${pct(q[f].agreement)}</td><td class="n">${pct(q[f].baseline)}</td></tr>`).join('');
  const mail = `mailto:naksnack.world@gmail.com?subject=${encodeURIComponent(t('a.ask.subject'))}&body=${encodeURIComponent(t('a.ask.body'))}`;
  $('#panel-about').innerHTML = `<div class="prose">
    <h2>${esc(t('a.how.h'))}</h2>
    <p>${esc(t('a.how.1'))}</p><p>${esc(t('a.how.2'))}</p><p>${esc(t('a.how.3'))}</p><p>${esc(t('a.how.4'))}</p>
    <h2>${esc(t('a.privacy.h'))}</h2>
    <p>${esc(t('a.privacy.1'))}</p><p>${esc(t('a.privacy.2'))}</p><p>${esc(t('a.privacy.3'))}</p>
    <h2>${esc(t('a.labels.h'))}</h2>
    <p>${esc(t('a.labels.1', { n: fmtNum(q.role_family?.n ?? 0) }))}</p>
    <table class="q-table"><thead><tr><th>${esc(t('a.labels.field'))}</th><th>${esc(t('a.labels.agree'))}</th><th>${esc(t('a.labels.base'))}</th></tr></thead><tbody>${rows}</tbody></table>
    <p>${esc(t('a.labels.2'))}</p>
    <h2>${esc(t('a.sources.h'))}</h2>
    <p>${esc(t('a.sources.1'))}</p>
    <ul class="src-list">${data.meta.sources.map((s) => `<li>${s.url ? `<a href="${esc(safeUrl(s.url))}" rel="noopener noreferrer">${esc(s.name)}</a>` : esc(s.name)} <span class="num">${fmtNum(s.jobs)}</span></li>`).join('')}</ul>
    <p>${esc(t('a.sources.2'))}</p>
    <h2>${esc(t('a.who.h'))}</h2>
    <p>${esc(t('a.who.1'))} <a href="https://89jdvm.github.io/agentic-workflows-portfolio/">Portfolio</a> · <a href="https://www.linkedin.com/in/jdv42">LinkedIn</a> · <a href="https://github.com/89jdvm/openfrom">GitHub</a></p>
    <div class="ask"><p>${esc(t('a.ask.1'))}</p><a class="secondary" href="${esc(mail)}" style="text-decoration:none;display:inline-block">${esc(t('a.ask.btn'))}</a></div>
  </div>`;
}

/* ---------- start ---------- */

async function start(): Promise<void> {
  initTheme();
  initTabs();
  applyLang(detectLang(), false);
  $('#lang').addEventListener('click', () => applyLang(getLang() === 'es' ? 'en' : 'es'));
  initInput();
  $('#stats').textContent = t('stats.loading');
  try {
    data = await loadData();
  } catch {
    status(t('err.data'), 'error');
    $('#stats').textContent = '';
    return;
  }
  skillRx = compileSkills(data.skills);
  renderStats();
  fillCountries();
  renderAbout();
  renderBefore();
  const cv = $<HTMLTextAreaElement>('#cv-text').value;
  if (cv) maybeGuessCountry(cv);
}

// Test hook for the Node/browser embedding parity check (e2e/parity.spec.ts): only with ?parity in the URL.
if (new URLSearchParams(location.search).has('parity')) {
  (window as unknown as { openfromEmbed: (t: string[]) => Promise<number[][]> }).openfromEmbed = async (texts) => {
    embedder ??= new Embedder();
    await embedder.init(() => {});
    return (await embedder.embed(texts)).map((v) => Array.from(v));
  };
}

void start();
