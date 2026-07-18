<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { Download, Pause, Play, RefreshCw, Volume2 } from 'lucide-svelte';
  import type { MessageVoiceNote } from '$lib/messaging/types';

  let {
    voice,
    messageId,
    load
  }: {
    voice: MessageVoiceNote;
    messageId: string;
    load: () => Promise<Blob>;
  } = $props();

  let playbackState: 'idle' | 'loading' | 'ready' | 'failed' | 'unavailable' = $state('idle');
  let playing = $state(false);
  let currentTime = $state(0);
  let speed: 1 | 1.5 | 2 = $state(1);
  let audio: HTMLAudioElement | null = null;
  let objectUrl = '';
  let frame = 0;
  let destroyed = false;

  const totalSeconds = $derived(Math.max(0.6, voice.duration_ms / 1000));
  const currentLabel = $derived(formatTime(currentTime));
  const totalLabel = $derived(formatTime(totalSeconds));

  function formatTime(seconds: number) {
    const value = Math.max(0, Math.floor(seconds));
    return `${Math.floor(value / 60)}:${String(value % 60).padStart(2, '0')}`;
  }

  function release() {
    if (frame) cancelAnimationFrame(frame);
    frame = 0;
    if (audio) {
      audio.pause();
      audio.src = '';
      audio.load();
    }
    audio = null;
    playing = false;
    if (objectUrl) URL.revokeObjectURL(objectUrl);
    objectUrl = '';
  }

  function progress() {
    if (!audio) return;
    currentTime = Number.isFinite(audio.currentTime) ? audio.currentTime : 0;
    if (!audio.paused) frame = requestAnimationFrame(progress);
  }

  async function ensureLoaded() {
    if (playbackState === 'ready' && audio) return true;
    playbackState = 'loading';
    try {
      const blob = await load();
      if (destroyed) return false;
      if (!blob.size || blob.type.split(';', 1)[0] !== 'audio/mp4') {
        playbackState = 'unavailable';
        return false;
      }
      objectUrl = URL.createObjectURL(blob);
      audio = new Audio(objectUrl);
      audio.preload = 'metadata';
      audio.playbackRate = speed;
      audio.addEventListener('ended', () => { playing = false; currentTime = totalSeconds; });
      audio.addEventListener('pause', () => { playing = false; });
      audio.addEventListener('error', () => { playbackState = 'unavailable'; release(); });
      playbackState = 'ready';
      return true;
    } catch {
      playbackState = 'failed';
      return false;
    }
  }

  async function toggle() {
    if (playing) {
      audio?.pause();
      playing = false;
      return;
    }
    if (!(await ensureLoaded()) || !audio) return;
    window.dispatchEvent(new CustomEvent('chh:voice-play', { detail: { id: messageId } }));
    try {
      audio.playbackRate = speed;
      await audio.play();
      playing = true;
      progress();
    } catch {
      playbackState = 'failed';
    }
  }

  function seek(event: Event) {
    const next = Number((event.currentTarget as HTMLInputElement).value);
    currentTime = next;
    if (audio) audio.currentTime = next;
  }

  function cycleSpeed() {
    speed = speed === 1 ? 1.5 : speed === 1.5 ? 2 : 1;
    if (audio) audio.playbackRate = speed;
  }

  function retry() {
    release();
    playbackState = 'idle';
    void ensureLoaded();
  }

  function otherPlayback(event: Event) {
    const id = (event as CustomEvent<{ id?: string }>).detail?.id;
    if (id && id !== messageId && audio) {
      audio.pause();
      playing = false;
    }
  }

  onMount(() => window.addEventListener('chh:voice-play', otherPlayback));
  onDestroy(() => {
    destroyed = true;
    window.removeEventListener('chh:voice-play', otherPlayback);
    release();
  });
</script>

<div class="min-w-[15rem] max-w-full" data-testid="protected-voice-note">
  <div class="flex items-center gap-2">
    <button type="button" class="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-slate-900 text-white disabled:opacity-50" disabled={playbackState === 'loading' || playbackState === 'unavailable'} onclick={() => void toggle()} aria-label={playing ? $_('messaging.pauseVoiceNote') : $_('messaging.playVoiceNote')}>
      {#if playbackState === 'loading'}<Download size={16} class="animate-pulse" />{:else if playing}<Pause size={17} fill="currentColor" />{:else}<Play size={17} fill="currentColor" />{/if}
    </button>
    <Volume2 size={16} class="shrink-0 opacity-60" aria-hidden="true" />
    <input type="range" min="0" max={totalSeconds} step="0.05" value={currentTime} oninput={seek} class="h-2 min-w-0 flex-1 accent-current" aria-label={$_('messaging.voicePosition', { values: { elapsed: currentLabel, duration: totalLabel } })} />
    <button type="button" class="min-h-9 min-w-11 rounded-full bg-black/10 px-2 text-xs font-black" onclick={cycleSpeed} aria-label={$_('messaging.playbackSpeed', { values: { speed } })}>{speed}x</button>
  </div>
  <div class="mt-1 flex items-center justify-between gap-3 text-[0.65rem] font-bold opacity-70">
    <span class="tabular-nums">{currentLabel} / {totalLabel}</span>
    {#if playbackState === 'idle'}<span>{$_('messaging.voiceTapToDownload')}</span>{/if}
    {#if playbackState === 'loading'}<span>{$_('messaging.voiceLoading')}</span>{/if}
    {#if playbackState === 'failed'}<button type="button" class="inline-flex items-center gap-1 underline" onclick={retry}><RefreshCw size={12} />{$_('messaging.retry')}</button>{/if}
    {#if playbackState === 'unavailable'}<span>{$_('messaging.voiceUnavailable')}</span>{/if}
  </div>
</div>
