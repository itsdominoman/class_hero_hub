<script lang="ts">
  import { _ } from 'svelte-i18n';

  let {
    disabled = false,
    sending = false,
    offline = false,
    onsend
  }: {
    disabled?: boolean;
    sending?: boolean;
    offline?: boolean;
    onsend: (body: string) => Promise<boolean>;
  } = $props();

  let body = $state('');

  async function submit() {
    const value = body.trim();
    if (!value || disabled || sending || offline) return;
    body = '';
    const accepted = await onsend(value);
    if (!accepted) body = value;
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      void submit();
    }
  }
</script>

<form class="border-t border-slate-200 bg-white p-3 sm:p-4" onsubmit={(event) => { event.preventDefault(); void submit(); }}>
  {#if offline}
    <p class="mb-2 rounded-xl bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-800" role="status">{$_('messaging.offlineComposer')}</p>
  {/if}
  <div class="flex items-end gap-2">
    <label class="sr-only" for="message-body">{$_('messaging.messageLabel')}</label>
    <textarea
      id="message-body"
      bind:value={body}
      rows="1"
      maxlength="10000"
      disabled={disabled || sending}
      onkeydown={handleKeydown}
      placeholder={disabled ? $_('messaging.readOnlyPlaceholder') : $_('messaging.messagePlaceholder')}
      class="max-h-36 min-h-12 flex-1 resize-y rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm leading-6 text-slate-900 shadow-inner outline-none transition placeholder:text-slate-400 focus:border-hero focus:bg-white focus:ring-2 focus:ring-hero/15 disabled:cursor-not-allowed disabled:opacity-60"
      dir="auto"
    ></textarea>
    <button
      type="submit"
      disabled={disabled || sending || offline || !body.trim()}
      class="grid h-12 min-w-12 place-items-center rounded-2xl bg-slate-900 px-4 text-sm font-bold text-white shadow-sm transition hover:bg-hero focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-hero disabled:cursor-not-allowed disabled:opacity-40"
      aria-label={sending ? $_('messaging.sending') : $_('messaging.send')}
    >
      {sending ? '…' : $_('messaging.send')}
    </button>
  </div>
  <p class="mt-2 hidden text-[0.68rem] text-slate-400 sm:block">{$_('messaging.sendShortcut')}</p>
</form>
