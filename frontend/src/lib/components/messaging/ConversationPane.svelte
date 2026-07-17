<script lang="ts">
  import { tick } from 'svelte';
  import { _, locale } from 'svelte-i18n';
  import type { ConversationDetail, OptimisticMessage } from '$lib/messaging/types';
  import { conversationSubtitle, conversationTitle } from '$lib/messaging/presentation';
  import { highestServerSequence } from '$lib/messaging/state';
  import MessageComposer from './MessageComposer.svelte';

  let {
    conversation,
    messages,
    loading = false,
    loadingOlder = false,
    hasOlder = false,
    sending = false,
    offline = false,
    onback,
    onloadolder,
    onsend,
    onretry
  }: {
    conversation: ConversationDetail | null;
    messages: OptimisticMessage[];
    loading?: boolean;
    loadingOlder?: boolean;
    hasOlder?: boolean;
    sending?: boolean;
    offline?: boolean;
    onback: () => void;
    onloadolder: () => void;
    onsend: (body: string) => Promise<boolean>;
    onretry: (message: OptimisticMessage) => void;
  } = $props();

  const arabic = $derived($locale === 'ar');
  let timeline = $state<HTMLDivElement>();
  let nearBottom = $state(true);
  let unseenMessages = $state(0);
  let previousHighest = 0;
  let trackedConversationId: string | null = null;

  function updateScrollPosition() {
    if (!timeline) return;
    nearBottom = timeline.scrollHeight - timeline.scrollTop - timeline.clientHeight < 96;
    if (nearBottom) unseenMessages = 0;
  }

  function scrollToLatest(behavior: ScrollBehavior = 'smooth') {
    if (!timeline) return;
    timeline.scrollTo({ top: timeline.scrollHeight, behavior });
    nearBottom = true;
    unseenMessages = 0;
  }

  $effect(() => {
    const nextConversationId = conversation?.id ?? null;
    if (nextConversationId === trackedConversationId) return;
    trackedConversationId = nextConversationId;
    previousHighest = 0;
    nearBottom = true;
    unseenMessages = 0;
  });

  $effect(() => {
    const highest = highestServerSequence(messages);
    const added = Math.max(0, highest - previousHighest);
    const shouldFollow = nearBottom;
    previousHighest = Math.max(previousHighest, highest);
    if (!added) return;
    void tick().then(() => {
      if (shouldFollow) scrollToLatest('auto');
      else unseenMessages += added;
    });
  });

  function relationshipLabel(value: string | null | undefined) {
    return value && ['mother', 'father', 'guardian', 'other'].includes(value)
      ? $_(`messaging.relationships.${value}`)
      : '';
  }

  function senderLabel(message: OptimisticMessage) {
    const relationship = relationshipLabel(message.sender_relationship);
    return [message.sender_display_name, relationship].filter(Boolean).join(' · ');
  }

  function formatDate(value: string) {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short'
    }).format(new Date(value));
  }
</script>

