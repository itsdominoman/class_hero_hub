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

<div class="min-h-screen flex flex-col">
  <header class="bg-white/80 backdrop-blur-xl sticky top-0 z-50 border-b border-slate-200/50 shadow-sm">
    <div class="max-w-7xl mx-auto px-4 h-20 flex items-center justify-between">
      <a href="/" class="flex items-center gap-3 group">
        <img src="/family-hero-hub-logo.png" alt="Family Hero Hub" class="w-12 h-12 rounded-2xl object-cover shadow-xl shadow-hero/30 group-hover:rotate-6 transition-all duration-300" />
        <div class="flex flex-col -space-y-1 min-w-0">
          <span class="text-xl sm:text-2xl font-black tracking-tighter text-slate-900 uppercase leading-none">Family Hero</span>
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

      <!-- Mobile Menu Button (Placeholder) -->
      <button aria-label="Open mobile menu" class="md:hidden w-10 h-10 flex items-center justify-center text-slate-500">
        <div class="w-6 h-0.5 bg-current mb-1.5 shadow-[0_6px_0_0_currentColor,0_12px_0_0_currentColor]"></div>
      </button>
    </div>
  </header>

  <main class="flex-1">
    {@render children()}
  </main>

  <footer class="bg-slate-900 text-slate-400 py-20 mt-20 relative overflow-hidden">
    <div class="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-hero/50 to-transparent"></div>
    <div class="max-w-7xl mx-auto px-4 grid md:grid-cols-2 gap-12 items-center">
      <div class="text-left">
        <div class="flex items-center gap-3 mb-6 opacity-50 grayscale">
          <img src="/family-hero-hub-logo.png" alt="Family Hero Hub" class="w-10 h-10 rounded-xl object-cover bg-white" />
          <span class="text-xl font-black tracking-tighter text-white uppercase">Family Hero Hub</span>
        </div>
        <p class="text-lg leading-relaxed max-w-md">Empowering the next generation with the responsibility they need to thrive.</p>
      </div>
      <div class="text-left md:text-right space-y-4">
        <p class="font-black text-white uppercase tracking-widest text-sm">Family Hero Hub</p>
        <p class="text-sm">Built with ❤️ for families everywhere.</p>
        <div class="flex md:justify-end gap-6 text-xs font-black uppercase tracking-tighter">
          <a href="/privacy" class="hover:text-hero transition-colors">Privacy Policy</a>
          <a href="/terms" class="hover:text-hero transition-colors">Terms of Service</a>
          <a href="/contact" class="hover:text-hero transition-colors">Contact</a>
        </div>
      </div>
    </div>
  </footer>
</div>
