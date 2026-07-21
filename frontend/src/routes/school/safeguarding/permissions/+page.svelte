<script lang="ts">
  import { onMount } from 'svelte';
  import { _ , locale } from 'svelte-i18n';
  import { AlertTriangle, CheckCircle2, ShieldCheck } from 'lucide-svelte';
  import { api } from '$lib/api';
  import SafeguardingHeader from '$lib/components/safeguarding/SafeguardingHeader.svelte';
  import {
    findEligibleSafeguardingMemberships,
    membershipHref,
    requestedMembershipId,
    type EligibleSafeguardingMembership
  } from '$lib/safeguarding/context';
  import {
    isMeaningfulJustification,
    permissionDescriptionKey,
    permissionLabelKey,
    roleLabelKey,
    SAFEGUARDING_PERMISSIONS
  } from '$lib/safeguarding/presentation';
  import { safeguardingApi } from '$lib/safeguarding/api';
  import type {
    SafeguardingContext,
    SafeguardingMembership,
    SafeguardingPermissionsResponse
  } from '$lib/safeguarding/types';
  import type { SessionUser } from '$lib/roleRouting';

  type StaffRow = SafeguardingPermissionsResponse['memberships'][number];

  let loading = $state(true);
  let working = $state(false);
  let error = $state<string | null>(null);
  let notice = $state<string | null>(null);
  let eligible = $state<EligibleSafeguardingMembership[]>([]);
  let memberships = $state<SafeguardingMembership[]>([]);
  let membership = $state<SafeguardingMembership | null>(null);
  let context = $state<SafeguardingContext | null>(null);
  let permissions = $state<SafeguardingPermissionsResponse | null>(null);
  let staffMembershipId = $state('');
  let selectedPermissions = $state<string[]>([]);
  let reason = $state('');
  let saveAttempted = $state(false);

  let canManage = $derived(Boolean(context?.permissions.includes('messaging.manage_safeguarding_permissions')));
  let selectedStaff = $derived(
    permissions?.memberships.find((row) => row.membership_id === Number(staffMembershipId)) || null
  );
  let originalPermissions = $derived(selectedStaff?.permissions.map((grant) => grant.permission) || []);
  let changes = $derived({
    grant: selectedPermissions.filter((permission) => !originalPermissions.includes(permission)),
    revoke: originalPermissions.filter((permission) => !selectedPermissions.includes(permission))
  });
  let hasChanges = $derived(changes.grant.length > 0 || changes.revoke.length > 0);
  let reasonIsMeaningful = $derived(isMeaningfulJustification(reason, 8));
  let grantingManage = $derived(
    changes.grant.includes('messaging.manage_safeguarding_permissions')
  );

  function messageForFailure(value: unknown) {
    return value instanceof Error ? value.message : $_('safeguarding.errors.failed');
  }

  function localizedBranch(row: StaffRow) {
    if (!row.branch) return '';
    return $locale === 'ar' && row.branch.name_ar ? row.branch.name_ar : row.branch.name;
  }

  function setMembership(row: EligibleSafeguardingMembership) {
    membership = row.membership;
    context = row.context;
    const url = new URL(window.location.href);
    url.searchParams.set('membership', String(row.membership.membership_id));
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
      if (canManage) await loadPermissions();
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
    setMembership(chosen);
    permissions = null;
    staffMembershipId = '';
    selectedPermissions = [];
    if (canManage) await loadPermissions();
  }

  async function loadPermissions() {
    if (!membership || !canManage) return;
    permissions = await safeguardingApi.permissions(membership);
  }

  function chooseStaff(event: Event) {
    staffMembershipId = (event.currentTarget as HTMLSelectElement).value;
    const row = permissions?.memberships.find(
      (item) => item.membership_id === Number(staffMembershipId)
    );
    selectedPermissions = row?.permissions.map((grant) => grant.permission) || [];
    reason = '';
    saveAttempted = false;
    notice = null;
    error = null;
  }

  function togglePermission(permission: string, checked: boolean) {
    selectedPermissions = checked
      ? Array.from(new Set([...selectedPermissions, permission]))
      : selectedPermissions.filter((value) => value !== permission);
  }

  async function saveAccess(event: SubmitEvent) {
    event.preventDefault();
    saveAttempted = true;
    if (!membership || !selectedStaff || !hasChanges || !reasonIsMeaningful) return;
    working = true;
    error = null;
    notice = null;
    try {
      for (const permission of changes.grant) {
        await safeguardingApi.grantPermission(membership, {
          membership_id: selectedStaff.membership_id,
          permission,
          reason
        });
      }
      const revokeOrder = [...changes.revoke].sort((permission) =>
        permission === 'messaging.manage_safeguarding_permissions' ? 1 : -1
      );
      for (const permission of revokeOrder) {
        const grant = selectedStaff.permissions.find((row) => row.permission === permission);
        if (grant) await safeguardingApi.revokePermission(membership, grant.id, reason);
      }
      const selectedId = selectedStaff.membership_id;
      reason = '';
      saveAttempted = false;
      await loadPermissions();
      staffMembershipId = String(selectedId);
      const refreshed = permissions?.memberships.find((row) => row.membership_id === selectedId);
      selectedPermissions = refreshed?.permissions.map((grant) => grant.permission) || [];
      notice = $_('safeguarding.permissionsPage.saved');
    } catch (value) {
      error = messageForFailure(value);
      await loadPermissions().catch(() => undefined);
    } finally {
      working = false;
    }
  }

  onMount(() => void initialize());
