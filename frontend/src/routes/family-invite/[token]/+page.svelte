<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { page } from '$app/state';
  import { api } from '$lib/api';
  import { LogIn, UserPlus, CheckCircle2, AlertCircle, Loader2, ArrowRight } from 'lucide-svelte';

  let token = page.params.token;
  let loading = $state(true);
  let error = $state<string | null>(null);
  let inviteEmail = $state<string | null>(null);

  function inviteErrorMessage(e: unknown) {
    const message = e instanceof Error ? e.message : '';

    const normalisedMessage = message.toLowerCase();

    if (
      normalisedMessage.includes('invalid') ||
      normalisedMessage.includes('expired') ||
      normalisedMessage.includes('not found') ||
      normalisedMessage.includes('already used') ||
      normalisedMessage.includes('revoked')
    ) {
      return $_('familyInvite.invalidOrExpired');
    }

    return message || $_('familyInvite.invalidOrExpired');
  }

  async function verifyInvite() {
    try {
      loading = true;
      error = null;
      const data = await api.get(`/auth/invite/verify/${token}`);
      inviteEmail = data.email;
    } catch (e) {
      error = inviteErrorMessage(e);
    } finally {
      loading = false;
    }
  }

  function goToLogin() {
    window.location.href = '/login';
  }

  onMount(verifyInvite);
</script>

<div class="min-h-dvh bg-slate-50 flex items-center justify-center px-3 sm:px-4 py-[calc(2rem+var(--safe-top))] pb-[calc(2rem+var(--safe-bottom))]">
  <div class="max-w-md w-full">
    <div class="bg-white rounded-[2rem] sm:rounded-[2.5rem] shadow-2xl p-6 sm:p-8 md:p-12 text-center border border-slate-100">
      {#if loading}
        <div class="flex flex-col items-center gap-6 py-8">
          <div class="relative">
            <div class="w-20 h-20 bg-hero/10 rounded-3xl flex items-center justify-center text-hero">
              <Loader2 size={40} class="animate-spin" />
            </div>
          </div>
          <div>
            <h1 class="text-2xl font-black text-slate-900 uppercase tracking-tight">{$_('familyInvite.loadingTitle')}</h1>
            <p class="text-slate-500 font-medium mt-2">{$_('familyInvite.loadingText')}</p>
          </div>
        </div>
      {:else if error}
        <div class="flex flex-col items-center gap-6 py-8">
          <div class="w-20 h-20 bg-red-50 rounded-3xl flex items-center justify-center text-red-500">
            <AlertCircle size={40} />
          </div>
          <div>
            <h1 class="text-2xl font-black text-slate-900 uppercase tracking-tight">{$_('familyInvite.errorTitle')}</h1>
            <p class="text-red-500 font-bold mt-2">{error}</p>
            <p class="text-slate-500 text-sm mt-4">{$_('familyInvite.errorText')}</p>
          </div>
          <a href="/" class="btn-secondary w-full py-4 rounded-2xl flex items-center justify-center gap-2">
            {$_('familyInvite.backHome')}
          </a>
        </div>
      {:else}
        <div class="flex flex-col items-center gap-6">
          <div class="w-20 h-20 bg-savings/10 rounded-3xl flex items-center justify-center text-savings">
            <UserPlus size={40} />
          </div>
          <div>
            <h1 class="text-2xl sm:text-3xl font-black text-slate-900 uppercase tracking-tight">{$_('familyInvite.invitedTitle')}</h1>
            <p class="text-slate-600 font-medium mt-3">
              {$_('familyInvite.invitedText', { values: { appName: $_('app.name') } })}
            </p>
          </div>

          <div class="w-full bg-slate-50 rounded-2xl p-6 border-2 border-dashed border-slate-200">
            <p class="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">{$_('familyInvite.emailLabel')}</p>
            <p class="text-lg font-black text-slate-900 break-all">{inviteEmail}</p>
            <p class="text-[10px] text-slate-400 font-bold mt-2">{$_('familyInvite.loginRequirement')}</p>
          </div>

          <div class="space-y-4 w-full pt-4">
            <button onclick={goToLogin} class="btn-hero w-full py-5 rounded-2xl flex items-center justify-center gap-3 text-base sm:text-lg shadow-xl shadow-hero/20 hover:scale-[1.02] active:scale-95 transition-all">
              <LogIn size={24} /> {$_('login.continueGoogle')}
            </button>
            <p class="text-xs text-slate-400 font-medium">
              {$_('familyInvite.benefitsText')}
            </p>
          </div>
        </div>
      {/if}
    </div>

    <!-- Branding -->
    <div class="mt-12 flex flex-col items-center gap-4 opacity-40 grayscale">
        <img src="/family-hero-hub-logo.png" alt="Family Hero Hub" class="h-12 w-auto" />
        <span class="text-[10px] font-black uppercase tracking-[0.4em] text-slate-900">Family Hero Hub</span>
    </div>
  </div>
</div>

<style>
  :global(.btn-hero) {
    background: #7C3AED;
    color: white;
    font-weight: 900;
  }
  
  :global(.btn-secondary) {
    background: white;
    border: 2px solid #F1F5F9;
    color: #64748B;
    font-weight: 800;
  }

  .text-hero { color: #7C3AED; }
  .text-savings { color: #10B981; }
</style>
