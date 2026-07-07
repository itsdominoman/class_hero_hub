<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { api } from '$lib/api';

  type Identity = {
    id?: number;
    email?: string | null;
    name?: string | null;
    is_admin?: boolean;
    school_roles?: string[];
  };

  let identity = $state<Identity | null>(null);
  let loading = $state(true);
  let error = $state<string | null>(null);

  async function loadIdentity() {
    loading = true;
    error = null;
    try {
      identity = await api.get('/me');
    } catch (err: any) {
      error = err?.message || $_('parent.failedLoad');
      identity = null;
    } finally {
      loading = false;
    }
  }

  onMount(loadIdentity);
</script>

<svelte:head>
  <title>{$_('parent.title')}</title>
</svelte:head>

<div class="mx-auto max-w-3xl px-4 py-12">
  {#if loading}
    <div class="card p-8 text-center">
      <p class="text-sm font-semibold uppercase tracking-wide text-slate-500">{$_('common.loading')}</p>
    </div>
  {:else if error}
    <div class="card p-8 text-center">
      <h1 class="text-3xl font-black text-slate-900">{$_('parent.loginRequired')}</h1>
      <p class="mt-3 text-slate-600">{error}</p>
      <a href="/login" class="btn-hero mt-6 inline-flex rounded-2xl px-6 py-3">{$_('parent.goToLogin')}</a>
    </div>
  {:else}
    <section class="card p-8">
      <p class="text-sm font-bold uppercase tracking-wide text-hero">{$_('parent.eyebrow')}</p>
      <h1 class="mt-3 text-3xl font-black text-slate-900">{$_('parent.noRoleHeading')}</h1>
      <p class="mt-4 text-lg leading-relaxed text-slate-600">{$_('parent.noRoleText')}</p>

      {#if identity?.email || identity?.name}
        <div class="mt-8 rounded-2xl border border-slate-200 bg-slate-50 p-5">
          <p class="text-xs font-bold uppercase tracking-wide text-slate-400">{$_('parent.signedInAs')}</p>
          <p class="mt-2 font-bold text-slate-900">{identity.name || identity.email}</p>
          {#if identity.name && identity.email}
            <p class="mt-1 text-sm text-slate-500">{identity.email}</p>
          {/if}
        </div>
      {/if}
    </section>
  {/if}
</div>
