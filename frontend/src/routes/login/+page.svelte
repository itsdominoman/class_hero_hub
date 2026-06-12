<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { api } from '$lib/api';
  import LanguageSelector from '$lib/components/LanguageSelector.svelte';

  const handleGoogleLogin = () => {
    window.location.href = '/api/auth/google/login';
  };

  onMount(async () => {
    try {
      await api.get('/me');
      window.location.href = '/parent';
    } catch {
      // Not signed in yet. Stay on the login page.
    }
  });
</script>

<svelte:head>
  <title>{$_('login.title')}</title>
</svelte:head>

<div class="min-h-[calc(100dvh-5rem)] flex items-center justify-center px-3 sm:px-4 py-8">
  <div class="max-w-md w-full">
    <div class="card p-6 sm:p-8 md:p-12 text-center relative overflow-hidden">
      <div class="mb-4 flex justify-end">
        <LanguageSelector compact />
      </div>
      <div class="absolute -top-24 -right-24 w-48 h-48 bg-hero/5 rounded-full blur-3xl"></div>
      <div class="absolute -bottom-24 -left-24 w-48 h-48 bg-savings/5 rounded-full blur-3xl"></div>

      <div class="w-20 h-20 bg-white rounded-3xl flex items-center justify-center shadow-xl shadow-hero/20 border border-slate-200 mx-auto mb-8 relative overflow-hidden">
        <img src="/family-hero-hub-logo.png" alt="Family Hero Hub" class="w-full h-full object-cover" />
      </div>

      <h1 class="text-3xl font-bold text-slate-900 mb-3">{$_('login.title')}</h1>
      <p class="text-slate-600 text-base sm:text-lg leading-relaxed">
        {$_('login.intro')}
      </p>

      <button
        onclick={handleGoogleLogin}
        class="mt-8 w-full flex items-center justify-center gap-3 rounded-2xl border-2 border-slate-200 bg-white px-6 py-4 font-bold text-slate-700 transition-all hover:border-hero/30 hover:bg-slate-50 active:scale-[0.98] group"
      >
        <img src="https://www.google.com/favicon.ico" alt="Google" class="w-6 h-6 group-hover:scale-110 transition-transform" />
        {$_('login.continueGoogle')}
      </button>

      <div class="mt-6 rounded-2xl border-2 border-slate-100 bg-slate-50 p-4 text-left text-sm leading-relaxed text-slate-600">
        <p>
          {$_('login.accountHelp')}
        </p>
      </div>

      <div class="mt-4 text-sm text-slate-500 leading-relaxed">
        <p>{$_('login.sessionHelp')}</p>
      </div>

      <div class="mt-8 pt-8 border-t border-slate-100 text-left">
        <p class="text-xs font-bold uppercase tracking-wide text-slate-400">{$_('login.childrenDoNotSignIn')}</p>
        <p class="mt-3 text-sm text-slate-500 leading-relaxed">
          {$_('login.childHelp')}
        </p>
      </div>

      <div class="mt-6 text-center">
        <p class="text-slate-500 text-sm">
          {$_('login.noAccess')} <a href="/request-access" class="text-hero font-bold hover:underline">{$_('login.requestAccess')}</a>
        </p>
      </div>
    </div>
  </div>
</div>
