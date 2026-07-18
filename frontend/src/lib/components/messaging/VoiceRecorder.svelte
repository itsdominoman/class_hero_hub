<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { Lock, Mic, Pause, Play, RotateCcw, SendHorizontal, Square, Trash2 } from 'lucide-svelte';
  import {
    deleteNativeRecording,
    isNativeAndroidVoiceRecorder,
    nativeRecordingBlob,
    NativeVoiceRecorder,
    type NativeVoiceRecording
  } from '$lib/nativeVoiceRecorder';

  let {
    disabled = false,
    sending = false,
    onvoice
  }: {
    disabled?: boolean;
    sending?: boolean;
    onvoice: (recording: { blob: Blob; duration_ms: number; mime_type: string }) => Promise<boolean>;
  } = $props();

  type State = 'idle' | 'recording' | 'locked' | 'paused' | 'preview' | 'error';
  let recorderState: State = $state('idle');
  let elapsedMs = $state(0);
  let levels: number[] = $state(Array(18).fill(8));
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

  const nativeAndroid = typeof window !== 'undefined' && isNativeAndroidVoiceRecorder();

  const formatted = $derived(`${Math.floor(elapsedMs / 60000)}:${String(Math.floor(elapsedMs / 1000) % 60).padStart(2, '0')}`);

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
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    const nativeReference = previewNativeReference;
    previewUrl = '';
    previewBlob = null;
    previewDuration = 0;
    previewNativeReference = null;
    if (nativeReference) void deleteNativeRecording(nativeReference).catch(() => undefined);
  }

  function reset() {
    releaseStream();
    mediaRecorder = null;
    nativeRecording = false;
    nativeFinishing = false;
    chunks = [];
    locked = false;
    pointerHeld = false;
    pointerId = null;
    elapsedMs = 0;
    levels = Array(18).fill(8);
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
    const step = Math.max(1, Math.floor(values.length / 18));
    levels = Array.from({ length: 18 }, (_, index) => {
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
    levels = Array.from({ length: 18 }, (_, index) => 10 + Math.round(12 * Math.abs(Math.sin(phase + index * 0.55))));
    animationFrame = requestAnimationFrame(visualizeNative);
  }

  async function startRecording(mode: 'holding' | 'locked') {
    if (disabled || sending || recorderState !== 'idle') return;
    error = '';
    clearPreview();
    if (nativeAndroid) {
      await startNativeRecording(mode);
      return;
    }
    await startWebRecording(mode);
  }

  async function startNativeRecording(mode: 'holding' | 'locked') {
    try {
      await NativeVoiceRecorder.start();
      if (destroyed || (mode === 'holding' && !pointerHeld)) {
        await NativeVoiceRecorder.cancel().catch(() => undefined);
        reset();
        return;
      }
      nativeRecording = true;
      startedAt = performance.now();
      pausedAt = 0;
      pausedTotal = 0;
      elapsedMs = 0;
      locked = mode === 'locked';
      recorderState = locked ? 'locked' : 'recording';
      timer = setInterval(updateElapsed, 100);
      visualizeNative();
      haptic(35);
    } catch (caught) {
      const code = (caught as { code?: string })?.code || 'recording_start_failed';
      nativeRecording = false;
      recorderState = 'error';
      error = code === 'permission_denied' || code === 'permission_permanently_denied'
        ? $_('messaging.microphonePermissionDenied')
        : $_('messaging.microphoneUnavailable');
    }
  }

  async function startWebRecording(mode: 'holding' | 'locked') {
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
      if (destroyed || (mode === 'holding' && !pointerHeld)) {
        captured.getTracks().forEach((track) => track.stop());
        reset();
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
      locked = mode === 'locked';
      recorderState = locked ? 'locked' : 'recording';
      mediaRecorder.start(250);
      timer = setInterval(updateElapsed, 100);
      visualize();
      haptic(35);
    } catch (caught) {
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
    } catch {
      await deleteNativeRecording(result.fileReference).catch(() => undefined);
      recorderState = 'error';
      error = $_('messaging.voiceRecordingFailed');
      reset();
      return;
    }
    const duration = result.durationMs;
    if (destroyed || duration < 600 || !blob.size) {
      await deleteNativeRecording(result.fileReference).catch(() => undefined);
      if (duration < 600 && !destroyed) error = $_('messaging.voiceTooShort');
      reset();
      return;
    }
    previewNativeReference = result.fileReference;
    if (mode === 'send') {
      haptic([25, 30, 25]);
      const accepted = await onvoice({ blob, duration_ms: duration, mime_type: result.mimeType });
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
    if (destroyed || mode === 'cancel' || duration < 600 || !blob.size) {
      if (duration < 600 && mode !== 'cancel' && !destroyed) error = $_('messaging.voiceTooShort');
      reset();
      return;
    }
    if (mode === 'send') {
      haptic([25, 30, 25]);
      const accepted = await onvoice({ blob, duration_ms: duration, mime_type: mimeType });
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
    if (nativeAndroid) {
      if (!nativeRecording || nativeFinishing) return;
      nativeFinishing = true;
      updateElapsed();
      if (mode === 'cancel') {
        await NativeVoiceRecorder.cancel().catch(() => undefined);
        nativeRecording = false;
        nativeFinishing = false;
        haptic([40, 35, 40]);
        reset();
        return;
      }
      try {
        const result = await NativeVoiceRecorder.stop();
        nativeRecording = false;
        nativeFinishing = false;
        releaseStream();
        await nativeStopped(result, mode);
      } catch {
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
    startX = event.clientX;
    startY = event.clientY;
    (event.currentTarget as HTMLElement).setPointerCapture?.(event.pointerId);
    void startRecording('holding');
  }

  function pointerMove(event: PointerEvent) {
    if (!pointerHeld || pointerId !== event.pointerId || recorderState !== 'recording') return;
    const rtl = getComputedStyle(document.documentElement).direction === 'rtl';
    const cancelDistance = rtl ? event.clientX - startX : startX - event.clientX;
    if (cancelDistance > 72) {
      pointerHeld = false;
      void finish('cancel');
      return;
    }
    if (startY - event.clientY > 72) {
      locked = true;
      pointerHeld = false;
      recorderState = 'locked';
      haptic([25, 20, 25]);
    }
  }

  function pointerUp(event: PointerEvent) {
    if (pointerId !== event.pointerId) return;
    pointerHeld = false;
    pointerId = null;
    if (recorderState === 'recording' && !locked) void finish('send');
  }

  function pointerCancel(event: PointerEvent) {
    if (pointerId !== event.pointerId) return;
    pointerHeld = false;
    pointerId = null;
    if (!locked) void finish('cancel');
  }

  async function pauseRecording() {
    if (nativeAndroid) {
      if (!nativeRecording || (recorderState !== 'recording' && recorderState !== 'locked')) return;
      try {
        await NativeVoiceRecorder.pause();
        pausedAt = performance.now();
        recorderState = 'paused';
        if (animationFrame) cancelAnimationFrame(animationFrame);
        animationFrame = 0;
        levels = Array(18).fill(8);
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
    if (nativeAndroid) {
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
    if (!previewBlob || sending) return;
    const accepted = await onvoice({ blob: previewBlob, duration_ms: previewDuration, mime_type: previewBlob.type });
    if (accepted) {
      clearPreview();
      reset();
    }
  }

  function rerecord() {
    clearPreview();
    recorderState = 'idle';
    void startRecording('locked');
  }

  function cancelCurrent() {
    clearPreview();
    if (nativeRecording || (mediaRecorder && mediaRecorder.state !== 'inactive')) void finish('cancel');
    else reset();
  }

  function visibilityChanged() {
    if (document.hidden && ((nativeRecording && (recorderState === 'recording' || recorderState === 'locked')) || mediaRecorder?.state === 'recording')) {
      locked = true;
      void pauseRecording();
    }
  }

  function nativeBack(event: Event) {
    if (recorderState === 'idle' || event.defaultPrevented) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    cancelCurrent();
  }

  onMount(() => {
    document.addEventListener('visibilitychange', visibilityChanged);
    window.addEventListener('chh:native-back', nativeBack, { capture: true });
  });

  onDestroy(() => {
    destroyed = true;
    document.removeEventListener('visibilitychange', visibilityChanged);
    window.removeEventListener('chh:native-back', nativeBack, { capture: true });
    clearPreview();
    if (nativeRecording) void NativeVoiceRecorder.cancel().catch(() => undefined);
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      stopMode = 'cancel';
      mediaRecorder.stop();
    }
    releaseStream();
  });
</script>

{#if recorderState === 'idle' || recorderState === 'error'}
  <div class="relative">
    <button
      type="button"
      data-testid="message-voice-record"
      class="grid h-11 w-11 shrink-0 touch-none select-none place-items-center rounded-full bg-hero text-white shadow-sm transition active:scale-95 disabled:cursor-not-allowed disabled:opacity-40"
      disabled={disabled || sending}
      aria-label={$_('messaging.recordVoiceNote')}
      onpointerdown={pointerDown}
      onpointermove={pointerMove}
      onpointerup={pointerUp}
      onpointercancel={pointerCancel}
    ><Mic size={19} aria-hidden="true" /></button>
    {#if error}<p class="absolute bottom-14 end-0 w-64 rounded-xl bg-red-50 p-3 text-xs font-bold text-red-800 shadow-lg" role="alert">{error}<br />{$_('messaging.microphoneSettingsHelp')}</p>{/if}
  </div>
{:else if recorderState === 'recording'}
  <div class="flex min-w-0 flex-1 items-center gap-3 rounded-2xl bg-red-50 px-3 py-2 text-red-800" data-testid="voice-recording-hold">
    <span class="h-2.5 w-2.5 animate-pulse rounded-full bg-red-600"></span>
    <strong class="tabular-nums">{formatted}</strong>
    <span class="min-w-0 flex-1 truncate text-xs font-bold">{$_('messaging.slideCancel')} / {$_('messaging.swipeLock')}</span>
    <Lock size={17} aria-hidden="true" />
  </div>
{:else if recorderState === 'locked' || recorderState === 'paused'}
  <div class="min-w-0 flex-1 rounded-2xl border border-red-100 bg-red-50 px-3 py-2" data-testid="voice-recording-locked">
    <div class="flex items-center gap-2">
      <span class="h-2.5 w-2.5 rounded-full bg-red-600" class:animate-pulse={recorderState === 'locked'}></span>
      <strong class="w-12 tabular-nums text-red-800">{formatted}</strong>
      <div class="flex h-9 min-w-0 flex-1 items-center justify-center gap-1" aria-label={$_('messaging.recordingLevel')}>
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
  <div class="min-w-0 flex-1 rounded-2xl border border-slate-200 bg-white px-3 py-2 shadow-sm" data-testid="voice-recording-preview">
    <div class="flex items-center gap-2">
      <audio class="h-9 min-w-0 flex-1" src={previewUrl} controls preload="metadata" aria-label={$_('messaging.voicePreview')}></audio>
      <span class="text-xs font-bold tabular-nums text-slate-500">{Math.round(previewDuration / 1000)}s</span>
      <button type="button" class="grid h-9 w-9 place-items-center rounded-full bg-slate-100 text-red-700" onclick={cancelCurrent} aria-label={$_('messaging.deleteRecording')}><Trash2 size={16} /></button>
      <button type="button" class="grid h-9 w-9 place-items-center rounded-full bg-slate-100 text-slate-700" onclick={rerecord} aria-label={$_('messaging.rerecord')}><RotateCcw size={16} /></button>
      <button type="button" class="grid h-9 w-9 place-items-center rounded-full bg-hero text-white disabled:opacity-40" disabled={sending} onclick={() => void sendPreview()} aria-label={$_('messaging.sendVoiceNote')}><SendHorizontal size={16} class="rtl:-scale-x-100" /></button>
    </div>
  </div>
{/if}
