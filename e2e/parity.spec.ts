/**
 * Embedding parity: the same 20 texts embedded in Node (tools/parity_node.mjs, run first)
 * and in the browser must agree, cosine >= 0.995 for every text.
 */
import { chromium, expect, test } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

const BASE = process.env.OPENFROM_URL || 'https://89jdvm.github.io/openfrom/';

test('Node and browser embeddings agree', async () => {
  const texts: string[] = JSON.parse(fs.readFileSync('e2e/parity_texts.json', 'utf8'));
  const node: number[][] = JSON.parse(fs.readFileSync('.tmp/parity_node.json', 'utf8'));
  const ctx = await chromium.launchPersistentContext(path.resolve('.tmp/pw-profile'));
  const page = await ctx.newPage();
  await page.goto(BASE + '?parity');
  await page.waitForFunction(() => 'openfromEmbed' in window);
  const browser: number[][] = await page.evaluate(
    (t) => (window as unknown as { openfromEmbed: (x: string[]) => Promise<number[][]> }).openfromEmbed(t), texts);
  const cos = browser.map((b, i) => {
    let d = 0, na = 0, nb = 0;
    for (let k = 0; k < b.length; k++) { d += b[k] * node[i][k]; na += b[k] ** 2; nb += node[i][k] ** 2; }
    return d / Math.sqrt(na * nb);
  });
  fs.writeFileSync('.tmp/parity_result.json', JSON.stringify({ min: Math.min(...cos), cos }, null, 1));
  console.log(`parity: min cosine ${Math.min(...cos).toFixed(5)} over ${cos.length} texts`);
  for (const c of cos) expect(c).toBeGreaterThanOrEqual(0.995);
  await ctx.close();
});
