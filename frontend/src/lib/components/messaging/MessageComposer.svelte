<script lang="ts">
  import { _ } from 'svelte-i18n';
  import { Camera, ImagePlus, Mic, RefreshCw, SendHorizontal, X } from 'lucide-svelte';
  import type { SelectedMessagePhoto } from '$lib/messaging/types';

  let {
    draft = $bindable(''),
    disabled = false,
    sending = false,
    offline = false,
    photos = [],
    onselectphotos,
    onremovephoto,
    onretryphoto,
    onsend
  }: {
    draft?: string;
    disabled?: boolean;
    sending?: boolean;
    offline?: boolean;
    photos?: SelectedMessagePhoto[];
    onselectphotos: (files: File[]) => void;
    onremovephoto: (photo: SelectedMessagePhoto) => void;
    onretryphoto: (photo: SelectedMessagePhoto) => void;
    onsend: (body: string) => Promise<boolean>;
  } = $props();

  async function submit() {
    const value = draft.trim();
    const readyPhotos = photos.filter((photo) => photo.state === 'ready');
    if ((!value && readyPhotos.length === 0) || disabled || sending || offline || photos.some((photo) => photo.state !== 'ready')) return;
    const accepted = await onsend(value);
    if (accepted) draft = '';
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      void submit();
    }
  }

  function selected(event: Event) {
    const input = event.currentTarget as HTMLInputElement;
    onselectphotos(Array.from(input.files || []));
    input.value = '';
  }
</script>

<form
  data-testid="message-composer"
  class="sticky bottom-0 z-20 shrink-0 border-t border-slate-200 bg-white/95 px-3 pb-[calc(0.5rem+var(--safe-bottom))] pt-2 backdrop-blur sm:px-4 sm:pt-2.5"
  onsubmit={(event) => { event.preventDefault(); void submit(); }}
>
  {#if offline}
    <p class="mb-2 rounded-xl bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-800" role="status">{$_('messaging.offlineComposer')}</p>
  {/if}
  {#if photos.length}
    <div class="mb-2 flex gap-2 overflow-x-auto pb-1" aria-label={$_('messaging.selectedPhotos')}>
      {#each photos as photo (photo.client_upload_id)}
        <div class="relative h-16 w-16 shrink-0 overflow-hidden rounded-xl border border-slate-200 bg-slate-100">
          <img src={photo.preview_url} alt={$_('messaging.selectedPhoto')} class="h-full w-full object-cover" />
          <div class="absolute inset-x-0 bottom-0 bg-slate-950/75 px-1.5 py-1 text-center text-[0.6rem] font-bold text-white">
            {photo.state === 'uploading' ? $_('messaging.uploadingPhoto') : photo.state === 'failed' ? $_('messaging.photoUploadFailed') : photo.state === 'ready' ? $_('messaging.photoReady') : $_('messaging.photoPending')}
          </div>
          <button type="button" onclick={() => onremovephoto(photo)} class="absolute right-1 top-1 grid h-7 w-7 place-items-center rounded-full bg-slate-950/80 text-white" aria-label={$_('messaging.removePhoto')}><X size={14} /></button>
          {#if photo.state === 'failed'}
            <button type="button" onclick={() => onretryphoto(photo)} class="absolute left-1 top-1 grid h-7 w-7 place-items-center rounded-full bg-white text-red-700 shadow" aria-label={$_('messaging.retryPhoto')}><RefreshCw size={14} /></button>
          {/if}
        </div>
      {/each}
    </div>
  {/if}
  <div class="flex items-end gap-2">
    <label class="sr-only" for="message-body">{$_('messaging.messageLabel')}</label>
    <div class="flex min-w-0 flex-1 items-end rounded-[1.4rem] border border-slate-200 bg-slate-50 shadow-sm transition focus-within:border-hero focus-within:bg-white focus-within:ring-2 focus-within:ring-hero/15">
      <div class="flex h-11 shrink-0 items-center ps-1">
        <label class="grid h-10 w-10 shrink-0 cursor-pointer place-items-center rounded-full text-slate-600 transition hover:bg-slate-200/70 focus-within:outline focus-within:outline-2 focus-within:outline-offset-[-2px] focus-within:outline-hero" aria-label={$_('messaging.choosePhotos')}>
          <ImagePlus size={18} aria-hidden="true" />
          <input class="sr-only" type="file" accept="image/jpeg,image/png,image/webp,image/heic,image/heif,.heic,.heif" multiple disabled={disabled || sending || photos.length >= 5} onchange={selected} />
        </label>
        <label class="grid h-10 w-10 shrink-0 cursor-pointer place-items-center rounded-full text-slate-600 transition hover:bg-slate-200/70 focus-within:outline focus-within:outline-2 focus-within:outline-offset-[-2px] focus-within:outline-hero" aria-label={$_('messaging.takePhoto')}>
          <Camera size={18} aria-hidden="true" />
          <input class="sr-only" type="file" accept="image/*" capture="environment" disabled={disabled || sending || photos.length >= 5} onchange={selected} />
        </label>
      </div>
      <textarea
        id="message-body"
        bind:value={draft}
        rows="1"
        maxlength="10000"
        disabled={disabled || sending}
        onkeydown={handleKeydown}
        placeholder={disabled ? $_('messaging.readOnlyPlaceholder') : $_('messaging.messagePlaceholder')}
        class="min-h-11 max-h-32 min-w-0 flex-1 resize-none bg-transparent px-2 py-2.5 text-sm leading-6 text-slate-900 outline-none placeholder:text-slate-400 disabled:cursor-not-allowed disabled:opacity-60 sm:resize-y"
        dir="auto"
      ></textarea>
    </div>
    {#if draft.trim() || photos.length}
      <button
        type="submit"
        data-testid="message-send"
        disabled={disabled || sending || offline || (!draft.trim() && !photos.some((photo) => photo.state === 'ready')) || photos.some((photo) => photo.state !== 'ready')}
        class="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-hero text-white shadow-sm transition hover:brightness-95 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-hero disabled:cursor-not-allowed disabled:opacity-40"
        aria-label={sending ? $_('messaging.sending') : $_('messaging.send')}
      >
        {#if sending}…{:else}<SendHorizontal size={19} class="rtl:-scale-x-100" aria-hidden="true" />{/if}
      </button>
    {:else}
      <button
        type="button"
        data-testid="message-voice-placeholder"
        class="grid h-11 w-11 shrink-0 cursor-not-allowed place-items-center rounded-full bg-hero/10 text-hero/50"
        aria-label={$_('messaging.voiceNotesUnavailable')}
        title={$_('messaging.voiceNotesUnavailable')}
        disabled
      >
        <Mic size={19} aria-hidden="true" />
      </button>
    {/if}
  </div>
</form>
