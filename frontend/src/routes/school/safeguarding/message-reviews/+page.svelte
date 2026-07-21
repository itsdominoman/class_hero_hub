<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { _ , locale } from 'svelte-i18n';
  import { Check, ChevronDown, Filter, Search, X } from 'lucide-svelte';
  import { api } from '$lib/api';
  import SafeguardingHeader from '$lib/components/safeguarding/SafeguardingHeader.svelte';
  import {
    findEligibleSafeguardingMemberships,
    membershipHref,
    requestedMembershipId,
    type EligibleSafeguardingMembership
  } from '$lib/safeguarding/context';
  import {
    conversationKindLabelKey,
    isMeaningfulJustification,
    roleLabelKey,
    stateLabelKey
  } from '$lib/safeguarding/presentation';
  import { safeguardingApi } from '$lib/safeguarding/api';
  import type {
    SafeguardingContext,
    SafeguardingMembership,
    SafeguardingNamedOption,
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

  let loading = $state(true);
  let working = $state(false);
  let error = $state<string | null>(null);
  let eligible = $state<EligibleSafeguardingMembership[]>([]);
  let memberships = $state<SafeguardingMembership[]>([]);
  let membership = $state<SafeguardingMembership | null>(null);
  let context = $state<SafeguardingContext | null>(null);
  let results = $state<SafeguardingSearchItem[]>([]);
  let selected = $state<SafeguardingSearchItem | null>(null);
  let advancedOpen = $state(false);
  let startDialogOpen = $state(false);
  let startAttempted = $state(false);

  let student = $state('');
  let participant = $state('');
  let dateFrom = $state('');
  let dateTo = $state('');
  let status = $state('');
  let participantRole = $state('');
  let classGrade = $state('');
  let branch = $state('');
  let messageType = $state('');
  let direction = $state('');
  let reference = $state('');
  let flagged = $state(false);
  let restricted = $state(false);
  let closed = $state(false);

  let reasonCategory = $state('reported_concern');
  let justification = $state('');
  let acknowledgement = $state(false);
  let reviewDuration = $state('30');

  let canReview = $derived(Boolean(context?.permissions.includes('messaging.safeguarding_review')));
  let advancedFilterCount = $derived(
    [participantRole, classGrade, branch, messageType, direction, reference].filter(Boolean).length +
      [flagged, restricted, closed].filter(Boolean).length
  );
  let meaningfulJustification = $derived(isMeaningfulJustification(justification));

  function messageForFailure(value: unknown) {
    return value instanceof Error ? value.message : $_('safeguarding.errors.failed');
  }

  function formatDate(value: string) {
    return new Intl.DateTimeFormat($locale || undefined, {
      dateStyle: 'medium',
      timeStyle: 'short'
    }).format(new Date(value));
  }

  function localizedName(option: SafeguardingNamedOption | null | undefined) {
    if (!option) return '';
    return $locale === 'ar' && option.name_ar ? option.name_ar : option.name;
  }

  function schoolContextLabel(row: SafeguardingSearchItem) {
    const schoolContext = row.school_context;
    if (!schoolContext) return '';
    const className = localizedName(schoolContext.class_section);
    const gradeName = localizedName(schoolContext.grade_level);
    return [className, gradeName].filter(Boolean).join(' · ');
  }

  function participantLabel(person: SafeguardingSearchItem['participants'][number]) {
    return `${person.display_name} · ${$_(roleLabelKey(person.role || person.kind))}`;
  }

  function setMembership(row: EligibleSafeguardingMembership) {
    membership = row.membership;
    context = row.context;
    const url = new URL(window.location.href);
    url.searchParams.set('membership', String(row.membership.membership_id));
    url.searchParams.delete('start');
    window.history.replaceState(window.history.state, '', `${url.pathname}${url.search}`);
  }

  async function initialize() {
    loading = true;
    error = null;
    try {
      const user = (await api.get('/me')) as SessionUser;
      eligible = await findEligibleSafeguardingMemberships(user);
      memberships = eligible.map((row) => row.membership);
      const requested = requestedMembershipId(new URL(window.location.href));
      const chosen = eligible.find((row) => row.membership.membership_id === requested) || eligible[0];
      if (!chosen) return;
      setMembership(chosen);
      if (canReview) await searchConversations();
    } catch (value) {
      error = messageForFailure(value);
    } finally {
      loading = false;
    }
  }

  async function changeMembership(event: Event) {
    const id = Number((event.currentTarget as HTMLSelectElement).value);
    const chosen = eligible.find((row) => row.membership.membership_id === id);
    if (!chosen) return;
    closeStartFlow(false);
    setMembership(chosen);
    results = [];
    await searchConversations();
  }

  function classFilterValues() {
    if (classGrade.startsWith('class:')) return { class_section_id: classGrade.slice(6) };
    if (classGrade.startsWith('grade:')) return { grade_level_id: classGrade.slice(6) };
    return {};
  }

  async function searchConversations(event?: SubmitEvent) {
    event?.preventDefault();
    if (!membership) return;
    working = true;
    error = null;
    try {
      const statusFilters = {
        conversation_status: status === 'active' ? 'active' : undefined,
        restricted: status === 'read_only' ? true : status === 'active' ? false : restricted || undefined,
        closed: status === 'closed' ? true : status === 'active' || status === 'read_only' ? false : closed || undefined
      };
      const response = await safeguardingApi.search(membership, {
        student,
        participant,
        participant_role: participantRole,
        ...classFilterValues(),
        branch_id: branch,
        date_from: dateFrom ? `${dateFrom}T00:00:00Z` : undefined,
        date_to: dateTo ? `${dateTo}T23:59:59Z` : undefined,
        ...statusFilters,
        message_type: messageType,
        direction,
        reference,
        flagged: flagged || undefined,
        limit: 50
      });
      results = response.items;
      syncStartState();
    } catch (value) {
      error = messageForFailure(value);
    } finally {
      working = false;
    }
  }

  function clearFilters() {
    student = '';
    participant = '';
    dateFrom = '';
    dateTo = '';
    status = '';
    participantRole = '';
    classGrade = '';
    branch = '';
    messageType = '';
    direction = '';
    reference = '';
    flagged = false;
    restricted = false;
    closed = false;
    advancedOpen = false;
  }

  function chooseConversation(row: SafeguardingSearchItem) {
    selected = row;
    justification = '';
    acknowledgement = false;
    startAttempted = false;
    startDialogOpen = true;
    const url = new URL(window.location.href);
    url.searchParams.set('start', row.conversation_id);
    window.history.pushState(
      { ...(window.history.state || {}), safeguardingStart: true },
      '',
      `${url.pathname}${url.search}`
    );
  }

  function syncStartState() {
    const conversationId = new URL(window.location.href).searchParams.get('start');
    const row = results.find((item) => item.conversation_id === conversationId) || null;
    selected = row;
    startDialogOpen = Boolean(row);
  }

  function closeStartFlow(useHistory = true) {
    startDialogOpen = false;
    selected = null;
    startAttempted = false;
    if (useHistory && window.history.state?.safeguardingStart) {
      window.history.back();
      return;
    }
    const url = new URL(window.location.href);
    url.searchParams.delete('start');
    window.history.replaceState(window.history.state, '', `${url.pathname}${url.search}`);
  }

  async function startReview(event: SubmitEvent) {
    event.preventDefault();
    startAttempted = true;
    if (!membership || !selected || !meaningfulJustification || !acknowledgement) return;
    working = true;
    error = null;
    try {
      const started = await safeguardingApi.startReview(membership, {
        conversation_id: selected.conversation_id,
        reason_category: reasonCategory,
        justification,
        acknowledgement,
        ttl_minutes: Number(reviewDuration)
      });
      const href = membershipHref(
        `/school/safeguarding/message-reviews/${started.review_session_id}`,
        membership
      );
      await goto(href, { replaceState: true });
    } catch (value) {
      error = messageForFailure(value);
    } finally {
      working = false;
    }
  }

  function handleNativeBack(event: Event) {
    if (!startDialogOpen) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    closeStartFlow();
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape' && startDialogOpen) closeStartFlow();
  }

  onMount(() => {
    void initialize();
    window.addEventListener('popstate', syncStartState);
    window.addEventListener('keydown', handleKeydown);
    window.addEventListener('chh:native-back', handleNativeBack, { capture: true });
    return () => {
      window.removeEventListener('popstate', syncStartState);
      window.removeEventListener('keydown', handleKeydown);
      window.removeEventListener('chh:native-back', handleNativeBack, { capture: true });
    };
  });
</script>

<svelte:head><title>{$_('safeguarding.search.pageTitle')} · {$_('app.name')}</title></svelte:head>

<div class="min-h-full min-w-0 bg-slate-50 pb-12">
  <div class="mx-auto w-full min-w-0 max-w-6xl px-3 py-4 sm:px-6 sm:py-6">
    <SafeguardingHeader
      title={$_('safeguarding.search.pageTitle')}
      subtitle={$_('safeguarding.search.metadataOnly')}
      {context}
      {memberships}
      {membership}
      backHref={membership ? membershipHref('/school/safeguarding', membership) : '/school/safeguarding'}
      onMembershipChange={changeMembership}
    />

    {#if error}<div class="alert-error" role="alert">{error}</div>{/if}

    {#if loading}
      <div class="grid min-h-52 place-items-center text-sm font-bold text-slate-500">{$_('common.loading')}</div>
    {:else if !context || !membership || !canReview}
      <section class="empty-card"><h2>{$_('safeguarding.noAccessTitle')}</h2><p>{$_('safeguarding.noAccessBody')}</p></section>
    {:else}
      <form class="mt-4 min-w-0 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5" onsubmit={searchConversations} data-testid="safeguarding-search-form">
        <div class="mb-4"><h2 class="text-lg font-black text-slate-950">{$_('safeguarding.search.title')}</h2><p class="mt-1 text-xs leading-5 text-slate-500">{$_('safeguarding.search.help')}</p></div>

        <div class="grid min-w-0 gap-3 md:grid-cols-2">
          <label class="field-label"><span>{$_('safeguarding.search.student')}</span><input class="field" bind:value={student} autocomplete="off" /></label>
          <label class="field-label"><span>{$_('safeguarding.search.participant')}</span><input class="field" bind:value={participant} autocomplete="off" /></label>
          <fieldset class="min-w-0 md:col-span-2">
            <legend class="field-label mb-1">{$_('safeguarding.search.dateRange')}</legend>
            <div class="grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2">
              <label class="field-label"><span>{$_('safeguarding.search.from')}</span><input class="field" type="date" bind:value={dateFrom} /></label>
              <label class="field-label"><span>{$_('safeguarding.search.to')}</span><input class="field" type="date" bind:value={dateTo} /></label>
            </div>
          </fieldset>
          <label class="field-label md:col-span-2"><span>{$_('safeguarding.search.status')}</span><select class="field" bind:value={status}><option value="">{$_('safeguarding.search.anyStatus')}</option><option value="active">{$_('safeguarding.states.active')}</option><option value="read_only">{$_('safeguarding.states.read_only')}</option><option value="closed">{$_('safeguarding.states.closed')}</option></select></label>
        </div>

        <button class="mt-4 flex w-full items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold text-slate-800 md:w-auto md:min-w-56" type="button" aria-expanded={advancedOpen} aria-controls="advanced-safeguarding-filters" onclick={() => (advancedOpen = !advancedOpen)} data-testid="advanced-filters-toggle">
          <span class="inline-flex items-center gap-2"><Filter class="h-4 w-4" aria-hidden="true" />{$_('safeguarding.search.moreFilters')}{#if advancedFilterCount}<span class="rounded-full bg-amber-200 px-2 py-0.5 text-xs text-amber-950">{advancedFilterCount}</span>{/if}</span>
          <ChevronDown class={`h-4 w-4 transition ${advancedOpen ? 'rotate-180' : ''}`} aria-hidden="true" />
        </button>

        {#if advancedOpen}
          <div id="advanced-safeguarding-filters" class="mt-3 grid min-w-0 gap-3 rounded-xl border border-slate-200 bg-slate-50 p-3 md:grid-cols-2" data-testid="advanced-filters">
            <label class="field-label"><span>{$_('safeguarding.search.role')}</span><select class="field" bind:value={participantRole}><option value="">{$_('safeguarding.search.anyParticipantType')}</option><option value="teacher">{$_('safeguarding.roles.teacher')}</option><option value="school_admin">{$_('safeguarding.roles.schoolAdmin')}</option><option value="guardian">{$_('safeguarding.roles.guardian')}</option></select></label>
            <label class="field-label"><span>{$_('safeguarding.search.grade')}</span><select class="field" bind:value={classGrade}><option value="">{$_('safeguarding.search.anyClassGrade')}</option>{#each context.filters.class_sections as option}<option value={`class:${option.id}`}>{localizedName(option)}</option>{/each}{#each context.filters.grade_levels as option}<option value={`grade:${option.id}`}>{localizedName(option)}</option>{/each}</select></label>
            <label class="field-label"><span>{$_('safeguarding.search.branch')}</span><select class="field" bind:value={branch} data-testid="branch-filter"><option value="">{$_('safeguarding.search.anyBranch')}</option>{#each context.filters.branches as option}<option value={option.id}>{localizedName(option)}</option>{/each}</select></label>
            <label class="field-label"><span>{$_('safeguarding.search.messageType')}</span><select class="field" bind:value={messageType}><option value="">{$_('safeguarding.search.anyType')}</option><option value="standard">{$_('safeguarding.messageTypes.standard')}</option><option value="photo">{$_('safeguarding.messageTypes.photo')}</option><option value="voice_note">{$_('safeguarding.messageTypes.voice_note')}</option></select></label>
            <label class="field-label"><span>{$_('safeguarding.search.direction')}</span><select class="field" bind:value={direction}><option value="">{$_('safeguarding.search.anyDirection')}</option><option value="family_to_staff">{$_('safeguarding.directions.family_to_staff')}</option><option value="staff_to_family">{$_('safeguarding.directions.staff_to_family')}</option><option value="staff_internal">{$_('safeguarding.directions.staff_internal')}</option></select></label>
            <label class="field-label"><span>{$_('safeguarding.search.reference')}</span><input class="field" bind:value={reference} autocomplete="off" /></label>
            <fieldset class="min-w-0 md:col-span-2"><legend class="field-label mb-2">{$_('safeguarding.search.additionalStates')}</legend><div class="flex min-w-0 flex-wrap gap-2"><label class="check-pill"><input type="checkbox" bind:checked={flagged} />{$_('safeguarding.search.flagged')}</label><label class="check-pill"><input type="checkbox" bind:checked={restricted} />{$_('safeguarding.search.restricted')}</label><label class="check-pill"><input type="checkbox" bind:checked={closed} />{$_('safeguarding.search.closed')}</label></div></fieldset>
          </div>
        {/if}

        {#if advancedFilterCount}
          <p class="mt-3 text-xs font-bold text-amber-900" role="status">{$_('safeguarding.search.activeAdvanced', { values: { count: advancedFilterCount } })}</p>
        {/if}

        <div class="mt-4 flex min-w-0 flex-col gap-2 sm:flex-row sm:items-center">
          <button class="btn-hero inline-flex w-full items-center justify-center gap-2 rounded-xl px-5 py-2.5 text-sm sm:w-auto" type="submit" disabled={working} data-testid="safeguarding-search-action"><Search class="h-4 w-4" aria-hidden="true" />{$_('safeguarding.search.action')}</button>
          <button class="btn-secondary w-full rounded-xl px-5 py-2.5 text-sm sm:w-auto" type="button" onclick={clearFilters}>{$_('safeguarding.search.clear')}</button>
        </div>
      </form>

      <section class="mt-4 min-w-0" aria-labelledby="search-results-title">
        <div class="flex min-w-0 items-end justify-between gap-3"><div class="min-w-0"><h2 id="search-results-title" class="text-lg font-black text-slate-950">{$_('safeguarding.search.results')}</h2><p class="text-xs text-slate-500">{$_('safeguarding.search.resultCount', { values: { count: results.length } })}</p></div></div>
        <div class="mt-3 grid min-w-0 gap-3 lg:grid-cols-2" data-testid="safeguarding-results">
          {#each results as row}
            {@const isSelected = selected?.conversation_id === row.conversation_id}
            <article class:selected-card={isSelected} class="result-card" data-testid="conversation-card">
              <div class="flex min-w-0 items-start justify-between gap-3">
                <div class="min-w-0"><h3 class="break-words text-base font-black text-slate-950">{row.student?.display_name || $_('safeguarding.search.staffConversation')}</h3><p class="mt-0.5 text-xs font-bold text-slate-600">{$_(conversationKindLabelKey(row.kind))}</p></div>
                {#if isSelected}<span class="selected-indicator"><Check class="h-4 w-4" aria-hidden="true" />{$_('safeguarding.search.selected')}</span>{/if}
              </div>
              <div class="mt-3 min-w-0 space-y-1 text-sm text-slate-700">{#each row.participants as person}<p class="min-w-0 break-words leading-5">{participantLabel(person)}</p>{/each}</div>
              {#if schoolContextLabel(row)}<p class="mt-3 break-words text-xs font-bold text-slate-600">{schoolContextLabel(row)}</p>{/if}
              {#if row.branch}<p class="mt-1 break-words text-xs text-slate-500">{$_('safeguarding.search.branch')}: {localizedName(row.branch)}</p>{/if}
              <p class="mt-2 text-xs text-slate-500">{$_('safeguarding.search.lastActivity')}: {formatDate(row.last_activity_at)}</p>
              <div class="mt-3 flex min-w-0 flex-wrap gap-1.5"><span class="badge">{$_(stateLabelKey(row.participant_state))}</span>{#if row.restricted}<span class="badge badge-amber">{$_('safeguarding.search.restricted')}</span>{/if}{#if row.flag_count}<span class="badge badge-red">{$_('safeguarding.search.flagged')}</span>{/if}</div>
              <div class="mt-4 flex min-w-0 flex-wrap items-center justify-between gap-2">
                <details class="min-w-0 text-xs text-slate-500"><summary class="cursor-pointer font-bold">{$_('safeguarding.search.details')}</summary><p class="mt-1 break-all">{$_('safeguarding.search.conversationId')}: {row.reference}</p></details>
                <button class={isSelected ? 'selected-button' : 'select-button'} type="button" aria-pressed={isSelected} onclick={() => chooseConversation(row)}>{#if isSelected}<Check class="h-4 w-4" aria-hidden="true" />{$_('safeguarding.search.selected')}{:else}{$_('safeguarding.search.review')}{/if}</button>
              </div>
            </article>
          {:else}
            <p class="col-span-full rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">{$_('safeguarding.search.empty')}</p>
          {/each}
        </div>
      </section>
    {/if}
  </div>
</div>

{#if startDialogOpen && selected && membership}
  <div class="dialog-backdrop" role="presentation" data-testid="start-review-dialog">
    <button class="absolute inset-0 h-full w-full" type="button" aria-label={$_('common.close')} onclick={() => closeStartFlow()}></button>
    <div class="start-sheet" role="dialog" aria-modal="true" aria-labelledby="start-review-title">
      <div class="flex min-w-0 items-start justify-between gap-3 border-b border-slate-200 p-4 sm:p-5">
        <div class="min-w-0"><h2 id="start-review-title" class="break-words text-xl font-black text-slate-950">{$_('safeguarding.start.title')}</h2><p class="mt-1 text-sm text-slate-600">{$_('safeguarding.start.body')}</p></div>
        <button class="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-slate-100 text-slate-700" type="button" aria-label={$_('common.close')} onclick={() => closeStartFlow()}><X class="h-5 w-5" aria-hidden="true" /></button>
      </div>
      <form class="min-w-0" onsubmit={startReview} novalidate>
        <div class="min-w-0 space-y-4 p-4 sm:p-5">
          <div class="min-w-0 rounded-xl bg-amber-50 p-3"><strong class="block break-words text-slate-950">{selected.student?.display_name || $_('safeguarding.search.staffConversation')}</strong><span class="mt-1 block break-words text-xs text-slate-600">{selected.participants.map(participantLabel).join(' · ')}</span></div>
          <label class="field-label"><span>{$_('safeguarding.reasonCategory')}</span><select class="field" bind:value={reasonCategory}>{#each reasonCategories as value}<option {value}>{$_(`safeguarding.reasons.${value}`)}</option>{/each}</select></label>
          <label class="field-label"><span>{$_('safeguarding.justification')}</span><textarea class="field min-h-28 resize-y" minlength="15" maxlength="2000" bind:value={justification} aria-invalid={startAttempted && !meaningfulJustification}></textarea><small class="mt-1 block font-normal text-slate-500">{$_('safeguarding.start.justificationHelp')}</small>{#if startAttempted && !meaningfulJustification}<span class="field-error" role="alert">{$_('safeguarding.start.justificationError')}</span>{/if}</label>
          <label class="field-label"><span>{$_('safeguarding.start.duration')}</span><select class="field" bind:value={reviewDuration}><option value="15">{$_('safeguarding.start.minutes', { values: { count: 15 } })}</option><option value="30">{$_('safeguarding.start.minutes', { values: { count: 30 } })}</option><option value="45">{$_('safeguarding.start.minutes', { values: { count: 45 } })}</option><option value="60">{$_('safeguarding.start.minutes', { values: { count: 60 } })}</option></select></label>
          <label class="acknowledgement"><input class="mt-1 h-5 w-5 shrink-0" type="checkbox" bind:checked={acknowledgement} /><span>{$_('safeguarding.start.acknowledgement')}</span></label>{#if startAttempted && !acknowledgement}<span class="field-error" role="alert">{$_('safeguarding.start.acknowledgementError')}</span>{/if}
        </div>
        <div class="sticky bottom-0 flex flex-col-reverse gap-2 border-t border-slate-200 bg-white p-4 sm:flex-row sm:justify-end"><button class="btn-secondary w-full sm:w-auto" type="button" onclick={() => closeStartFlow()}>{$_('common.cancel')}</button><button class="btn-hero w-full sm:w-auto" type="submit" disabled={working}>{$_('safeguarding.start.action')}</button></div>
      </form>
    </div>
  </div>
{/if}

<style>
  .field-label { display: block; min-width: 0; font-size: .75rem; font-weight: 700; color: rgb(51 65 85); }
  .field-label > span:first-child { margin-bottom: .35rem; display: block; }
  .field { width: 100%; max-width: 100%; min-width: 0; border: 1px solid rgb(203 213 225); border-radius: .75rem; background: white; padding: .7rem .8rem; color: rgb(15 23 42); font-weight: 400; }
  .field:focus { border-color: rgb(245 158 11); outline: 2px solid rgb(254 243 199); outline-offset: 1px; }
  .check-pill { display: inline-flex; min-width: 0; align-items: center; gap: .45rem; border: 1px solid rgb(203 213 225); border-radius: 999px; background: white; padding: .55rem .75rem; font-size: .75rem; font-weight: 700; }
  .result-card { min-width: 0; max-width: 100%; overflow: hidden; border: 1px solid rgb(226 232 240); border-radius: 1rem; background: white; padding: 1rem; box-shadow: 0 1px 2px rgb(15 23 42 / .05); }
  .selected-card { border: 2px solid rgb(217 119 6); box-shadow: 0 0 0 3px rgb(254 243 199); }
  .selected-indicator { display: inline-flex; flex: none; align-items: center; gap: .25rem; border-radius: 999px; background: rgb(217 119 6); padding: .35rem .6rem; font-size: .7rem; font-weight: 900; color: white; }
  .badge { border-radius: 999px; background: rgb(241 245 249); padding: .3rem .55rem; font-size: .7rem; font-weight: 800; color: rgb(51 65 85); }
  .badge-amber { background: rgb(254 243 199); color: rgb(146 64 14); }
  .badge-red { background: rgb(254 226 226); color: rgb(153 27 27); }
  .select-button, .selected-button { display: inline-flex; min-width: 6.5rem; align-items: center; justify-content: center; gap: .35rem; border-radius: .75rem; padding: .55rem .9rem; font-size: .8rem; font-weight: 900; }
  .select-button { background: rgb(15 23 42); color: white; }
  .selected-button { background: rgb(217 119 6); color: white; }
  .dialog-backdrop { position: fixed; inset: 0; z-index: 120; display: flex; min-width: 0; align-items: flex-end; justify-content: center; background: rgb(15 23 42 / .72); padding-top: var(--safe-top); }
  .start-sheet { position: relative; width: 100%; max-width: 44rem; min-width: 0; max-height: calc(100dvh - var(--safe-top)); overflow-x: hidden; overflow-y: auto; scroll-padding-bottom: calc(6rem + var(--safe-bottom)); border-radius: 1.25rem 1.25rem 0 0; background: white; padding-bottom: var(--safe-bottom); box-shadow: 0 -16px 50px rgb(15 23 42 / .3); }
  .acknowledgement { display: flex; min-width: 0; align-items: flex-start; gap: .65rem; border: 1px solid rgb(253 230 138); border-radius: .85rem; background: rgb(255 251 235); padding: .85rem; font-size: .8rem; font-weight: 700; line-height: 1.35rem; color: rgb(120 53 15); }
  .field-error { display: block; margin-top: .35rem; overflow-wrap: anywhere; font-size: .75rem; font-weight: 700; color: rgb(185 28 28); }
  .alert-error { margin-top: 1rem; overflow-wrap: anywhere; border: 1px solid rgb(254 202 202); border-radius: 1rem; background: rgb(254 242 242); padding: 1rem; font-size: .875rem; font-weight: 700; color: rgb(153 27 27); }
  .empty-card { margin-top: 1rem; border: 1px solid rgb(226 232 240); border-radius: 1rem; background: white; padding: 2rem 1rem; text-align: center; }
  .empty-card h2 { font-size: 1.25rem; font-weight: 900; }
  .empty-card p { margin-top: .5rem; font-size: .875rem; color: rgb(71 85 105); }
  @media (min-width: 640px) { .dialog-backdrop { align-items: center; padding: 1.5rem; } .start-sheet { max-height: min(48rem, calc(100dvh - 3rem)); border-radius: 1.25rem; padding-bottom: 0; } }
</style>
