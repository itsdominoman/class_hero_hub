<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { _ } from 'svelte-i18n';

  let { load, alt = '', onclick }: { load: () => Promise<Blob>; alt?: string; onclick: () => void } = $props();
  let photoState = $state<'loading' | 'ready' | 'failed'>('loading');
  let objectUrl = $state('');
  let active = true;

  async function fetchPhoto() {
    photoState = 'loading';
    try {
      const blob = await load();
      if (!active || !blob.type.startsWith('image/')) throw new Error('invalid image');
      if (objectUrl) URL.revokeObjectURL(objectUrl);
      objectUrl = URL.createObjectURL(blob);
      photoState = 'ready';
    } catch {
      if (active) photoState = 'failed';
    }
  }

  onMount(() => { void fetchPhoto(); });
  onDestroy(() => {
    active = false;
    if (objectUrl) URL.revokeObjectURL(objectUrl);
  });
</script>

<div class="relative aspect-square overflow-hidden rounded-xl bg-slate-100">
  {#if photoState === 'ready'}
    <button type="button" class="h-full w-full focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-hero" {onclick} aria-label={alt || $_('messaging.openPhoto')}>
      <img src={objectUrl} {alt} class="h-full w-full object-cover" draggable="false" />
    </button>
  {:else if photoState === 'failed'}
    <button type="button" onclick={fetchPhoto} class="grid h-full w-full place-items-center p-2 text-center text-[0.68rem] font-bold text-slate-600" aria-label={$_('messaging.retryPhoto')}>
      {$_('messaging.photoUnavailable')}<br />{$_('messaging.retry')}
    </button>
  {:else}
    <div class="grid h-full w-full place-items-center" role="status" aria-label={$_('messaging.loadingPhoto')}>
      <span class="h-6 w-6 animate-spin rounded-full border-2 border-slate-300 border-t-hero"></span>
    </div>
  {/if}
</div>
