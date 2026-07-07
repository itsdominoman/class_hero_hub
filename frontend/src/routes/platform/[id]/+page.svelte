<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/state';
  import { _ } from 'svelte-i18n';
  import { api } from '$lib/api';

  type StaffInvite = {
    id: number;
    email: string;
    role: string;
    status: string;
    created_at: string;
    expires_at: string;
    accepted_at?: string | null;
    revoked_at?: string | null;
  };

  type SchoolDetail = {
    id: number;
    name: string;
    status: string;
    timezone: string;
    locale_default: string;
    created_at: string;
    suspend_reason?: string | null;
    counts: { memberships_by_role: Record<string, number>; students: number };
    setup_flags: { has_school_admin: boolean; students_configured: boolean };
    invites: StaffInvite[];
  };

  const schoolId = page.params.id;
  let school = $state<SchoolDetail | null>(null);
  let loading = $state(true);
  let saving = $state(false);
  let error = $state<string | null>(null);
  let inviteEmail = $state('');
  let reason = $state('');

  const formatDate = (value?: string | null) => value ? new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : '-';
  const roleCount = (role: string) => school?.counts?.memberships_by_role?.[role] || 0;

  async function loadSchool() {
    loading = true;
    error = null;
    try {
      school = await api.get(`/platform/schools/${schoolId}`);
    } catch (err: any) {
      error = err?.message || $_('platform.loadError');
    } finally {
      loading = false;
    }
  }

  async function sendInvite() {
    if (!school) return;
    await createInvite(inviteEmail);
    inviteEmail = '';
  }

  async function createInvite(email: string) {
    if (!school) return;
    saving = true;
    error = null;
    try {
      const invite = await api.post(`/platform/schools/${school.id}/invites`, { email });
      school = { ...school, invites: [invite, ...school.invites] };
    } catch (err: any) {
      error = err?.message || $_('platform.inviteError');
    } finally {
      saving = false;
    }
  }

  async function revokeInvite(inviteId: number) {
    if (!school) return;
    saving = true;
    error = null;
    try {
      await api.delete(`/platform/invites/${inviteId}`);
      await loadSchool();
    } catch (err: any) {
      error = err?.message || $_('platform.revokeError');
    } finally {
      saving = false;
    }
  }

  async function suspendOrReactivate(action: 'suspend' | 'reactivate') {
    if (!school) return;
    saving = true;
    error = null;
    try {
      school = await api.post(`/platform/schools/${school.id}/${action}`, { reason });
      reason = '';
    } catch (err: any) {
      error = err?.message || $_('platform.actionError');
    } finally {
      saving = false;
    }
  }

  onMount(loadSchool);
</script>

