import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const recorder = await readFile(
  new URL('../src/lib/components/messaging/VoiceRecorder.svelte', import.meta.url),
  'utf8'
);
const bridge = await readFile(new URL('../src/lib/nativeVoiceRecorder.ts', import.meta.url), 'utf8');
const composer = await readFile(
  new URL('../src/lib/components/messaging/MessageComposer.svelte', import.meta.url),
  'utf8'
);

test('Capacitor Android selects the native recorder before the browser fallback', () => {
  assert.match(recorder, /const runtime = nativeVoiceRuntimeStatus\(\);\s*if \(runtime\.platform === 'android'\)/);
  assert.match(recorder, /if \(!runtime\.nativePlatform \|\| !runtime\.pluginAvailable\)/);
  assert.match(recorder, /await startNativeRecording\(mode, generation, runtime\);\s*return;/);
  assert.match(recorder, /NativeVoiceRecorder\.start\(\)/);
  assert.match(recorder, /NativeVoiceRecorder\.stop\(\)/);
  assert.match(recorder, /NativeVoiceRecorder\.pause\(\)/);
  assert.match(recorder, /NativeVoiceRecorder\.resume\(\)/);
  assert.ok(recorder.indexOf("if (runtime.platform === 'android')") < recorder.indexOf('await startWebRecording(mode, generation)'));
  assert.ok(recorder.indexOf('await startWebRecording(mode, generation)') < recorder.indexOf('getUserMedia({ audio: true })'));
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
  assert.match(recorder, /submitVoice\(\{ blob, duration_ms: duration, mime_type: result\.mimeType \}\)/);
  assert.match(recorder, /deleteNativeRecording\(reference\)/);
  assert.match(recorder, /NativeVoiceRecorder\.cancel\(\)/);
});

test('native bridge exposes permission, recording lifecycle, settings and cleanup methods', () => {
  for (const method of ['permissionStatus', 'start', 'pause', 'resume', 'stop', 'cancel', 'openSettings', 'deleteTemporary', 'purgeTemporary']) {
    assert.match(bridge, new RegExp(`\\b${method}\\(`));
  }
  assert.match(bridge, /platform: Capacitor\.getPlatform\(\)/);
  assert.match(bridge, /nativePlatform: Capacitor\.isNativePlatform\(\)/);
  assert.match(bridge, /pluginAvailable: Capacitor\.isPluginAvailable\('NativeVoiceRecorder'\)/);
  assert.match(bridge, /stage: 'recording'/);
  assert.match(bridge, /fileCreated: true/);
});

test('active recorder state owns the full composer width without remounting', () => {
  assert.match(composer, /let voiceActive = \$state\(false\)/);
  assert.match(composer, /onactivechange=\{\(active\) => \{ voiceActive = active; \}\}/);
  assert.match(composer, /class:w-full=\{voiceActive\}/);
  assert.match(composer, /\{#if !voiceActive\}[\s\S]*id="message-body"/);
  assert.equal((composer.match(/var\(--safe-bottom\)/g) || []).length, 1);
  assert.equal((recorder.match(/data-testid="message-voice-record"/g) || []).length, 1);
  assert.ok(recorder.indexOf('data-testid="message-voice-record"') < recorder.indexOf("{#if recorderState === 'idle'"));
  assert.match(recorder, /class:absolute=\{recorderActive\}/);
  assert.match(recorder, /class:pointer-events-none=\{recorderActive\}/);
});

test('tap, hold, slide, back and background transitions are explicit and race guarded', () => {
  assert.match(recorder, /const TAP_LOCK_MS = 320/);
  assert.match(recorder, /const release = performance\.now\(\) - pointerDownAt <= TAP_LOCK_MS \? 'lock' : 'send'/);
  assert.match(recorder, /pendingRelease = 'cancel'/);
  assert.match(recorder, /startGeneration \+= 1/);
  assert.match(recorder, /window\.addEventListener\('pointerup', pointerUp, \{ capture: true \}\)/);
  assert.match(recorder, /\['starting', 'recording', 'locked', 'paused'\]\.includes\(recorderState\)\) cancelCurrent\(\)/);
  assert.match(recorder, /window\.addEventListener\('chh:native-back'/);
});

test('native startup and file-read failures expose safe physical-device stages', () => {
  assert.match(recorder, /NativeVoiceRecorder\.permissionStatus\(\)/);
  assert.match(recorder, /result\.stage !== 'recording'/);
  assert.match(recorder, /result\.fileCreated/);
  assert.match(recorder, /\[native-voice\] recorder failure/);
  assert.match(recorder, /data-testid="voice-diagnostic-code"/);
  assert.doesNotMatch(recorder, /console\.warn\([^\n]*caught/);
});

test('locked and preview states expose complete full-width controls', () => {
  assert.match(recorder, /data-testid="voice-recording-locked"/);
  assert.match(recorder, /pauseRecording/);
  assert.match(recorder, /resumeRecording/);
  assert.match(recorder, /finish\('preview'\)/);
  assert.match(recorder, /type="range"/);
  assert.match(recorder, /togglePreview/);
  assert.match(recorder, /deleteRecording/);
  assert.match(recorder, /rerecord/);
  assert.match(recorder, /sendPreview/);
});
