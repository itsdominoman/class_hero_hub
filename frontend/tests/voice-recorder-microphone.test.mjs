import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const source = await readFile(
  new URL('../src/lib/components/messaging/VoiceRecorder.svelte', import.meta.url),
  'utf8'
);

test('voice capture starts directly with an unconstrained audio request', () => {
  assert.match(source, /getUserMedia\(\{\s*audio:\s*true\s*\}\)/);
  assert.doesNotMatch(source, /enumerateDevices\s*\(/);
  assert.doesNotMatch(source, /deviceId\s*:/);
});

test('voice capture logs only safe capability, exception-name and track-count diagnostics', () => {
  assert.match(source, /mediaDevicesAvailable/);
  assert.match(source, /getUserMediaAvailable/);
  assert.match(source, /microphoneExceptionName\(caught\)/);
  assert.match(source, /\{\s*name:\s*exceptionName\s*\}/);
  assert.match(source, /captured\.getAudioTracks\(\)\.length/);
  assert.doesNotMatch(source, /console\.(?:info|warn)\([^\n]*(?:blob|chunks|recording)/i);
});
