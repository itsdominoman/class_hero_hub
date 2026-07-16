import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

import {
  ProtectedUpdatePhotoCache,
  protectedUpdatePhotoKey,
  protectedUpdatePhotoPath
} from '../src/lib/protected-update-photo.ts';

test('authenticated photo download supplies school context without putting it in the URL', async () => {
  const calls = [];
  const cache = new ProtectedUpdatePhotoCache({
    createObjectURL: () => 'blob:protected-photo',
    revokeObjectURL: () => {}
  });

  const path = protectedUpdatePhotoPath(41, 9, 'thumbnail');
  const url = await cache.load(protectedUpdatePhotoKey(41, 9, 'thumbnail'), path, 7, async (requestPath, options) => {
    calls.push({ path: requestPath, options });
    return new Blob(['image'], { type: 'image/jpeg' });
  });

  assert.equal(url, 'blob:protected-photo');
  assert.equal(calls.length, 1);
  assert.equal(calls[0].path, '/api/teach/updates/41/photos/9/thumbnail');
  assert.equal(new Headers(calls[0].options.headers).get('X-School-Id'), '7');
  assert.equal(calls[0].path.includes('?'), false);
  assert.equal(calls[0].path.includes('token'), false);
});

test('thumbnail and full viewer use distinct protected paths and cache keys', async () => {
  let downloads = 0;
  const cache = new ProtectedUpdatePhotoCache({
    createObjectURL: (blob) => `blob:${blob.type}:${blob.size}`,
    revokeObjectURL: () => {}
  });
  const download = async (path) => {
    downloads += 1;
    return new Blob([path.includes('thumbnail') ? 'thumb' : 'full-image'], { type: 'image/webp' });
  };

  const thumbnailKey = protectedUpdatePhotoKey(8, 3, 'thumbnail');
  const fullKey = protectedUpdatePhotoKey(8, 3, 'full');
  const thumbnailPath = protectedUpdatePhotoPath(8, 3, 'thumbnail');
  const fullPath = protectedUpdatePhotoPath(8, 3, 'full');
  const [thumbnailUrl, viewerUrl] = await Promise.all([
    cache.load(thumbnailKey, thumbnailPath, 2, download),
    cache.load(fullKey, fullPath, 2, download)
  ]);
  const reopenedViewerUrl = await cache.load(fullKey, fullPath, 2, download);

  assert.notEqual(viewerUrl, thumbnailUrl);
  assert.equal(reopenedViewerUrl, viewerUrl);
  assert.equal(downloads, 2);
});

test('cleanup revokes loaded object URLs', async () => {
  const revoked = [];
  let nextUrl = 0;
  const cache = new ProtectedUpdatePhotoCache({
    createObjectURL: () => `blob:photo-${++nextUrl}`,
    revokeObjectURL: (url) => revoked.push(url)
  });
  const download = async () => new Blob(['image'], { type: 'image/png' });

  await cache.load('one', protectedUpdatePhotoPath(1, 1, 'thumbnail'), 4, download);
  await cache.load('two', protectedUpdatePhotoPath(1, 2, 'full'), 4, download);
  cache.clear();

  assert.deepEqual(revoked.sort(), ['blob:photo-1', 'blob:photo-2']);
  assert.equal(cache.get('one'), undefined);
  assert.equal(cache.get('two'), undefined);
});

test('cleanup prevents an in-flight download from creating a leaked object URL', async () => {
  let resolveDownload;
  let created = 0;
  const cache = new ProtectedUpdatePhotoCache({
    createObjectURL: () => {
      created += 1;
      return 'blob:late-photo';
    },
    revokeObjectURL: () => {}
  });
  const pendingBlob = new Promise((resolve) => {
    resolveDownload = resolve;
  });

  const load = cache.load('late', protectedUpdatePhotoPath(3, 1, 'thumbnail'), 6, () => pendingBlob);
  cache.clear();
  resolveDownload(new Blob(['image'], { type: 'image/jpeg' }));

  await assert.rejects(load, /cleared/);
  assert.equal(created, 0);
  assert.equal(cache.get('late'), undefined);
});

test('one failed photo does not prevent another photo from loading', async () => {
  const cache = new ProtectedUpdatePhotoCache({
    createObjectURL: () => 'blob:healthy-photo',
    revokeObjectURL: () => {}
  });

  await assert.rejects(
    cache.load('failed', protectedUpdatePhotoPath(2, 1, 'thumbnail'), 5, async () => {
      throw new Error('missing photo');
    }),
    /missing photo/
  );

  const loaded = await cache.load(
    'healthy',
    protectedUpdatePhotoPath(2, 2, 'thumbnail'),
    5,
    async () => new Blob(['image'], { type: 'image/jpeg' })
  );

  assert.equal(cache.get('failed'), undefined);
  assert.equal(loaded, 'blob:healthy-photo');
});

test('component uses authenticated blobs for browser and native without raw media URLs', () => {
  const pageSource = readFileSync(
    new URL('../src/routes/teach/assignments/[id]/+page.svelte', import.meta.url),
    'utf8'
  );
  const apiSource = readFileSync(new URL('../src/lib/api.ts', import.meta.url), 'utf8');

  assert.match(pageSource, /protectedPhotoCache\.load\(/);
  assert.match(pageSource, /api\.download/);
  assert.match(pageSource, /updatePhotoObjectUrls\[updatePhotoLightbox\.key\]/);
  assert.match(pageSource, /loadProtectedUpdatePhoto\(post, photo, 'full'\)/);
  assert.match(pageSource, /loadProtectedUpdatePhoto\(loadedUpdate, photo, 'thumbnail'\)/);
  assert.match(pageSource, /protectedPhotoCache\.clear\(\)/);
  assert.doesNotMatch(pageSource, /src=\{updatePhotoPath/);
  assert.doesNotMatch(pageSource, /updatePhotoLightbox\s*=\s*\{[^}]*url:/);
  assert.doesNotMatch(pageSource, /photos\/\$\{photo\.id\}\/view\?school_id/);

  const parentPageSource = readFileSync(
    new URL('../src/routes/parent/+page.svelte', import.meta.url),
    'utf8'
  );
  assert.match(parentPageSource, /photos\/\$\{photo\.id\}\/thumbnail/);
  assert.match(parentPageSource, /photos\/\$\{photo\.id\}\/view/);

  assert.match(apiSource, /const token = await getNativeAccessToken\(\)/);
  assert.match(apiSource, /headers\.set\('Authorization', `Bearer \$\{token\}`\)/);
  assert.match(apiSource, /credentials: isNativePlatform\(\) \? 'omit' : 'include'/);
});
