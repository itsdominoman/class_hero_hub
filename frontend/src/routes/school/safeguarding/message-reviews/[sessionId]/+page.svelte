<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { _ , locale } from 'svelte-i18n';
  import { AlertTriangle, Clock3, RefreshCw, ShieldAlert, X } from 'lucide-svelte';
  import { api } from '$lib/api';
  import ProtectedMessagePhoto from '$lib/components/messaging/ProtectedMessagePhoto.svelte';
  import ProtectedVoiceNote from '$lib/components/messaging/ProtectedVoiceNote.svelte';
  import {
    findEligibleSafeguardingMemberships,
    membershipHref,
    requestedMembershipId
  } from '$lib/safeguarding/context';
  import {
    conversationKindLabelKey,
    flagStatusLabelKey,
    friendlyTechnicalLabel,
    isMeaningfulJustification,
    restrictionLabelKey,
    roleLabelKey,
    severityLabelKey,
    stateLabelKey
  } from '$lib/safeguarding/presentation';
  import { safeguardingApi } from '$lib/safeguarding/api';
  import type { SafeguardingMembership, SafeguardingReview } from '$lib/safeguarding/types';
  import type { SessionUser } from '$lib/roleRouting';

  type ConfirmAction = 'restrict' | 'unrestrict' | 'close' | 'reopen' | 'tombstone' | 'restore' | 'export';

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

  let loading = $state(true);
  let working = $state(false);
  let error = $state<string | null>(null);
  let notice = $state<string | null>(null);
  let membership = $state<SafeguardingMembership | null>(null);
  let review = $state<SafeguardingReview | null>(null);
  let fullPhotoUrl = $state<string | null>(null);
  let fullPhotoAlt = $state('');
  let pendingAction = $state<{ action: ConfirmAction; messageId?: string } | null>(null);
  let now = $state(Date.now());
  let clockTimer: ReturnType<typeof setInterval> | null = null;

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

  let canModerate = $derived(Boolean(review?.capabilities.can_moderate));
  let canExport = $derived(Boolean(review?.capabilities.can_export));
  let sessionId = $derived($page.params.sessionId || '');
  let moderationReasonValid = $derived(isMeaningfulJustification(confidentialReason, 8));
  let exportReasonValid = $derived(isMeaningfulJustification(exportJustification, 15));

  function messageForFailure(value: unknown) {
    return value instanceof Error ? value.message : $_('safeguarding.errors.failed');
  }

  function formatDate(value: string) {
    return new Intl.DateTimeFormat($locale || undefined, {
      dateStyle: 'medium',
      timeStyle: 'short'
    }).format(new Date(value));
  }

  function localizedName(option: { name: string; name_ar?: string | null } | null | undefined) {
    if (!option) return '';
    return $locale === 'ar' && option.name_ar ? option.name_ar : option.name;
  }

  function remainingLabel(expiresAt: string) {
    const seconds = Math.max(0, Math.floor((new Date(expiresAt).getTime() - now) / 1000));
    if (!seconds) return $_('safeguarding.active.expired');
    const minutes = Math.floor(seconds / 60);
    return `${minutes}:${String(seconds % 60).padStart(2, '0')}`;
  }

  function conversationTitle(activeReview: SafeguardingReview) {
    return activeReview.conversation.student?.display_name || $_('safeguarding.search.staffConversation');
  }

  function participantRole(person: SafeguardingReview['conversation']['participants'][number]) {
    return $_(roleLabelKey(person.role || person.kind));
  }

  async function initialize() {
    loading = true;
    error = null;
    try {
      const user = (await api.get('/me')) as SessionUser;
      const eligible = await findEligibleSafeguardingMemberships(user);
      const requested = requestedMembershipId(new URL(window.location.href));
      const chosen = eligible.find((row) => row.membership.membership_id === requested);
      if (!chosen || !chosen.context.permissions.includes('messaging.safeguarding_review')) return;
      membership = chosen.membership;
      await refreshReview();
    } catch (value) {
      error = messageForFailure(value);
    } finally {
      loading = false;
    }
  }

  async function refreshReview() {
    if (!membership) return;
    review = await safeguardingApi.review(membership, sessionId);
  }

  async function endReview() {
    if (!membership) return;
    working = true;
    error = null;
    try {
      await safeguardingApi.endReview(membership, sessionId);
      closePhoto();
      await goto(membershipHref('/school/safeguarding/message-reviews', membership), {
        replaceState: true
      });
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

  function requestModeration(action: ConfirmAction, messageId?: string) {
    if (action === 'export') {
      if (!exportReasonValid) {
        error = $_('safeguarding.active.exportReasonError');
        return;
      }
    } else if (!moderationReasonValid) {
      error = $_('safeguarding.active.moderationReasonError');
      return;
    }
    error = null;
    pendingAction = { action, messageId };
  }

  async function confirmAction() {
    if (!pendingAction || !membership) return;
    const { action, messageId } = pendingAction;
    pendingAction = null;
    working = true;
    error = null;
    try {
      if (action === 'restrict') {
        await safeguardingApi.restriction(membership, sessionId, {
          ...moderationPayload(),
          restriction_type: restrictionType,
          reopening_requires_approval: reopeningRequiresApproval
        });
      } else if (action === 'unrestrict') {
        await safeguardingApi.removeRestriction(membership, sessionId, moderationPayload());
      } else if (action === 'close') {
        await safeguardingApi.close(membership, sessionId, {
          ...moderationPayload(),
          reopening_requires_approval: reopeningRequiresApproval
        });
      } else if (action === 'reopen') {
        await safeguardingApi.reopen(membership, sessionId, {
          ...moderationPayload(),
          remove_existing_restriction: false
        });
      } else if (action === 'tombstone' && messageId) {
        await safeguardingApi.tombstone(membership, sessionId, messageId, moderationPayload());
      } else if (action === 'restore' && messageId) {
        await safeguardingApi.restore(membership, sessionId, messageId, moderationPayload());
      } else if (action === 'export') {
        const created = (await safeguardingApi.export(membership, sessionId, {
          export_mode: 'internal',
          reason_category: exportReason,
          justification: exportJustification,
          include_internal_notes: includeInternalNotes
        })) as { id: string };
        exportJustification = '';
        await refreshReview();
        await downloadExport(created.id);
        return;
      }
      confidentialReason = '';
      participantSafeReason = '';
      notice = $_('safeguarding.notices.moderationSaved');
      await refreshReview();
    } catch (value) {
      error = messageForFailure(value);
    } finally {
      working = false;
    }
  }

  async function addNote() {
    if (!membership || noteBody.trim().length < 3) return;
    working = true;
    error = null;
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
    if (!membership || flagCategory.trim().length < 3) return;
    working = true;
    error = null;
    try {
      await safeguardingApi.addFlag(membership, sessionId, {
        message_id: messageId,
        category: flagCategory,
        severity: flagSeverity,
        internal_note: confidentialReason || null
      });
      confidentialReason = '';
      await refreshReview();
    } catch (value) {
      error = messageForFailure(value);
    } finally {
      working = false;
    }
  }

  async function downloadExport(id: string) {
    if (!membership) return;
    try {
      const blob = await safeguardingApi.downloadExport(membership, id);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `chh-message-evidence-${id.slice(0, 8)}.zip`;
      link.click();
      URL.revokeObjectURL(url);
      await refreshReview();
    } catch (value) {
      error = messageForFailure(value);
    }
  }

  async function openPhoto(mediaId: string, alt: string) {
    if (!membership) return;
    closePhoto();
    try {
      const blob = await safeguardingApi.photo(membership, sessionId, mediaId, 'full');
      if (!blob.type.startsWith('image/')) throw new Error($_('safeguarding.errors.failed'));
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

  function handleKeydown(event: KeyboardEvent) {
    if (event.key !== 'Escape') return;
    if (fullPhotoUrl) closePhoto();
    else if (pendingAction) pendingAction = null;
  }

  function handleNativeBack(event: Event) {
    if (!fullPhotoUrl && !pendingAction) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    if (fullPhotoUrl) closePhoto();
    else pendingAction = null;
  }

  onMount(() => {
    void initialize();
    clockTimer = setInterval(() => (now = Date.now()), 1000);
    window.addEventListener('keydown', handleKeydown);
    window.addEventListener('chh:native-back', handleNativeBack, { capture: true });
    return () => {
      if (clockTimer) clearInterval(clockTimer);
      closePhoto();
      window.removeEventListener('keydown', handleKeydown);
      window.removeEventListener('chh:native-back', handleNativeBack, { capture: true });
    };
  });
</script>

<svelte:head><title>{$_('safeguarding.active.title')} · {$_('app.name')}</title></svelte:head>

<div class="min-h-full min-w-0 bg-slate-50 pb-12">
  {#if error}<div class="mx-auto mt-3 w-[calc(100%-1.5rem)] max-w-6xl rounded-xl border border-red-200 bg-red-50 p-3 text-sm font-bold text-red-800" role="alert">{error}</div>{/if}
  {#if notice}<div class="mx-auto mt-3 w-[calc(100%-1.5rem)] max-w-6xl rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm font-bold text-emerald-800" role="status">{notice}</div>{/if}

  {#if loading}
    <div class="grid min-h-64 place-items-center text-sm font-bold text-slate-500">{$_('common.loading')}</div>
  {:else if !membership || !review}
    <section class="mx-auto mt-4 w-[calc(100%-1.5rem)] max-w-3xl rounded-2xl border border-slate-200 bg-white p-8 text-center"><h1 class="text-xl font-black">{$_('safeguarding.noAccessTitle')}</h1><p class="mt-2 text-sm text-slate-600">{$_('safeguarding.active.unavailable')}</p></section>
  {:else}
    {@const activeReview = review}
    <div class="review-banner sticky z-40 border-y border-amber-500 bg-amber-300 shadow-md" data-testid="safeguarding-review-mode-banner">
      <div class="mx-auto flex min-w-0 max-w-6xl flex-wrap items-center justify-between gap-3 px-3 py-2.5 sm:px-6">
        <div class="flex min-w-0 items-center gap-2"><ShieldAlert class="h-5 w-5 shrink-0" aria-hidden="true" /><div class="min-w-0"><strong class="block text-sm font-black text-slate-950">{$_('safeguarding.mode')}</strong><span class="block break-words text-xs font-bold text-slate-800">{conversationTitle(activeReview)}</span></div></div>
        <div class="flex min-w-0 flex-wrap items-center gap-2"><span class="inline-flex items-center gap-1 rounded-full bg-white/80 px-2.5 py-1 text-xs font-black text-slate-900"><Clock3 class="h-4 w-4" aria-hidden="true" />{remainingLabel(activeReview.review.expires_at)}</span><button class="compact-action" type="button" disabled={working} aria-label={$_('safeguarding.refresh')} onclick={() => void refreshReview()}><RefreshCw class="h-4 w-4" aria-hidden="true" /><span class="hidden sm:inline">{$_('safeguarding.refresh')}</span></button><button class="compact-action bg-slate-950 text-white" type="button" disabled={working} onclick={endReview}>{$_('safeguarding.endReview')}</button></div>
      </div>
    </div>

    <main class="mx-auto w-full min-w-0 max-w-6xl px-3 py-4 sm:px-6" data-testid="safeguarding-review-workspace">
      <a class="mb-3 inline-flex min-h-10 items-center text-sm font-bold text-amber-800" href={membershipHref('/school/safeguarding/message-reviews', membership)}>← {$_('safeguarding.active.backToSearch')}</a>

      <section class="context-card">
        <div class="grid min-w-0 gap-3 md:grid-cols-[1.2fr_1fr]">
          <div class="min-w-0"><h1 class="break-words text-xl font-black text-slate-950">{conversationTitle(activeReview)}</h1><p class="mt-1 text-sm font-bold text-slate-600">{$_(conversationKindLabelKey(activeReview.conversation.kind))}</p>{#if activeReview.conversation.school_context}<p class="mt-2 break-words text-sm text-slate-600">{localizedName(activeReview.conversation.school_context.class_section)} · {localizedName(activeReview.conversation.school_context.grade_level)}{#if activeReview.conversation.branch} · {localizedName(activeReview.conversation.branch)}{/if}</p>{/if}</div>
          <div class="min-w-0 rounded-xl bg-amber-50 p-3 text-sm"><strong class="block text-xs uppercase tracking-wide text-amber-900">{$_('safeguarding.active.reviewReason')}</strong><span class="mt-1 block font-bold text-slate-900">{$_(`safeguarding.reasons.${activeReview.review.reason_category}`)}</span><span class="mt-1 block break-words text-xs leading-5 text-slate-600">{activeReview.review.justification}</span></div>
        </div>
        <div class="mt-4 grid min-w-0 gap-2 sm:grid-cols-2 lg:grid-cols-3">{#each activeReview.conversation.participants as person}<div class="min-w-0 rounded-xl border border-slate-200 bg-white p-3"><strong class="block break-words text-sm text-slate-950">{person.display_name}</strong><span class="mt-0.5 block text-xs text-slate-500">{participantRole(person)}</span></div>{/each}</div>
        <div class="mt-3 flex min-w-0 flex-wrap gap-2 text-xs"><span class="badge">{$_(stateLabelKey(activeReview.conversation.status))}</span>{#if activeReview.conversation.restriction_type}<span class="badge badge-amber">{$_(restrictionLabelKey(activeReview.conversation.restriction_type))}</span>{/if}<span class="text-slate-500">{$_('safeguarding.expires')} {formatDate(activeReview.review.expires_at)}</span></div>
        <details class="mt-3 text-xs text-slate-500"><summary class="cursor-pointer font-bold">{$_('safeguarding.search.details')}</summary><p class="mt-1 break-all">{$_('safeguarding.search.conversationId')}: {activeReview.conversation.reference}</p></details>
      </section>

      <p class="mt-3 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs font-bold leading-5 text-amber-950">{$_('safeguarding.reviewAuditNotice')}</p>

      <div class="mt-4 grid min-w-0 gap-4 xl:grid-cols-[minmax(0,1.6fr)_minmax(18rem,.85fr)]">
        <section class="min-w-0" aria-label={$_('safeguarding.timeline')}>
          <h2 class="mb-3 text-lg font-black text-slate-950">{$_('safeguarding.timeline')}</h2>
          <div class="min-w-0 space-y-3">
            {#each activeReview.messages as message}
              <article class:staff-message={message.sender_side === 'staff'} class:tombstoned-message={message.state === 'tombstoned'} class="message-bubble">
                <div class="flex min-w-0 flex-wrap items-start justify-between gap-2"><div class="min-w-0"><strong class="block break-words text-sm text-slate-950">{message.sender_display_name}</strong><span class="text-xs text-slate-500">{$_(roleLabelKey(message.sender_role || message.sender_kind))}</span></div><time class="shrink-0 text-xs font-bold text-slate-500">{formatDate(message.created_at)}</time></div>
                {#if message.body}<p class="mt-3 whitespace-pre-wrap break-words text-sm leading-6 text-slate-800">{message.body}</p>{/if}
                {#if message.photos.length}<div class="mt-3 grid min-w-0 grid-cols-3 gap-2 sm:grid-cols-5">{#each message.photos as photo, index}<ProtectedMessagePhoto load={() => safeguardingApi.photo(membership!, sessionId, photo.id, 'thumbnail')} alt={$_('safeguarding.photoNumber', { values: { number: index + 1 } })} onclick={() => void openPhoto(photo.id, $_('safeguarding.photoNumber', { values: { number: index + 1 } }))} />{/each}</div>{/if}
                {#if message.voice_note}<div class="mt-3 min-w-0 rounded-xl bg-slate-100 p-3"><ProtectedVoiceNote voice={message.voice_note} messageId={message.id} load={() => safeguardingApi.voice(membership!, sessionId, message.voice_note!.id)} /></div>{/if}
                <div class="mt-3 flex min-w-0 flex-wrap gap-1.5"><span class="badge">{$_(stateLabelKey(message.state))}</span>{#each message.flags as flag}<span class="badge badge-amber">{friendlyTechnicalLabel(flag.category)} · {$_(severityLabelKey(flag.severity))} · {$_(flagStatusLabelKey(flag.status))}</span>{/each}</div>
                {#if canModerate}<div class="mt-3 flex min-w-0 flex-wrap gap-2"><button class="small-action" type="button" disabled={working || flagCategory.trim().length < 3} onclick={() => void addFlag(message.id)}>{$_('safeguarding.flagMessage')}</button>{#if message.state === 'active'}<button class="small-danger" type="button" disabled={working} onclick={() => requestModeration('tombstone', message.id)}>{$_('safeguarding.tombstone')}</button>{:else}<button class="small-action" type="button" disabled={working} onclick={() => requestModeration('restore', message.id)}>{$_('safeguarding.restore')}</button>{/if}</div>{/if}
              </article>
            {:else}<p class="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">{$_('safeguarding.active.noMessages')}</p>{/each}
          </div>
        </section>

        <aside class="min-w-0 space-y-3" aria-label={$_('safeguarding.active.tools')}>
          {#if canModerate}
            <details class="tool-panel"><summary>{$_('safeguarding.active.conversationActions')}</summary><div class="tool-body"><label class="field-label"><span>{$_('safeguarding.reasonCategory')}</span><select class="field" bind:value={moderationReason}>{#each reasonCategories as value}<option {value}>{$_(`safeguarding.reasons.${value}`)}</option>{/each}</select></label><label class="field-label mt-3"><span>{$_('safeguarding.confidentialReason')}</span><textarea class="field min-h-24 resize-y" bind:value={confidentialReason}></textarea><small class="help-text">{$_('safeguarding.active.moderationHelp')}</small></label><label class="field-label mt-3"><span>{$_('safeguarding.safeReason')}</span><input class="field" maxlength="240" bind:value={participantSafeReason} /></label><label class="field-label mt-3"><span>{$_('safeguarding.active.restrictionType')}</span><select class="field" bind:value={restrictionType}><option value="family_replies">{$_('safeguarding.restrictions.family_replies')}</option><option value="staff_replies">{$_('safeguarding.restrictions.staff_replies')}</option><option value="both_replies">{$_('safeguarding.restrictions.both_replies')}</option><option value="read_only">{$_('safeguarding.restrictions.read_only')}</option></select></label><label class="mt-3 flex min-w-0 items-start gap-2 text-xs font-bold"><input class="mt-0.5 h-5 w-5 shrink-0" type="checkbox" bind:checked={reopeningRequiresApproval} /><span>{$_('safeguarding.approval')}</span></label><div class="mt-4 grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2"><button class="small-action" type="button" disabled={working} onclick={() => requestModeration('restrict')}>{$_('safeguarding.applyRestriction')}</button><button class="small-action" type="button" disabled={working} onclick={() => requestModeration('unrestrict')}>{$_('safeguarding.removeRestriction')}</button><button class="small-danger" type="button" disabled={working} onclick={() => requestModeration('close')}>{$_('safeguarding.close')}</button><button class="small-action" type="button" disabled={working} onclick={() => requestModeration('reopen')}>{$_('safeguarding.reopen')}</button></div></div></details>

            <details class="tool-panel"><summary>{$_('safeguarding.active.flags')}</summary><div class="tool-body"><label class="field-label"><span>{$_('safeguarding.flagCategory')}</span><input class="field" bind:value={flagCategory} /></label><label class="field-label mt-3"><span>{$_('safeguarding.active.severity')}</span><select class="field" bind:value={flagSeverity}><option value="low">{$_('safeguarding.severities.low')}</option><option value="medium">{$_('safeguarding.severities.medium')}</option><option value="high">{$_('safeguarding.severities.high')}</option><option value="critical">{$_('safeguarding.severities.critical')}</option></select></label><button class="small-action mt-3 w-full" type="button" disabled={working || flagCategory.trim().length < 3} onclick={() => void addFlag()}>{$_('safeguarding.flagConversation')}</button>{#if activeReview.conversation_flags.length}<div class="mt-3 space-y-2">{#each activeReview.conversation_flags as flag}<div class="rounded-xl bg-amber-50 p-3 text-xs"><strong>{friendlyTechnicalLabel(flag.category)}</strong><span class="mt-1 block text-slate-600">{$_(severityLabelKey(flag.severity))} · {$_(flagStatusLabelKey(flag.status))}</span></div>{/each}</div>{/if}</div></details>

            <details class="tool-panel"><summary>{$_('safeguarding.internalNotes')}</summary><div class="tool-body"><p class="text-xs leading-5 text-slate-500">{$_('safeguarding.internalOnly')}</p><textarea class="field mt-3 min-h-24 resize-y" bind:value={noteBody} aria-label={$_('safeguarding.internalNotes')}></textarea><button class="small-action mt-2" type="button" disabled={working || noteBody.trim().length < 3} onclick={addNote}>{$_('safeguarding.addNote')}</button><div class="mt-3 space-y-2">{#each activeReview.internal_notes as note}<div class="rounded-xl bg-amber-50 p-3 text-xs"><p class="whitespace-pre-wrap break-words leading-5">{note.body}</p><time class="mt-1 block font-bold text-amber-800">{formatDate(note.created_at)}</time></div>{/each}</div></div></details>
          {/if}

          {#if canExport}
            <details class="tool-panel"><summary>{$_('safeguarding.export.title')}</summary><div class="tool-body"><label class="field-label"><span>{$_('safeguarding.reasonCategory')}</span><select class="field" bind:value={exportReason}>{#each reasonCategories as value}<option {value}>{$_(`safeguarding.reasons.${value}`)}</option>{/each}</select></label><label class="field-label mt-3"><span>{$_('safeguarding.justification')}</span><textarea class="field min-h-24 resize-y" bind:value={exportJustification}></textarea></label>{#if activeReview.permissions.includes('messaging.export_internal_notes')}<label class="mt-3 flex min-w-0 items-start gap-2 text-xs font-bold"><input class="mt-0.5 h-5 w-5 shrink-0" type="checkbox" bind:checked={includeInternalNotes} /><span>{$_('safeguarding.export.includeNotes')}</span></label>{/if}<button class="small-action mt-3 w-full" type="button" disabled={working} onclick={() => requestModeration('export')}>{$_('safeguarding.export.create')}</button><div class="mt-3 space-y-2">{#each activeReview.exports as item}<button class="w-full min-w-0 rounded-xl bg-slate-50 p-3 text-start text-xs" type="button" disabled={item.state !== 'ready'} onclick={() => void downloadExport(item.id)}><strong class="block break-words">{$_('safeguarding.active.evidencePackage')} · {friendlyTechnicalLabel(item.state)}</strong>{#if item.artifact_sha256}<span class="mt-1 block break-all text-slate-500">SHA-256 {item.artifact_sha256.slice(0, 16)}…</span>{/if}</button>{/each}</div></div></details>
          {/if}

          <details class="tool-panel"><summary>{$_('safeguarding.auditHistory')}</summary><div class="tool-body max-h-80 overflow-y-auto">{#each activeReview.audit_history as item}<div class="mb-2 min-w-0 rounded-xl bg-slate-50 p-2 text-xs"><strong class="block break-words">{friendlyTechnicalLabel(item.action)}</strong><time class="mt-1 block text-slate-500">{formatDate(String(item.occurred_at))}</time></div>{/each}</div></details>
          <details class="tool-panel"><summary>{$_('safeguarding.moderationHistory')}</summary><div class="tool-body max-h-80 overflow-y-auto">{#each activeReview.moderation_history as item}<div class="mb-2 min-w-0 rounded-xl bg-slate-50 p-2 text-xs"><strong class="block break-words">{friendlyTechnicalLabel(item.action)}</strong><time class="mt-1 block text-slate-500">{formatDate(String(item.occurred_at))}</time></div>{/each}</div></details>
        </aside>
      </div>
    </main>
  {/if}
</div>

{#if pendingAction}
  <div class="modal-backdrop" role="presentation"><button class="absolute inset-0 h-full w-full" type="button" aria-label={$_('common.cancel')} onclick={() => (pendingAction = null)}></button><div class="confirm-card" role="alertdialog" aria-modal="true" aria-labelledby="confirm-action-title"><AlertTriangle class="h-8 w-8 text-red-700" aria-hidden="true" /><h2 id="confirm-action-title" class="mt-3 text-lg font-black text-slate-950">{$_(`safeguarding.confirm.${pendingAction.action}Title`)}</h2><p class="mt-2 text-sm leading-6 text-slate-600">{$_(`safeguarding.confirm.${pendingAction.action}Body`)}</p><div class="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end"><button class="btn-secondary w-full sm:w-auto" type="button" onclick={() => (pendingAction = null)}>{$_('common.cancel')}</button><button class="small-danger w-full sm:w-auto" type="button" disabled={working} onclick={confirmAction}>{$_('safeguarding.confirm.action')}</button></div></div></div>
{/if}

{#if fullPhotoUrl}
  <div class="fixed inset-0 z-[130] grid min-w-0 place-items-center bg-slate-950/90 p-4" role="dialog" aria-modal="true" aria-label={fullPhotoAlt}><button class="absolute inset-0 h-full w-full" type="button" aria-label={$_('safeguarding.closePhoto')} onclick={closePhoto}></button><img class="relative max-h-[90dvh] max-w-full rounded-2xl object-contain" src={fullPhotoUrl} alt={fullPhotoAlt} /><button class="absolute end-4 top-[calc(1rem+var(--safe-top))] rounded-full bg-white px-4 py-2 text-sm font-black" type="button" onclick={closePhoto}>{$_('safeguarding.closePhoto')}</button></div>
{/if}

<style>
  .review-banner { top: calc(5rem + var(--safe-top)); }
  :global(.native-app) .review-banner { top: 0; }
  .compact-action { display: inline-flex; min-height: 2.25rem; align-items: center; justify-content: center; gap: .35rem; border-radius: .65rem; background: rgb(255 255 255 / .8); padding: .4rem .65rem; font-size: .75rem; font-weight: 900; }
  .context-card { min-width: 0; max-width: 100%; overflow: hidden; border: 1px solid rgb(226 232 240); border-radius: 1rem; background: white; padding: 1rem; box-shadow: 0 1px 2px rgb(15 23 42 / .05); }
  .message-bubble { width: min(92%, 42rem); min-width: 0; max-width: 100%; overflow: hidden; border: 1px solid rgb(226 232 240); border-radius: 1rem 1rem 1rem .35rem; background: white; padding: 1rem; box-shadow: 0 1px 2px rgb(15 23 42 / .05); }
  .staff-message { margin-inline-start: auto; border-radius: 1rem 1rem .35rem 1rem; background: rgb(255 251 235); border-color: rgb(253 230 138); }
  .tombstoned-message { border-color: rgb(254 202 202); background: rgb(254 242 242); }
  .badge { border-radius: 999px; background: rgb(241 245 249); padding: .3rem .55rem; font-size: .7rem; font-weight: 800; color: rgb(51 65 85); }
  .badge-amber { background: rgb(254 243 199); color: rgb(146 64 14); }
  .small-action, .small-danger { display: inline-flex; min-height: 2.5rem; min-width: 0; align-items: center; justify-content: center; border-radius: .7rem; padding: .55rem .75rem; font-size: .75rem; font-weight: 900; }
  .small-action { border: 1px solid rgb(203 213 225); background: white; color: rgb(30 41 59); }
  .small-danger { background: rgb(185 28 28); color: white; }
  .tool-panel { min-width: 0; max-width: 100%; overflow: hidden; border: 1px solid rgb(226 232 240); border-radius: 1rem; background: white; }
  .tool-panel > summary { cursor: pointer; padding: .9rem 1rem; font-size: .875rem; font-weight: 900; color: rgb(15 23 42); }
  .tool-body { min-width: 0; border-top: 1px solid rgb(241 245 249); padding: 1rem; }
  .field-label { display: block; min-width: 0; font-size: .75rem; font-weight: 700; color: rgb(51 65 85); }
  .field-label > span:first-child { display: block; margin-bottom: .35rem; }
  .field { width: 100%; max-width: 100%; min-width: 0; border: 1px solid rgb(203 213 225); border-radius: .75rem; background: white; padding: .7rem .8rem; color: rgb(15 23 42); font-weight: 400; }
  .field:focus { border-color: rgb(245 158 11); outline: 2px solid rgb(254 243 199); outline-offset: 1px; }
  .help-text { margin-top: .35rem; display: block; font-size: .7rem; font-weight: 400; line-height: 1.15rem; color: rgb(100 116 139); }
  .modal-backdrop { position: fixed; inset: 0; z-index: 125; display: grid; min-width: 0; place-items: center; overflow-y: auto; background: rgb(15 23 42 / .72); padding: calc(1rem + var(--safe-top)) 1rem calc(1rem + var(--safe-bottom)); }
  .confirm-card { position: relative; width: 100%; max-width: 28rem; min-width: 0; overflow: hidden; border-radius: 1rem; background: white; padding: 1.25rem; box-shadow: 0 20px 50px rgb(15 23 42 / .35); }
</style>
