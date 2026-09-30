/** Read a CV file in the browser, strip contact details, and split it into passages. */

export class CvError extends Error {
  constructor(public code: 'pdf' | 'file') { super(code); }
}

export async function readFile(file: File): Promise<string> {
  const name = file.name.toLowerCase();
  const buf = await file.arrayBuffer();
  if (name.endsWith('.pdf') || file.type === 'application/pdf') return readPdf(buf);
  if (name.endsWith('.docx')) return readDocx(buf);
  if (name.endsWith('.txt') || file.type.startsWith('text/')) return new TextDecoder().decode(buf);
  throw new CvError('file');
}

async function readPdf(buf: ArrayBuffer): Promise<string> {
  const pdfjs = await import('pdfjs-dist');
  const workerUrl = (await import('pdfjs-dist/build/pdf.worker.min.mjs?url')).default;
  pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;
  let doc;
  try {
    // pdf.js 5 never uses eval; the flag is kept for older builds that read it.
    const opts = { data: new Uint8Array(buf), isEvalSupported: false } as Parameters<typeof pdfjs.getDocument>[0];
    doc = await pdfjs.getDocument(opts).promise;
  } catch {
    throw new CvError('file');
  }
  const pages: string[] = [];
  for (let i = 1; i <= Math.min(doc.numPages, 12); i++) {
    const page = await doc.getPage(i);
    const content = await page.getTextContent();
    let line = '';
    let lastY: number | null = null;
    const lines: string[] = [];
    for (const item of content.items as { str: string; transform: number[]; hasEOL?: boolean }[]) {
      const y = item.transform?.[5] ?? 0;
      if (lastY !== null && Math.abs(y - lastY) > 2) { lines.push(line); line = ''; }
      line += (line && !line.endsWith(' ') ? ' ' : '') + item.str;
      lastY = y;
      if (item.hasEOL) { lines.push(line); line = ''; lastY = null; }
    }
    lines.push(line);
    pages.push(lines.map((l) => l.trim()).filter(Boolean).join('\n'));
  }
  const text = pages.join('\n\n');
  if (text.replace(/\s/g, '').length < 80) throw new CvError('pdf');
  return text;
}

async function readDocx(buf: ArrayBuffer): Promise<string> {
  try {
    const mammoth = await import('mammoth/mammoth.browser');
    const r = await (mammoth.default ?? mammoth).extractRawText({ arrayBuffer: buf });
    return r.value;
  } catch {
    throw new CvError('file');
  }
}

const EMAIL = /[\w.+-]+@[\w-]+(\.[\w-]+)+/g;
const URL_RX = /\b(https?:\/\/|www\.)\S+|\b(linkedin|github)\.com\/\S*/gi;
const PHONE = /(\+?\d[\d\s().-]{7,}\d)/g;
const CONTACT_WORDS = /\b(e-?mail|phone|tel[eé]fono|m[oó]vil|mobile|address|direcci[oó]n|linkedin|github|skype|whatsapp|date of birth|fecha de nacimiento|nationality|nacionalidad|marital|estado civil)\b/i;

/** Remove contact details: emails, links, phone numbers, and short header lines that are only contact data. */
export function stripContact(text: string): string {
  const lines = text.replace(/\r/g, '').split('\n');
  const out: string[] = [];
  lines.forEach((raw, i) => {
    let l = raw.replace(EMAIL, ' ').replace(URL_RX, ' ').replace(PHONE, ' ');
    const words = l.trim().split(/\s+/).filter(Boolean);
    if (i < 8 && words.length <= 6 && !/[a-z]{4,}.*[a-z]{4,}.*[a-z]{4,}/i.test(l)) return; // name / address header
    if (CONTACT_WORDS.test(raw) && words.length <= 10) return;
    l = l.replace(/\s{2,}/g, ' ').trim();
    if (l) out.push(l);
  });
  return out.join('\n');
}

/** Passages of roughly 250-600 characters, cut on line breaks, for embedding as queries. */
export function chunks(text: string, max = 600, min = 120): string[] {
  const lines = stripContact(text).split('\n');
  const out: string[] = [];
  let cur = '';
  for (const l of lines) {
    if ((cur + ' ' + l).length > max && cur.length >= min) {
      out.push(cur.trim());
      cur = '';
    }
    cur += (cur ? ' ' : '') + l;
    while (cur.length > max * 1.5) {
      const cut = cur.lastIndexOf(' ', max);
      out.push(cur.slice(0, cut > min ? cut : max).trim());
      cur = cur.slice(cut > min ? cut : max).trim();
    }
  }
  if (cur.trim().length >= 40) out.push(cur.trim());
  return out.slice(0, 40);
}

export const wordCount = (s: string): number => (s.match(/\p{L}{2,}/gu) || []).length;
