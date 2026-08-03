<script lang="ts">
  import { onMount, tick } from 'svelte';
  import { page } from '$app/state';
  import { _, locale } from 'svelte-i18n';
  import { api } from '$lib/api';
  import {
    capabilityDependents,
    entitlementRelationshipBlock,
    entitlementStatus,
    isCapabilityKey,
    type CapabilityKey,
    type EntitlementRelationshipBlock,
    type EntitlementSource,
    type SchoolEntitlement,
    type SchoolEntitlementPayload
  } from '$lib/entitlements';
  import type { SessionUser } from '$lib/roleRouting';

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
    name_ar?: string | null;
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
  let canManageEntitlements = $state(false);
  let entitlements = $state<SchoolEntitlementPayload | null>(null);
  let savingCapability = $state<string | null>(null);
  let entitlementMessage = $state<string | null>(null);
  let entitlementError = $state<string | null>(null);
  let relationshipBlock = $state<EntitlementRelationshipBlock | null>(null);
  let relationshipDialog = $state<HTMLDivElement | null>(null);

  const entitlementSources: EntitlementSource[] = ['pilot', 'trial', 'paid', 'complimentary'];
  const today = () => new Date().toISOString().slice(0, 10);

  const formatDate = (value?: string | null) => value ? new Intl.DateTimeFormat($locale === 'ar' ? 'ar' : undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : '-';
  const roleCount = (role: string) => school?.counts?.memberships_by_role?.[role] || 0;

  function capabilityLabel(capability: CapabilityKey): string {
    return String($_(`entitlements.capabilities.${capability}`));
  }

  function capabilityList(capabilities: CapabilityKey[]): string {
    return new Intl.ListFormat($locale === 'ar' ? 'ar' : 'en', { style: 'long', type: 'conjunction' })
      .format(capabilities.map(capabilityLabel));
  }

  function showRelationshipBlock(block: EntitlementRelationshipBlock) {
    relationshipBlock = block;
    void tick().then(() => relationshipDialog?.focus());
  }

  function closeRelationshipBlock() {
    relationshipBlock = null;
  }

  function reviewCapability(capability: CapabilityKey) {
    relationshipBlock = null;
    void tick().then(() => {
      const card = document.getElementById(`entitlement-${capability}`);
      card?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      card?.focus({ preventScroll: true });
    });
  }

  function relationshipTitle(block: EntitlementRelationshipBlock): string {
    if (block.reason === 'enabled_dependents') {
      return String($_('entitlements.blockedDisableTitle', { values: { feature: capabilityLabel(block.capability) } }));
    }
    if (block.reason === 'missing_dependencies') {
      return String($_('entitlements.blockedEnableTitle', { values: { feature: capabilityLabel(block.capability) } }));
    }
    return String($_('entitlements.blockedDatesTitle'));
  }

  function relationshipBody(block: EntitlementRelationshipBlock): string {
    if (block.reason === 'enabled_dependents') {
      const key = block.related.length === 1 ? 'entitlements.blockedDisableBodyOne' : 'entitlements.blockedDisableBodyMany';
      return String($_(key, { values: { dependents: capabilityList(block.related), dependent: capabilityList(block.related) } }));
    }
    if (block.reason === 'missing_dependencies') {
      const key = block.related.length === 1 ? 'entitlements.blockedEnableBodyOne' : 'entitlements.blockedEnableBodyMany';
      return String($_(key, {
        values: {
          feature: capabilityLabel(block.capability),
          dependencies: capabilityList(block.related),
          dependency: capabilityList(block.related)
        }
      }));
    }
    const key = block.related.length === 1 ? 'entitlements.blockedDatesBodyOne' : 'entitlements.blockedDatesBodyMany';
    return String($_(key, {
      values: {
        feature: capabilityLabel(block.capability),
        dependencies: capabilityList(block.related),
        dependency: capabilityList(block.related)
      }
    }));
  }

  function relationshipTargets(block: EntitlementRelationshipBlock): CapabilityKey[] {
    return block.reason === 'dependency_window'
      ? [...new Set([block.capability, ...block.related])]
      : block.related;
  }

  function relationshipBlockFromError(err: any): EntitlementRelationshipBlock | null {
    const detail = err?.detail;
    if (!detail || !isCapabilityKey(detail.capability) || !isCapabilityKey(detail.dependency)) return null;
    if (detail.code === 'entitlement_dependency_window') {
      return { reason: 'dependency_window', capability: detail.capability, related: [detail.dependency] };
    }
    if (detail.code !== 'entitlement_dependency_required') return null;
    return detail.dependency === savingCapability
      ? { reason: 'enabled_dependents', capability: detail.dependency, related: [detail.capability] }
      : { reason: 'missing_dependencies', capability: detail.capability, related: [detail.dependency] };
  }

  async function loadSchool() {
    loading = true;
    error = null;
    try {
      const [schoolResponse, session] = await Promise.all([
        api.get(`/platform/schools/${schoolId}`),
        api.get('/me') as Promise<SessionUser>
      ]);
      school = schoolResponse;
      canManageEntitlements = Boolean(session.can_manage_school_entitlements);
      if (canManageEntitlements) {
        const response = await api.get(`/platform/schools/${schoolId}/entitlements`) as SchoolEntitlementPayload;
        entitlements = {
          ...response,
          entitlements: response.entitlements.map((row) => ({
            ...row,
            source: row.source || 'trial',
            effective_from: row.effective_from || today()
          }))
        };
      }
    } catch (err: any) {
      error = err?.message || $_('platform.loadError');
    } finally {
      loading = false;
    }
  }

  async function saveEntitlement(entitlement: SchoolEntitlement) {
    if (!entitlements || !entitlement.source || !entitlement.effective_from) return;
    const block = entitlementRelationshipBlock(entitlements.entitlements, entitlement);
    if (block) {
      showRelationshipBlock(block);
      return;
    }
    savingCapability = entitlement.capability;
    entitlementMessage = null;
    entitlementError = null;
    try {
      const updated = await api.put(
        `/platform/schools/${schoolId}/entitlements/${entitlement.capability}`,
        {
          enabled: entitlement.enabled,
          source: entitlement.source,
          effective_from: entitlement.effective_from,
          expires_on: entitlement.expires_on || null,
          internal_note: entitlement.internal_note?.trim() || null,
          expected_entitlement_version: entitlement.entitlement_version
        }
      ) as SchoolEntitlement;
      entitlements.entitlements = entitlements.entitlements.map((row) =>
        row.capability === updated.capability ? updated : row
      );
      entitlementMessage = $_('entitlements.saved');
    } catch (err: any) {
      const serverBlock = relationshipBlockFromError(err);
      if (serverBlock) showRelationshipBlock(serverBlock);
      else entitlementError = err?.message || $_('entitlements.saveError');
    } finally {
      savingCapability = null;
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
        <h1 class="mt-2 text-3xl font-black text-slate-900">{$locale === 'ar' && school.name_ar ? school.name_ar : school.name}</h1>
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

    {#if canManageEntitlements && entitlements}
      <section class="mt-8 rounded-3xl border border-slate-200 bg-slate-50 p-5 sm:p-7" aria-labelledby="school-entitlements-title">
        <div class="max-w-3xl">
          <p class="eyebrow">{$_('entitlements.optionalTitle')}</p>
          <h2 id="school-entitlements-title" class="mt-2 text-2xl font-black text-slate-950">{$_('entitlements.managerTitle')}</h2>
          <p class="mt-2 leading-7 text-slate-600">{$_('entitlements.managerIntro')}</p>
          <p class="mt-2 text-sm font-semibold leading-6 text-slate-500">{$_('entitlements.relationshipIntro')}</p>
        </div>

        <div class="mt-6 rounded-2xl border border-slate-200 bg-white p-5">
          <h3 class="font-black text-slate-900">{$_('entitlements.foundationTitle')}</h3>
          <p class="mt-1 text-sm text-slate-600">{$_('entitlements.foundationIntro')}</p>
          <ul class="mt-4 grid gap-2 text-sm font-bold text-slate-700 sm:grid-cols-2 lg:grid-cols-3">
            {#each entitlements.foundation as capability}
              <li class="rounded-xl bg-emerald-50 px-3 py-2 text-emerald-900">{$_(`entitlements.foundation.${capability}`)}</li>
            {/each}
          </ul>
        </div>

        {#if entitlementMessage}
          <p class="mt-5 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm font-bold text-emerald-800">{entitlementMessage}</p>
        {/if}
        {#if entitlementError}
          <p class="mt-5 rounded-xl border border-red-200 bg-red-50 p-3 text-sm font-bold text-red-700">{entitlementError}</p>
        {/if}

        <div class="mt-5 grid gap-5 xl:grid-cols-2">
          {#each entitlements.entitlements as entitlement (entitlement.capability)}
            {@const dependents = capabilityDependents(entitlements.entitlements, entitlement.capability)}
            <article id={`entitlement-${entitlement.capability}`} tabindex="-1" class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm outline-none focus-visible:ring-4 focus-visible:ring-violet-300/70">
              <div class="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 class="font-black text-slate-950">{$_(`entitlements.capabilities.${entitlement.capability}`)}</h3>
                  <p class="mt-1 text-xs font-bold uppercase tracking-wide text-slate-500">
                    {$_(`entitlements.statuses.${entitlementStatus(entitlement)}`)}
                  </p>
                </div>
                <label class="inline-flex items-center gap-2 text-sm font-bold text-slate-700">
                  <input type="checkbox" bind:checked={entitlement.enabled} class="h-5 w-5 rounded border-slate-300 text-hero" />
                  {$_('entitlements.statuses.enabled')}
                </label>
              </div>

              <div class="mt-5 grid gap-4 sm:grid-cols-2">
                <label class="grid gap-1 text-sm font-bold text-slate-700">
                  {$_('entitlements.source')}
                  <select bind:value={entitlement.source} class="rounded-xl border border-slate-300 bg-white px-3 py-2.5 font-medium">
                    {#each entitlementSources as source}
                      <option value={source}>{$_(`entitlements.sources.${source}`)}</option>
                    {/each}
                  </select>
                </label>
                <label class="grid gap-1 text-sm font-bold text-slate-700">
                  {$_('entitlements.effectiveFrom')}
                  <input required type="date" bind:value={entitlement.effective_from} class="rounded-xl border border-slate-300 px-3 py-2.5 font-medium" />
                </label>
                <label class="grid gap-1 text-sm font-bold text-slate-700 sm:col-span-2">
                  {$_('entitlements.expiresOn')}
                  <input type="date" bind:value={entitlement.expires_on} class="rounded-xl border border-slate-300 px-3 py-2.5 font-medium" />
                </label>
                <label class="grid gap-1 text-sm font-bold text-slate-700 sm:col-span-2">
                  {$_('entitlements.internalNote')}
                  <textarea bind:value={entitlement.internal_note} rows="3" class="rounded-xl border border-slate-300 px-3 py-2.5 font-medium"></textarea>
                </label>
              </div>

              <dl class="mt-4 space-y-2 text-sm text-slate-600">
                {#if entitlement.dependencies.length}
                  <div>
                    <dt class="inline font-bold text-slate-800">{$_('entitlements.dependencies')}: </dt>
                    <dd class="inline">{capabilityList(entitlement.dependencies)}</dd>
                  </div>
                {/if}
                {#if dependents.length}
                  <div>
                    <dt class="inline font-bold text-slate-800">{$_('entitlements.usedBy')}: </dt>
                    <dd class="inline">{capabilityList(dependents)}</dd>
                  </div>
                {/if}
                <div>
                  <dt class="inline font-bold text-slate-800">{$_('entitlements.lastChange')}: </dt>
                  <dd class="inline">
                    {entitlement.last_changed_at ? formatDate(entitlement.last_changed_at) : $_('entitlements.neverChanged')}
                    {entitlement.last_actor ? ` ${$_('entitlements.by', { values: { name: entitlement.last_actor.name } })}` : ''}
                  </dd>
                </div>
              </dl>

              <button
                type="button"
                class="btn-hero mt-5 w-full rounded-xl px-4 py-3 disabled:opacity-60"
                disabled={savingCapability === entitlement.capability || !entitlement.effective_from}
                onclick={() => saveEntitlement(entitlement)}
              >
                {$_('entitlements.save')}
              </button>
            </article>
          {/each}
        </div>
      </section>
    {/if}

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
                  <p class="mt-1 text-sm text-slate-500">{$locale === 'ar' ? $_(`platform.roles.${invite.role}`) : invite.role} · {$_(`platform.inviteStatuses.${invite.status}`)} · {formatDate(invite.created_at)}</p>
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

{#if relationshipBlock}
  <div
    class="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/55 p-0 sm:items-center sm:p-4"
    role="presentation"
    onclick={(event) => { if (event.target === event.currentTarget) closeRelationshipBlock(); }}
  >
    <div
      bind:this={relationshipDialog}
      class="w-full max-w-lg rounded-t-3xl bg-white p-6 shadow-2xl outline-none sm:rounded-3xl"
      role="dialog"
      aria-modal="true"
      aria-labelledby="entitlement-relationship-title"
      aria-describedby="entitlement-relationship-body"
      tabindex="-1"
      onkeydown={(event) => { if (event.key === 'Escape') closeRelationshipBlock(); }}
    >
      <h2 id="entitlement-relationship-title" class="text-2xl font-black text-slate-950">{relationshipTitle(relationshipBlock)}</h2>
      <p id="entitlement-relationship-body" class="mt-3 leading-7 text-slate-600">{relationshipBody(relationshipBlock)}</p>
      <div class="mt-6 grid gap-2 sm:grid-cols-2">
        {#each relationshipTargets(relationshipBlock) as capability}
          <button type="button" class="btn-hero rounded-xl px-4 py-3" onclick={() => reviewCapability(capability)}>
            {$_('entitlements.reviewFeature', { values: { feature: capabilityLabel(capability) } })}
          </button>
        {/each}
        <button type="button" class="btn-secondary rounded-xl px-4 py-3" onclick={closeRelationshipBlock}>{$_('entitlements.closeRelationship')}</button>
      </div>
    </div>
  </div>
{/if}
