/**
 * End-to-end checks against the live site, in one persistent browser profile so the
 * 118 MB model downloads once. For each synthetic CV: matches appear, every shown job is
 * open to the CV's country, the market map renders, English and Spanish both render, and
 * with bring-your-own-key off the only requests are GETs to allowed hosts with no CV text.
 * Screenshots at 390 px and 1280 px, light and dark, go to .tmp/shots/ for review.
 */
import { chromium, expect, test, type BrowserContext, type Page, type Request } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

const BASE = process.env.OPENFROM_URL || 'https://89jdvm.github.io/openfrom/';
const SHOTS = path.resolve('.tmp/shots');
const ALLOWED = [new URL(BASE).hostname, 'huggingface.co', '.huggingface.co', '.hf.co'];

const CVS = [
  { file: 'cv_kenya_climate.txt', country: 'KE', name: 'kenya' },
  { file: 'cv_colombia_mye.txt', country: 'CO', name: 'colombia' },
  { file: 'cv_germany_data.txt', country: 'DE', name: 'germany' },
];

let ctx: BrowserContext;
test.describe.configure({ mode: 'serial' });

test.beforeAll(async () => {
  fs.mkdirSync(SHOTS, { recursive: true });
  ctx = await chromium.launchPersistentContext(path.resolve('.tmp/pw-profile'), { viewport: { width: 1280, height: 900 } });
});
test.afterAll(async () => { await ctx?.close(); });

function hostAllowed(u: string): boolean {
  const h = new URL(u).hostname;
  return ALLOWED.some((a) => (a.startsWith('.') ? h.endsWith(a) : h === a));
}

async function match(page: Page, cv: string, country: string): Promise<void> {
  await page.goto(BASE);
  await expect(page.locator('#stats')).toContainText(/\d/);
  await page.locator('#cv-text').fill(cv);
  await expect(page.locator('#country')).toHaveValue(country, { timeout: 10_000 });
  await page.locator('input[name="mode"][value="model"]').check();
  await page.locator('#go').click();
  await expect(page.locator('.jobs .job').first()).toBeVisible({ timeout: 14 * 60 * 1000 });
}

for (const c of CVS) {
  test(`matches for ${c.name}`, async () => {
    const cv = fs.readFileSync(path.join('e2e', 'fixtures', c.file), 'utf8');
    const page = await ctx.newPage();
    const requests: Request[] = [];
    page.on('request', (r) => requests.push(r));
    await match(page, cv, c.country);

    const n = await page.locator('.jobs .job').count();
    expect(n).toBeGreaterThan(0);
    expect(await page.locator('.jobs .job .who.open').count()).toBe(n);   // every shown job is open to them
    expect(await page.locator('.jobs .job.closed').count()).toBe(0);

    await page.locator('#tab-market').click();
    await expect(page.locator('#panel-market .family').first()).toBeVisible();
    expect(await page.locator('#panel-market .family svg').count()).toBeGreaterThan(0);
    await page.locator('#tab-matches').click();

    // Privacy: only GETs to allowed hosts, and no request carries CV text.
    const needle = cv.split('\n').find((l) => l.length > 40)!.slice(0, 30);
    for (const r of requests) {
      expect(r.method(), r.url()).toBe('GET');
      expect(hostAllowed(r.url()), r.url()).toBe(true);
      expect(r.url().includes(encodeURIComponent(needle.slice(0, 12)))).toBe(false);
      expect(r.postData() ?? '').not.toContain(needle);
    }

    // Spanish renders.
    await page.locator('#lang').click();
    await expect(page.locator('h1')).toHaveText(/Empleos remotos/);
    await expect(page.locator('.summary')).toContainText(/empleos remotos/);
    await page.locator('#lang').click();
    await expect(page.locator('h1')).toHaveText(/Remote jobs/);

    if (c.name === 'kenya') {
      for (const theme of ['light', 'dark'] as const) {
        await page.evaluate((t) => { document.documentElement.dataset.theme = t; }, theme);
        for (const w of [1280, 390]) {
          await page.setViewportSize({ width: w, height: w === 390 ? 844 : 900 });
          await page.evaluate(() => window.scrollTo(0, 0));
          await page.screenshot({ path: path.join(SHOTS, `matches-${theme}-${w}.png`), fullPage: false });
          await page.locator('#panel-matches').scrollIntoViewIfNeeded();
          await page.screenshot({ path: path.join(SHOTS, `results-${theme}-${w}.png`), fullPage: false });
          await page.locator('#tab-market').click();
          await page.screenshot({ path: path.join(SHOTS, `market-${theme}-${w}.png`), fullPage: true });
          await page.locator('#tab-about').click();
          await page.screenshot({ path: path.join(SHOTS, `about-${theme}-${w}.png`), fullPage: true });
          await page.locator('#tab-matches').click();
        }
      }
      await page.evaluate(() => { delete document.documentElement.dataset.theme; });
      await page.setViewportSize({ width: 1280, height: 900 });
    }
    if (c.name === 'colombia') {
      await page.locator('#lang').click();
      await page.setViewportSize({ width: 390, height: 844 });
      await page.screenshot({ path: path.join(SHOTS, `results-es-390.png`), fullPage: false });
      await page.locator('#lang').click();
    }
    await page.close();
  });
}

test('first screen before any CV', async () => {
  const page = await ctx.newPage();
  for (const theme of ['light', 'dark'] as const) {
    for (const w of [1280, 390, 320]) {
      await page.setViewportSize({ width: w, height: w === 1280 ? 900 : 760 });
      await page.goto(BASE);
      await page.evaluate((t) => { document.documentElement.dataset.theme = t; }, theme);
      await expect(page.locator('#stats')).toContainText(/\d/);
      const scrollW = await page.evaluate(() => document.documentElement.scrollWidth);
      expect(scrollW, `no sideways scroll at ${w}px`).toBeLessThanOrEqual(w);
      await page.screenshot({ path: path.join(SHOTS, `first-${theme}-${w}.png`), fullPage: false });
    }
  }
  await page.close();
});
