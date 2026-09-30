// Node loader hook: replace the "sharp" image library with an empty stub.
// Text embedding never touches images, and some Windows machines block sharp's
// native file. Use: node --import ./tools/no-sharp.mjs tools/embed.mjs ...
import { register } from 'node:module';

register('data:text/javascript,' + encodeURIComponent(`
export async function resolve(spec, ctx, next) {
  if (spec === 'sharp') return { url: 'data:text/javascript,export default function sharp(){throw new Error("sharp stubbed")}', shortCircuit: true };
  return next(spec, ctx);
}`));
