<script lang="ts">
  import { _, locale } from 'svelte-i18n';
  import type { ConversationSummary } from '$lib/messaging/types';
  import { conversationSubtitle, conversationTitle } from '$lib/messaging/presentation';

  let {
    conversations,
    selectedId,
    loading = false,
    onselect
  }: {
    conversations: ConversationSummary[];
    selectedId: string | null;
    loading?: boolean;
    onselect: (conversation: ConversationSummary) => void;
  } = $props();
  const arabic = $derived($locale === 'ar');

  function formatTime(value: string | null | undefined) {
    if (!value) return '';
    const date = new Date(value);
    const now = new Date();
    const sameDay = date.toDateString() === now.toDateString();
    return new Intl.DateTimeFormat(undefined, sameDay
      ? { hour: '2-digit', minute: '2-digit' }
      : { month: 'short', day: 'numeric' }).format(date);
  }
</script>

<div class="min-h-0 flex-1 overflow-y-auto" aria-live="polite" aria-busy={loading}>
  {#if loading && conversations.length === 0}
    <div class="space-y-3 p-4" aria-label={$_('messaging.loadingInbox')}>
      {#each Array(5) as _}
        <div class="h-24 animate-pulse rounded-2xl bg-slate-100"></div>
      {/each}
    </div>
  {:else if conversations.length === 0}
    <div class="flex min-h-64 flex-col items-center justify-center px-8 text-center">
      <div class="mb-4 grid h-14 w-14 place-items-center rounded-2xl bg-emerald-50 text-2xl" aria-hidden="true">✉</div>
      <h2 class="text-lg font-bold text-slate-900">{$_('messaging.emptyTitle')}</h2>
      <p class="mt-2 max-w-xs text-sm leading-6 text-slate-500">{$_('messaging.emptyBody')}</p>
    </div>
  {:else}
    <ul class="divide-y divide-slate-100" aria-label={$_('messaging.conversationList')}>
      {#each conversations as conversation (conversation.id)}
        <li>
          <button
            type="button"
            class:!bg-emerald-50={selectedId === conversation.id}
            class="group flex w-full gap-3 bg-white px-4 py-4 text-start transition hover:bg-slate-50 focus-visible:relative focus-visible:z-10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-inset focus-visible:outline-hero"
            aria-current={selectedId === conversation.id ? 'page' : undefined}
            onclick={() => onselect(conversation)}
          >
            <span class="mt-0.5 grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-slate-100 font-bold text-slate-600 group-hover:bg-white" aria-hidden="true">
              {conversationTitle(conversation, arabic).trim().slice(0, 1).toLocaleUpperCase()}
            </span>
            <span class="min-w-0 flex-1">
              <span class="flex items-start justify-between gap-3">
                <span dir="auto" class:font-extrabold={conversation.unread_count > 0} class="truncate text-sm font-bold text-slate-900">
                  {conversationTitle(conversation, arabic)}
                </span>
                <span class="shrink-0 text-[0.7rem] font-semibold text-slate-400">
                  {formatTime(conversation.last_message_at)}
                </span>
              </span>
              <span dir="auto" class="mt-0.5 block truncate text-xs font-semibold text-slate-500">
                {conversationSubtitle(conversation, arabic)}
              </span>
              <span class="mt-2 flex items-center justify-between gap-3">
                <span dir="auto" class:font-bold={conversation.unread_count > 0} class="truncate text-xs text-slate-500">
                  {conversation.last_message?.body || (conversation.last_message?.message_type === 'voice_note' ? $_('messaging.voiceNote') : conversation.last_message?.photo_count ? $_('messaging.photoMessage') : $_('messaging.noMessagesYet'))}
                </span>
                {#if conversation.unread_count > 0}
                  <span class="grid min-w-5 shrink-0 place-items-center rounded-full bg-hero px-1.5 py-0.5 text-[0.65rem] font-extrabold text-white" aria-label={$_('messaging.unreadCount', { values: { count: conversation.unread_count } })}>
                    {conversation.unread_count > 99 ? '99+' : conversation.unread_count}
                  </span>
                {:else if conversation.read_only}
                  <span class="shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-[0.6rem] font-bold uppercase tracking-wide text-slate-500">{$_('messaging.closed')}</span>
                {/if}
              </span>
            </span>
          </button>
        </li>
      {/each}
    </ul>
  {/if}
</div>
