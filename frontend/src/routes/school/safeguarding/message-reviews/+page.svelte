<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { api } from '$lib/api';
  import ProtectedMessagePhoto from '$lib/components/messaging/ProtectedMessagePhoto.svelte';
  import ProtectedVoiceNote from '$lib/components/messaging/ProtectedVoiceNote.svelte';
  import { safeguardingApi } from '$lib/safeguarding/api';
  import type {
    SafeguardingContext,
    SafeguardingMembership,
    SafeguardingPermissionsResponse,
    SafeguardingReview,
    SafeguardingSearchItem
  } from '$lib/safeguarding/types';
  import type { SessionUser } from '$lib/roleRouting';

  const reasonCategories = [
    'reported_concern',
    'safeguarding_investigation',
    'complaint',
    'staff_conduct_review',
    'parent_communication_review',
    'legal_regulatory_request',
    'authorised_technical_support',
    'other'
  ];
  const permissionNames = [
    'messaging.safeguarding_review',
    'messaging.moderate',
    'messaging.export_evidence',
    'messaging.export_internal_notes',
    'messaging.manage_safeguarding_permissions'
  ];

  let loading = $state(true);
  let working = $state(false);
  let error = $state<string | null>(null);
  let notice = $state<string | null>(null);
  let memberships = $state<SafeguardingMembership[]>([]);
  let membership = $state<SafeguardingMembership | null>(null);
  let context = $state<SafeguardingContext | null>(null);
  let results = $state<SafeguardingSearchItem[]>([]);
  let selected = $state<SafeguardingSearchItem | null>(null);
  let sessionId = $state<string | null>(null);
  let review = $state<SafeguardingReview | null>(null);
  let permissions = $state<SafeguardingPermissionsResponse | null>(null);
  let fullPhotoUrl = $state<string | null>(null);
  let fullPhotoAlt = $state('');

  let reference = $state('');
  let student = $state('');
  let participant = $state('');
  let participantRole = $state('');
  let grade = $state('');
  let branch = $state('');
  let dateFrom = $state('');
  let dateTo = $state('');
  let status = $state('');
  let messageType = $state('');
  let direction = $state('');
  let flagged = $state(false);
  let restricted = $state(false);
  let closed = $state(false);

  let reasonCategory = $state('reported_concern');
  let justification = $state('');
  let acknowledgement = $state(false);
  let moderationReason = $state('safeguarding_investigation');
  let confidentialReason = $state('');
  let participantSafeReason = $state('');
  let restrictionType = $state('family_replies');
  let reopeningRequiresApproval = $state(true);
  let noteBody = $state('');
  let flagCategory = $state('follow_up');
  let flagSeverity = $state('medium');
  let exportReason = $state('safeguarding_investigation');
  let exportJustification = $state('');
  let includeInternalNotes = $state(false);
  let grantMembershipId = $state('');
  let grantPermission = $state(permissionNames[0]);
  let grantReason = $state('');

  let canModerate = $derived(Boolean(review?.capabilities.can_moderate));
  let canExport = $derived(Boolean(review?.capabilities.can_export));
  let canReview = $derived(Boolean(context?.permissions.includes('messaging.safeguarding_review')));
  let canManage = $derived(Boolean(context?.permissions.includes('messaging.manage_safeguarding_permissions')));

  function requestedMembershipId() {
    const value = Number(new URL(window.location.href).searchParams.get('membership'));
    return Number.isInteger(value) && value > 0 ? value : null;
  }

  function setMembershipQuery(value: SafeguardingMembership) {
    const url = new URL(window.location.href);
    url.searchParams.set('membership', String(value.membership_id));
    window.history.replaceState(window.history.state, '', `${url.pathname}${url.search}`);
  }

  function messageForFailure(value: unknown) {
    return value instanceof Error ? value.message : $_('safeguarding.errors.failed');
  }

  function formatDate(value: string) {
    return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
  }

  async function findEligibleMemberships(user: SessionUser) {
    const candidates = (user.memberships || []).filter((row) =>
      Number.isInteger(row.membership_id) && Number.isInteger(row.school_id)
    );
    const eligible: Array<{ membership: SafeguardingMembership; context: SafeguardingContext }> = [];
    for (const candidate of candidates) {
      try {
        const availability = await safeguardingApi.availability(candidate);
        if (!availability.available) continue;
        const candidateContext = await safeguardingApi.context(candidate);
        eligible.push({ membership: candidate, context: candidateContext });
      } catch {
        // Permission-gated navigation intentionally treats denial as absence.
      }
    }
    return eligible;
  }

  async function initialize() {
    loading = true;
    error = null;
    try {
      const user = await api.get('/me') as SessionUser;
      const eligible = await findEligibleMemberships(user);
      memberships = eligible.map((row) => row.membership);
      const requested = requestedMembershipId();
      const chosen = eligible.find((row) => row.membership.membership_id === requested) || eligible[0];
      if (!chosen) {
        context = null;
        return;
      }
      membership = chosen.membership;
      context = chosen.context;
      setMembershipQuery(chosen.membership);
      if (canReview) await searchConversations();
      if (canManage) await loadPermissions();
    } catch (value) {
      error = messageForFailure(value);
    } finally {
      loading = false;
    }
  }

  async function changeMembership(event: Event) {
    const id = Number((event.currentTarget as HTMLSelectElement).value);
    const next = memberships.find((row) => row.membership_id === id);
    if (!next) return;
    closePhoto();
    selected = null;
    sessionId = null;
    review = null;
    membership = next;
    setMembershipQuery(next);
    working = true;
    try {
      context = await safeguardingApi.context(next);
      if (canReview) await searchConversations();
      permissions = null;
      if (canManage) await loadPermissions();
    } catch (value) {
      error = messageForFailure(value);
    } finally {
      working = false;
    }
  }

  async function searchConversations() {
    if (!membership) return;
    working = true;
    error = null;
    try {
      const response = await safeguardingApi.search(membership, {
        reference, student, participant, participant_role: participantRole, class_grade: grade,
        branch_id: branch,
        date_from: dateFrom ? `${dateFrom}T00:00:00Z` : undefined,
        date_to: dateTo ? `${dateTo}T23:59:59Z` : undefined,
        conversation_status: status,
        message_type: messageType, direction, flagged: flagged || undefined,
        restricted: restricted || undefined, closed: closed || undefined, limit: 50
      });
      results = response.items;
    } catch (value) {
      error = messageForFailure(value);
    } finally {
      working = false;
    }
  }

  function chooseConversation(row: SafeguardingSearchItem) {
    selected = row;
    sessionId = null;
    review = null;
    justification = '';
    acknowledgement = false;
    notice = null;
  }

  async function startReview() {
    if (!membership || !selected) return;
    working = true;
    error = null;
    try {
      const started = await safeguardingApi.startReview(membership, {
        conversation_id: selected.conversation_id,
        reason_category: reasonCategory,
        justification,
        acknowledgement
      });
      sessionId = started.review_session_id;
      await refreshReview();
    } catch (value) {
      error = messageForFailure(value);
    } finally {
      working = false;
    }
  }

  async function refreshReview() {
    if (!membership || !sessionId) return;
    review = await safeguardingApi.review(membership, sessionId);
  }

  async function endReview() {
    if (!membership || !sessionId) return;
    working = true;
    try {
      await safeguardingApi.endReview(membership, sessionId);
      closePhoto();
      sessionId = null;
      review = null;
      notice = $_('safeguarding.notices.reviewEnded');
    } catch (value) {
      error = messageForFailure(value);
    } finally {
      working = false;
    }
  }

  function moderationPayload() {
    return {
      reason_category: moderationReason,
      confidential_reason: confidentialReason,
      participant_safe_reason: participantSafeReason || null
    };
  }

  async function runModeration(action: 'restrict' | 'unrestrict' | 'close' | 'reopen') {
    if (!membership || !sessionId) return;
    working = true;
    error = null;
    try {
      if (action === 'restrict') await safeguardingApi.restriction(membership, sessionId, {
        ...moderationPayload(), restriction_type: restrictionType, reopening_requires_approval: reopeningRequiresApproval
      });
      if (action === 'unrestrict') await safeguardingApi.removeRestriction(membership, sessionId, moderationPayload());
      if (action === 'close') await safeguardingApi.close(membership, sessionId, {
        ...moderationPayload(), reopening_requires_approval: reopeningRequiresApproval
      });
      if (action === 'reopen') await safeguardingApi.reopen(membership, sessionId, {
        ...moderationPayload(), remove_existing_restriction: false
      });
      confidentialReason = '';
      participantSafeReason = '';
      notice = $_('safeguarding.notices.moderationSaved');
      await refreshReview();
      await searchConversations();
    } catch (value) {
      error = messageForFailure(value);
    } finally {
      working = false;
    }
  }

  async function changeMessage(messageId: string, action: 'tombstone' | 'restore') {
    if (!membership || !sessionId) return;
    working = true;
    try {
      if (action === 'tombstone') await safeguardingApi.tombstone(membership, sessionId, messageId, moderationPayload());
      else await safeguardingApi.restore(membership, sessionId, messageId, moderationPayload());
      confidentialReason = '';
      participantSafeReason = '';
      await refreshReview();
    } catch (value) {
      error = messageForFailure(value);
    } finally {
      working = false;
    }
  }

  async function addNote() {
    if (!membership || !sessionId) return;
    working = true;
    try {
      await safeguardingApi.addNote(membership, sessionId, noteBody);
      noteBody = '';
      await refreshReview();
    } catch (value) {
      error = messageForFailure(value);
    } finally {
      working = false;
    }
  }

  async function addFlag(messageId: string | null = null) {
    if (!membership || !sessionId) return;
    working = true;
    try {
      await safeguardingApi.addFlag(membership, sessionId, {
        message_id: messageId, category: flagCategory, severity: flagSeverity,
        internal_note: confidentialReason || null
      });
      confidentialReason = '';
      await refreshReview();
      await searchConversations();
    } catch (value) {
      error = messageForFailure(value);
    } finally {
      working = false;
    }
  }

  async function createExport() {
    if (!membership || !sessionId) return;
    working = true;
    try {
      const created = await safeguardingApi.export(membership, sessionId, {
        export_mode: 'internal', reason_category: exportReason,
        justification: exportJustification, include_internal_notes: includeInternalNotes
      }) as { id: string };
      exportJustification = '';
      await refreshReview();
      await downloadExport(created.id);
    } catch (value) {
      error = messageForFailure(value);
    } finally {
      working = false;
    }
  }

  async function downloadExport(id: string) {
    if (!membership) return;
    const blob = await safeguardingApi.downloadExport(membership, id);
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `chh-message-evidence-${id.slice(0, 8)}.zip`;
    link.click();
    URL.revokeObjectURL(url);
    if (sessionId) await refreshReview();
  }

  async function openPhoto(mediaId: string, alt: string) {
    if (!membership || !sessionId) return;
    closePhoto();
    try {
      const blob = await safeguardingApi.photo(membership, sessionId, mediaId, 'full');
      if (!blob.type.startsWith('image/')) throw new Error('Invalid image');
      fullPhotoUrl = URL.createObjectURL(blob);
      fullPhotoAlt = alt;
    } catch (value) {
      error = messageForFailure(value);
    }
  }

  function closePhoto() {
    if (fullPhotoUrl) URL.revokeObjectURL(fullPhotoUrl);
    fullPhotoUrl = null;
    fullPhotoAlt = '';
  }

  async function loadPermissions() {
    if (membership && canManage) permissions = await safeguardingApi.permissions(membership);
  }

  async function createGrant() {
    if (!membership) return;
    working = true;
    try {
      await safeguardingApi.grantPermission(membership, {
        membership_id: Number(grantMembershipId), permission: grantPermission, reason: grantReason
      });
      grantReason = '';
      await loadPermissions();
    } catch (value) {
      error = messageForFailure(value);
    } finally {
      working = false;
    }
  }

  async function revokeGrant(id: string) {
    if (!membership || !grantReason.trim()) {
      error = $_('safeguarding.errors.revocationReason');
      return;
    }
    working = true;
    try {
      await safeguardingApi.revokePermission(membership, id, grantReason);
      grantReason = '';
      await loadPermissions();
    } catch (value) {
      error = messageForFailure(value);
    } finally {
      working = false;
    }
  }

  onMount(() => void initialize());
  onDestroy(closePhoto);
