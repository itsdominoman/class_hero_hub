<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { page } from '$app/state';
  import { api } from '$lib/api';
  import { ArrowRight, ShieldCheck, Sparkles } from 'lucide-svelte';

  type ExchangeResponse = {
    child: {
      id: number;
      display_name: string;
    };
    session_expires_at: string;
  };

  let token = $derived(page.params.token);
  let loading = $state(true);
  let error = $state<string | null>(null);
  let childName = $state('');

  const getErrorMessageText = (e: unknown) =>
    e instanceof Error ? e.message : typeof e === 'string' ? e : '';

  const getLinkErrorMessage = (e: unknown) => {
    const message = getErrorMessageText(e).trim().toLowerCase();

    if (
      message.includes('invalid or expired child link') ||
      message.includes('invalid child link') ||
      message.includes('expired child link')
    ) {
      return $_('childLink.invalidOrExpired');
    }

    return $_('childLink.genericLinkError');
  };

  onMount(async () => {
    try {
      loading = true;
      error = null;
      const result = await api.post('/child-link/exchange', { token }) as ExchangeResponse;
      childName = result.child.display_name;
      window.location.replace(`/child/${result.child.id}`);
    } catch (e) {
      error = getLinkErrorMessage(e);
      loading = false;
    }
  });
</script>

<div class="min-h-dvh bg-[linear-gradient(180deg,#fffaf4_0%,#ffffff_100%)] flex items-center justify-center px-3 sm:px-4 py-[calc(3rem+var(--safe-top))] pb-[calc(3rem+var(--safe-bottom))] overflow-x-hidden">
  <div class="card bg-white max-w-xl w-full min-w-0 p-6 sm:p-8 md:p-10 text-center border border-slate-100 shadow-2xl">
    {#if loading}
      <div class="flex flex-col items-center gap-4">
        <div class="w-16 h-16 rounded-2xl bg-hero/10 text-hero flex items-center justify-center animate-pulse">
          <Sparkles size={30} />
        </div>
        <h1 class="text-2xl sm:text-3xl font-black text-slate-950">{$_('childLink.loadingTitle')}</h1>
        <p class="text-slate-600 max-w-md">
          {$_('childLink.loadingText')}
        </p>
        <div class="animate-spin w-12 h-12 border-4 border-hero border-t-transparent rounded-full mt-2"></div>
      </div>
    {:else if error}
      <div class="flex flex-col items-center gap-4">
        <div class="w-16 h-16 rounded-2xl bg-red-100 text-red-600 flex items-center justify-center">
          <ShieldCheck size={30} />
        </div>
        <h1 class="text-2xl sm:text-3xl font-black text-slate-950">{$_('childLink.errorTitle')}</h1>
        <p class="text-slate-600 max-w-md break-words">{error}</p>
        <p class="text-xs font-black uppercase tracking-[0.22em] text-slate-400">
          {$_('childLink.errorHint')}
        </p>
      </div>
    {/if}
  </div>
</div>

<style>
  :global(.card) {
    border-radius: 2rem;
  }
</style>
