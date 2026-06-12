#!/usr/bin/env node
/**
 * Fails (exit 1) if the English and Arabic message trees in
 * src/lib/i18n/messages.ts do not contain exactly the same keys.
 *
 * Run with: npm run check:i18n
 */
import { readFileSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';

const messagesPath = fileURLToPath(new URL('../src/lib/i18n/messages.ts', import.meta.url));
// messages.ts is plain ESM (no TypeScript syntax), so import it via a .mjs copy.
const tmpPath = join(tmpdir(), `fhh-messages-${process.pid}.mjs`);
writeFileSync(tmpPath, readFileSync(messagesPath));

let en, ar;
try {
  ({ en, ar } = await import(pathToFileURL(tmpPath)));
} finally {
  rmSync(tmpPath, { force: true });
}

function collectKeys(node, prefix = '', out = new Set()) {
  for (const [key, value] of Object.entries(node)) {
    const path = prefix ? `${prefix}.${key}` : key;
    if (value && typeof value === 'object') {
      collectKeys(value, path, out);
    } else {
      out.add(path);
    }
  }
  return out;
}

const enKeys = collectKeys(en);
const arKeys = collectKeys(ar);

const missingInAr = [...enKeys].filter((key) => !arKeys.has(key));
const missingInEn = [...arKeys].filter((key) => !enKeys.has(key));

if (missingInAr.length === 0 && missingInEn.length === 0) {
  console.log(`i18n parity OK: ${enKeys.size} keys in both en and ar.`);
  process.exit(0);
}

if (missingInAr.length > 0) {
  console.error(`Missing in ar (${missingInAr.length}):`);
  for (const key of missingInAr) console.error(`  - ${key}`);
}
if (missingInEn.length > 0) {
  console.error(`Missing in en (${missingInEn.length}):`);
  for (const key of missingInEn) console.error(`  - ${key}`);
}
process.exit(1);