{#if loading}
  <div class="grid h-full min-h-[30rem] place-items-center" aria-live="polite">
    <div class="text-center">
      <div class="mx-auto h-9 w-9 animate-spin rounded-full border-4 border-emerald-100 border-t-hero"></div>
      <p class="mt-3 text-sm font-semibold text-slate-500">{$_('messaging.loadingConversation')}</p>
    </div>
  </div>
{:else if !conversation}
  <div class="hidden h-full min-h-[30rem] place-items-center bg-slate-50/60 text-center md:grid">
    <div>
      <div class="mx-auto grid h-16 w-16 place-items-center rounded-3xl bg-white text-3xl shadow-sm" aria-hidden="true">💬</div>
      <h2 class="mt-5 text-xl font-extrabold text-slate-900">{$_('messaging.selectTitle')}</h2>
      <p class="mt-2 text-sm text-slate-500">{$_('messaging.selectBody')}</p>
    </div>
  </div>
{:else}
  <section class="flex h-full min-h-0 flex-col bg-slate-50/70" aria-label={$_('messaging.conversationWith', { values: { name: conversationTitle(conversation, arabic) } })}>
    <header class="border-b border-slate-200 bg-white px-3 py-3 sm:px-5 sm:py-4">
      <div class="flex items-start gap-3">
        <button type="button" class="mt-0.5 grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-slate-200 text-slate-600 md:hidden" onclick={onback} aria-label={$_('messaging.backToInbox')}>←</button>
        <div class="min-w-0 flex-1">
          <div class="flex flex-wrap items-center gap-2">
            <h2 dir="auto" class="truncate text-base font-extrabold text-slate-900 sm:text-lg">{conversationTitle(conversation, arabic)}</h2>
            {#if conversation.read_only}
              <span class="rounded-full bg-slate-100 px-2 py-1 text-[0.65rem] font-bold uppercase tracking-wide text-slate-600">{$_('messaging.readOnly')}</span>
            {/if}
          </div>
          <p dir="auto" class="mt-0.5 truncate text-xs font-semibold text-slate-500">{conversationSubtitle(conversation, arabic)}</p>
          {#if conversation.shared_guardian_visibility}
            <p class="mt-1 text-[0.68rem] font-medium text-slate-400">{$_('messaging.sharedGuardians')}</p>
          {/if}
        </div>
      </div>
    </header>

    {#if conversation.safeguarding_disclosure}
      <div class="border-b border-sky-100 bg-sky-50 px-4 py-2 text-center text-[0.7rem] font-semibold leading-5 text-sky-800">
        {$_('messaging.safeguardingDisclosure')}
      </div>
    {/if}

    <div bind:this={timeline} onscroll={updateScrollPosition} class="relative min-h-0 flex-1 overflow-y-auto px-3 py-5 sm:px-6" aria-live="polite" data-testid="message-timeline">
      {#if hasOlder}
        <div class="mb-5 text-center">
          <button type="button" class="rounded-full border border-slate-200 bg-white px-4 py-2 text-xs font-bold text-slate-600 shadow-sm hover:border-hero hover:text-hero disabled:opacity-50" disabled={loadingOlder} onclick={onloadolder}>
            {loadingOlder ? $_('messaging.loadingOlder') : $_('messaging.loadOlder')}
          </button>
        </div>
      {/if}
      {#if messages.length === 0}
        <div class="grid min-h-72 place-items-center text-center">
          <div>
            <p class="font-bold text-slate-700">{$_('messaging.threadEmptyTitle')}</p>
            <p class="mt-2 text-sm text-slate-500">{$_('messaging.threadEmptyBody')}</p>
          </div>
        </div>
      {:else}
        <ol class="mx-auto flex max-w-3xl flex-col gap-3">
          {#each messages as message (message.client_message_id || message.id)}
            <li class:self-end={message.sender_is_self} class="max-w-[88%] self-start sm:max-w-[75%]">
              <div
                class:bg-hero={message.sender_is_self}
                class:text-white={message.sender_is_self}
                class:bg-white={!message.sender_is_self}
                class:text-slate-800={!message.sender_is_self}
                class:ring-red-300={message.local_state === 'failed'}
                class="rounded-2xl px-4 py-3 shadow-sm ring-1 ring-slate-100"
              >
                {#if !message.sender_is_self}
                  <p dir="auto" class="mb-1 text-[0.68rem] font-extrabold text-emerald-700">{senderLabel(message)}</p>
                {/if}
                {#if message.state === 'active'}
                  <p dir="auto" class="whitespace-pre-wrap break-words text-sm leading-6">{message.body}</p>
                {:else}
                  <p class="text-sm italic opacity-75">{$_('messaging.messageUnavailable')}</p>
                {/if}
                <div class:justify-end={message.sender_is_self} class="mt-1.5 flex flex-wrap items-center gap-2 text-[0.62rem] opacity-70">
                  <time datetime={message.created_at}>{formatDate(message.created_at)}</time>
                  {#if message.local_state === 'sending'}<span>{$_('messaging.sending')}</span>{/if}
                  {#if message.local_state === 'failed'}<span class="font-bold">{$_('messaging.failed')}</span>{/if}
                </div>
              </div>
              {#if message.local_state === 'failed'}
                <button type="button" class="mt-1 px-2 text-xs font-bold text-red-700 underline underline-offset-2" onclick={() => onretry(message)}>
                  {$_('messaging.retry')}
                </button>
              {/if}
            </li>
          {/each}
        </ol>
      {/if}
      {#if unseenMessages > 0}
        <div class="sticky bottom-2 z-10 mt-4 flex justify-center">
          <button type="button" onclick={() => scrollToLatest()} class="rounded-full bg-slate-900 px-4 py-2 text-xs font-extrabold text-white shadow-lg focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-hero">
            {$_('messaging.newMessages', { values: { count: unseenMessages } })}
          </button>
        </div>
      {/if}
    </div>

    {#if conversation.read_only || !conversation.capabilities.can_send}
      <div class="border-t border-slate-200 bg-slate-100 px-4 py-3 text-center text-xs font-semibold text-slate-600">{$_('messaging.readOnlyNotice')}</div>
    {/if}
    <MessageComposer
      disabled={conversation.read_only || !conversation.capabilities.can_send}
      {sending}
      {offline}
      {onsend}
    />
  </section>
{/if}
