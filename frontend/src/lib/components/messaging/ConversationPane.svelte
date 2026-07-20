<script lang="ts">
  import { tick } from 'svelte';
  import { _, locale } from 'svelte-i18n';
  import { ShieldCheck } from 'lucide-svelte';
  import type { ConversationDetail, MessagePhoto, MessageVoiceNote, OptimisticMessage, SelectedMessagePhoto } from '$lib/messaging/types';
  import {
    activeGuardianCount,
    conversationTitle,
    staffContextLabel
  } from '$lib/messaging/presentation';
  import { highestServerSequence } from '$lib/messaging/state';
  import MessageComposer from './MessageComposer.svelte';
  import MessageReceiptTicks from './MessageReceiptTicks.svelte';
  import ProtectedMessagePhoto from './ProtectedMessagePhoto.svelte';
  import ProtectedPhotoViewer from './ProtectedPhotoViewer.svelte';
  import ProtectedVoiceNote from './ProtectedVoiceNote.svelte';

  let {
    conversation,
    messages,
    loading = false,
    loadingOlder = false,
    hasOlder = false,
    sending = false,
    offline = false,
    noticeOpen = false,
    noticeAcknowledged = false,
    persistentBack = false,
    backLabel,
    draft = $bindable(''),
    urgent = $bindable(false),
    selectedPhotos = [],
    onback,
    onloadolder,
    onsend,
    onretry,
    onselectphotos,
    onremovephoto,
    onretryphoto,
    onvoice,
    loadphoto,
    loadvoice,
    ontogglenotice,
    onacknowledgenotice,
    onclosenotice
  }: {
    conversation: ConversationDetail | null;
    messages: OptimisticMessage[];
    loading?: boolean;
    loadingOlder?: boolean;
    hasOlder?: boolean;
    sending?: boolean;
    offline?: boolean;
    noticeOpen?: boolean;
    noticeAcknowledged?: boolean;
    persistentBack?: boolean;
    backLabel?: string;
    draft?: string;
    urgent?: boolean;
    selectedPhotos?: SelectedMessagePhoto[];
    onback: () => void;
    onloadolder: () => void;
    onsend: (body: string, urgent: boolean) => Promise<boolean>;
    onretry: (message: OptimisticMessage) => void;
    onselectphotos: (files: File[]) => void;
    onremovephoto: (photo: SelectedMessagePhoto) => void;
    onretryphoto: (photo: SelectedMessagePhoto) => void;
    onvoice: (recording: { blob: Blob; duration_ms: number; mime_type: string }) => Promise<boolean>;
    loadphoto: (photo: MessagePhoto, variant: 'thumbnail' | 'full') => Promise<Blob>;
    loadvoice: (voice: MessageVoiceNote) => Promise<Blob>;
    ontogglenotice: () => void;
    onacknowledgenotice: () => void;
    onclosenotice: () => void;
  } = $props();

  const arabic = $derived($locale === 'ar');
  const hasConversationNotice = $derived(Boolean(
    conversation?.shared_guardian_visibility || conversation?.safeguarding_disclosure
  ));
  const guardianCount = $derived(conversation ? activeGuardianCount(conversation) : 0);
  const guardianCountLabel = $derived(
    guardianCount === 1
      ? $_('messaging.guardianCountOne')
      : $_('messaging.guardianCountMany', { values: { count: guardianCount } })
  );
  const headerContext = $derived(conversation
    ? staffContextLabel(conversation.staff_context, arabic, {
        administration: $_('messaging.contextAdministration'),
        homeroom: $_('messaging.contextHomeroom'),
        teacher: $_('messaging.contextSubjectTeacher'),
        staff: $_('messaging.contextStaff')
      }) || (arabic ? conversation.context.label_ar : conversation.context.label) || ''
    : '');
  const headerSubtitle = $derived([headerContext, guardianCount ? guardianCountLabel : '']
    .filter(Boolean)
    .join(' · '));
  let timeline = $state<HTMLDivElement>();
  let nearBottom = $state(true);
  let unseenMessages = $state(0);
  let previousHighest = 0;
  let trackedConversationId: string | null = null;
  let viewerPhotos = $state<MessagePhoto[]>([]);
  let viewerIndex = $state(0);

  function openViewer(photos: MessagePhoto[], index: number) {
    viewerPhotos = photos;
    viewerIndex = index;
  }

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

  function participantDetail(participant: ConversationDetail['participant_details'][number]) {
    if (participant.side === 'guardian') {
      return relationshipLabel(participant.relationship) || $_('messaging.guardianParticipant');
    }
    return $_('messaging.staffParticipant');
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

  function receiptLabel(state: 'sent' | 'delivered' | 'read') {
    return $_({
      sent: 'messaging.receiptSent',
      delivered: 'messaging.receiptDelivered',
      read: 'messaging.receiptRead'
    }[state]);
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
        <button type="button" class="mt-0.5 grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-slate-200 text-slate-600 {persistentBack ? '' : 'md:hidden'}" onclick={onback} aria-label={backLabel || $_('messaging.backToInbox')} title={backLabel || $_('messaging.backToInbox')}>←</button>
        <div class="min-w-0 flex-1">
          <div class="flex flex-wrap items-center gap-2">
            <h2 dir="auto" class="truncate text-base font-extrabold text-slate-900 sm:text-lg">{conversationTitle(conversation, arabic)}</h2>
            {#if conversation.read_only}
              <span class="rounded-full bg-slate-100 px-2 py-1 text-[0.65rem] font-bold uppercase tracking-wide text-slate-600">{conversation.participant_state === 'closed' ? $_('messaging.closed') : $_('messaging.readOnly')}</span>
            {/if}
          </div>
          {#if headerSubtitle}<p dir="auto" class="mt-0.5 truncate text-xs font-semibold text-slate-500">{headerSubtitle}</p>{/if}
        </div>
        {#if noticeAcknowledged && hasConversationNotice}
          <button
            type="button"
            class="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-slate-200 text-slate-600 transition hover:border-hero hover:text-hero focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-hero"
            onclick={ontogglenotice}
            aria-label={$_('messaging.conversationInformation')}
            aria-expanded={noticeOpen}
            aria-controls="conversation-information"
            data-testid="conversation-information-button"
          >
            <ShieldCheck size={18} aria-hidden="true" />
          </button>
        {/if}
      </div>
    </header>

    {#if hasConversationNotice && noticeOpen}
      <aside
        id="conversation-information"
        class="border-b border-sky-100 bg-sky-50 px-4 py-3 text-sky-950 sm:px-5"
        aria-labelledby="conversation-information-title"
        data-testid="conversation-information-panel"
      >
        <div class="mx-auto flex max-w-3xl gap-3">
          <ShieldCheck size={19} class="mt-0.5 shrink-0 text-sky-700" aria-hidden="true" />
          <div class="min-w-0 flex-1">
            <h3 id="conversation-information-title" class="text-xs font-extrabold">{$_('messaging.conversationNoticeTitle')}</h3>
            {#if conversation.shared_guardian_visibility}
              <p class="mt-1 text-xs leading-5">{$_('messaging.sharedGuardians')}</p>
            {/if}
            {#if conversation.safeguarding_disclosure}
              <p class="mt-1 text-xs leading-5">{$_('messaging.safeguardingDisclosure')}</p>
            {/if}
            {#if conversation.participant_details.length}
              <div class="mt-2 border-t border-sky-200/70 pt-2">
                <h4 class="text-[0.68rem] font-extrabold uppercase tracking-wide text-sky-800">{$_('messaging.participants')}</h4>
                <ul class="mt-1 flex flex-wrap gap-1.5">
                  {#each conversation.participant_details as participant}
                    <li dir="auto" class="rounded-full bg-white/80 px-2.5 py-1 text-[0.68rem] font-semibold text-slate-700 ring-1 ring-sky-100">
                      {participant.display_name} · {participantDetail(participant)}{participant.active ? '' : ` · ${$_('messaging.inactiveParticipant')}`}
                    </li>
                  {/each}
                </ul>
              </div>
            {/if}
            <button
              type="button"
              class="mt-3 inline-flex min-h-10 items-center justify-center rounded-xl bg-slate-900 px-4 py-2 text-xs font-extrabold text-white shadow-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-hero"
              onclick={noticeAcknowledged ? onclosenotice : onacknowledgenotice}
            >
              {noticeAcknowledged ? $_('messaging.closeInformation') : $_('messaging.acknowledgeNotice')}
            </button>
          </div>
        </div>
      </aside>
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
                  {#if message.body}<p dir="auto" class="whitespace-pre-wrap break-words text-sm leading-6">{message.body}</p>{/if}
                  {#if message.photos?.length}
                    <div class="mt-2 grid gap-1.5" class:grid-cols-2={message.photos.length > 1} class:grid-cols-1={message.photos.length === 1}>
                      {#each message.photos as photo, photoIndex (photo.id)}
                        <ProtectedMessagePhoto load={() => loadphoto(photo, 'thumbnail')} onclick={() => openViewer(message.photos, photoIndex)} alt={$_('messaging.photoAlt', { values: { number: photoIndex + 1 } })} />
                      {/each}
                    </div>
                  {/if}
                  {#if message.voice_note}
                    <div class="mt-1"><ProtectedVoiceNote voice={message.voice_note} messageId={message.id} load={() => loadvoice(message.voice_note!)} /></div>
                  {/if}
                  {#if message.local_voice_url}
                    <audio class="mt-1 h-10 w-full min-w-[15rem]" src={message.local_voice_url} controls preload="metadata" aria-label={$_('messaging.voiceNote')}></audio>
                  {/if}
                  {#if message.local_photo_urls?.length}
                    <div class="mt-2 grid grid-cols-2 gap-1.5">
                      {#each message.local_photo_urls as url}
                        <img src={url} alt={$_('messaging.selectedPhoto')} class="aspect-square w-full rounded-xl object-cover opacity-90" />
                      {/each}
                    </div>
                  {/if}
                {:else}
                  <p class="text-sm italic opacity-75">{$_('messaging.messageUnavailable')}</p>
                {/if}
                <div class:justify-end={message.sender_is_self} class="mt-1.5 flex flex-wrap items-center gap-2 text-[0.62rem] opacity-70">
                  <time datetime={message.created_at}>{formatDate(message.created_at)}</time>
                  {#if message.sender_is_self && message.receipt && !message.local_state}
                    <MessageReceiptTicks receipt={message.receipt} label={receiptLabel(message.receipt.state)} />
                  {/if}
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
      <div class="border-t border-slate-200 bg-slate-100 px-4 py-3 text-center text-xs font-semibold text-slate-600">{conversation.participant_state === 'closed' ? $_('messaging.closedNotice') : $_('messaging.readOnlyNotice')}</div>
    {/if}
    <MessageComposer
      bind:draft
      bind:urgent
      disabled={conversation.read_only || !conversation.capabilities.can_send}
      {sending}
      {offline}
      photos={selectedPhotos}
      voiceEnabled={conversation.capabilities.voice_notes_enabled}
      canMarkUrgent={conversation.capabilities.can_mark_urgent}
      {onselectphotos}
      {onremovephoto}
      {onretryphoto}
      {onvoice}
      {onsend}
    />
  </section>
{/if}

{#if viewerPhotos.length}
  <ProtectedPhotoViewer photos={viewerPhotos} bind:index={viewerIndex} load={(photo) => loadphoto(photo, 'full')} onclose={() => viewerPhotos = []} />
{/if}