<section class="mx-auto max-w-6xl px-4 py-10">
  <a href="/platform" class="text-sm font-bold text-hero hover:text-hero-dark">{$_('platform.backToSchools')}</a>

  {#if loading}
    <div class="mt-8 card p-8 text-center text-sm font-semibold uppercase tracking-wide text-slate-500">{$_('common.loading')}</div>
  {:else if error && !school}
    <div class="mt-8 rounded-lg border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">{error}</div>
  {:else if school}
    <div class="mt-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <p class="eyebrow">{$_('platform.schoolDetail')}</p>
        <h1 class="mt-2 text-3xl font-black text-slate-900">{school.name}</h1>
        <p class="mt-2 text-slate-500">{school.timezone} · {school.locale_default}</p>
      </div>
      <span class="w-fit rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-bold text-slate-700">{$_(`platform.statuses.${school.status}`)}</span>
    </div>

    {#if error}
      <div class="mt-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">{error}</div>
    {/if}

    <div class="mt-8 grid gap-4 sm:grid-cols-3">
      <div class="rounded-lg border border-slate-200 bg-white p-5">
        <p class="text-xs font-bold uppercase tracking-wide text-slate-400">{$_('platform.admins')}</p>
        <p class="mt-2 text-3xl font-black text-slate-900">{roleCount('school_admin')}</p>
      </div>
      <div class="rounded-lg border border-slate-200 bg-white p-5">
        <p class="text-xs font-bold uppercase tracking-wide text-slate-400">{$_('platform.students')}</p>
        <p class="mt-2 text-3xl font-black text-slate-900">{school.counts.students}</p>
      </div>
      <div class="rounded-lg border border-slate-200 bg-white p-5">
        <p class="text-xs font-bold uppercase tracking-wide text-slate-400">{$_('platform.created')}</p>
        <p class="mt-2 font-bold text-slate-900">{formatDate(school.created_at)}</p>
      </div>
    </div>

    <div class="mt-8 grid gap-6 lg:grid-cols-[1fr_22rem]">
      <div class="rounded-lg border border-slate-200 bg-white">
        <div class="border-b border-slate-200 p-5">
          <h2 class="text-xl font-black text-slate-900">{$_('platform.invites')}</h2>
        </div>
        <form class="flex flex-col gap-3 border-b border-slate-200 p-5 sm:flex-row" onsubmit={(event) => { event.preventDefault(); sendInvite(); }}>
          <input required type="email" bind:value={inviteEmail} placeholder={$_('platform.adminEmail')} class="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-3 font-medium" />
          <button disabled={saving} class="btn-hero rounded-lg px-4 py-3 disabled:opacity-60">{$_('platform.sendInvite')}</button>
        </form>

        {#if school.invites.length === 0}
          <div class="p-5 text-sm text-slate-500">{$_('platform.noInvites')}</div>
        {:else}
          <div class="divide-y divide-slate-100">
            {#each school.invites as invite}
              <div class="flex flex-col gap-3 p-5 sm:flex-row sm:items-center sm:justify-between">
                <div class="min-w-0">
                  <p class="break-all font-bold text-slate-900">{invite.email}</p>
                  <p class="mt-1 text-sm text-slate-500">{invite.role} · {$_(`platform.inviteStatuses.${invite.status}`)} · {formatDate(invite.created_at)}</p>
                </div>
                <div class="flex shrink-0 gap-2">
                  <button disabled={saving} class="btn-secondary rounded-lg px-3 py-2 text-sm" onclick={() => createInvite(invite.email)}>{$_('platform.resend')}</button>
                  {#if invite.status === 'pending'}
                    <button disabled={saving} class="btn-secondary rounded-lg px-3 py-2 text-sm" onclick={() => revokeInvite(invite.id)}>{$_('platform.revoke')}</button>
                  {/if}
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>

      <aside class="rounded-lg border border-slate-200 bg-white p-5">
        <h2 class="text-lg font-black text-slate-900">{$_('platform.accountStatus')}</h2>
        {#if school.status === 'suspended' && school.suspend_reason}
          <p class="mt-3 rounded-lg bg-red-50 p-3 text-sm font-semibold text-red-700">{school.suspend_reason}</p>
        {/if}
        <label class="mt-5 grid gap-2 text-sm font-bold text-slate-700">
          {$_('platform.reason')}
          <textarea required bind:value={reason} rows="4" class="rounded-lg border border-slate-300 px-3 py-3 font-medium"></textarea>
        </label>
        {#if school.status === 'suspended'}
          <button disabled={saving || !reason.trim()} class="btn-hero mt-4 w-full rounded-lg px-4 py-3 disabled:opacity-60" onclick={() => suspendOrReactivate('reactivate')}>{$_('platform.reactivate')}</button>
        {:else}
          <button disabled={saving || !reason.trim()} class="mt-4 w-full rounded-lg bg-red-600 px-4 py-3 font-bold text-white shadow-lg shadow-red-600/20 transition hover:bg-red-700 disabled:opacity-60" onclick={() => suspendOrReactivate('suspend')}>{$_('platform.suspend')}</button>
        {/if}
      </aside>
    </div>
  {/if}
</section>
