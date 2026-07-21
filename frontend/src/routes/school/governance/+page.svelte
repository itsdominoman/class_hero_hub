<script lang="ts">
  import { onMount } from 'svelte';
  import { _, locale } from 'svelte-i18n';
  import { api } from '$lib/api';

  type Membership = { school_id: number; membership_id: number; school_name: string; role: string };
  type StaffRow = {
    membership_id: number;
    display_name: string;
    display_name_ar?: string | null;
    role: 'school_admin' | 'teacher';
    membership_status: string;
  };

  let membership = $state<Membership | null>(null);
  let data = $state<any>(null);
  let loading = $state(true);
  let error = $state('');
  let reason = $state('');
  let targetId = $state('');
  let confirmationId = $state('');
  let saving = $state(false);
  let query = $state('');
  let roleFilter = $state('all');
  let statusFilter = $state('all');

  function options() {
    return membership
      ? { headers: { 'X-School-Id': String(membership.school_id), 'X-Membership-Id': String(membership.membership_id) } }
      : {};
  }

  function displayName(row: StaffRow) {
    return $locale === 'ar' && row.display_name_ar ? row.display_name_ar : row.display_name;
  }

  function roleLabel(role: string) {
    return role === 'school_admin' ? $_('governancePage.schoolAdministrator') : $_('governancePage.teacher');
  }

  function statusLabel(status: string) {
    if (status === 'active') return $_('governancePage.active');
    if (status === 'inactive') return $_('governancePage.inactive');
    if (status === 'archived') return $_('governancePage.archived');
    return status.replaceAll('_', ' ');
  }

  let transferCandidates = $derived(
    (data?.staff || []).filter(
      (row: StaffRow) =>
        row.role === 'school_admin' &&
        row.membership_status === 'active' &&
        row.membership_id !== data?.owner?.membership_id
    )
  );

  let filteredStaff = $derived(
    (data?.staff || []).filter((row: StaffRow) => {
      const name = `${row.display_name} ${row.display_name_ar || ''}`.toLocaleLowerCase();
      return (
        name.includes(query.trim().toLocaleLowerCase()) &&
        (roleFilter === 'all' || row.role === roleFilter) &&
        (statusFilter === 'all' || row.membership_status === statusFilter)
      );
    })
  );

  async function load() {
    loading = true;
    error = '';
    try {
      const me = await api.get('/me');
      membership = (me.memberships || []).find((row: Membership) => row.role === 'school_admin') || null;
      if (!membership) throw new Error($_('governancePage.adminRequired'));
      data = await api.get('/school/governance', options());
    } catch (caught: any) {
      error = caught?.message || $_('governancePage.loadError');
    } finally {
      loading = false;
    }
  }

  async function transfer() {
    if (!targetId || targetId !== confirmationId) {
      error = $_('governancePage.transferMismatch');
      return;
    }
    saving = true;
    error = '';
    try {
      await api.post(
        '/school/governance/transfer',
        {
          target_membership_id: Number(targetId),
          confirmation_membership_id: Number(confirmationId),
          reason
        },
        options()
      );
      reason = '';
      targetId = confirmationId = '';
      await load();
    } catch (caught: any) {
      error = caught?.message || $_('governancePage.transferFailed');
    } finally {
      saving = false;
    }
  }

  onMount(load);
</script>

<svelte:head><title>{$_('governancePage.pageTitle')}</title></svelte:head>

