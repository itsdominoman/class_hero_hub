<script lang="ts">
  import '../app.css';
  import { onMount } from 'svelte';
  import { api } from '$lib/api';

  let { children } = $props();
  let currentParent = $state(null);

  async function loadSession() {
    try {
      currentParent = await api.get('/me');
    } catch {
      currentParent = null;
    }
  }

  async function handleLogout() {
    try {
      await api.post('/auth/logout', {});
    } finally {
      currentParent = null;
      window.location.href = '/';
    }
  }

  onMount(loadSession);

  let dashboardHref = $derived(currentParent ? '/parent' : '/login');
</script>

<div class="min-h-dvh max-w-full overflow-x-hidden flex flex-col">
  <header class="bg-white/80 backdrop-blur-xl sticky top-0 z-50 border-b border-slate-200/50 shadow-sm pt-[var(--safe-top)]">
    <div class="max-w-7xl mx-auto px-3 sm:px-4 min-h-20 py-3 flex items-center justify-between gap-3">
      <a href="/" class="flex min-w-0 items-center gap-3 group">
        <img src="/family-hero-hub-logo.png" alt="Family Hero Hub" class="w-11 h-11 sm:w-12 sm:h-12 rounded-2xl object-cover shadow-xl shadow-hero/30 group-hover:rotate-6 transition-all duration-300 shrink-0" />
        <div class="flex flex-col -space-y-1 min-w-0">
          <span class="truncate text-lg sm:text-2xl font-black tracking-tighter text-slate-900 uppercase leading-none">Family Hero</span>
          <span class="text-xs font-black text-hero tracking-[0.22em] uppercase opacity-80 leading-none">Hub</span>
        </div>
      </a>
      
      <nav class="hidden md:flex items-center gap-8">
        <a href={dashboardHref} class="text-sm font-black text-slate-500 hover:text-hero uppercase tracking-widest transition-colors">
          {currentParent ? 'Parent Dashboard' : 'Login'}
        </a>
        {#if currentParent && currentParent.is_admin}
          <a href="/admin/registration-requests" class="text-sm font-black text-slate-500 hover:text-hero uppercase tracking-widest transition-colors">
            Admin
          </a>
        {/if}
        {#if currentParent}
          <button onclick={handleLogout} class="btn-hero px-6 py-3 rounded-2xl text-sm uppercase tracking-widest">Logout</button>
        {/if}
      </nav>

      {#if currentParent}
        <button onclick={handleLogout} class="md:hidden inline-flex shrink-0 items-center justify-center rounded-full border border-slate-200 bg-white px-3 py-2 text-[10px] font-black uppercase tracking-[0.1em] text-slate-700 shadow-sm transition hover:border-hero hover:text-hero">
          Logout
        </button>
      {:else}
        <a href={dashboardHref} class="md:hidden inline-flex shrink-0 items-center justify-center rounded-full bg-slate-900 px-4 py-2.5 text-xs font-black uppercase tracking-[0.12em] text-white shadow-sm">
          Login
        </a>
      {/if}
    </div>
  </header>

  <main class="flex-1 max-w-full overflow-x-hidden">
    {@render children()}
  </main>

  <footer class="bg-slate-900 text-slate-400 pt-16 pb-[calc(4rem+var(--safe-bottom))] md:pt-20 mt-16 md:mt-20 relative overflow-hidden">
    <div class="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-hero/50 to-transparent"></div>
    <div class="max-w-7xl mx-auto px-4">
      <div class="grid gap-10 lg:grid-cols-[1.1fr_0.9fr] lg:gap-12">
        <div class="text-left">
          <div class="flex items-center gap-3 mb-6 opacity-50 grayscale">
            <img src="/family-hero-hub-logo.png" alt="Family Hero Hub" class="w-10 h-10 rounded-xl object-cover bg-white" />
            <span class="text-xl font-black tracking-tighter text-white uppercase">Family Hero Hub</span>
          </div>
          <p class="text-lg leading-relaxed max-w-md">Family Hero Hub is a private, parent-led family app for points, rewards, routines, school prep, and everyday responsibility.</p>
          <p class="mt-6 text-sm font-black uppercase tracking-[0.2em] text-white">Built for families. Controlled by parents. Designed for children.</p>
        </div>

        <div class="grid gap-8 sm:grid-cols-3">
          <div class="min-w-0">
            <p class="text-white font-black uppercase tracking-[0.18em] text-sm mb-4">Product</p>
            <div class="flex flex-col gap-3 text-sm font-semibold">
              <a href="/" class="hover:text-hero transition-colors">Home</a>
              <a href="/#how-it-works" class="hover:text-hero transition-colors">How it works</a>
              <a href="/faq" class="hover:text-hero transition-colors">FAQ</a>
              <a href="/request-access" class="hover:text-hero transition-colors">Request access</a>
            </div>
          </div>

          <div class="min-w-0">
            <p class="text-white font-black uppercase tracking-[0.18em] text-sm mb-4">Support</p>
            <div class="flex flex-col gap-3 text-sm font-semibold">
              <a href="/contact" class="hover:text-hero transition-colors">Contact</a>
              <a href="/parent-guide" class="hover:text-hero transition-colors">Parent guide</a>
              <a href="/child-guide" class="hover:text-hero transition-colors">Child guide</a>
            </div>
          </div>

          <div class="min-w-0">
            <p class="text-white font-black uppercase tracking-[0.18em] text-sm mb-4">Legal</p>
            <div class="flex flex-col gap-3 text-sm font-semibold">
              <a href="/privacy" class="hover:text-hero transition-colors">Privacy Policy</a>
              <a href="/terms" class="hover:text-hero transition-colors">Terms of Service</a>
            </div>
          </div>
        </div>
      </div>
    </div>
  </footer>
</div>
