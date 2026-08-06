<script lang="ts">
  import { _ } from 'svelte-i18n';
  import { Download, FileText } from 'lucide-svelte';
  import type { MessageDocument } from '$lib/messaging/types';

  let {
    document,
    load
  }: {
    document: MessageDocument;
    load: () => Promise<Blob>;
  } = $props();

  let loading = $state(false);
  let error = $state('');

  function sizeLabel(bytes: number) {
    return bytes >= 1_000_000
      ? `${(bytes / 1_000_000).toFixed(1)} MB`
      : `${Math.max(1, Math.ceil(bytes / 1_000))} KB`;
  }

  async function download() {
    if (!document.available || loading) return;
    loading = true;
    error = '';
    try {
      const blob = await load();
      const url = URL.createObjectURL(blob);
      const anchor = window.document.createElement('a');
      anchor.href = url;
      anchor.download = document.filename;
      anchor.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1_000);
    } catch (cause) {
      error = cause instanceof Error ? cause.message : $_('messaging.documentDownloadError');
    } finally {
      loading = false;
    }
  }
</script>

<div class="mt-2 min-w-[15rem] rounded-xl border border-current/15 bg-white/95 p-3 text-slate-800 shadow-sm">
  <div class="flex items-center gap-3">
    <span class="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-violet-50 text-hero"><FileText size={20} aria-hidden="true" /></span>
    <span class="min-w-0 flex-1">
      <span dir="auto" class="block truncate text-sm font-extrabold">{document.filename}</span>
      <span class="block text-[0.68rem] font-semibold text-slate-500">{document.content_type === 'application/pdf' ? 'PDF' : 'CSV'} · {sizeLabel(document.size_bytes)}</span>
    </span>
    {#if document.available}
      <button type="button" class="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-slate-200 text-hero hover:bg-violet-50 disabled:opacity-50" disabled={loading} onclick={download} aria-label={$_('messaging.downloadDocument')} title={$_('messaging.downloadDocument')}>
        {#if loading}<span aria-hidden="true">…</span>{:else}<Download size={18} aria-hidden="true" />{/if}
      </button>
    {/if}
  </div>
  {#if !document.available}<p class="mt-2 text-xs font-semibold text-slate-500">{$_('messaging.documentUnavailable')}</p>{/if}
  {#if error}<p class="mt-2 text-xs font-semibold text-red-700" role="alert">{error}</p>{/if}
</div>
