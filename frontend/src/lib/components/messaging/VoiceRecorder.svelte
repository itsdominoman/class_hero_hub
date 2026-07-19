<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { Lock, Mic, Pause, Play, RotateCcw, SendHorizontal, Square, Trash2 } from 'lucide-svelte';
  import {
    deleteNativeRecording,
    nativeRecordingBlob,
    nativeVoiceRuntimeStatus,
    NativeVoiceRecorder,
    type NativeVoiceRecording,
    type NativeVoiceRuntimeStatus
  } from '$lib/nativeVoiceRecorder';

  let {
    disabled = false,
    sending = false,
    onvoice,
    onactivechange = () => undefined
  }: {
    disabled?: boolean;
    sending?: boolean;
    onvoice: (recording: { blob: Blob; duration_ms: number; mime_type: string }) => Promise<boolean>;
    onactivechange?: (active: boolean) => void;
  } = $props();

  type State = 'idle' | 'starting' | 'recording' | 'locked' | 'paused' | 'preview' | 'error';
  type PendingRelease = 'lock' | 'send' | 'cancel' | null;
  const TAP_LOCK_MS = 320;
  const MIN_RECORDING_MS = 600;
  let recorderState: State = $state('idle');
  let elapsedMs = $state(0);
  let levels: number[] = $state(Array(12).fill(8));
  let error = $state('');
  let mediaRecorder: MediaRecorder | null = null;
  let stream: MediaStream | null = null;
  let audioContext: AudioContext | null = null;
  let analyser: AnalyserNode | null = null;
  let animationFrame = 0;
  let timer: ReturnType<typeof setInterval> | null = null;
  let startedAt = 0;
  let pausedAt = 0;
  let pausedTotal = 0;
  let chunks: Blob[] = [];
  let stopMode: 'send' | 'preview' | 'cancel' = 'cancel';
  let pointerHeld = false;
  let pointerId: number | null = null;
  let pointerDownAt = 0;
  let pendingRelease: PendingRelease = null;
  let startX = 0;
  let startY = 0;
  let locked = false;
  let previewBlob: Blob | null = null;
  let previewUrl = $state('');
  let previewDuration = $state(0);
  let destroyed = false;
  let nativeRecording = false;
  let nativeFinishing = false;
  let previewNativeReference: string | null = null;
  let startGeneration = 0;
  let voiceSubmitting = $state(false);
  let previewAudio = $state<HTMLAudioElement | null>(null);
  let previewPlaying = $state(false);
  let previewPositionMs = $state(0);
  let diagnosticCode = $state('');

  const formatted = $derived(`${Math.floor(elapsedMs / 60000)}:${String(Math.floor(elapsedMs / 1000) % 60).padStart(2, '0')}`);
  const previewPositionFormatted = $derived(formatDuration(previewPositionMs));
  const previewDurationFormatted = $derived(formatDuration(previewDuration));
  const recorderActive = $derived(recorderState !== 'idle' && recorderState !== 'error');

  $effect(() => {
    onactivechange(recorderActive);
  });

  function formatDuration(value: number) {
    return `${Math.floor(value / 60000)}:${String(Math.floor(value / 1000) % 60).padStart(2, '0')}`;
  }

  function haptic(pattern: number | number[]) {
    try { navigator.vibrate?.(pattern); } catch { /* Unsupported haptics are harmless. */ }
  }

  function recordingMimeType() {
    for (const value of ['audio/mp4', 'audio/webm;codecs=opus', 'audio/webm']) {
      if (MediaRecorder.isTypeSupported?.(value)) return value;
    }
    return '';
  }

  function microphoneExceptionName(caught: unknown): string {
    if (caught instanceof DOMException) return caught.name || 'DOMException';
    if (caught instanceof Error && caught.message === 'unsupported') return 'unsupported';
    if (caught instanceof Error) return caught.name || 'Error';
    return 'unknown';
  }

  function nativeErrorCode(caught: unknown): string {
    const code = (caught as { code?: unknown })?.code;
    if (typeof code === 'string' && /^[a-z0-9_-]{1,64}$/.test(code)) return code;
    const message = caught instanceof Error ? caught.message : '';
    if (message === 'native_recording_unreadable' || message === 'native_recording_invalid_size') return message;
    return 'unknown';
  }

  function reportNativeFailure(
    phase: 'runtime' | 'start' | 'stop' | 'read',
    runtime: NativeVoiceRuntimeStatus,
    permissionState: string,
    caught: unknown
  ) {
    const code = nativeErrorCode(caught);
    diagnosticCode = [
      'native',
      runtime.platform,
      runtime.nativePlatform ? 'platform-ready' : 'platform-missing',
      runtime.pluginAvailable ? 'plugin-ready' : 'plugin-missing',
      `permission-${permissionState}`,
      phase,
      code
    ].join('/');
    console.warn('[native-voice] recorder failure', {
      phase,
      platform: runtime.platform,
      nativePlatform: runtime.nativePlatform,
      pluginAvailable: runtime.pluginAvailable,
      permissionState,
      code
    });
  }

  function releaseStream() {
    if (animationFrame) cancelAnimationFrame(animationFrame);
    animationFrame = 0;
    analyser = null;
    if (audioContext) void audioContext.close().catch(() => undefined);
    audioContext = null;
    stream?.getTracks().forEach((track) => track.stop());
    stream = null;
    if (timer) clearInterval(timer);
    timer = null;
  }

  function clearPreview() {
    previewAudio?.pause();
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    const nativeReference = previewNativeReference;
    previewUrl = '';
    previewBlob = null;
    previewDuration = 0;
    previewPlaying = false;
    previewPositionMs = 0;
    previewNativeReference = null;
    if (nativeReference) void deleteNativeRecording(nativeReference).catch(() => undefined);
  }

  function reset() {
    releaseStream();
    mediaRecorder = null;
    nativeRecording = false;
    nativeFinishing = false;
    voiceSubmitting = false;
    chunks = [];
    locked = false;
    pointerHeld = false;
    pointerId = null;
    pointerDownAt = 0;
    pendingRelease = null;
    elapsedMs = 0;
    levels = Array(12).fill(8);
    if (!destroyed) recorderState = 'idle';
  }

  function updateElapsed() {
    if (!startedAt) return;
    const now = performance.now();
    elapsedMs = Math.min(180_000, Math.round(now - startedAt - pausedTotal - (pausedAt ? now - pausedAt : 0)));
    if (elapsedMs >= 180_000 && (nativeRecording || mediaRecorder?.state !== 'inactive')) void finish('preview');
  }

  function visualize() {
    if (!analyser || !stream) return;
    const values = new Uint8Array(analyser.frequencyBinCount);
    analyser.getByteTimeDomainData(values);
    const step = Math.max(1, Math.floor(values.length / 12));
    levels = Array.from({ length: 12 }, (_, index) => {
      let peak = 0;
      for (let offset = index * step; offset < Math.min(values.length, (index + 1) * step); offset += 1) {
        peak = Math.max(peak, Math.abs(values[offset] - 128));
      }
      return Math.max(8, Math.min(34, 8 + peak * 0.75));
    });
    animationFrame = requestAnimationFrame(visualize);
  }

  function visualizeNative() {
    if (!nativeRecording || recorderState === 'paused') return;
    const phase = performance.now() / 180;
    levels = Array.from({ length: 12 }, (_, index) => 10 + Math.round(12 * Math.abs(Math.sin(phase + index * 0.55))));
    animationFrame = requestAnimationFrame(visualizeNative);
  }

  async function startRecording(mode: 'holding' | 'locked') {
    if (disabled || sending || recorderState !== 'idle') return;
    error = '';
    diagnosticCode = '';
    clearPreview();
    const generation = ++startGeneration;
    recorderState = 'starting';
    const runtime = nativeVoiceRuntimeStatus();
    if (runtime.platform === 'android') {
      if (!runtime.nativePlatform || !runtime.pluginAvailable) {
        reportNativeFailure('runtime', runtime, 'unknown', { code: 'native_plugin_unavailable' });
        recorderState = 'error';
        error = $_('messaging.microphoneUnavailable');
        return;
      }
      await startNativeRecording(mode, generation, runtime);
      return;
    }
    await startWebRecording(mode, generation);
  }

  function completeGestureAfterStart(mode: 'holding' | 'locked') {
    const release = pendingRelease;
    pendingRelease = null;
    locked = mode === 'locked' || release === 'lock';
    recorderState = locked ? 'locked' : 'recording';
    if (release === 'cancel') void finish('cancel');
    else if (release === 'send') void finish('send');
  }

  async function submitVoice(recording: { blob: Blob; duration_ms: number; mime_type: string }) {
    if (voiceSubmitting || destroyed) return false;
    voiceSubmitting = true;
    try {
      return await onvoice(recording);
    } finally {
      voiceSubmitting = false;
    }
  }

  async function startNativeRecording(mode: 'holding' | 'locked', generation: number, runtime: NativeVoiceRuntimeStatus) {
    let permissionState = 'unknown';
    try {
      permissionState = (await NativeVoiceRecorder.permissionStatus()).state;
      const result = await NativeVoiceRecorder.start();
      if (!result.started || result.stage !== 'recording' || !result.fileCreated) {
        throw { code: 'invalid_start_result' };
      }
      if (destroyed || generation !== startGeneration) {
        await NativeVoiceRecorder.cancel().catch(() => undefined);
        return;
      }
      nativeRecording = true;
      startedAt = performance.now();
      pausedAt = 0;
      pausedTotal = 0;
      elapsedMs = 0;
      timer = setInterval(updateElapsed, 100);
      visualizeNative();
      completeGestureAfterStart(mode);
      haptic(35);
    } catch (caught) {
      if (destroyed || generation !== startGeneration) return;
      const code = nativeErrorCode(caught);
      reportNativeFailure('start', runtime, permissionState, caught);
      nativeRecording = false;
      recorderState = 'error';
      error = code === 'permission_denied' || code === 'permission_permanently_denied'
        ? $_('messaging.microphonePermissionDenied')
        : $_('messaging.microphoneUnavailable');
    }
  }

  async function startWebRecording(mode: 'holding' | 'locked', generation: number) {
    try {
      const mediaDevices = navigator.mediaDevices;
      const mediaDevicesAvailable = Boolean(mediaDevices);
      const getUserMediaAvailable = typeof mediaDevices?.getUserMedia === 'function';
      console.info('[voice-mic] capture capability', { mediaDevicesAvailable, getUserMediaAvailable });
      if (!mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
        throw new Error('unsupported');
      }
      const captured = await mediaDevices.getUserMedia({ audio: true });
      const audioTrackCount = captured.getAudioTracks().length;
      console.info('[voice-mic] getUserMedia resolved', { audioTrackCount });
      if (!audioTrackCount) {
        captured.getTracks().forEach((track) => track.stop());
        throw new DOMException('Audio capture returned no audio track', 'NotFoundError');
      }
      if (destroyed || generation !== startGeneration) {
        captured.getTracks().forEach((track) => track.stop());
        return;
      }
      stream = captured;
      const mimeType = recordingMimeType();
      mediaRecorder = new MediaRecorder(captured, mimeType ? { mimeType, audioBitsPerSecond: 96_000 } : { audioBitsPerSecond: 96_000 });
      chunks = [];
      mediaRecorder.ondataavailable = (event) => { if (event.data.size) chunks.push(event.data); };
      mediaRecorder.onstop = () => void stopped(mediaRecorder?.mimeType || mimeType || 'application/octet-stream');
      mediaRecorder.onerror = () => {
        error = $_('messaging.voiceRecordingFailed');
        recorderState = 'error';
        releaseStream();
      };
      audioContext = new AudioContext();
      const source = audioContext.createMediaStreamSource(captured);
      analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      startedAt = performance.now();
      pausedAt = 0;
      pausedTotal = 0;
      elapsedMs = 0;
      mediaRecorder.start(250);
      timer = setInterval(updateElapsed, 100);
      visualize();
      completeGestureAfterStart(mode);
      haptic(35);
    } catch (caught) {
      if (destroyed || generation !== startGeneration) return;
      const exceptionName = microphoneExceptionName(caught);
      console.warn('[voice-mic] capture startup failed', { name: exceptionName });
      releaseStream();
      mediaRecorder = null;
      recorderState = 'error';
      error = exceptionName === 'NotAllowedError' || exceptionName === 'SecurityError'
        ? $_('messaging.microphonePermissionDenied')
        : $_('messaging.microphoneUnavailable');
    }
  }

  async function nativeStopped(result: NativeVoiceRecording, mode: 'send' | 'preview') {
    let blob: Blob;
    try {
      blob = await nativeRecordingBlob(result);
    } catch (caught) {
      await deleteNativeRecording(result.fileReference).catch(() => undefined);
      reportNativeFailure('read', nativeVoiceRuntimeStatus(), 'granted', caught);
      recorderState = 'error';
      error = $_('messaging.voiceRecordingFailed');
      reset();
      return;
    }
    const duration = result.durationMs;
    if (destroyed || duration < MIN_RECORDING_MS || !blob.size) {
      await deleteNativeRecording(result.fileReference).catch(() => undefined);
      reset();
      return;
    }
    previewNativeReference = result.fileReference;
    if (mode === 'send') {
      haptic([25, 30, 25]);
      const accepted = await submitVoice({ blob, duration_ms: duration, mime_type: result.mimeType });
      if (destroyed) {
        await deleteNativeRecording(result.fileReference).catch(() => undefined);
        return;
      }
      if (accepted) {
        const reference = previewNativeReference;
        previewNativeReference = null;
        await deleteNativeRecording(reference).catch(() => undefined);
        reset();
      } else {
        previewBlob = blob;
        previewDuration = duration;
        previewUrl = URL.createObjectURL(blob);
        recorderState = 'preview';
      }
      return;
    }
    previewBlob = blob;
    previewDuration = duration;
    previewUrl = URL.createObjectURL(blob);
    recorderState = 'preview';
    haptic(20);
  }

  async function stopped(mimeType: string) {
    updateElapsed();
    const duration = elapsedMs;
    const mode = stopMode;
    const blob = new Blob(chunks, { type: mimeType });
    releaseStream();
    mediaRecorder = null;
    chunks = [];
    if (destroyed || mode === 'cancel' || duration < MIN_RECORDING_MS || !blob.size) {
      reset();
      return;
    }
    if (mode === 'send') {
      haptic([25, 30, 25]);
      const accepted = await submitVoice({ blob, duration_ms: duration, mime_type: mimeType });
      if (destroyed) return;
      if (accepted) reset();
      else {
        previewBlob = blob;
        previewDuration = duration;
        previewUrl = URL.createObjectURL(blob);
        recorderState = 'preview';
      }
      return;
    }
    previewBlob = blob;
    previewDuration = duration;
    previewUrl = URL.createObjectURL(blob);
    recorderState = 'preview';
    haptic(20);
  }

  async function finish(mode: 'send' | 'preview' | 'cancel') {
    if (nativeVoiceRuntimeStatus().platform === 'android') {
      if (!nativeRecording || nativeFinishing) return;
      nativeFinishing = true;
      updateElapsed();
      if (mode === 'cancel' || elapsedMs < MIN_RECORDING_MS) {
        await NativeVoiceRecorder.cancel().catch(() => undefined);
        nativeRecording = false;
        nativeFinishing = false;
        if (mode === 'cancel') haptic([40, 35, 40]);
        reset();
        return;
      }
      try {
        const result = await NativeVoiceRecorder.stop();
        nativeRecording = false;
        nativeFinishing = false;
        releaseStream();
        await nativeStopped(result, mode);
      } catch (caught) {
        if (nativeErrorCode(caught) === 'recording_too_short') {
          nativeRecording = false;
          nativeFinishing = false;
          releaseStream();
          reset();
          return;
        }
        reportNativeFailure('stop', nativeVoiceRuntimeStatus(), 'granted', caught);
        nativeRecording = false;
        nativeFinishing = false;
        releaseStream();
        recorderState = 'error';
        error = $_('messaging.voiceRecordingFailed');
      }
      return;
    }
    if (!mediaRecorder || mediaRecorder.state === 'inactive') return;
    stopMode = mode;
    if (mediaRecorder.state === 'paused') mediaRecorder.resume();
    mediaRecorder.stop();
    if (mode === 'cancel') haptic([40, 35, 40]);
  }

  function pointerDown(event: PointerEvent) {
    if (recorderState === 'error') recorderState = 'idle';
    if (disabled || sending || recorderState !== 'idle') return;
    event.preventDefault();
    pointerHeld = true;
    pointerId = event.pointerId;
    pointerDownAt = performance.now();
    pendingRelease = null;
    startX = event.clientX;
    startY = event.clientY;
    (event.currentTarget as HTMLElement).setPointerCapture?.(event.pointerId);
    void startRecording('holding');
  }

  function pointerMove(event: PointerEvent) {
    if (!pointerHeld || pointerId !== event.pointerId || (recorderState !== 'starting' && recorderState !== 'recording')) return;
    const rtl = getComputedStyle(document.documentElement).direction === 'rtl';
    const cancelDistance = rtl ? event.clientX - startX : startX - event.clientX;
    if (cancelDistance > 72) {
      pointerHeld = false;
      pointerId = null;
      pendingRelease = 'cancel';
      cancelCurrent();
      return;
    }
    if (startY - event.clientY > 72) {
      locked = true;
      pointerHeld = false;
      pointerId = null;
      if (recorderState === 'starting') pendingRelease = 'lock';
      else recorderState = 'locked';
      haptic([25, 20, 25]);
    }
  }

  function pointerUp(event: PointerEvent) {
    if (pointerId !== event.pointerId) return;
    const release = performance.now() - pointerDownAt <= TAP_LOCK_MS ? 'lock' : 'send';
    pointerHeld = false;
    pointerId = null;
    if (recorderState === 'starting') {
      pendingRelease = release;
      return;
    }
    if (recorderState === 'recording' && !locked) {
      if (release === 'lock') {
        locked = true;
        recorderState = 'locked';
        haptic([25, 20, 25]);
      } else {
        void finish('send');
      }
    }
  }

  function pointerCancel(event: PointerEvent) {
    if (pointerId !== event.pointerId) return;
    pointerHeld = false;
    pointerId = null;
    if (!locked) {
      pendingRelease = 'cancel';
      cancelCurrent();
    }
  }

  async function pauseRecording() {
    if (nativeVoiceRuntimeStatus().platform === 'android') {
      if (!nativeRecording || (recorderState !== 'recording' && recorderState !== 'locked')) return;
      try {
        await NativeVoiceRecorder.pause();
        pausedAt = performance.now();
        recorderState = 'paused';
        if (animationFrame) cancelAnimationFrame(animationFrame);
        animationFrame = 0;
        levels = Array(12).fill(8);
        haptic(15);
      } catch {
        error = $_('messaging.voiceRecordingFailed');
      }
      return;
    }
    if (!mediaRecorder || mediaRecorder.state !== 'recording') return;
    mediaRecorder.pause();
    pausedAt = performance.now();
    recorderState = 'paused';
    haptic(15);
  }

  async function resumeRecording() {
    if (nativeVoiceRuntimeStatus().platform === 'android') {
      if (!nativeRecording || recorderState !== 'paused') return;
      try {
        await NativeVoiceRecorder.resume();
        const now = performance.now();
        pausedTotal += pausedAt ? now - pausedAt : 0;
        pausedAt = 0;
        locked = true;
        recorderState = 'locked';
        visualizeNative();
        haptic(15);
      } catch {
        error = $_('messaging.voiceRecordingFailed');
      }
      return;
    }
    if (!mediaRecorder || mediaRecorder.state !== 'paused') return;
    const now = performance.now();
    pausedTotal += pausedAt ? now - pausedAt : 0;
    pausedAt = 0;
    mediaRecorder.resume();
    locked = true;
    recorderState = 'locked';
    haptic(15);
  }

  async function sendPreview() {
    if (!previewBlob || sending || voiceSubmitting) return;
    const accepted = await submitVoice({ blob: previewBlob, duration_ms: previewDuration, mime_type: previewBlob.type });
    if (destroyed) return;
    if (accepted) {
      clearPreview();
      reset();
    }
  }

  async function togglePreview() {
    if (!previewAudio) return;
    if (previewAudio.paused) {
      try {
        await previewAudio.play();
        previewPlaying = true;
      } catch {
        previewPlaying = false;
      }
    } else {
      previewAudio.pause();
      previewPlaying = false;
    }
  }

  function seekPreview(event: Event) {
    if (!previewAudio) return;
    const position = Number((event.currentTarget as HTMLInputElement).value);
    previewAudio.currentTime = position / 1000;
    previewPositionMs = position;
  }

  function rerecord() {
    clearPreview();
    recorderState = 'idle';
    void startRecording('locked');
  }

  function cancelCurrent() {
    clearPreview();
    pointerHeld = false;
    pointerId = null;
    if (recorderState === 'starting') {
      startGeneration += 1;
      pendingRelease = null;
      if (nativeVoiceRuntimeStatus().pluginAvailable) void NativeVoiceRecorder.cancel().catch(() => undefined);
      reset();
    } else if (nativeRecording || (mediaRecorder && mediaRecorder.state !== 'inactive')) void finish('cancel');
    else reset();
  }

  function visibilityChanged() {
    if (document.hidden && ['starting', 'recording', 'locked', 'paused'].includes(recorderState)) cancelCurrent();
  }

  function nativeBack(event: Event) {
    if (recorderState === 'idle' || recorderState === 'error' || event.defaultPrevented) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    cancelCurrent();
  }

  onMount(() => {
    document.addEventListener('visibilitychange', visibilityChanged);
    window.addEventListener('chh:native-back', nativeBack, { capture: true });
    window.addEventListener('pointermove', pointerMove, { capture: true });
    window.addEventListener('pointerup', pointerUp, { capture: true });
    window.addEventListener('pointercancel', pointerCancel, { capture: true });
  });

  onDestroy(() => {
    destroyed = true;
    startGeneration += 1;
    document.removeEventListener('visibilitychange', visibilityChanged);
    window.removeEventListener('chh:native-back', nativeBack, { capture: true });
    window.removeEventListener('pointermove', pointerMove, { capture: true });
    window.removeEventListener('pointerup', pointerUp, { capture: true });
    window.removeEventListener('pointercancel', pointerCancel, { capture: true });
    clearPreview();
    if (nativeRecording || recorderState === 'starting') void NativeVoiceRecorder.cancel().catch(() => undefined);
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      stopMode = 'cancel';
      mediaRecorder.stop();
    }
    releaseStream();
  });
