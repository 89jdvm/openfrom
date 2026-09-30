/** Promise wrapper around the embedding worker. */

type Reply = { id: number; type: string; [k: string]: unknown };

export class Embedder {
  private worker: Worker;
  private seq = 0;
  private waiting = new Map<number, { resolve: (r: Reply) => void; reject: (e: Error) => void; onProgress?: (l: number, t: number) => void }>();

  constructor() {
    this.worker = new Worker(new URL('./embed.worker.ts', import.meta.url), { type: 'module' });
    this.worker.onmessage = (e: MessageEvent<Reply>) => {
      const r = e.data;
      const w = this.waiting.get(r.id);
      if (!w) return;
      if (r.type === 'progress') { w.onProgress?.(r.loaded as number, r.total as number); return; }
      this.waiting.delete(r.id);
      if (r.type === 'error') w.reject(new Error(String(r.message)));
      else w.resolve(r);
    };
  }

  private call(msg: object, transfer: Transferable[] = [], onProgress?: (l: number, t: number) => void): Promise<Reply> {
    const id = ++this.seq;
    return new Promise((resolve, reject) => {
      this.waiting.set(id, { resolve, reject, onProgress });
      this.worker.postMessage({ ...msg, id }, transfer);
    });
  }

  init(onProgress: (loaded: number, total: number) => void): Promise<Reply> {
    return this.call({ type: 'init' }, [], onProgress);
  }

  async embed(texts: string[]): Promise<Float32Array[]> {
    const r = await this.call({ type: 'embed', texts });
    return r.vecs as Float32Array[];
  }

  async setVectors(buf: ArrayBuffer, n: number): Promise<void> {
    await this.call({ type: 'vectors', buf, n });
  }

  async score(queries: Float32Array[], whole: Float32Array, prior: Float32Array): Promise<{ best: Float32Array; which: Uint8Array }> {
    const r = await this.call({ type: 'score', queries, whole, prior });
    return { best: r.best as Float32Array, which: r.which as Uint8Array };
  }
}
