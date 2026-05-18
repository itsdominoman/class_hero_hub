#!/usr/bin/env node

import { readdirSync, statSync } from 'node:fs';
import { join, relative, sep } from 'node:path';

const repoRoot = process.cwd();
const routesRoot = join(repoRoot, 'frontend', 'src', 'routes');

function isPageFile(name) {
  return name === '+page.svelte' || name === '+page.ts' || name === '+page.js' || name === '+page.server.ts' || name === '+page.server.js';
}

function isRouteGroup(segment) {
  return segment.startsWith('(') && segment.endsWith(')');
}

function toRoutePath(filePath) {
  const relativePath = relative(routesRoot, filePath);
  const parts = relativePath.split(sep);
  const routeParts = parts.slice(0, -1).filter((part) => !isRouteGroup(part));

  if (routeParts.length === 0) {
    return '/';
  }

  return `/${routeParts.join('/')}`;
}

function walk(dir, files = []) {
  for (const entry of readdirSync(dir)) {
    const fullPath = join(dir, entry);
    const entryStat = statSync(fullPath);
    if (entryStat.isDirectory()) {
      walk(fullPath, files);
      continue;
    }

    if (isPageFile(entry)) {
      files.push(fullPath);
    }
  }

  return files;
}

function formatRoute(routePath) {
  const segments = routePath.split('/').filter(Boolean);
  const dynamic = segments.some((segment) => /^\[.+\]$/.test(segment));
  return {
    route: routePath,
    dynamic: dynamic ? 'yes' : 'no'
  };
}

if (!readdirSync(routesRoot, { withFileTypes: true }).length) {
  console.error(`No routes found under ${routesRoot}`);
  process.exit(1);
}

const discovered = walk(routesRoot)
  .map((filePath) => ({
    ...formatRoute(toRoutePath(filePath)),
    file: relative(repoRoot, filePath)
  }))
  .sort((left, right) => left.route.localeCompare(right.route));

console.log('Discovered SvelteKit routes');
console.log('route | dynamic | file');
console.log('--- | --- | ---');
for (const route of discovered) {
  console.log(`${route.route} | ${route.dynamic} | ${route.file}`);
}
