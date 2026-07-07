<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/state';
  import { _ } from 'svelte-i18n';
  import { api } from '$lib/api';

  const token = page.params.token || '';
  let loading = $state(true);
  let error = $state<string | null>(null);

  async function exchangeInvite() {
    loading = true;
    error = null;
    try {
      await api.get('/me/v2');
    } catch (err: any) {
      if (err?.status === 401) {
        const returnTo = `/invite/${encodeURIComponent(token)}`;
        window.location.href = `/login?returnTo=${encodeURIComponent(returnTo)}`;
        return;
      }
      error = err?.message || $_('invite.loadError');
      loading = false;
      return;
    }

    try {
      const result = await api.post('/invites/exchange', { token });
      window.location.href = result?.landing_path || (result?.membership?.role === 'teacher' ? '/teach' : '/school');
    } catch (err: any) {
      error = err?.message || $_('invite.exchangeError');
      loading = false;
    }
  }

  onMount(exchangeInvite);
</script>

<svelte:head>
  <title>{$_('invite.title')}</title>
</svelte:head>

<section class="mx-auto flex min-h-[calc(100dvh-5rem)] max-w-xl items-center px-4 py-12">
  <div class="w-full rounded-lg border border-slate-200 bg-white p-8 text-center shadow-sm">
    {#if loading}
      <p class="text-sm font-semibold uppercase tracking-wide text-slate-500">{$_('invite.accepting')}</p>
    {:else}
      <h1 class="text-2xl font-black text-slate-900">{$_('invite.errorTitle')}</h1>
      <p class="mt-3 text-red-600">{error}</p>
      <a href="/login" class="btn-hero mt-6 inline-flex rounded-lg px-5 py-3">{$_('nav.login')}</a>
    {/if}
  </div>
</section>
