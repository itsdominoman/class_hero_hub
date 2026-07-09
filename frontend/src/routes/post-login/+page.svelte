<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { api } from '$lib/api';
  import { defaultLandingPath } from '$lib/roleRouting';

  onMount(async () => {
    let target = '/login';
    try {
      const me = await api.get('/me');
      target = defaultLandingPath(me);
    } catch {
      target = '/login';
    }
    window.location.href = target;
  });
</script>

<svelte:head>
  <title>{$_('postLogin.title')}</title>
</svelte:head>

<div class="flex min-h-[calc(100dvh-5rem)] items-center justify-center px-4">
  <p class="text-sm font-semibold uppercase tracking-wide text-slate-500">{$_('postLogin.redirecting')}</p>
</div>
