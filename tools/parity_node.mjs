#!/usr/bin/env node
/** Embed the parity texts in Node (same settings as the nightly build) for the browser parity test.
 *  Usage: node --import ./tools/no-sharp.mjs tools/parity_node.mjs  -> .tmp/parity_node.json */
import fs from 'node:fs';
import { embed } from './embed.mjs';

const texts = JSON.parse(fs.readFileSync('e2e/parity_texts.json', 'utf8'));
const vecs = await embed(texts);
fs.mkdirSync('.tmp', { recursive: true });
fs.writeFileSync('.tmp/parity_node.json', JSON.stringify(vecs.map((v) => Array.from(v))));
console.log(`embedded ${vecs.length} parity texts in Node`);
