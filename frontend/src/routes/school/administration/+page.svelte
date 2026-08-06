<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { api } from '$lib/api';

  type Membership = { school_id: number; membership_id: number; school_name: string; role: string; capabilities: string[] };

  let membership = $state<Membership | null>(null);
  let governance = $state<any>(null);
  let loading = $state(true);
  let error = $state('');

  function options() {
    return membership
      ? { headers: { 'X-School-Id': String(membership.school_id), 'X-Membership-Id': String(membership.membership_id) } }
      : {};
  }

  async function load() {
    loading = true;
    error = '';
    try {
      const me = await api.get('/me');
      membership = (me.memberships || []).find((row: Membership) => row.role === 'school_admin') || null;
      if (!membership) throw new Error($_('administration.accessDenied'));
      governance = await api.get('/school/governance', options());
    } catch (caught: any) {
      error = caught?.message || $_('administration.loadError');
    } finally {
      loading = false;
    }
  }

  onMount(load);
</script>

<svelte:head><title>{$_('administration.title')} | {$_('app.name')}</title></svelte:head>

<section class="mx-auto max-w-6xl px-4 py-8">
  <p class="eyebrow">{$_('administration.eyebrow')}</p>
  <h1 class="mt-2 text-3xl font-black text-slate-900">{$_('administration.title')}</h1>
  <p class="mt-2 max-w-3xl text-slate-600">{$_('administration.intro')}</p>

  {#if error}
    <div class="mt-5 rounded-xl border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">{error}</div>
  {/if}

  {#if loading}
    <div class="card mt-6 p-6">{$_('common.loading')}…</div>
  {:else if membership && governance}
    <div class="mt-6 grid gap-4 sm:grid-cols-2">
      {#if membership.capabilities.includes('positive_recognition')}
      <a href="/school/recognition" class="card group flex min-h-44 flex-col p-6 transition hover:-translate-y-0.5 hover:border-hero/40 hover:shadow-xl">
        <span class="text-xs font-black uppercase tracking-wide text-emerald-700">{$_('recognitionPage.eyebrow')}</span>
        <h2 class="mt-2 text-xl font-black text-slate-900">{$_('recognitionPage.title')}</h2>
        <p class="mt-2 flex-1 text-sm leading-6 text-slate-600">{$_('recognitionPage.adminCardHelp')}</p>
        <span class="mt-5 font-black text-hero">{$_('administration.open')} <span class="inline-block rtl:-scale-x-100" aria-hidden="true">→</span></span>
      </a>
      {/if}

      <a href="/school?tab=settings#compliance-feature-controls-title" class="card group flex min-h-44 flex-col p-6 transition hover:-translate-y-0.5 hover:border-hero/40 hover:shadow-xl">
        <span class="text-xs font-black uppercase tracking-wide text-slate-500">{$_('administration.restricted')}</span>
        <h2 class="mt-2 text-xl font-black text-slate-900">{$_('administration.compliance')}</h2>
        <p class="mt-2 flex-1 text-sm leading-6 text-slate-600">{$_('administration.complianceHelp')}</p>
        <span class="mt-5 font-black text-hero">{$_('administration.open')} <span class="inline-block rtl:-scale-x-100" aria-hidden="true">→</span></span>
      </a>

      {#if governance.is_current_owner}
        <a href="/school/governance" class="card group flex min-h-44 flex-col p-6 transition hover:-translate-y-0.5 hover:border-hero/40 hover:shadow-xl">
          <span class="text-xs font-black uppercase tracking-wide text-slate-500">{$_('governancePage.eyebrow')}</span>
          <h2 class="mt-2 text-xl font-black text-slate-900">{$_('administration.systemOwner')}</h2>
          <p class="mt-2 flex-1 text-sm leading-6 text-slate-600">{$_('administration.systemOwnerHelp')}</p>
          <span class="mt-5 font-black text-hero">{$_('administration.open')} <span class="inline-block rtl:-scale-x-100" aria-hidden="true">→</span></span>
        </a>

      {/if}
    </div>
    <p class="mt-5 text-sm text-slate-500">{$_('administration.restrictedHelp')}</p>
  {/if}
</section>
