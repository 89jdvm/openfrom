#!/usr/bin/env node
/**
 * embed.mjs -- embed texts with the same model, settings and pooling as the browser.
 *
 * Input:  JSONL with {uid, text}; text already carries its "passage: " / "query: " prefix.
 * Output: <out>.bin  rows of [float32 scale][384 x int8], little-endian
 *         <out>.uids one uid per line, in the same order
 *
 * Resumable: rows already in <out>.uids are skipped; a half-written tail is trimmed.
 *
 * Usage: node tools/embed.mjs <in.jsonl> <out-prefix> [--batch 16] [--limit N]
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { pipeline, env } from '@huggingface/transformers';

export const MODEL = 'Xenova/multilingual-e5-small';
export const REVISION = '761b726dd34fb83930e26aab4e9ac3899aa1fa78';
export const DTYPE = 'q8';
export const DIM = 384;
const ROW = 4 + DIM;

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
env.cacheDir = process.env.OPENFROM_MODEL_CACHE || path.join(ROOT, '.tmp', 'models');
env.allowLocalModels = false;

let extractor;
export async function getExtractor() {
  extractor ??= await pipeline('feature-extraction', MODEL, { dtype: DTYPE, revision: REVISION });
  return extractor;
}

/** Mean-pooled, L2-normalised vectors as Float32Array[]. */
export async function embed(texts) {
  const ex = await getExtractor();
  const out = await ex(texts, { pooling: 'mean', normalize: true });
  const data = out.data;
  return texts.map((_, i) => data.slice(i * DIM, (i + 1) * DIM));
}

export function quantize(v) {
  let m = 0;
  for (const x of v) m = Math.max(m, Math.abs(x));
  const scale = m / 127 || 1;
  const buf = Buffer.alloc(ROW);
  buf.writeFloatLE(scale, 0);
  for (let i = 0; i < DIM; i++) buf.writeInt8(Math.round(v[i] / scale), 4 + i);
  return buf;
}

async function main() {
  const args = process.argv.slice(2);
  const [inPath, outPrefix] = args;
  const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? Number(args[i + 1]) : d; };
  const batch = opt('--batch', 16);
  const limit = opt('--limit', Infinity);
  if (!inPath || !outPrefix) {
    console.error('usage: node tools/embed.mjs <in.jsonl> <out-prefix> [--batch 16] [--limit N]');
    process.exit(2);
  }
  const binPath = `${outPrefix}.bin`, uidPath = `${outPrefix}.uids`;
  let done = fs.existsSync(uidPath) ? fs.readFileSync(uidPath, 'utf8').split('\n').filter(Boolean) : [];
  // Trim to whichever file is shorter, so a crash mid-write cannot misalign them.
  const binRows = fs.existsSync(binPath) ? Math.floor(fs.statSync(binPath).size / ROW) : 0;
  const n = Math.min(done.length, binRows);
  done = done.slice(0, n);
  fs.writeFileSync(uidPath, done.length ? done.join('\n') + '\n' : '');
  if (fs.existsSync(binPath)) fs.truncateSync(binPath, n * ROW);
  const seen = new Set(done);

  const todo = [];
  // Split on newlines only: readline also splits on U+2028/U+2029, which JSON strings may contain.
  for (const line of fs.readFileSync(inPath, 'utf8').split('\n')) {
    if (!line.trim()) continue;
    const r = JSON.parse(line);
    if (!seen.has(r.uid)) todo.push(r);
    if (todo.length >= limit) break;
  }
  console.log(`already embedded ${seen.size}, to do ${todo.length}`);
  await getExtractor();
  const t0 = Date.now();
  for (let i = 0; i < todo.length; i += batch) {
    const chunk = todo.slice(i, i + batch);
    const vecs = await embed(chunk.map((r) => r.text));
    fs.appendFileSync(binPath, Buffer.concat(vecs.map(quantize)));
    fs.appendFileSync(uidPath, chunk.map((r) => r.uid).join('\n') + '\n');
    if ((i / batch) % 25 === 0) {
      const rate = (i + chunk.length) / ((Date.now() - t0) / 1000);
      console.log(`${i + chunk.length}/${todo.length}  ${rate.toFixed(1)}/s`);
    }
  }
  console.log(`done: ${todo.length} new rows in ${((Date.now() - t0) / 1000).toFixed(0)}s`);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch((e) => { console.error(e); process.exit(1); });
}
