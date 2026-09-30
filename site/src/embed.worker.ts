/// <reference lib="webworker" />
/**
 * Runs the embedding model in the browser and scores jobs against CV passages.
 * Same model, revision, dtype, pooling and normalisation as tools/embed.mjs.
 */
import { env, pipeline, type FeatureExtractionPipeline } from '@huggingface/transformers';

const MODEL = 'Xenova/multilingual-e5-small';
const REVISION = '761b726dd34fb83930e26aab4e9ac3899aa1fa78';
const DIM = 384;

env.allowLocalModels = false;
env.useBrowserCache = true;
(env as unknown as { useWasmCache: boolean }).useWasmCache = false; // load the runtime from our own origin, never a blob
const ortBase = new URL('../ort/', self.location.href).href; // worker lives in assets/ (build) or src/ (dev)
const onnx = env.backends.onnx as { wasm?: { wasmPaths?: unknown; numThreads?: number } };
if (onnx.wasm) {
  onnx.wasm.wasmPaths = { mjs: ortBase + 'ort-wasm-simd-threaded.mjs', wasm: ortBase + 'ort-wasm-simd-threaded.wasm' };
  onnx.wasm.numThreads = 1; // GitHub Pages cannot send the headers threads need
}

let extractor: Promise<FeatureExtractionPipeline> | null = null;
let jobs: { q: Int8Array; scale: Float32Array; n: number } | null = null;

type Msg =
  | { id: number; type: 'init' }
  | { id: number; type: 'embed'; texts: string[] }
  | { id: number; type: 'vectors'; buf: ArrayBuffer; n: number }
  | { id: number; type: 'score'; queries: Float32Array[] };

const post = (m: unknown, transfer: Transferable[] = []) => (self as DedicatedWorkerGlobalScope).postMessage(m, transfer);

function init(id: number): Promise<FeatureExtractionPipeline> {
  if (!extractor) {
    const files = new Map<string, { loaded: number; total: number }>();
    extractor = pipeline('feature-extraction', MODEL, {
      dtype: 'q8',
      revision: REVISION,
      progress_callback: (p: { status: string; file?: string; loaded?: number; total?: number }) => {
        if (p.status === 'progress' && p.file) {
          files.set(p.file, { loaded: p.loaded ?? 0, total: p.total ?? 0 });
          let loaded = 0, total = 0;
          for (const f of files.values()) { loaded += f.loaded; total += f.total; }
          post({ id, type: 'progress', loaded, total });
        }
      },
    }) as Promise<FeatureExtractionPipeline>;
    extractor.catch(() => { extractor = null; });
  }
  return extractor;
}

async function embed(texts: string[]): Promise<Float32Array[]> {
  const ex = await init(-1);
  const out: Float32Array[] = [];
  for (let i = 0; i < texts.length; i += 8) {
    const batch = texts.slice(i, i + 8);
    const t = await ex(batch, { pooling: 'mean', normalize: true });
    const data = t.data as Float32Array;
    for (let j = 0; j < batch.length; j++) out.push(data.slice(j * DIM, (j + 1) * DIM));
  }
  return out;
}

/** For each job: best cosine over the CV passages, and which passage it was. */
function score(queries: Float32Array[]): { best: Float32Array; which: Uint8Array } {
  if (!jobs) throw new Error('vectors not loaded');
  const { q, scale, n } = jobs;
  const best = new Float32Array(n).fill(-1);
  const which = new Uint8Array(n);
  for (let k = 0; k < queries.length; k++) {
    const v = queries[k];
    for (let i = 0; i < n; i++) {
      let s = 0;
      const off = i * DIM;
      for (let d = 0; d < DIM; d++) s += q[off + d] * v[d];
      s *= scale[i];
      if (s > best[i]) { best[i] = s; which[i] = k; }
    }
  }
  return { best, which };
}

self.onmessage = async (e: MessageEvent<Msg>) => {
  const m = e.data;
  try {
    if (m.type === 'init') {
      await init(m.id);
      post({ id: m.id, type: 'ready' });
    } else if (m.type === 'embed') {
      const vecs = await embed(m.texts);
      post({ id: m.id, type: 'embedded', vecs });
    } else if (m.type === 'vectors') {
      jobs = { q: new Int8Array(m.buf, 0, m.n * DIM), scale: new Float32Array(m.buf.slice(m.n * DIM, m.n * DIM + m.n * 4)), n: m.n };
      post({ id: m.id, type: 'ok' });
    } else if (m.type === 'score') {
      const r = score(m.queries);
      post({ id: m.id, type: 'scored', ...r }, [r.best.buffer, r.which.buffer]);
    }
  } catch (err) {
    post({ id: m.id, type: 'error', message: String((err as Error)?.message ?? err) });
  }
};
