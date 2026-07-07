<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { api } from '$lib/api';

  let { children } = $props();
  let loading = $state(true);
  let allowed = $state(false);
  let error = $state<string | null>(null);

  onMount(async () => {
    try {
      const me = await api.get('/me/v2');
      allowed = Boolean(me?.is_platform_admin);
      if (!allowed) error = $_('platform.accessDenied');
    } catch (err: any) {
      if (err?.status === 401) {
        window.location.href = `/login?returnTo=${encodeURIComponent('/platform')}`;
        return;
      }
      error = err?.message || $_('platform.loadError');
    } finally {
      loading = false;
    }
  });
</script>

<svelte:head>
  <title>{$_('platform.title')}</title>
</svelte:head>

{#if loading}
  <section class="mx-auto max-w-5xl px-4 py-12">
    <div class="card p-8 text-center">
      <p class="text-sm font-semibold uppercase tracking-wide text-slate-500">{$_('common.loading')}</p>
    </div>
  </section>
{:else if !allowed}
  <section class="mx-auto max-w-3xl px-4 py-12">
    <div class="card p-8 text-center">
      <h1 class="text-2xl font-black text-slate-900">{$_('platform.accessDeniedTitle')}</h1>
      <p class="mt-3 text-slate-600">{error}</p>
    </div>
  </section>
{:else}
  {@render children()}
{/if}
