// Copy the ONNX runtime's WebAssembly files next to the site, so the page never
// loads code from a CDN (the CSP allows scripts from 'self' only).
import fs from 'node:fs';
import path from 'node:path';

const src = path.resolve('node_modules/onnxruntime-web/dist');
const dst = path.resolve('site/public/ort');
fs.mkdirSync(dst, { recursive: true });
for (const f of ['ort-wasm-simd-threaded.mjs', 'ort-wasm-simd-threaded.wasm']) {
  fs.copyFileSync(path.join(src, f), path.join(dst, f));
}
console.log('copied onnxruntime wasm files to site/public/ort');
