<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { api } from '$lib/api';
  import type { SessionUser } from '$lib/roleRouting';
  import ComposeDialog from '$lib/components/messaging/ComposeDialog.svelte';
  import ConversationPane from '$lib/components/messaging/ConversationPane.svelte';
  import InboxList from '$lib/components/messaging/InboxList.svelte';
  import { errorStatus, messagingApi } from '$lib/messaging/api';
  import { filterConversations } from '$lib/messaging/presentation';
  import type {
    ConversationDetail,
    ConversationSummary,
    MessagingMembership,
    OptimisticMessage,
    RecipientResults
  } from '$lib/messaging/types';

  let loadingSession = $state(true);
  let available = $state(true);
  let memberships = $state<MessagingMembership[]>([]);
  let membership = $state<MessagingMembership | null>(null);
  let conversations = $state<ConversationSummary[]>([]);
  let loadingInbox = $state(false);
  let loadingConversation = $state(false);
  let selectedId = $state<string | null>(null);
  let selectedConversation = $state<ConversationDetail | null>(null);
  let messages = $state<OptimisticMessage[]>([]);
  let messagesCursor = $state<string | null>(null);
  let loadingOlder = $state(false);
  let sending = $state(false);
  let error = $state<string | null>(null);
  let conversationError = $state<string | null>(null);
  let search = $state('');
  let filter = $state<'all' | 'unread' | 'active' | 'closed'>('all');
  let composeOpen = $state(false);
  let recipients = $state<RecipientResults>({ students: [], staff: [] });
  let loadingRecipients = $state(false);
  let creatingConversation = $state(false);
  let offline = $state(false);
  let mobileThreadOpen = $state(false);
  let pollTimer: ReturnType<typeof setInterval> | null = null;

  let filteredConversations = $derived(filterConversations(conversations, search, filter));
  let totalUnread = $derived(conversations.reduce((sum, row) => sum + row.unread_count, 0));

  function updateConversationQuery(id: string | null) {
    const url = new URL(window.location.href);
    if (id) url.searchParams.set('conversation', id);
    else url.searchParams.delete('conversation');
    window.history.replaceState(window.history.state, '', `${url.pathname}${url.search}${url.hash}`);
  }

  function requestedConversationId(): string | null {
    return new URL(window.location.href).searchParams.get('conversation');
  }

  async function loadInbox(options: { preserveError?: boolean; openRequested?: boolean } = {}) {
    if (!membership || loadingInbox || offline) return;
    loadingInbox = true;
    if (!options.preserveError) error = null;
    try {
      const page = await messagingApi.inbox(membership);
      conversations = page.items;
      available = true;
      const requested = options.openRequested ? requestedConversationId() : selectedId;
      if (requested) {
        const exists = page.items.some((row) => row.id === requested);
        if (exists || options.openRequested) await openConversation(requested, false);
      } else if (selectedId && !page.items.some((row) => row.id === selectedId)) {
        closeConversation();
      }
    } catch (cause) {
      if (errorStatus(cause) === 404) {
        available = false;
        conversations = [];
      } else {
        error = cause instanceof Error ? cause.message : $_('messaging.loadError');
      }
    } finally {
      loadingInbox = false;
    }
  }

  async function openConversation(id: string, updateUrl = true) {
    if (!membership) return;
    selectedId = id;
    mobileThreadOpen = true;
    loadingConversation = true;
    conversationError = null;
    if (updateUrl) updateConversationQuery(id);
    try {
      const [detail, page] = await Promise.all([
        messagingApi.detail(membership, id),
        messagingApi.messages(membership, id)
      ]);
      selectedConversation = detail;
      messages = page.items;
      messagesCursor = page.next_cursor;
      const highest = page.items.at(-1)?.sequence ?? 0;
      if (detail.unread_count > 0 && highest > 0) {
        try {
          await messagingApi.acknowledgeRead(membership, id, highest);
          conversations = conversations.map((row) =>
            row.id === id ? { ...row, unread_count: 0 } : row
          );
          selectedConversation = { ...detail, unread_count: 0 };
        } catch {
          conversationError = $_('messaging.readUpdateError');
        }
      }
    } catch (cause) {
      const status = errorStatus(cause);
      conversationError =
        status === 403 || status === 404
          ? $_('messaging.accessChanged')
          : cause instanceof Error
            ? cause.message
            : $_('messaging.conversationLoadError');
      selectedConversation = null;
      messages = [];
      if (status === 403 || status === 404) void loadInbox({ preserveError: true });
    } finally {
      loadingConversation = false;
    }
  }

  function chooseConversation(conversation: ConversationSummary) {
    void openConversation(conversation.id);
  }

  function closeConversation() {
    selectedId = null;
    selectedConversation = null;
    messages = [];
    messagesCursor = null;
    mobileThreadOpen = false;
    conversationError = null;
    updateConversationQuery(null);
  }

  async function loadOlderMessages() {
    if (!membership || !selectedId || !messagesCursor || loadingOlder) return;
    loadingOlder = true;
    try {
      const page = await messagingApi.messages(membership, selectedId, messagesCursor);
      const known = new Set(messages.map((row) => row.id));
      messages = [...page.items.filter((row) => !known.has(row.id)), ...messages];
      messagesCursor = page.next_cursor;
    } catch (cause) {
      conversationError = cause instanceof Error ? cause.message : $_('messaging.olderLoadError');
    } finally {
      loadingOlder = false;
    }
  }

  async function dispatchMessage(clientMessageId: string, body: string): Promise<boolean> {
    if (!membership || !selectedId || !selectedConversation) return false;
    const optimistic: OptimisticMessage = {
      id: `local:${clientMessageId}`,
      client_message_id: clientMessageId,
      sequence: Number.MAX_SAFE_INTEGER,
      sender_display_name: '',
      sender_is_self: true,
      body,
      state: 'active',
      urgent: false,
      created_at: new Date().toISOString(),
      local_state: 'sending'
    };
    const existingIndex = messages.findIndex((row) => row.client_message_id === clientMessageId);
    if (existingIndex >= 0) {
      messages = messages.map((row, index) =>
        index === existingIndex ? { ...row, local_state: 'sending', error: undefined } : row
      );
    } else {
      messages = [...messages, optimistic];
    }
    sending = true;
    try {
      const saved = await messagingApi.send(membership, selectedId, clientMessageId, body);
      const reconciled: OptimisticMessage = { ...saved, sender_is_self: true };
      messages = messages.map((row) =>
        row.client_message_id === clientMessageId ? reconciled : row
      );
      selectedConversation = {
        ...selectedConversation,
        last_message: {
          id: saved.id,
          sequence: saved.sequence,
          sender_display_name: saved.sender_display_name,
          body: saved.body,
          state: saved.state,
          created_at: saved.created_at
        },
        last_message_at: saved.created_at
      };
      conversations = conversations.map((row) =>
        row.id === selectedId
          ? {
              ...row,
              last_message: {
                id: saved.id,
                sequence: saved.sequence,
                sender_display_name: saved.sender_display_name,
                body: saved.body,
                state: saved.state,
                created_at: saved.created_at
              },
              last_message_at: saved.created_at
            }
          : row
      );
      return true;
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : $_('messaging.sendError');
      messages = messages.map((row) =>
        row.client_message_id === clientMessageId
          ? { ...row, local_state: 'failed', error: message }
          : row
      );
      // The draft is now owned by the failed optimistic row. Keeping the
      // composer clear prevents a second UUID from accidentally duplicating it.
      return true;
    } finally {
      sending = false;
    }
  }

  function sendMessage(body: string) {
    return dispatchMessage(crypto.randomUUID(), body);
  }

  function retryMessage(message: OptimisticMessage) {
    if (message.client_message_id && message.body) {
      void dispatchMessage(message.client_message_id, message.body);
    }
  }

  function retrySelectedConversation() {
    if (selectedId) void openConversation(selectedId, false);
  }

  async function openCompose() {
    if (!membership || offline) return;
    composeOpen = true;
    await searchRecipients('');
  }

  async function searchRecipients(query: string) {
    if (!membership) return;
    loadingRecipients = true;
    try {
      recipients = await messagingApi.recipients(membership, query);
    } catch (cause) {
      error = cause instanceof Error ? cause.message : $_('messaging.recipientLoadError');
    } finally {
      loadingRecipients = false;
    }
  }

  async function createStudentConversation(studentId: number) {
    if (!membership || creatingConversation) return;
    creatingConversation = true;
    try {
      const result = await messagingApi.createStudentConversation(membership, studentId);
      composeOpen = false;
      await loadInbox({ preserveError: true });
      await openConversation(result.conversation_id);
    } catch (cause) {
      error = cause instanceof Error ? cause.message : $_('messaging.createError');
    } finally {
      creatingConversation = false;
    }
  }

  async function createStaffConversation(otherMembershipId: number) {
    if (!membership || creatingConversation) return;
    creatingConversation = true;
    try {
      const result = await messagingApi.createStaffConversation(membership, otherMembershipId);
      composeOpen = false;
      await loadInbox({ preserveError: true });
      await openConversation(result.conversation_id);
    } catch (cause) {
      error = cause instanceof Error ? cause.message : $_('messaging.createError');
    } finally {
      creatingConversation = false;
    }
  }

  async function selectMembership(id: number) {
    const next = memberships.find((row) => row.membership_id === id);
    if (!next || next.membership_id === membership?.membership_id) return;
    membership = next;
    available = true;
    conversations = [];
    closeConversation();
    await loadInbox();
  }

  function handleMembershipChange(event: Event) {
    void selectMembership(Number((event.currentTarget as HTMLSelectElement).value));
  }

  async function initialize() {
    try {
      const user = (await api.get('/me')) as SessionUser;
      memberships = (user.memberships || []).filter(
        (row): row is MessagingMembership =>
          (row.role === 'teacher' || row.role === 'school_admin') &&
          Number.isInteger(row.membership_id)
      );
      membership = memberships[0] || null;
      for (const candidate of memberships) {
        try {
          await messagingApi.unreadCount(candidate);
          membership = candidate;
          break;
        } catch (cause) {
          if (errorStatus(cause) !== 403 && errorStatus(cause) !== 404) break;
        }
      }
      if (membership) await loadInbox({ openRequested: true });
    } catch {
      window.location.href = '/login';
    } finally {
      loadingSession = false;
    }
  }

  onMount(() => {
    offline = !navigator.onLine;
    void initialize();

    const onOnline = () => {
      offline = false;
      void loadInbox({ preserveError: true });
      if (selectedId) void openConversation(selectedId, false);
    };
    const onOffline = () => {
      offline = true;
    };
    const onFocus = () => {
      if (!offline) void loadInbox({ preserveError: true });
    };
    window.addEventListener('online', onOnline);
    window.addEventListener('offline', onOffline);
    window.addEventListener('focus', onFocus);
    pollTimer = setInterval(() => {
      if (!document.hidden && !offline) void loadInbox({ preserveError: true });
    }, 20_000);
    return () => {
      window.removeEventListener('online', onOnline);
      window.removeEventListener('offline', onOffline);
      window.removeEventListener('focus', onFocus);
      if (pollTimer) clearInterval(pollTimer);
    };
  });
