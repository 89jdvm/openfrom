/** Market map: for the visitor's top role families, how much of the market is open to them. */
import type { Data } from './data';
import { fmtDate, fmtNum, getLang, t } from './i18n';
import { esc } from './ui';

const SVG = 'http://www.w3.org/2000/svg';

let tip: HTMLDivElement | null = null;
function showTip(text: string, x: number, y: number): void {
  if (!tip) {
    tip = document.createElement('div');
    tip.className = 'tip';
    tip.setAttribute('role', 'tooltip');
    document.body.appendChild(tip);
  }
  tip.textContent = text;
  tip.hidden = false;
  const w = tip.offsetWidth;
  tip.style.left = `${Math.min(Math.max(8, x - w / 2), window.innerWidth - w - 8)}px`;
  tip.style.top = `${Math.max(8, y - 36)}px`;
}
function hideTip(): void { if (tip) tip.hidden = true; }

function hover(el: SVGElement, text: string): void {
  el.setAttribute('tabindex', '0');
  el.setAttribute('aria-label', text);
  el.addEventListener('pointermove', (e) => showTip(text, e.clientX, e.clientY));
  el.addEventListener('pointerleave', hideTip);
  el.addEventListener('focus', () => {
    const r = el.getBoundingClientRect();
    showTip(text, r.left + r.width / 2, r.top);
  });
  el.addEventListener('blur', hideTip);
}

function svg(w: number, h: number, label: string): SVGSVGElement {
  const s = document.createElementNS(SVG, 'svg');
  s.setAttribute('viewBox', `0 0 ${w} ${h}`);
  s.setAttribute('role', 'img');
  s.setAttribute('aria-label', label);
  return s;
}
function el<K extends keyof SVGElementTagNameMap>(tag: K, attrs: Record<string, string | number>, parent?: Element): SVGElementTagNameMap[K] {
  const e = document.createElementNS(SVG, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, String(v));
  parent?.appendChild(e);
  return e;
}
/** A bar with its top corners rounded (radius r), anchored to the baseline. */
function barPath(x: number, y: number, w: number, h: number, r = 3): string {
  const rr = Math.min(r, w / 2, h);
  return `M${x},${y + h}V${y + rr}Q${x},${y} ${x + rr},${y}H${x + w - rr}Q${x + w},${y} ${x + w},${y + rr}V${y + h}Z`;
}

function mondayOf(iso: string): string {
  const d = new Date(iso + 'T12:00:00Z');
  const day = (d.getUTCDay() + 6) % 7;
  d.setUTCDate(d.getUTCDate() - day);
  return d.toISOString().slice(0, 10);
}

function quantile(sorted: number[], q: number): number {
  const i = (sorted.length - 1) * q;
  const lo = Math.floor(i), hi = Math.ceil(i);
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (i - lo);
}

function shareFig(open: number, total: number): HTMLElement {
  const fig = document.createElement('div');
  fig.className = 'fig';
  const W = 480, H = 14, gap = 2;
  const s = svg(W, H, `${t('m.shareOpen')}: ${open}. ${t('m.shareClosed')}: ${total - open}.`);
  const wOpen = total ? Math.max(open ? 3 : 0, (W * open) / total) : 0;
  if (open) el('rect', { x: 0, y: 0, width: Math.max(0, wOpen - (open < total ? gap : 0)), height: H, rx: 3, class: 'open' }, s);
  if (open < total) el('rect', { x: wOpen, y: 0, width: W - wOpen, height: H, rx: 3, class: 'closed' }, s);
  fig.innerHTML = `<h3>${esc(t('m.share'))}</h3>`;
  fig.appendChild(s);
  const legend = document.createElement('p');
  legend.className = 'note';
  legend.innerHTML = `<span style="color:var(--open-ink);font-weight:600">${esc(t('m.shareOpen'))} ${fmtNum(open)}</span> · ${esc(t('m.shareClosed'))} ${fmtNum(total - open)}`;
  fig.appendChild(legend);
  return fig;
}

