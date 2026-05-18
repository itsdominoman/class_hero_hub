<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  
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

<div class="min-h-[calc(100dvh-5rem)] flex items-center justify-center px-3 sm:px-4 py-8">
  <div class="max-w-md w-full">
    <div class="card p-6 sm:p-8 md:p-12 text-center relative overflow-hidden">
      <!-- Decorative background -->
      <div class="absolute -top-24 -right-24 w-48 h-48 bg-hero/5 rounded-full blur-3xl"></div>
      <div class="absolute -bottom-24 -left-24 w-48 h-48 bg-savings/5 rounded-full blur-3xl"></div>

      <div class="w-20 h-20 bg-hero rounded-3xl flex items-center justify-center shadow-xl shadow-hero/30 mx-auto mb-8 relative overflow-hidden">
        <img src="/family-hero-hub-logo.png" alt="Family Hero Hub" class="w-full h-full object-cover" />
      </div>

      <h1 class="text-3xl font-black text-slate-900 mb-2">Parent sign-in</h1>
      <p class="text-slate-600 mb-8">Sign in with Google to open your parent dashboard.</p>

      <div class="bg-slate-50 border-2 border-slate-100 p-4 sm:p-6 rounded-2xl mb-8 text-sm text-slate-600 leading-relaxed">
        <p>Family Hero Hub never asks for or stores your Google password. Google handles the secure sign-in screen.</p>
      </div>

      <button 
        onclick={handleGoogleLogin}
        class="w-full flex items-center justify-center gap-3 bg-white border-2 border-slate-200 py-4 px-6 rounded-2xl font-bold text-slate-700 hover:bg-slate-50 hover:border-hero/30 transition-all active:scale-[0.98] group"
      >
        <img src="https://www.google.com/favicon.ico" alt="Google" class="w-6 h-6 group-hover:scale-110 transition-transform" />
        Continue with Google
      </button>

      <div class="mt-6 text-center">
        <p class="text-slate-500 text-sm">
          Don’t have access yet? <a href="/request-access" class="text-hero font-bold hover:underline">Request access</a>
        </p>
      </div>

      <div class="mt-10 pt-8 border-t border-slate-100">
        <p class="text-xs text-slate-400 uppercase tracking-widest font-bold mb-4">Parent access only</p>
        <p class="text-sm text-slate-500 italic">Children use a linked dashboard on their own device and do not need Google accounts.</p>
      </div>
    </div>
  </div>
</div>