</script>

<div class="relative" class:w-full={recorderActive}>
  <!-- Keep the original pointer-capture target mounted while the composer switches
       to voice mode. Removing it during pointerdown makes Android WebView emit
       pointercancel and races NativeVoiceRecorder.start() against cancel(). -->
  <button
    type="button"
    data-testid="message-voice-record"
    class="grid h-11 w-11 shrink-0 touch-none select-none place-items-center rounded-full bg-hero text-white shadow-sm transition active:scale-95 disabled:cursor-not-allowed disabled:opacity-40"
    class:absolute={recorderActive}
    class:pointer-events-none={recorderActive}
    class:opacity-0={recorderActive}
    disabled={disabled || sending}
    aria-hidden={recorderActive}
    aria-label={$_('messaging.recordVoiceNote')}
    tabindex={recorderActive ? -1 : undefined}
    onpointerdown={pointerDown}
    onpointermove={pointerMove}
    onpointerup={pointerUp}
    onpointercancel={pointerCancel}
  ><Mic size={19} aria-hidden="true" /></button>
  {#if recorderState === 'idle' || recorderState === 'error'}
    {#if error}
      <p class="absolute bottom-14 end-0 w-64 rounded-xl bg-red-50 p-3 text-xs font-bold text-red-800 shadow-lg" role="alert">
        {error}<br />{$_('messaging.microphoneSettingsHelp')}
        {#if diagnosticCode}<span class="mt-1 block break-all font-mono text-[10px]" data-testid="voice-diagnostic-code">{diagnosticCode}</span>{/if}
      </p>
    {/if}
  {:else if recorderState === 'starting' || recorderState === 'recording'}
  <div class="flex w-full min-w-0 items-center gap-3 rounded-2xl bg-red-50 px-3 py-2 text-red-800" data-testid="voice-recording-hold" aria-live="polite">
    <span class="h-2.5 w-2.5 animate-pulse rounded-full bg-red-600"></span>
    <strong class="tabular-nums">{formatted}</strong>
    <span class="min-w-0 flex-1 truncate text-xs font-bold">{$_('messaging.slideCancel')} / {$_('messaging.swipeLock')}</span>
    <Lock size={17} aria-hidden="true" />
  </div>
  {:else if recorderState === 'locked' || recorderState === 'paused'}
  <div class="w-full min-w-0 rounded-2xl border border-red-100 bg-red-50 px-3 py-2" data-testid="voice-recording-locked">
    <div class="flex items-center gap-2">
      <span class="h-2.5 w-2.5 rounded-full bg-red-600" class:animate-pulse={recorderState === 'locked'}></span>
      <strong class="w-12 tabular-nums text-red-800">{formatted}</strong>
      <div class="flex h-9 min-w-0 flex-1 items-center justify-center gap-0.5 overflow-hidden" aria-label={$_('messaging.recordingLevel')}>
        {#each levels as level}<span class="w-1 rounded-full bg-red-400 transition-[height]" style:height={`${recorderState === 'paused' ? 8 : level}px`}></span>{/each}
      </div>
      <button type="button" class="grid h-9 w-9 place-items-center rounded-full bg-white text-slate-700" onclick={recorderState === 'paused' ? resumeRecording : pauseRecording} aria-label={recorderState === 'paused' ? $_('messaging.resumeRecording') : $_('messaging.pauseRecording')}>
        {#if recorderState === 'paused'}<Play size={16} fill="currentColor" />{:else}<Pause size={16} fill="currentColor" />{/if}
      </button>
      <button type="button" class="grid h-9 w-9 place-items-center rounded-full bg-white text-red-700" onclick={cancelCurrent} aria-label={$_('messaging.deleteRecording')}><Trash2 size={16} /></button>
      <button type="button" class="grid h-9 w-9 place-items-center rounded-full bg-slate-900 text-white" onclick={() => void finish('preview')} aria-label={$_('messaging.stopAndPreview')}><Square size={14} fill="currentColor" /></button>
    </div>
  </div>
  {:else if recorderState === 'preview'}
  <div class="w-full min-w-0 rounded-2xl border border-slate-200 bg-white px-3 py-2 shadow-sm" data-testid="voice-recording-preview">
    <audio bind:this={previewAudio} class="hidden" src={previewUrl} preload="metadata" aria-label={$_('messaging.voicePreview')} onplay={() => { previewPlaying = true; }} onpause={() => { previewPlaying = false; }} ontimeupdate={() => { previewPositionMs = Math.round((previewAudio?.currentTime || 0) * 1000); }} onended={() => { previewPlaying = false; previewPositionMs = previewDuration; }}></audio>
    <div class="flex min-w-0 items-center gap-2">
      <button type="button" class="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-slate-100 text-slate-800" onclick={() => void togglePreview()} aria-label={$_('messaging.voicePreview')}>
        {#if previewPlaying}<Pause size={16} fill="currentColor" />{:else}<Play size={16} fill="currentColor" />{/if}
      </button>
      <input class="h-2 min-w-0 flex-1 accent-hero" type="range" min="0" max={Math.max(previewDuration, 1)} value={previewPositionMs} oninput={seekPreview} aria-label={$_('messaging.voicePreview')} />
      <span class="shrink-0 text-xs font-bold tabular-nums text-slate-500">{previewPositionFormatted}/{previewDurationFormatted}</span>
    </div>
    <div class="mt-2 flex items-center justify-end gap-2">
      <button type="button" class="grid h-9 w-9 place-items-center rounded-full bg-slate-100 text-red-700" onclick={cancelCurrent} aria-label={$_('messaging.deleteRecording')}><Trash2 size={16} /></button>
      <button type="button" class="grid h-9 w-9 place-items-center rounded-full bg-slate-100 text-slate-700" onclick={rerecord} aria-label={$_('messaging.rerecord')}><RotateCcw size={16} /></button>
      <button type="button" class="grid h-9 w-9 place-items-center rounded-full bg-hero text-white disabled:opacity-40" disabled={sending || voiceSubmitting} onclick={() => void sendPreview()} aria-label={$_('messaging.sendVoiceNote')}><SendHorizontal size={16} class="rtl:-scale-x-100" /></button>
    </div>
  </div>
  {/if}
</div>
