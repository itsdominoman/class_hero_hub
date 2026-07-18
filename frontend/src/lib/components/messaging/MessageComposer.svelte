<script lang="ts">
  import { _ } from 'svelte-i18n';
  import { Camera, ImagePlus, RefreshCw, X } from 'lucide-svelte';
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
  class="sticky bottom-0 z-20 shrink-0 border-t border-slate-200 bg-white/95 p-3 pb-[calc(0.75rem+var(--safe-bottom))] backdrop-blur sm:p-4"
  onsubmit={(event) => { event.preventDefault(); void submit(); }}
>
  {#if offline}
    <p class="mb-2 rounded-xl bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-800" role="status">{$_('messaging.offlineComposer')}</p>
  {/if}
  {#if photos.length}
    <div class="mb-3 grid grid-cols-3 gap-2 sm:grid-cols-5" aria-label={$_('messaging.selectedPhotos')}>
      {#each photos as photo (photo.client_upload_id)}
        <div class="relative aspect-square overflow-hidden rounded-xl border border-slate-200 bg-slate-100">
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
    <label class="grid h-12 w-12 shrink-0 cursor-pointer place-items-center rounded-2xl border border-slate-200 bg-white text-slate-700 shadow-sm" aria-label={$_('messaging.choosePhotos')}>
      <ImagePlus size={19} aria-hidden="true" />
      <input class="sr-only" type="file" accept="image/jpeg,image/png,image/webp,image/heic,image/heif,.heic,.heif" multiple disabled={disabled || sending || photos.length >= 5} onchange={selected} />
    </label>
    <label class="grid h-12 w-12 shrink-0 cursor-pointer place-items-center rounded-2xl border border-slate-200 bg-white text-slate-700 shadow-sm" aria-label={$_('messaging.takePhoto')}>
      <Camera size={19} aria-hidden="true" />
      <input class="sr-only" type="file" accept="image/*" capture="environment" disabled={disabled || sending || photos.length >= 5} onchange={selected} />
    </label>
    <label class="sr-only" for="message-body">{$_('messaging.messageLabel')}</label>
    <textarea
      id="message-body"
      bind:value={draft}
      rows="1"
      maxlength="10000"
      disabled={disabled || sending}
      onkeydown={handleKeydown}
      placeholder={disabled ? $_('messaging.readOnlyPlaceholder') : $_('messaging.messagePlaceholder')}
      class="max-h-36 min-h-12 flex-1 resize-none rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm leading-6 text-slate-900 shadow-inner outline-none transition placeholder:text-slate-400 focus:border-hero focus:bg-white focus:ring-2 focus:ring-hero/15 disabled:cursor-not-allowed disabled:opacity-60 sm:resize-y"
      dir="auto"
    ></textarea>
    <button
      type="submit"
      data-testid="message-send"
      disabled={disabled || sending || offline || (!draft.trim() && !photos.some((photo) => photo.state === 'ready')) || photos.some((photo) => photo.state !== 'ready')}
      class="grid h-12 min-w-12 place-items-center rounded-2xl bg-slate-900 px-4 text-sm font-bold text-white shadow-sm transition hover:bg-hero focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-hero disabled:cursor-not-allowed disabled:opacity-40"
      aria-label={sending ? $_('messaging.sending') : $_('messaging.send')}
    >
      {sending ? '…' : $_('messaging.send')}
    </button>
  </div>
  <p class="mt-2 hidden text-[0.68rem] text-slate-400 sm:block">{$_('messaging.sendShortcut')}</p>
</form>
