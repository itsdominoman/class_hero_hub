<script lang="ts">
  import { onMount } from 'svelte';
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

  onMount(async () => {
    try {
      loading = true;
      error = null;
      const result = await api.post('/child-link/exchange', { token }) as ExchangeResponse;
      childName = result.child.display_name;
      window.location.replace(`/child/${result.child.id}`);
    } catch (e) {
      error = e instanceof Error ? e.message : 'Could not link this device';
      loading = false;
    }
  });
</script>

<div class="min-h-screen bg-[linear-gradient(180deg,#fffaf4_0%,#ffffff_100%)] flex items-center justify-center px-4 py-20 overflow-x-hidden">
  <div class="card bg-white max-w-xl w-full min-w-0 p-8 md:p-10 text-center border border-slate-100 shadow-2xl">
    {#if loading}
      <div class="flex flex-col items-center gap-4">
        <div class="w-16 h-16 rounded-2xl bg-hero/10 text-hero flex items-center justify-center animate-pulse">
          <Sparkles size={30} />
        </div>
        <h1 class="text-3xl font-black text-slate-950">Linking child device</h1>
        <p class="text-slate-600 max-w-md">
          We are opening the dashboard now.
        </p>
        <div class="animate-spin w-12 h-12 border-4 border-hero border-t-transparent rounded-full mt-2"></div>
      </div>
    {:else if error}
      <div class="flex flex-col items-center gap-4">
        <div class="w-16 h-16 rounded-2xl bg-red-100 text-red-600 flex items-center justify-center">
          <ShieldCheck size={30} />
        </div>
        <h1 class="text-3xl font-black text-slate-950">Link expired</h1>
        <p class="text-slate-600 max-w-md break-words">{error}</p>
        <p class="text-xs font-black uppercase tracking-[0.22em] text-slate-400">
          Ask a parent to generate a fresh QR code.
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