function weeksFig(dates: string[], today: string): HTMLElement {
  const fig = document.createElement('div');
  fig.className = 'fig';
  const weeks: string[] = [];
  let w = mondayOf(today);
  for (let i = 0; i < 8; i++) {
    weeks.unshift(w);
    const d = new Date(w + 'T12:00:00Z');
    d.setUTCDate(d.getUTCDate() - 7);
    w = d.toISOString().slice(0, 10);
  }
  const counts = weeks.map(() => 0);
  for (const d of dates) {
    const i = weeks.indexOf(mondayOf(d));
    if (i >= 0) counts[i]++;
  }
  const max = Math.max(1, ...counts);
  // The chart itself carries no text: labels are HTML below it, so they stay legible at any width.
  const W = 480, H = 96, top = 4, base = H - 1, gap = 6;
  const bw = (W - gap * (weeks.length - 1)) / weeks.length;
  const s = svg(W, H, t('m.weeks'));
  s.setAttribute('preserveAspectRatio', 'none');
  s.classList.add('bars');
  s.style.height = `${H}px`;
  el('line', { x1: 0, x2: W, y1: base + 0.5, y2: base + 0.5, class: 'axis' }, s);
  const partial = today < addDays(weeks[weeks.length - 1], 6); // the current week is not over yet
  let peak = 0;
  counts.forEach((c, i) => {
    const x = i * (bw + gap);
    const h = ((base - top) * c) / max;
    const g = el('g', {}, s);
    const last = i === weeks.length - 1;
    if (c) el('path', { d: barPath(x, base - h, bw, h), class: `open bar${last && partial ? ' partial' : ''}` }, g);
    const hit = el('rect', { x: x - gap / 2, y: 0, width: bw + gap, height: base, class: 'hit' }, g);
    hover(hit, t('m.weekTip', { date: fmtDate(weeks[i]), n: fmtNum(c) }) + (last && partial ? ` (${t('m.partial')})` : ''));
    if (c === max) peak = i;
  });
  fig.innerHTML = `<h3>${esc(t('m.weeks'))}</h3>`;
  fig.appendChild(s);
  fig.insertAdjacentHTML('beforeend', `<div class="axis-row"><span>${esc(fmtDate(weeks[0]))}</span><span>${esc(fmtDate(weeks[weeks.length - 1]))}</span></div>` +
    `<p class="note">${esc(t('m.peak', { n: fmtNum(counts[peak]), date: fmtDate(weeks[peak]) }))}${partial ? ' ' + esc(t('m.partialNote')) : ''}</p>`);
  const rows = weeks.map((wk, i) => `<tr><td>${esc(fmtDate(wk))}</td><td>${fmtNum(counts[i])}</td></tr>`).join('');
  fig.insertAdjacentHTML('beforeend', `<details class="table"><summary>${esc(t('m.table'))}</summary><table><thead><tr><th>${esc(t('m.colWeek'))}</th><th>${esc(t('m.colJobs'))}</th></tr></thead><tbody>${rows}</tbody></table></details>`);
  return fig;
}

/** Labelled rows with thin bars. `scale`: the value a full bar stands for (default: the largest row).
 *  `neutral`: grey bars, for anything that is not "open to you". */
function rowsFig(title: string, rows: [string, number, string][], note = '', opts: { scale?: number; neutral?: boolean; bars?: boolean } = {}): HTMLElement {
  const fig = document.createElement('div');
  fig.className = 'fig';
  const max = opts.scale ?? Math.max(1, ...rows.map((r) => r[1]));
  fig.innerHTML = `<h3>${esc(title)}</h3><ul class="rows${opts.neutral ? ' neutral' : ''}">${rows.map(([name, v, label]) =>
    `<li><span class="name" title="${esc(name)}">${esc(name)}</span><span class="val">${esc(label)}</span>` +
    (opts.bars === false ? '' : `<span class="bar-track" aria-hidden="true"><span class="bar-fill" style="display:block;width:${Math.min(100, (100 * v) / max)}%"></span></span>`) + '</li>').join('')}</ul>` +
    (note ? `<p class="note">${esc(note)}</p>` : '');
  return fig;
}

