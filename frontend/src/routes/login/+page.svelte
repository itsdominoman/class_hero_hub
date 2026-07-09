<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/state';
  import { _ } from 'svelte-i18n';
  import { api } from '$lib/api';
  import LanguageSelector from '$lib/components/LanguageSelector.svelte';

  let magicEmail = $state('');
  let sendingMagic = $state(false);
  let magicNotice = $state<string | null>(null);
  let magicError = $state<string | null>(null);
  let magicToken = $state<string | null>(null);
  let exchangingMagic = $state(false);

  function safeReturnTo(value: string | null) {
    if (!value || !value.startsWith('/') || value.startsWith('//')) return '/post-login';
    return value;
  }

  const returnTo = $derived(safeReturnTo(page.url.searchParams.get('returnTo')));

  const handleGoogleLogin = () => {
    window.location.href = `/api/auth/google/login?return_to=${encodeURIComponent(returnTo)}`;
  };

  async function requestMagicLink() {
    sendingMagic = true;
    magicNotice = null;
    magicError = null;
    try {
      const response = await api.post('/auth/magic-link/request', { email: magicEmail, returnTo });
      magicNotice = response?.warning || $_('login.magicSent');
    } catch (err: any) {
      magicError = err?.message || $_('login.magicError');
    } finally {
      sendingMagic = false;
    }
  }

  async function continueMagicLogin() {
    if (!magicToken) return;
    exchangingMagic = true;
    magicError = null;
    try {
      const response = await api.post('/auth/magic-link/exchange', { token: magicToken });
      window.location.href = response?.return_to || returnTo;
    } catch (err: any) {
      magicError = err?.message || $_('login.magicExchangeError');
    } finally {
      exchangingMagic = false;
    }
  }

  onMount(async () => {
    magicToken = page.url.searchParams.get('magicToken');
    if (magicToken) {
      magicNotice = $_('login.magicReady');
      return;
    }
    try {
      await api.get('/me');
      window.location.href = returnTo;
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
      <div class="w-20 h-20 bg-white rounded-3xl flex items-center justify-center shadow-xl shadow-hero/20 border border-slate-200 mx-auto mb-6 relative overflow-hidden">
        <img src="/family-hero-hub-logo.png" alt={$_('app.name')} class="w-full h-full object-cover" />
      </div>

      <h1 class="text-3xl font-black text-slate-900 mb-3">{$_('login.title')}</h1>
      <p class="text-slate-600 text-base sm:text-lg leading-relaxed">
        {$_('login.intro')}
      </p>

      {#if magicToken}
        <button
          class="mt-8 w-full rounded-2xl bg-slate-900 px-6 py-4 font-bold text-white transition hover:bg-slate-700 disabled:opacity-60"
          disabled={exchangingMagic}
          onclick={continueMagicLogin}
        >
          {$_('login.continueMagic')}
        </button>
      {/if}

      <button
        onclick={handleGoogleLogin}
        class={`${magicToken ? 'mt-4' : 'mt-8'} w-full flex items-center justify-center gap-3 rounded-2xl border-2 border-slate-200 bg-white px-6 py-4 font-bold text-slate-700 transition-all hover:border-hero/30 hover:bg-slate-50 active:scale-[0.98] group`}
      >
        <svg class="w-6 h-6 group-hover:scale-110 transition-transform" viewBox="0 0 48 48" aria-hidden="true">
          <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
          <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
          <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
          <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
        </svg>
        {$_('login.continueGoogle')}
      </button>

      <form class="mt-5 text-left" onsubmit={(event) => { event.preventDefault(); requestMagicLink(); }}>
        <label class="block text-sm font-bold text-slate-700">
          {$_('login.emailLabel')}
          <input
            required
            type="email"
            bind:value={magicEmail}
            class="mt-2 w-full rounded-2xl border-2 border-slate-200 px-4 py-3 font-medium text-slate-900"
            placeholder={$_('login.emailPlaceholder')}
          />
        </label>
        <button
          disabled={sendingMagic}
          class="mt-3 w-full rounded-2xl bg-slate-900 px-6 py-4 font-bold text-white transition hover:bg-slate-700 disabled:opacity-60"
        >
          {$_('login.emailMagicLink')}
        </button>
      </form>

      {#if magicNotice}
        <div class="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-left text-sm font-semibold text-emerald-700">{magicNotice}</div>
      {/if}
      {#if magicError}
        <div class="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-left text-sm font-semibold text-red-700">{magicError}</div>
      {/if}

      <div class="mt-6 rounded-2xl border-2 border-slate-100 bg-slate-50 p-4 text-left text-sm leading-relaxed text-slate-600">
        <p>
          {$_('login.accountHelp')}
        </p>
      </div>

      <div class="mt-4 text-sm text-slate-500 leading-relaxed">
        <p>{$_('login.sessionHelp')}</p>
      </div>

      <div class="mt-6 text-center">
        <p class="text-slate-500 text-sm">
          {$_('login.accessHelp')}
        </p>
      </div>
    </div>
  </div>
</div>
