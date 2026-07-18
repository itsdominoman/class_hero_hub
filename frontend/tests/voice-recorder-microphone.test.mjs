import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const recorder = await readFile(
  new URL('../src/lib/components/messaging/VoiceRecorder.svelte', import.meta.url),
  'utf8'
);
const bridge = await readFile(new URL('../src/lib/nativeVoiceRecorder.ts', import.meta.url), 'utf8');

test('Capacitor Android selects the native recorder before the browser fallback', () => {
  assert.match(recorder, /if \(nativeAndroid\) \{\s*await startNativeRecording\(mode\);\s*return;/);
  assert.match(recorder, /NativeVoiceRecorder\.start\(\)/);
  assert.match(recorder, /NativeVoiceRecorder\.stop\(\)/);
  assert.match(recorder, /NativeVoiceRecorder\.pause\(\)/);
  assert.match(recorder, /NativeVoiceRecorder\.resume\(\)/);
  assert.ok(recorder.indexOf('if (nativeAndroid)') < recorder.indexOf('getUserMedia({ audio: true })'));
});

test('ordinary browsers retain direct MediaRecorder capture without device preflight', () => {
  assert.match(recorder, /async function startWebRecording/);
  assert.match(recorder, /getUserMedia\(\{\s*audio:\s*true\s*\}\)/);
  assert.doesNotMatch(recorder, /enumerateDevices\s*\(/);
  assert.doesNotMatch(recorder, /deviceId\s*:/);
});

test('native cache files are read into the existing Blob contract and explicitly deleted', () => {
  assert.match(bridge, /Capacitor\.convertFileSrc\(recording\.uri\)/);
  assert.match(bridge, /new Blob\(\[bytes\], \{ type: recording\.mimeType \}\)/);
  assert.match(recorder, /onvoice\(\{ blob, duration_ms: duration, mime_type: result\.mimeType \}\)/);
  assert.match(recorder, /deleteNativeRecording\(reference\)/);
  assert.match(recorder, /NativeVoiceRecorder\.cancel\(\)/);
});

test('native bridge exposes permission, recording lifecycle, settings and cleanup methods', () => {
  for (const method of ['permissionStatus', 'start', 'pause', 'resume', 'stop', 'cancel', 'openSettings', 'deleteTemporary', 'purgeTemporary']) {
    assert.match(bridge, new RegExp(`\\b${method}\\(`));
  }
  assert.match(bridge, /Capacitor\.getPlatform\(\) === 'android'/);
});
