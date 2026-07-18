<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import type { MessagePhoto } from '$lib/messaging/types';

  let { photos, index = $bindable(0), load, onclose }: {
    photos: MessagePhoto[];
    index?: number;
    load: (photo: MessagePhoto) => Promise<Blob>;
    onclose: () => void;
  } = $props();
  let objectUrl = $state('');
  let photoState = $state<'loading' | 'ready' | 'failed'>('loading');
  let stage = $state<HTMLElement>();
  let scale = $state(1);
  let translateX = $state(0);
  let translateY = $state(0);
  let epoch = 0;
  const pointers = new Map<number, { x: number; y: number }>();
  let gestureStart: { x: number; y: number } | null = null;
  let panStart = { x: 0, y: 0, translateX: 0, translateY: 0 };
  let pinchStart: { distance: number; scale: number } | null = null;

  function distance(values: Array<{ x: number; y: number }>) {
    return Math.hypot(values[0].x - values[1].x, values[0].y - values[1].y);
  }
  function resetTransform() { scale = 1; translateX = 0; translateY = 0; pointers.clear(); }
  function clampPan() {
    if (!stage || scale <= 1) { translateX = 0; translateY = 0; return; }
    const maxX = stage.clientWidth * (scale - 1) / 2;
    const maxY = stage.clientHeight * (scale - 1) / 2;
    translateX = Math.max(-maxX, Math.min(maxX, translateX));
    translateY = Math.max(-maxY, Math.min(maxY, translateY));
  }
  async function fetchFull() {
    const requestEpoch = ++epoch;
    photoState = 'loading';
    resetTransform();
    try {
      const blob = await load(photos[index]);
      if (requestEpoch !== epoch || !blob.type.startsWith('image/')) return;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
      objectUrl = URL.createObjectURL(blob);
      photoState = 'ready';
    } catch { if (requestEpoch === epoch) photoState = 'failed'; }
  }
  function move(delta: number) {
    const next = Math.max(0, Math.min(photos.length - 1, index + delta));
    if (next === index) return;
    index = next;
  }
  function pointerDown(event: PointerEvent) {
    stage?.setPointerCapture(event.pointerId);
    pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
    if (pointers.size === 1) {
      gestureStart = { x: event.clientX, y: event.clientY };
      panStart = { x: event.clientX, y: event.clientY, translateX, translateY };
    } else if (pointers.size === 2) {
      pinchStart = { distance: distance([...pointers.values()]), scale };
      gestureStart = null;
    }
  }
  function pointerMove(event: PointerEvent) {
    if (!pointers.has(event.pointerId)) return;
    pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
    if (pointers.size === 2 && pinchStart) {
      scale = Math.max(1, Math.min(4, pinchStart.scale * distance([...pointers.values()]) / Math.max(1, pinchStart.distance)));
      clampPan();
    } else if (pointers.size === 1 && scale > 1) {
      translateX = panStart.translateX + event.clientX - panStart.x;
      translateY = panStart.translateY + event.clientY - panStart.y;
      clampPan();
    }
  }
  function pointerUp(event: PointerEvent) {
    const start = gestureStart;
    const single = pointers.size === 1;
    pointers.delete(event.pointerId);
    if (single && start && scale === 1) {
      const dx = event.clientX - start.x;
      const dy = event.clientY - start.y;
      if (Math.abs(dx) > 56 && Math.abs(dx) > Math.abs(dy)) move(dx < 0 ? 1 : -1);
    }
    gestureStart = null; pinchStart = null; clampPan();
  }
  function doubleClick() { scale = scale > 1 ? 1 : 2.5; clampPan(); }
  function nativeBack(event: Event) {
    if (event.defaultPrevented) return;
    event.preventDefault(); event.stopImmediatePropagation(); onclose();
  }
  function keydown(event: KeyboardEvent) {
    if (event.key === 'Escape') onclose();
    else if (event.key === 'ArrowLeft') move(-1);
    else if (event.key === 'ArrowRight') move(1);
  }

  $effect(() => { photos[index]?.id; void fetchFull(); });
  onMount(() => { window.addEventListener('chh:native-back', nativeBack, { capture: true }); });
  onDestroy(() => {
    epoch += 1;
    window.removeEventListener('chh:native-back', nativeBack, { capture: true });
    if (objectUrl) URL.revokeObjectURL(objectUrl);
  });
</script>

<div class="fixed inset-0 z-[100] flex flex-col bg-slate-950 text-white" role="dialog" aria-modal="true" aria-label={$_('messaging.photoViewer')} tabindex="0" onkeydown={keydown}>
  <header class="flex shrink-0 items-center justify-between gap-3 border-b border-white/10 px-4 py-3 pt-[calc(0.75rem+var(--safe-top))]">
    <span class="text-sm font-bold">{index + 1} / {photos.length}</span>
    <button type="button" onclick={onclose} class="grid h-11 w-11 place-items-center rounded-full bg-white/10 text-xl" aria-label={$_('messaging.closePhoto')}>×</button>
  </header>
  <div bind:this={stage} role="group" aria-label={$_('messaging.photoViewer')} class="relative flex min-h-0 flex-1 select-none items-center justify-center overflow-hidden p-3 pb-[calc(0.75rem+var(--safe-bottom))]" style="touch-action:none" onpointerdown={pointerDown} onpointermove={pointerMove} onpointerup={pointerUp} onpointercancel={pointerUp} ondblclick={doubleClick}>
    <button type="button" onclick={() => move(-1)} disabled={index === 0} class="absolute left-3 z-10 hidden h-11 w-11 place-items-center rounded-full bg-black/45 text-2xl disabled:opacity-20 sm:grid" aria-label={$_('messaging.previousPhoto')}>â€¹</button>
    {#if photoState === 'ready'}
      <img src={objectUrl} alt={$_('messaging.photoAlt', { values: { number: index + 1 } })} draggable="false" class="block max-h-full max-w-full origin-center object-contain will-change-transform" style:transform={`translate3d(${translateX}px,${translateY}px,0) scale(${scale})`} />
    {:else if photoState === 'failed'}
      <button type="button" onclick={fetchFull} class="rounded-2xl bg-white/10 px-5 py-4 text-sm font-bold">{$_('messaging.photoUnavailable')} Â· {$_('messaging.retry')}</button>
    {:else}<span class="h-10 w-10 animate-spin rounded-full border-4 border-white/30 border-t-white" aria-label={$_('messaging.loadingPhoto')}></span>{/if}
    <button type="button" onclick={() => move(1)} disabled={index === photos.length - 1} class="absolute right-3 z-10 hidden h-11 w-11 place-items-center rounded-full bg-black/45 text-2xl disabled:opacity-20 sm:grid" aria-label={$_('messaging.nextPhoto')}>â€º</button>
  </div>
</div>