</script>

<svelte:head>
  <title>{$_('messaging.pageTitle')}</title>
  <meta name="description" content={$_('messaging.pageDescription')} />
</svelte:head>

<div class="mx-auto max-w-7xl px-0 py-0 sm:px-4 sm:py-6 lg:px-6">
  {#if loadingSession}
    <div class="grid min-h-[36rem] place-items-center">
      <p class="font-semibold text-slate-500">{$_('messaging.loading')}</p>
    </div>
  {:else if memberships.length === 0}
    <section class="mx-4 my-10 rounded-3xl border border-slate-200 bg-white p-8 text-center shadow-sm">
      <h1 class="text-2xl font-extrabold text-slate-900">{$_('messaging.staffAccessRequired')}</h1>
      <p class="mt-3 text-slate-500">{$_('messaging.staffAccessBody')}</p>
      <a href="/" class="btn-hero mt-6 inline-flex rounded-2xl px-5 py-3">{$_('messaging.returnDashboard')}</a>
    </section>
  {:else if !available}
    <section class="mx-4 my-10 rounded-3xl border border-slate-200 bg-white p-8 text-center shadow-sm">
      <div class="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-slate-100 text-2xl" aria-hidden="true">✉</div>
      <h1 class="mt-5 text-2xl font-extrabold text-slate-900">{$_('messaging.notAvailableTitle')}</h1>
      <p class="mx-auto mt-3 max-w-xl text-slate-500">{$_('messaging.notAvailableBody')}</p>
      {#if memberships.length > 1}
        <label class="mx-auto mt-5 block max-w-sm text-start text-xs font-bold text-slate-600" for="unavailable-messaging-membership">{$_('messaging.chooseSchool')}</label>
        <select id="unavailable-messaging-membership" value={membership?.membership_id} onchange={handleMembershipChange} class="mx-auto mt-1 block w-full max-w-sm rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700">
          {#each memberships as option (option.membership_id)}
            <option value={option.membership_id}>{option.school_name} · {option.role === 'teacher' ? $_('messaging.teacher') : $_('messaging.schoolAdministrator')}</option>
          {/each}
        </select>
      {/if}
      <a href={membership?.role === 'teacher' ? '/teach' : '/school'} class="btn-hero mt-6 inline-flex rounded-2xl px-5 py-3">{$_('messaging.returnDashboard')}</a>
    </section>
  {:else}
    <section class="flex h-[calc(100dvh-5rem-var(--safe-top))] min-h-[38rem] overflow-hidden border-y border-slate-200 bg-white shadow-xl shadow-slate-200/40 sm:h-[calc(100dvh-8.5rem-var(--safe-top))] sm:rounded-3xl sm:border">
      <aside class:hidden={mobileThreadOpen} class="flex min-h-0 w-full flex-col border-e border-slate-200 md:flex md:w-[23rem] lg:w-[27rem]">
        <header class="border-b border-slate-200 px-4 py-4">
          <div class="flex items-center justify-between gap-3">
            <div class="min-w-0">
              <div class="flex items-center gap-2">
                <h1 class="text-xl font-extrabold text-slate-900">{$_('messaging.title')}</h1>
                {#if totalUnread > 0}
                  <span class="rounded-full bg-hero px-2 py-0.5 text-xs font-extrabold text-white" aria-label={$_('messaging.unreadCount', { values: { count: totalUnread } })}>{totalUnread > 99 ? '99+' : totalUnread}</span>
                {/if}
              </div>
              <p dir="auto" class="mt-0.5 truncate text-xs font-semibold text-slate-500">{membership?.school_name}</p>
            </div>
            <button type="button" disabled={offline} onclick={openCompose} class="grid h-11 min-w-11 place-items-center rounded-2xl bg-slate-900 px-3 text-xl font-bold text-white shadow-sm hover:bg-hero focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-hero disabled:opacity-40" aria-label={$_('messaging.newConversation')}>+</button>
          </div>

          {#if memberships.length > 1}
            <label class="mt-3 block text-[0.68rem] font-bold uppercase tracking-wide text-slate-500" for="messaging-membership">{$_('messaging.actingAs')}</label>
            <select id="messaging-membership" value={membership?.membership_id} onchange={handleMembershipChange} class="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700">
              {#each memberships as option (option.membership_id)}
                <option value={option.membership_id}>{option.school_name} · {option.role === 'teacher' ? $_('messaging.teacher') : $_('messaging.schoolAdministrator')}</option>
              {/each}
            </select>
          {/if}

          <label class="sr-only" for="conversation-search">{$_('messaging.searchConversations')}</label>
          <input id="conversation-search" bind:value={search} type="search" placeholder={$_('messaging.searchConversations')} class="mt-3 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm outline-none focus:border-hero focus:bg-white focus:ring-2 focus:ring-hero/15" />

          <div class="mt-3 flex gap-1 overflow-x-auto" aria-label={$_('messaging.filterConversations')}>
            {#each ['all', 'unread', 'active', 'closed'] as option}
              <button type="button" class:bg-slate-900={filter === option} class:text-white={filter === option} class="shrink-0 rounded-full px-3 py-1.5 text-xs font-bold text-slate-500 hover:bg-slate-100" onclick={() => filter = option as typeof filter}>
                {$_(`messaging.filters.${option}`)}
              </button>
            {/each}
          </div>
        </header>
        {#if offline}
          <p class="bg-amber-50 px-4 py-2 text-center text-xs font-semibold text-amber-800" role="status">{$_('messaging.offlineBanner')}</p>
        {/if}
        {#if error}
          <div class="m-3 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-800" role="alert">
            <p>{error}</p>
            <button type="button" class="mt-2 font-bold underline" onclick={() => loadInbox()}>{$_('messaging.retry')}</button>
          </div>
        {/if}
        <InboxList conversations={filteredConversations} {selectedId} loading={loadingInbox} onselect={chooseConversation} />
      </aside>

      <main class:hidden={!mobileThreadOpen} class="min-w-0 flex-1 md:block">
        {#if conversationError}
          <div class="m-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-800" role="alert">
            <p>{conversationError}</p>
            {#if selectedId}<button type="button" class="mt-2 font-bold underline" onclick={retrySelectedConversation}>{$_('messaging.retry')}</button>{/if}
          </div>
        {/if}
        <ConversationPane
          conversation={selectedConversation}
          {messages}
          loading={loadingConversation}
          loadingOlder={loadingOlder}
          hasOlder={Boolean(messagesCursor)}
          {sending}
          {offline}
          onback={closeConversation}
          onloadolder={() => void loadOlderMessages()}
          onsend={sendMessage}
          onretry={retryMessage}
        />
      </main>
    </section>
  {/if}
</div>

{#if composeOpen && membership}
  <ComposeDialog
    {membership}
    {recipients}
    loading={loadingRecipients}
    creating={creatingConversation}
    onclose={() => composeOpen = false}
    onsearch={(query) => void searchRecipients(query)}
    onstudent={(studentId) => void createStudentConversation(studentId)}
    onstaff={(membershipId) => void createStaffConversation(membershipId)}
  />
{/if}
