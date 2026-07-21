<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { ArrowRight, KeyRound, MessageSquare } from 'lucide-svelte';
  import { api } from '$lib/api';
  import SafeguardingHeader from '$lib/components/safeguarding/SafeguardingHeader.svelte';
  import {
    findEligibleSafeguardingMemberships,
    membershipHref,
    requestedMembershipId,
    type EligibleSafeguardingMembership
  } from '$lib/safeguarding/context';
  import type { SafeguardingContext, SafeguardingMembership } from '$lib/safeguarding/types';
  import type { SessionUser } from '$lib/roleRouting';

  let loading = $state(true);
  let error = $state<string | null>(null);
  let eligible = $state<EligibleSafeguardingMembership[]>([]);
  let memberships = $state<SafeguardingMembership[]>([]);
  let membership = $state<SafeguardingMembership | null>(null);
  let context = $state<SafeguardingContext | null>(null);
  let canReview = $derived(Boolean(context?.permissions.includes('messaging.safeguarding_review')));
  let canManage = $derived(Boolean(context?.permissions.includes('messaging.manage_safeguarding_permissions')));

  function messageForFailure(value: unknown) {
    return value instanceof Error ? value.message : $_('safeguarding.errors.failed');
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
      if (chosen) setMembership(chosen);
    } catch (value) {
      error = messageForFailure(value);
    } finally {
      loading = false;
    }
  }

  function changeMembership(event: Event) {
    const id = Number((event.currentTarget as HTMLSelectElement).value);
    const chosen = eligible.find((row) => row.membership.membership_id === id);
    if (chosen) setMembership(chosen);
  }

  onMount(() => void initialize());
</script>

<svelte:head><title>{$_('safeguarding.home.title')} · {$_('app.name')}</title></svelte:head>

<div class="min-h-full min-w-0 bg-slate-50 pb-12">
  <div class="mx-auto w-full min-w-0 max-w-5xl px-3 py-4 sm:px-6 sm:py-6">
    <SafeguardingHeader
      title={$_('safeguarding.home.title')}
      subtitle={$_('safeguarding.home.subtitle')}
      {context}
      {memberships}
      {membership}
      onMembershipChange={changeMembership}
    />

    {#if error}<div class="alert-error" role="alert">{error}</div>{/if}

    {#if loading}
      <div class="grid min-h-52 place-items-center text-sm font-bold text-slate-500">{$_('common.loading')}</div>
    {:else if !context || !membership}
      <section class="empty-card">
        <h2 class="text-xl font-black text-slate-900">{$_('safeguarding.noAccessTitle')}</h2>
        <p class="mt-2 text-sm text-slate-600">{$_('safeguarding.noAccessBody')}</p>
      </section>
    {:else}
      <section class="mt-4 grid min-w-0 gap-3 md:grid-cols-2" aria-label={$_('safeguarding.home.actions')}>
        {#if canReview}
          <a class="action-card group" href={membershipHref('/school/safeguarding/message-reviews', membership)} data-testid="message-reviews-action">
            <span class="icon-wrap bg-amber-100 text-amber-800"><MessageSquare class="h-6 w-6" aria-hidden="true" /></span>
            <span class="min-w-0 flex-1">
              <strong class="block text-lg font-black text-slate-950">{$_('safeguarding.home.messageReviews')}</strong>
              <span class="mt-1 block text-sm leading-5 text-slate-600">{$_('safeguarding.home.messageReviewsBody')}</span>
            </span>
            <ArrowRight class="h-5 w-5 shrink-0 text-slate-400 transition group-hover:translate-x-1 rtl:-scale-x-100" aria-hidden="true" />
          </a>
        {/if}

        {#if canManage}
          <a class="action-card group" href={membershipHref('/school/safeguarding/permissions', membership)} data-testid="permission-management-action">
            <span class="icon-wrap bg-violet-100 text-violet-800"><KeyRound class="h-6 w-6" aria-hidden="true" /></span>
            <span class="min-w-0 flex-1">
              <strong class="block text-lg font-black text-slate-950">{$_('safeguarding.home.permissionManagement')}</strong>
              <span class="mt-1 block text-sm leading-5 text-slate-600">{$_('safeguarding.home.permissionManagementBody')}</span>
            </span>
            <ArrowRight class="h-5 w-5 shrink-0 text-slate-400 transition group-hover:translate-x-1 rtl:-scale-x-100" aria-hidden="true" />
          </a>
        {/if}
      </section>

      <aside class="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-950">
        <strong class="block">{$_('safeguarding.home.auditedTitle')}</strong>
        <span>{$_('safeguarding.home.auditedBody')}</span>
      </aside>
    {/if}
  </div>
</div>

<style>
  .action-card { display: flex; min-width: 0; align-items: center; gap: .85rem; border: 1px solid rgb(226 232 240); border-radius: 1rem; background: white; padding: 1rem; box-shadow: 0 1px 2px rgb(15 23 42 / .05); }
  .action-card:hover { border-color: rgb(245 158 11); box-shadow: 0 8px 24px rgb(15 23 42 / .08); }
  .icon-wrap { display: grid; width: 2.75rem; height: 2.75rem; flex: none; place-items: center; border-radius: .85rem; }
  .alert-error { margin-top: 1rem; overflow-wrap: anywhere; border: 1px solid rgb(254 202 202); border-radius: 1rem; background: rgb(254 242 242); padding: 1rem; font-size: .875rem; font-weight: 700; color: rgb(153 27 27); }
  .empty-card { margin-top: 1rem; border: 1px solid rgb(226 232 240); border-radius: 1rem; background: white; padding: 2rem 1rem; text-align: center; box-shadow: 0 1px 2px rgb(15 23 42 / .05); }
</style>