function addDays(iso: string, n: number): string {
  const d = new Date(iso + 'T12:00:00Z');
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

function payFig(pays: number[]): HTMLElement {
  const fig = document.createElement('div');
  fig.className = 'fig';
  fig.innerHTML = `<h3>${esc(t('m.pay'))}</h3>`;
  if (pays.length < 5) {
    fig.insertAdjacentHTML('beforeend', `<p class="note">${esc(t('m.payNone'))}</p>`);
    return fig;
  }
  const s = [...pays].sort((a, b) => a - b);
  const p10 = quantile(s, 0.1), p25 = quantile(s, 0.25), med = quantile(s, 0.5), p75 = quantile(s, 0.75), p90 = quantile(s, 0.9);
  const lo = p10 * 0.9, hi = p90 * 1.05;
  const W = 480, H = 24, y = 4, x = (v: number) => ((v - lo) / (hi - lo)) * W;
  const money = (v: number) => '$' + fmtNum(Math.round(v / 10) * 10);
  const g = svg(W, H, `${money(p25)}–${money(p75)}, median ${money(med)}`);
  g.setAttribute('preserveAspectRatio', 'none');
  g.classList.add('bars');
  g.style.height = `${H}px`;
  el('line', { x1: x(p10), x2: x(p90), y1: y + 8, y2: y + 8, stroke: 'var(--closed)', 'stroke-width': 2 }, g);
  const box = el('rect', { x: x(p25), y, width: Math.max(4, x(p75) - x(p25)), height: 16, rx: 3, class: 'open' }, g);
  hover(box, `${money(p25)}–${money(p75)}`);
  el('rect', { x: x(med) - 1.5, y: 0, width: 3, height: H, fill: 'var(--ink)' }, g);
  fig.appendChild(g);
  // Value labels as HTML, placed under the box ends, so they keep their size on phones.
  const pct = (v: number) => Math.max(0, Math.min(100, (100 * x(v)) / W));
  // Keep labels inside the figure: near an edge, pin them to that edge.
  const loPos = pct(p25) < 18 ? 'left:0' : `right:${100 - pct(p25)}%`;
  const hiPos = pct(p75) > 82 ? 'right:0' : `left:${pct(p75)}%`;
  fig.insertAdjacentHTML('beforeend', `<div class="pay-labels"><span style="${loPos}">${esc(money(p25))}</span>` +
    `<span style="${hiPos}">${esc(money(p75))}</span></div>` +
    `<p class="note">${esc(t('m.payNote', { n: fmtNum(pays.length), median: money(med) }))}</p>`);
  return fig;
}

export function renderMarket(root: HTMLElement, data: Data, country: string, countryLabel: string,
  open: Uint8Array, topFamilies: string[], cvSkillIds: Set<string>): void {
  const { jobs, meta, skills } = data;
  const lang = getLang();
  const L = lang === 'es' ? 1 : 0;
  root.innerHTML = `<p class="market-intro">${esc(t('m.intro'))}</p>`;
  const skillName = new Map(skills.map((s) => [s.id, lang === 'es' ? s.es : s.en]));
  for (const f of topFamilies) {
    const idx: number[] = [];
    for (let i = 0; i < jobs.n; i++) if (jobs.rf[i] === f) idx.push(i);
    const openIdx = idx.filter((i) => open[i]);
    const sec = document.createElement('section');
    sec.className = 'family';
    const name = meta.labels.rf[f]?.[L] ?? f;
    const pct = idx.length ? Math.round((100 * openIdx.length) / idx.length) : 0;
    sec.innerHTML = `<div class="family-head"><h2>${esc(name)}</h2><span class="stat">${t('m.open', {
      open: fmtNum(openIdx.length), total: fmtNum(idx.length), country: esc(countryLabel), pct })}</span></div>`;
    const grid = document.createElement('div');
    grid.className = 'grid';
    grid.appendChild(shareFig(openIdx.length, idx.length));
    if (!openIdx.length) {
      grid.insertAdjacentHTML('beforeend', `<p class="note">${esc(t('m.none'))}</p>`);
    } else {
      const pays = openIdx.map((i) => jobs.pay[i]).filter((p): p is number[] => Array.isArray(p)).map((p) => (p[0] + p[1]) / 2);
      grid.appendChild(payFig(pays));
      grid.appendChild(weeksFig(openIdx.map((i) => jobs.posted[i]).filter(Boolean), meta.date));
      const orgs = new Map<string, number>();
      for (const i of openIdx) if (jobs.org[i]) orgs.set(jobs.org[i], (orgs.get(jobs.org[i]) ?? 0) + 1);
      const top = [...orgs].sort((a, b) => b[1] - a[1]).slice(0, 6);
      grid.appendChild(rowsFig(t('m.employers'), top.map(([o, n]) => [o, n, fmtNum(n)]), '', { bars: (top[0]?.[1] ?? 0) >= 5 }));
      const sk = new Map<string, number>();
      for (const i of openIdx) for (const s of jobs.sk[i] ? jobs.sk[i].split(',') : []) sk.set(s, (sk.get(s) ?? 0) + 1);
      const missing = [...sk].filter(([s, n]) => !cvSkillIds.has(s) && n / openIdx.length >= 0.05)
        .sort((a, b) => b[1] - a[1]).slice(0, 6);
      if (missing.length) {
        grid.appendChild(rowsFig(t('m.skills'), missing.map(([s, n]) =>
          [skillName.get(s) ?? s, (100 * n) / openIdx.length, `${Math.round((100 * n) / openIdx.length)}%`]),
          t('m.skillsNote'), { scale: 100, neutral: true }));
      } else {
        grid.appendChild(rowsFig(t('m.skills'), [], t('m.skillsNone')));
      }
    }
    sec.appendChild(grid);
    root.appendChild(sec);
  }
  void country;
}