</script>

<svelte:head><title>{$_('safeguarding.title')} · {$_('app.name')}</title></svelte:head>

<div class="min-h-full bg-slate-50 pb-16">
  <div class="mx-auto max-w-7xl px-4 py-6 sm:px-6">
    <header class="rounded-3xl bg-slate-950 px-5 py-5 text-white shadow-xl sm:px-7">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p class="text-xs font-black uppercase tracking-[0.22em] text-amber-300">{$_('safeguarding.mode')}</p>
          <h1 class="mt-1 text-2xl font-black sm:text-3xl">{$_('safeguarding.title')}</h1>
          <p class="mt-2 max-w-3xl text-sm leading-6 text-slate-300">{$_('safeguarding.subtitle')}</p>
        </div>
        {#if memberships.length > 1}
          <label class="text-xs font-bold text-slate-300">{$_('safeguarding.school')}
            <select class="mt-1 block rounded-xl border-white/20 bg-slate-900 px-3 py-2 text-white" value={membership?.membership_id} onchange={changeMembership}>
              {#each memberships as row}<option value={row.membership_id}>{row.school_name}</option>{/each}
            </select>
          </label>
        {/if}
      </div>
    </header>

    {#if error}<div class="mt-4 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm font-bold text-red-800" role="alert">{error}</div>{/if}
    {#if notice}<div class="mt-4 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm font-bold text-emerald-800" role="status">{notice}</div>{/if}

    {#if loading}
      <div class="grid min-h-64 place-items-center text-sm font-bold text-slate-500">{$_('common.loading')}</div>
    {:else if !context || !membership}
      <section class="mt-5 rounded-3xl border border-slate-200 bg-white p-8 text-center shadow-sm">
        <h2 class="text-xl font-black text-slate-900">{$_('safeguarding.noAccessTitle')}</h2>
        <p class="mt-2 text-sm text-slate-600">{$_('safeguarding.noAccessBody')}</p>
      </section>
    {:else}
      <section class="mt-5 grid gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm md:grid-cols-4" data-testid="safeguarding-context-banner">
        <div><span class="block text-xs font-bold uppercase text-amber-800">{$_('safeguarding.reviewer')}</span><strong>{context.reviewer.name}</strong></div>
        <div><span class="block text-xs font-bold uppercase text-amber-800">{$_('safeguarding.school')}</span><strong>{context.school.name}</strong></div>
        <div><span class="block text-xs font-bold uppercase text-amber-800">{$_('safeguarding.access')}</span><strong>{context.permissions.length} {$_('safeguarding.permissions')}</strong></div>
        <div><span class="block text-xs font-bold uppercase text-amber-800">{$_('safeguarding.audit')}</span><strong>{$_('safeguarding.audited')}</strong></div>
      </section>

      {#if !review && canReview}
        <section class="mt-5 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <div><h2 class="text-xl font-black text-slate-900">{$_('safeguarding.search.title')}</h2><p class="text-sm text-slate-500">{$_('safeguarding.search.metadataOnly')}</p></div>
            <button class="btn-hero rounded-xl px-5 py-2.5 text-sm" disabled={working} onclick={searchConversations}>{$_('safeguarding.search.action')}</button>
          </div>
          <div class="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <input class="form-input" placeholder={$_('safeguarding.search.reference')} bind:value={reference} />
            <input class="form-input" placeholder={$_('safeguarding.search.student')} bind:value={student} />
            <input class="form-input" placeholder={$_('safeguarding.search.participant')} bind:value={participant} />
            <select class="form-input" bind:value={participantRole}><option value="">{$_('safeguarding.search.role')}</option><option value="staff">Staff</option><option value="chh_guardian">CHH guardian</option><option value="fhh_parent">FHH parent</option></select>
            <input class="form-input" placeholder={$_('safeguarding.search.grade')} bind:value={grade} />
            <input class="form-input" type="number" min="1" placeholder={$_('safeguarding.search.branch')} bind:value={branch} />
            <input class="form-input" type="date" aria-label={$_('safeguarding.search.from')} bind:value={dateFrom} />
            <input class="form-input" type="date" aria-label={$_('safeguarding.search.to')} bind:value={dateTo} />
            <select class="form-input" bind:value={status}><option value="">{$_('safeguarding.search.anyStatus')}</option><option value="active">Active</option><option value="closed">Closed</option></select>
            <select class="form-input" bind:value={messageType}><option value="">{$_('safeguarding.search.anyType')}</option><option value="standard">Text</option><option value="photo">Photo</option><option value="voice_note">Voice</option></select>
            <select class="form-input" bind:value={direction}><option value="">{$_('safeguarding.search.anyDirection')}</option><option value="staff_to_family">Staff → family</option><option value="family_to_staff">Family → staff</option></select>
            <div class="flex flex-wrap gap-3 rounded-xl bg-slate-50 px-3 py-2 text-xs font-bold"><label><input type="checkbox" bind:checked={flagged} /> {$_('safeguarding.search.flagged')}</label><label><input type="checkbox" bind:checked={restricted} /> {$_('safeguarding.search.restricted')}</label><label><input type="checkbox" bind:checked={closed} /> {$_('safeguarding.search.closed')}</label></div>
          </div>

          <div class="mt-5 grid gap-3 lg:grid-cols-2">
            {#each results as row}
              <button type="button" class="rounded-2xl border p-4 text-start transition hover:border-amber-400 hover:bg-amber-50 {selected?.conversation_id === row.conversation_id ? 'border-amber-500 bg-amber-50' : 'border-slate-200 bg-white'}" onclick={() => chooseConversation(row)}>
                <div class="flex items-center justify-between gap-3"><strong class="font-mono text-sm">{row.reference}</strong><span class="rounded-full bg-slate-100 px-2 py-1 text-[0.65rem] font-black uppercase">{row.participant_state}</span></div>
                <p class="mt-2 font-black text-slate-900">{row.student?.display_name || $_('safeguarding.search.noStudent')}</p>
                <p class="mt-1 truncate text-xs text-slate-600">{row.participants.map((person) => `${person.display_name} · ${person.kind}`).join(' | ')}</p>
                <div class="mt-2 flex gap-2 text-[0.65rem] font-bold text-slate-500"><span>{formatDate(row.last_activity_at)}</span>{#if row.restricted}<span>• {$_('safeguarding.search.restricted')}</span>{/if}{#if row.flag_count}<span>• {row.flag_count} {$_('safeguarding.flags')}</span>{/if}</div>
              </button>
            {:else}
              <p class="col-span-full rounded-2xl bg-slate-50 p-8 text-center text-sm text-slate-500">{$_('safeguarding.search.empty')}</p>
            {/each}
          </div>
        </section>

        {#if selected}
          <section class="mt-5 rounded-3xl border border-amber-300 bg-white p-5 shadow-sm" data-testid="start-safeguarding-review">
            <h2 class="text-lg font-black">{$_('safeguarding.start.title')} · {selected.reference}</h2>
            <p class="mt-1 text-sm text-slate-600">{$_('safeguarding.start.body')}</p>
            <div class="mt-4 grid gap-3 md:grid-cols-[15rem_1fr]">
              <label class="text-xs font-bold">{$_('safeguarding.reasonCategory')}<select class="form-input mt-1 w-full" bind:value={reasonCategory}>{#each reasonCategories as value}<option {value}>{$_(`safeguarding.reasons.${value}`)}</option>{/each}</select></label>
              <label class="text-xs font-bold">{$_('safeguarding.justification')}<textarea class="form-input mt-1 min-h-24 w-full" minlength="8" maxlength="2000" bind:value={justification}></textarea></label>
            </div>
            <label class="mt-3 flex items-start gap-2 text-sm font-bold"><input class="mt-1" type="checkbox" bind:checked={acknowledgement} /> <span>{$_('safeguarding.start.acknowledgement')}</span></label>
            <button class="btn-hero mt-4 rounded-xl px-5 py-2.5 text-sm" disabled={working || !acknowledgement || justification.trim().length < 8} onclick={startReview}>{$_('safeguarding.start.action')}</button>
          </section>
        {/if}
      {:else}
        {@const activeReview = review!}
        <section class="mt-5 rounded-3xl border-2 border-amber-400 bg-white shadow-xl" data-testid="safeguarding-review-workspace">
          <div class="rounded-t-[1.35rem] bg-amber-400 p-4 text-slate-950">
            <div class="flex flex-wrap items-start justify-between gap-4">
              <div><p class="text-xs font-black uppercase tracking-[0.2em]">{$_('safeguarding.mode')}</p><h2 class="mt-1 text-xl font-black">{activeReview.conversation.reference}</h2><p class="mt-1 text-xs font-bold">{$_(`safeguarding.reasons.${activeReview.review.reason_category}`)} · {$_('safeguarding.expires')} {formatDate(activeReview.review.expires_at)}</p></div>
              <div class="flex gap-2"><button class="rounded-xl bg-slate-950 px-4 py-2 text-xs font-black text-white" disabled={working} onclick={() => void refreshReview()}>{$_('safeguarding.refresh')}</button><button class="rounded-xl bg-white px-4 py-2 text-xs font-black" disabled={working} onclick={endReview}>{$_('safeguarding.endReview')}</button></div>
            </div>
            <p class="mt-3 rounded-xl bg-white/60 px-3 py-2 text-xs font-bold">{$_('safeguarding.reviewAuditNotice')}</p>
          </div>

          <div class="grid gap-5 p-4 xl:grid-cols-[minmax(0,1.65fr)_minmax(20rem,0.85fr)]">
            <div class="min-w-0">
              <section class="rounded-2xl bg-slate-50 p-4">
                <h3 class="font-black">{$_('safeguarding.participants')}</h3>
                <div class="mt-3 grid gap-2 sm:grid-cols-2">
                  {#each activeReview.conversation.participants as person}
                    <div class="rounded-xl bg-white p-3 text-sm"><strong>{person.display_name}</strong><p class="text-xs text-slate-500">{person.kind} · {person.side} · D{person.receipt_cursor.delivered_sequence}/R{person.receipt_cursor.read_sequence}</p></div>
                  {/each}
                </div>
              </section>

              <section class="mt-4 space-y-3" aria-label={$_('safeguarding.timeline')}>
                {#each activeReview.messages as message}
                  <article class="rounded-2xl border p-4 {message.state === 'tombstoned' ? 'border-red-200 bg-red-50' : 'border-slate-200 bg-white'}">
                    <div class="flex flex-wrap items-center justify-between gap-2"><div><strong>{message.sender_display_name}</strong><span class="ms-2 text-xs text-slate-500">{message.sender_kind} · {message.sender_side}</span></div><time class="text-xs font-bold text-slate-500">#{message.sequence} · {formatDate(message.created_at)}</time></div>
                    {#if message.body}<p class="mt-3 whitespace-pre-wrap text-sm leading-6">{message.body}</p>{/if}
                    {#if message.photos.length}<div class="mt-3 grid grid-cols-3 gap-2 sm:grid-cols-5">{#each message.photos as photo, index}<ProtectedMessagePhoto load={() => safeguardingApi.photo(membership!, sessionId!, photo.id, 'thumbnail')} alt={$_('safeguarding.photoNumber', { values: { number: index + 1 } })} onclick={() => void openPhoto(photo.id, $_('safeguarding.photoNumber', { values: { number: index + 1 } }))} />{/each}</div>{/if}
                    {#if message.voice_note}<div class="mt-3 rounded-xl bg-slate-100 p-3"><ProtectedVoiceNote voice={message.voice_note} messageId={message.id} load={() => safeguardingApi.voice(membership!, sessionId!, message.voice_note!.id)} /></div>{/if}
                    <div class="mt-3 flex flex-wrap gap-2 text-[0.7rem] font-black uppercase"><span class="rounded-full bg-slate-100 px-2 py-1">{message.state}</span>{#each message.flags as flag}<span class="rounded-full bg-amber-100 px-2 py-1">{flag.category} · {flag.severity} · {flag.status}</span>{/each}</div>
                    {#if canModerate}<div class="mt-3 flex flex-wrap gap-2"><button class="btn-secondary rounded-lg px-3 py-1.5 text-xs" disabled={working || !confidentialReason.trim()} onclick={() => void addFlag(message.id)}>{$_('safeguarding.flagMessage')}</button>{#if message.state === 'active'}<button class="rounded-lg bg-red-700 px-3 py-1.5 text-xs font-bold text-white" disabled={working || confidentialReason.trim().length < 8} onclick={() => void changeMessage(message.id, 'tombstone')}>{$_('safeguarding.tombstone')}</button>{:else}<button class="btn-secondary rounded-lg px-3 py-1.5 text-xs" disabled={working || confidentialReason.trim().length < 8} onclick={() => void changeMessage(message.id, 'restore')}>{$_('safeguarding.restore')}</button>{/if}</div>{/if}
                  </article>
                {/each}
              </section>
            </div>

            <aside class="min-w-0 space-y-4">
              {#if canModerate}
                <section class="rounded-2xl border border-slate-200 p-4">
                  <h3 class="font-black">{$_('safeguarding.moderation')}</h3>
                  <label class="mt-3 block text-xs font-bold">{$_('safeguarding.reasonCategory')}<select class="form-input mt-1 w-full" bind:value={moderationReason}>{#each reasonCategories as value}<option {value}>{$_(`safeguarding.reasons.${value}`)}</option>{/each}</select></label>
                  <label class="mt-3 block text-xs font-bold">{$_('safeguarding.confidentialReason')}<textarea class="form-input mt-1 min-h-20 w-full" bind:value={confidentialReason}></textarea></label>
                  <label class="mt-3 block text-xs font-bold">{$_('safeguarding.safeReason')}<input class="form-input mt-1 w-full" maxlength="240" bind:value={participantSafeReason} /></label>
                  <div class="mt-3 grid grid-cols-2 gap-2"><select class="form-input" bind:value={restrictionType}><option value="family_replies">Family replies</option><option value="staff_replies">Staff replies</option><option value="both_replies">Both sides</option><option value="read_only">Read only</option></select><label class="flex items-center gap-2 text-xs font-bold"><input type="checkbox" bind:checked={reopeningRequiresApproval} /> {$_('safeguarding.approval')}</label></div>
                  <div class="mt-3 grid grid-cols-2 gap-2"><button class="btn-secondary rounded-xl p-2 text-xs" disabled={working || confidentialReason.trim().length < 8} onclick={() => void runModeration('restrict')}>{$_('safeguarding.applyRestriction')}</button><button class="btn-secondary rounded-xl p-2 text-xs" disabled={working || confidentialReason.trim().length < 8} onclick={() => void runModeration('unrestrict')}>{$_('safeguarding.removeRestriction')}</button><button class="rounded-xl bg-red-700 p-2 text-xs font-bold text-white" disabled={working || confidentialReason.trim().length < 8} onclick={() => void runModeration('close')}>{$_('safeguarding.close')}</button><button class="btn-secondary rounded-xl p-2 text-xs" disabled={working || confidentialReason.trim().length < 8} onclick={() => void runModeration('reopen')}>{$_('safeguarding.reopen')}</button></div>
                  <div class="mt-4 grid grid-cols-2 gap-2"><input class="form-input" placeholder={$_('safeguarding.flagCategory')} bind:value={flagCategory} /><select class="form-input" bind:value={flagSeverity}><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="critical">Critical</option></select></div>
                  <button class="btn-secondary mt-2 w-full rounded-xl p-2 text-xs" disabled={working} onclick={() => void addFlag()}>{$_('safeguarding.flagConversation')}</button>
                </section>

                <section class="rounded-2xl border border-slate-200 p-4"><h3 class="font-black">{$_('safeguarding.internalNotes')}</h3><p class="mt-1 text-xs text-slate-500">{$_('safeguarding.internalOnly')}</p><textarea class="form-input mt-3 min-h-24 w-full" bind:value={noteBody}></textarea><button class="btn-secondary mt-2 rounded-xl px-4 py-2 text-xs" disabled={working || noteBody.trim().length < 3} onclick={addNote}>{$_('safeguarding.addNote')}</button><div class="mt-3 space-y-2">{#each activeReview.internal_notes as note}<div class="rounded-xl bg-amber-50 p-3 text-xs"><p class="whitespace-pre-wrap">{note.body}</p><p class="mt-1 font-bold text-amber-800">{formatDate(note.created_at)} · #{note.author_membership_id}</p></div>{/each}</div></section>
              {/if}

              {#if canExport}
                <section class="rounded-2xl border border-slate-200 p-4"><h3 class="font-black">{$_('safeguarding.export.title')}</h3><select class="form-input mt-3 w-full" bind:value={exportReason}>{#each reasonCategories as value}<option {value}>{$_(`safeguarding.reasons.${value}`)}</option>{/each}</select><textarea class="form-input mt-2 min-h-20 w-full" placeholder={$_('safeguarding.justification')} bind:value={exportJustification}></textarea>{#if activeReview.permissions.includes('messaging.export_internal_notes')}<label class="mt-2 flex gap-2 text-xs font-bold"><input type="checkbox" bind:checked={includeInternalNotes} /> {$_('safeguarding.export.includeNotes')}</label>{/if}<button class="btn-secondary mt-3 rounded-xl px-4 py-2 text-xs" disabled={working || exportJustification.trim().length < 8} onclick={createExport}>{$_('safeguarding.export.create')}</button><div class="mt-3 space-y-2">{#each activeReview.exports as item}<button class="w-full rounded-xl bg-slate-50 p-3 text-start text-xs" disabled={item.state !== 'ready'} onclick={() => void downloadExport(item.id)}><strong>{item.mode} · {item.state}</strong><span class="block text-slate-500">SHA-256 {item.artifact_sha256?.slice(0, 16)}… · {item.download_count}/{item.max_downloads}</span></button>{/each}</div></section>
              {/if}

              <details class="rounded-2xl border border-slate-200 p-4"><summary class="cursor-pointer font-black">{$_('safeguarding.auditHistory')}</summary><div class="mt-3 max-h-72 space-y-2 overflow-auto">{#each activeReview.audit_history as item}<div class="rounded-xl bg-slate-50 p-2 text-xs"><strong>{String(item.action)}</strong><p class="text-slate-500">{formatDate(String(item.occurred_at))} · {String(item.event_id)}</p></div>{/each}</div></details>
              <details class="rounded-2xl border border-slate-200 p-4"><summary class="cursor-pointer font-black">{$_('safeguarding.moderationHistory')}</summary><div class="mt-3 max-h-72 space-y-2 overflow-auto">{#each activeReview.moderation_history as item}<div class="rounded-xl bg-slate-50 p-2 text-xs"><strong>{String(item.action)}</strong><p class="text-slate-500">{formatDate(String(item.occurred_at))}</p></div>{/each}</div></details>
            </aside>
          </div>
        </section>
      {/if}

      {#if canManage && permissions && !review}
        <section class="mt-5 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm"><h2 class="text-lg font-black">{$_('safeguarding.permissionAdmin')}</h2><p class="mt-1 text-sm text-slate-500">{$_('safeguarding.permissionAdminBody')}</p><div class="mt-4 grid gap-2 md:grid-cols-[1fr_1.4fr_1.5fr_auto]"><select class="form-input" bind:value={grantMembershipId}><option value="">{$_('safeguarding.selectStaff')}</option>{#each permissions.memberships as row}<option value={row.membership_id}>{row.name} · {row.role}</option>{/each}</select><select class="form-input" bind:value={grantPermission}>{#each permissionNames as value}<option {value}>{value}</option>{/each}</select><input class="form-input" placeholder={$_('safeguarding.permissionReason')} bind:value={grantReason} /><button class="btn-secondary rounded-xl px-4 py-2 text-xs" disabled={working || !grantMembershipId || grantReason.trim().length < 3} onclick={createGrant}>{$_('safeguarding.grant')}</button></div><div class="mt-4 grid gap-3 lg:grid-cols-2">{#each permissions.memberships as row}{#if row.permissions.length}<div class="rounded-2xl bg-slate-50 p-3"><strong>{row.name}</strong><p class="text-xs text-slate-500">{row.role}</p>{#each row.permissions as grant}<div class="mt-2 flex items-center justify-between gap-2 rounded-xl bg-white p-2 text-xs"><span class="min-w-0 break-all">{grant.permission}</span><button class="font-bold text-red-700" onclick={() => void revokeGrant(grant.id)}>{$_('safeguarding.revoke')}</button></div>{/each}</div>{/if}{/each}</div></section>
      {/if}
    {/if}
  </div>
</div>

{#if fullPhotoUrl}
  <div class="fixed inset-0 z-[120] grid place-items-center bg-slate-950/90 p-4" role="dialog" aria-modal="true" aria-label={fullPhotoAlt}><button class="absolute inset-0" aria-label={$_('safeguarding.closePhoto')} onclick={closePhoto}></button><img class="relative max-h-[90vh] max-w-full rounded-2xl object-contain" src={fullPhotoUrl} alt={fullPhotoAlt} /><button class="absolute end-4 top-[calc(1rem+var(--safe-top))] rounded-full bg-white px-4 py-2 text-sm font-black" onclick={closePhoto}>{$_('safeguarding.closePhoto')}</button></div>
{/if}

<style>
  .form-input { border: 1px solid rgb(203 213 225); border-radius: .75rem; background: white; padding: .65rem .8rem; color: rgb(15 23 42); font-size: .8rem; }
  .form-input:focus { border-color: rgb(245 158 11); outline: 2px solid rgb(254 243 199); outline-offset: 1px; }
</style>