</script>

<svelte:head><title>{$_('safeguarding.permissionsPage.title')} · {$_('app.name')}</title></svelte:head>

<div class="min-h-full min-w-0 bg-slate-50 pb-12">
  <div class="mx-auto w-full min-w-0 max-w-5xl px-3 py-4 sm:px-6 sm:py-6">
    <SafeguardingHeader
      title={$_('safeguarding.permissionsPage.title')}
      subtitle={$_('safeguarding.permissionsPage.subtitle')}
      {context}
      {memberships}
      {membership}
      backHref={membership ? membershipHref('/school/safeguarding', membership) : '/school/safeguarding'}
      onMembershipChange={changeMembership}
    />

    {#if error}<div class="alert-error" role="alert">{error}</div>{/if}
    {#if notice}<div class="alert-success" role="status"><CheckCircle2 class="h-5 w-5 shrink-0" aria-hidden="true" />{notice}</div>{/if}

    {#if loading}
      <div class="grid min-h-52 place-items-center text-sm font-bold text-slate-500">{$_('common.loading')}</div>
    {:else if !context || !membership || !canManage}
      <section class="empty-card"><h2>{$_('safeguarding.noAccessTitle')}</h2><p>{$_('safeguarding.permissionsPage.noAccess')}</p></section>
    {:else if permissions}
      <form class="mt-4 min-w-0 space-y-4" onsubmit={saveAccess} data-testid="permission-checklist-form">
        <section class="panel">
          <div class="flex min-w-0 items-start gap-3"><span class="icon-wrap"><ShieldCheck class="h-6 w-6" aria-hidden="true" /></span><div class="min-w-0"><h2 class="text-lg font-black text-slate-950">{$_('safeguarding.permissionsPage.selectTitle')}</h2><p class="mt-1 text-sm text-slate-600">{$_('safeguarding.permissionsPage.selectBody')}</p></div></div>
          <label class="field-label mt-4"><span>{$_('safeguarding.selectStaff')}</span><select class="field" value={staffMembershipId} onchange={chooseStaff} data-testid="staff-selector"><option value="">{$_('safeguarding.permissionsPage.chooseStaff')}</option>{#each permissions.memberships as row}<option value={row.membership_id}>{row.name} · {$_(roleLabelKey(row.role))}{#if localizedBranch(row)} · {localizedBranch(row)}{/if}</option>{/each}</select></label>
        </section>

        {#if selectedStaff}
          <section class="panel min-w-0">
            <div class="flex min-w-0 flex-wrap items-start justify-between gap-3 border-b border-slate-100 pb-4">
              <div class="min-w-0"><h2 class="break-words text-lg font-black text-slate-950">{selectedStaff.name}</h2><p class="mt-1 break-words text-sm text-slate-600">{$_(roleLabelKey(selectedStaff.role))}{#if localizedBranch(selectedStaff)} · {localizedBranch(selectedStaff)}{/if}</p></div>
              <span class:selected-inactive={!selectedStaff.active} class="status-pill">{selectedStaff.active ? $_('safeguarding.permissionsPage.active') : $_('safeguarding.permissionsPage.inactive')}</span>
            </div>

            <fieldset class="mt-4 min-w-0"><legend class="text-sm font-black text-slate-900">{$_('safeguarding.permissionsPage.currentAccess')}</legend><div class="mt-3 min-w-0 space-y-2">{#each SAFEGUARDING_PERMISSIONS as permission}<label class:danger-permission={permission === 'messaging.manage_safeguarding_permissions'} class="permission-row"><input class="mt-1 h-5 w-5 shrink-0" type="checkbox" checked={selectedPermissions.includes(permission)} onchange={(event) => togglePermission(permission, event.currentTarget.checked)} /><span class="min-w-0"><strong class="block break-words text-sm text-slate-950">{$_(permissionLabelKey(permission))}</strong><span class="mt-0.5 block break-words text-xs leading-5 text-slate-600">{$_(permissionDescriptionKey(permission))}</span></span></label>{/each}</div></fieldset>

            {#if grantingManage}
              <div class="mt-4 flex min-w-0 items-start gap-2 rounded-xl border border-red-300 bg-red-50 p-3 text-sm leading-5 text-red-900" role="alert" data-testid="manage-access-warning"><AlertTriangle class="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" /><span><strong class="block">{$_('safeguarding.permissionsPage.dangerTitle')}</strong>{$_('safeguarding.permissionsPage.dangerBody')}</span></div>
            {/if}

            <label class="field-label mt-4"><span>{$_('safeguarding.permissionReason')}</span><textarea class="field min-h-24 resize-y" maxlength="1000" bind:value={reason} aria-invalid={saveAttempted && !reasonIsMeaningful}></textarea><small class="mt-1 block font-normal text-slate-500">{$_('safeguarding.permissionsPage.reasonHelp')}</small>{#if saveAttempted && !reasonIsMeaningful}<span class="field-error" role="alert">{$_('safeguarding.permissionsPage.reasonError')}</span>{/if}</label>

            <div class="mt-4 flex min-w-0 flex-col gap-2 sm:flex-row sm:items-center sm:justify-between"><p class="text-xs font-bold text-slate-500" role="status">{#if hasChanges}{$_('safeguarding.permissionsPage.changeSummary', { values: { grants: changes.grant.length, revokes: changes.revoke.length } })}{:else}{$_('safeguarding.permissionsPage.noChanges')}{/if}</p><button class="btn-hero w-full sm:w-auto" type="submit" disabled={working || !hasChanges || !selectedStaff.active}>{$_('safeguarding.permissionsPage.save')}</button></div>
          </section>
        {:else}
          <section class="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">{$_('safeguarding.permissionsPage.selectPrompt')}</section>
        {/if}
      </form>
    {/if}
  </div>
</div>

<style>
  .panel { min-width: 0; max-width: 100%; overflow: hidden; border: 1px solid rgb(226 232 240); border-radius: 1rem; background: white; padding: 1rem; box-shadow: 0 1px 2px rgb(15 23 42 / .05); }
  .icon-wrap { display: grid; width: 2.75rem; height: 2.75rem; flex: none; place-items: center; border-radius: .85rem; background: rgb(237 233 254); color: rgb(91 33 182); }
  .field-label { display: block; min-width: 0; font-size: .75rem; font-weight: 700; color: rgb(51 65 85); }
  .field-label > span:first-child { display: block; margin-bottom: .35rem; }
  .field { width: 100%; max-width: 100%; min-width: 0; border: 1px solid rgb(203 213 225); border-radius: .75rem; background: white; padding: .7rem .8rem; color: rgb(15 23 42); font-weight: 400; }
  .field:focus { border-color: rgb(124 58 237); outline: 2px solid rgb(237 233 254); outline-offset: 1px; }
  .permission-row { display: flex; min-width: 0; align-items: flex-start; gap: .75rem; border: 1px solid rgb(226 232 240); border-radius: .85rem; padding: .8rem; }
  .danger-permission { border-color: rgb(254 202 202); background: rgb(254 242 242); }
  .status-pill { flex: none; border-radius: 999px; background: rgb(209 250 229); padding: .35rem .65rem; font-size: .7rem; font-weight: 900; color: rgb(6 95 70); }
  .selected-inactive { background: rgb(241 245 249); color: rgb(71 85 105); }
  .field-error { display: block; margin-top: .35rem; overflow-wrap: anywhere; font-size: .75rem; font-weight: 700; color: rgb(185 28 28); }
  .alert-error, .alert-success { margin-top: 1rem; display: flex; min-width: 0; align-items: flex-start; gap: .5rem; overflow-wrap: anywhere; border-radius: 1rem; padding: 1rem; font-size: .875rem; font-weight: 700; }
  .alert-error { border: 1px solid rgb(254 202 202); background: rgb(254 242 242); color: rgb(153 27 27); }
  .alert-success { border: 1px solid rgb(167 243 208); background: rgb(236 253 245); color: rgb(6 95 70); }
  .empty-card { margin-top: 1rem; border: 1px solid rgb(226 232 240); border-radius: 1rem; background: white; padding: 2rem 1rem; text-align: center; }
  .empty-card h2 { font-size: 1.25rem; font-weight: 900; }
  .empty-card p { margin-top: .5rem; font-size: .875rem; color: rgb(71 85 105); }
</style>