<section class="mx-auto max-w-5xl px-4 py-8">
  <p class="eyebrow">{$_('governancePage.eyebrow')}</p>
  <h1 class="mt-2 text-3xl font-black text-slate-900">{$_('governancePage.title')}</h1>
  <p class="mt-2 max-w-3xl text-slate-600">{$_('governancePage.intro')}</p>

  {#if error}
    <div class="mt-5 rounded-xl border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">{error}</div>
  {/if}
  {#if loading}
    <div class="card mt-6 p-6">{$_('common.loading')}…</div>
  {:else if data}
    {#if data.recovery_required}
      <div class="mt-6 rounded-xl border border-amber-300 bg-amber-50 p-5 text-amber-950">
        <strong>{$_('governancePage.recoveryRequired')}</strong>
        <p class="mt-2 text-sm">{$_('governancePage.recoveryGuidance')}</p>
      </div>
    {/if}

    <div class="mt-6 grid gap-5 lg:grid-cols-2">
      <article class="card p-6">
        <h2 class="text-lg font-black text-slate-900">{$_('governancePage.currentOwner')}</h2>
        {#if data.owner}
          <p class="mt-4 text-xl font-bold text-slate-900">{displayName(data.owner)}</p>
          <p class="mt-1 text-sm text-slate-500">{$_('governancePage.activeAdminVersion', { values: { version: data.owner_version } })}</p>
        {:else}
          <p class="mt-4 text-slate-600">{$_('governancePage.noOwner')}</p>
        {/if}
      </article>

      <article class="card p-6">
        <h2 class="text-lg font-black text-slate-900">{$_('governancePage.transferAuthority')}</h2>
        <p class="mt-2 text-sm leading-6 text-slate-600">{$_('governancePage.transferHelp')}</p>
        {#if data.is_current_owner}
          <label class="mt-4 block text-sm font-bold">
            {$_('governancePage.newAdministrator')}
            <select class="mt-1 min-h-12 w-full rounded-xl border border-slate-300 p-3" bind:value={targetId}>
              <option value="">{$_('governancePage.choose')}</option>
              {#each transferCandidates as row}
                <option value={String(row.membership_id)}>{displayName(row)}</option>
              {/each}
            </select>
          </label>
          <label class="mt-3 block text-sm font-bold">
            {$_('governancePage.confirmAdministrator')}
            <select class="mt-1 min-h-12 w-full rounded-xl border border-slate-300 p-3" bind:value={confirmationId}>
              <option value="">{$_('governancePage.chooseAgain')}</option>
              {#each transferCandidates as row}
                <option value={String(row.membership_id)}>{displayName(row)}</option>
              {/each}
            </select>
          </label>
          <label class="mt-3 block text-sm font-bold">
            {$_('governancePage.reason')}
            <span class="mt-1 block text-xs font-normal text-slate-500">{$_('governancePage.reasonHelp')}</span>
            <textarea class="mt-2 min-h-24 w-full rounded-xl border border-slate-300 p-3" bind:value={reason} minlength="8" maxlength="2000"></textarea>
          </label>
          <button class="btn-hero mt-4 min-h-12 rounded-xl px-5 py-3" disabled={saving || reason.trim().length < 8 || !targetId || targetId !== confirmationId} onclick={transfer}>
            {$_('governancePage.transfer')}
          </button>
        {:else}
          <p class="mt-4 rounded-xl bg-slate-50 p-4 text-sm font-semibold text-slate-600">{$_('governancePage.transferUnavailable')}</p>
        {/if}
      </article>
    </div>

    <article class="card mt-6 p-6">
      <h2 class="text-lg font-black text-slate-900">{$_('governancePage.roster')}</h2>
      <div class="mt-4 grid gap-3 sm:grid-cols-3">
        <label class="text-sm font-bold">
          <span class="sr-only">{$_('governancePage.search')}</span>
          <input class="min-h-12 w-full rounded-xl border border-slate-300 px-3" type="search" placeholder={$_('governancePage.search')} bind:value={query} />
        </label>
        <label class="text-sm font-bold">
          <span class="sr-only">{$_('governancePage.role')}</span>
          <select class="min-h-12 w-full rounded-xl border border-slate-300 px-3" bind:value={roleFilter}>
            <option value="all">{$_('governancePage.allRoles')}</option>
            <option value="school_admin">{$_('governancePage.schoolAdministrator')}</option>
            <option value="teacher">{$_('governancePage.teacher')}</option>
          </select>
        </label>
        <label class="text-sm font-bold">
          <span class="sr-only">{$_('governancePage.status')}</span>
          <select class="min-h-12 w-full rounded-xl border border-slate-300 px-3" bind:value={statusFilter}>
            <option value="all">{$_('governancePage.allStatuses')}</option>
            <option value="active">{$_('governancePage.active')}</option>
            <option value="inactive">{$_('governancePage.inactive')}</option>
            <option value="archived">{$_('governancePage.archived')}</option>
          </select>
        </label>
      </div>

      {#if filteredStaff.length}
        <div class="mt-5 grid gap-3 sm:grid-cols-2">
          {#each filteredStaff as row}
            <div class="min-w-0 rounded-xl border border-slate-200 bg-slate-50 p-4">
              <p class="break-words font-black text-slate-900">{displayName(row)}</p>
              <div class="mt-2 flex flex-wrap gap-2 text-xs font-bold">
                <span class="rounded-full bg-white px-2.5 py-1 text-slate-700">{roleLabel(row.role)}</span>
                <span class:!bg-emerald-100={row.membership_status === 'active'} class:!text-emerald-800={row.membership_status === 'active'} class="rounded-full bg-slate-200 px-2.5 py-1 text-slate-700">{statusLabel(row.membership_status)}</span>
              </div>
            </div>
          {/each}
        </div>
      {:else}
        <p class="mt-5 rounded-xl bg-slate-50 p-4 text-sm text-slate-600">{$_('governancePage.noMatches')}</p>
      {/if}
    </article>
  {/if}
</section>
