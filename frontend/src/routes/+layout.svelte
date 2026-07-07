<script lang="ts">
  import '../app.css';
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { api } from '$lib/api';
  import { initI18n } from '$lib/i18n';

  type UserSession = {
    is_platform_admin?: boolean;
  };

  let { children } = $props();
  let currentUser = $state<UserSession | null>(null);

  async function loadSession() {
    try {
      currentUser = await api.get('/me');
    } catch {
      currentUser = null;
    }
  }

  async function handleLogout() {
    try {
      await api.post('/auth/logout', {});
    } finally {
      currentUser = null;
      window.location.href = '/';
    }
  }

  initI18n();

  onMount(loadSession);

  let dashboardHref = $derived(currentUser ? '/parent' : '/login');
</script>

<div class="min-h-dvh max-w-full overflow-x-hidden flex flex-col">
  <header class="bg-white/80 backdrop-blur-xl sticky top-0 z-50 border-b border-slate-200/50 shadow-sm pt-[var(--safe-top)]">
    <div class="max-w-7xl mx-auto px-3 sm:px-4 min-h-20 py-3 flex items-center justify-between gap-3">
      <a href="/" class="flex min-w-0 items-center gap-3 group">
        <img src="/family-hero-hub-logo.png" alt={$_('app.name')} class="w-11 h-11 sm:w-12 sm:h-12 rounded-2xl object-cover shadow-xl shadow-hero/30 group-hover:rotate-6 transition-all duration-300 shrink-0" />
        <div class="flex flex-col -space-y-1 min-w-0">
          <span class="truncate text-lg sm:text-2xl font-bold tracking-tighter text-slate-900 uppercase leading-none">{$_('app.classHero')}</span>
          <span class="text-xs font-bold text-hero tracking-wide uppercase opacity-80 leading-none">{$_('app.hub')}</span>
        </div>
      </a>
      
      <nav class="hidden md:flex items-center gap-8">
        <a href={dashboardHref} class="text-sm font-bold text-slate-500 hover:text-hero uppercase tracking-wide transition-colors">
          {currentUser ? $_('nav.dashboard') : $_('nav.login')}
        </a>
        {#if currentUser && currentUser.is_platform_admin}
          <a href="/platform" class="text-sm font-bold text-slate-500 hover:text-hero uppercase tracking-wide transition-colors">
            {$_('nav.admin')}
          </a>
        {/if}
        {#if currentUser}
          <button onclick={handleLogout} class="btn-hero px-6 py-3 rounded-2xl text-sm uppercase tracking-wide">{$_('nav.logout')}</button>
        {/if}
      </nav>

      {#if currentUser}
        <button onclick={handleLogout} class="md:hidden inline-flex shrink-0 items-center justify-center rounded-full border border-slate-200 bg-white px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-slate-700 shadow-sm transition hover:border-hero hover:text-hero">
          {$_('nav.logout')}
        </button>
      {:else}
        <a href={dashboardHref} class="md:hidden inline-flex shrink-0 items-center justify-center rounded-full bg-slate-900 px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-white shadow-sm">
          {$_('nav.login')}
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
            <img src="/family-hero-hub-logo.png" alt={$_('app.name')} class="w-10 h-10 rounded-xl object-cover bg-white" />
            <span class="text-xl font-bold tracking-tighter text-white uppercase">{$_('app.name')}</span>
          </div>
          <p class="text-lg leading-relaxed max-w-md">{$_('footer.description')}</p>
          <p class="mt-6 text-sm font-semibold uppercase tracking-wide text-white">{$_('footer.tagline')}</p>
        </div>

        <div class="grid gap-8 sm:grid-cols-3">
          <div class="min-w-0">
            <p class="text-white font-semibold uppercase tracking-wide text-sm mb-4">{$_('nav.product')}</p>
            <div class="flex flex-col gap-3 text-sm font-semibold">
              <a href="/" class="hover:text-hero transition-colors">{$_('nav.home')}</a>
              <a href="/#how-it-works" class="hover:text-hero transition-colors">{$_('nav.howItWorks')}</a>
              <a href="/faq" class="hover:text-hero transition-colors">{$_('nav.faq')}</a>
            </div>
          </div>

          <div class="min-w-0">
            <p class="text-white font-semibold uppercase tracking-wide text-sm mb-4">{$_('nav.support')}</p>
            <div class="flex flex-col gap-3 text-sm font-semibold">
              <a href="/contact" class="hover:text-hero transition-colors">{$_('nav.contact')}</a>
              <a href="/safety-privacy" class="hover:text-hero transition-colors">{$_('nav.safetyPrivacy')}</a>
            </div>
          </div>

          <div class="min-w-0">
            <p class="text-white font-semibold uppercase tracking-wide text-sm mb-4">{$_('nav.legal')}</p>
            <div class="flex flex-col gap-3 text-sm font-semibold">
              <a href="/privacy" class="hover:text-hero transition-colors">{$_('nav.privacyPolicy')}</a>
              <a href="/terms" class="hover:text-hero transition-colors">{$_('nav.terms')}</a>
            </div>
          </div>
        </div>
      </div>
    </div>
  </footer>
</div>
