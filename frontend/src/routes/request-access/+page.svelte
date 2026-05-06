<script lang="ts">
  import { api } from '$lib/api';

  let name = $state('');
  let email = $state('');
  let familyName = $state('');
  let message = $state('');
  let loading = $state(false);
  let success = $state(false);
  let error = $state('');

  async function handleSubmit(e: Event) {
    e.preventDefault();
    loading = true;
    error = '';

    try {
      await api.post('/registration-requests', {
        name,
        email,
        family_name: familyName,
        message
      });
      success = true;
    } catch (err: any) {
      error = err.message || 'Failed to submit request. Please try again later.';
    } finally {
      loading = false;
    }
  }
</script>

<div class="min-h-[calc(100dvh-5rem)] flex items-center justify-center px-3 sm:px-4 py-8 md:py-12">
  <div class="max-w-xl w-full">
    <div class="card p-6 sm:p-8 md:p-12 relative overflow-hidden">
      <div class="absolute -top-24 -right-24 w-48 h-48 bg-hero/5 rounded-full blur-3xl"></div>

      {#if success}
        <div class="text-center py-8">
          <div class="w-20 h-20 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mx-auto mb-6">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-10 h-10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6L9 17l-5-5"/></svg>
          </div>
          <h1 class="text-3xl font-black text-slate-900 mb-4">Request Received!</h1>
          <p class="text-slate-600 mb-8 text-base sm:text-lg break-words">
            We've received your request to join Family Hero Hub. We'll review it and get back to you at <strong>{email}</strong> once your access is approved.
          </p>
          <a href="/login" class="btn-secondary inline-block">Return to Login</a>
        </div>
      {:else}
        <div class="mb-10 text-center">
          <h1 class="text-3xl font-black text-slate-900 mb-2">Request Access</h1>
          <p class="text-slate-600 mb-6">Family Hero Hub is currently in limited release. Request access below to start your family's hero journey.</p>
          
          <div class="bg-slate-50 border-2 border-slate-100 p-4 sm:p-6 rounded-2xl text-sm text-slate-600 leading-relaxed text-left">
            <p><strong>Note:</strong> This form does not create an account immediately. After approval, you will sign in using <strong>Google OAuth</strong>. Family Hero Hub never asks for your Google password.</p>
          </div>
        </div>

        {#if error}
          <div class="bg-rose-50 border-2 border-rose-100 text-rose-600 p-4 rounded-2xl mb-8 font-medium text-sm flex items-start gap-3 break-words">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
            {error}
          </div>
        {/if}

        <form onsubmit={handleSubmit} class="space-y-6">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div class="space-y-2">
              <label for="name" class="block text-sm font-bold text-slate-700 ml-1">Your Name</label>
              <input
                id="name"
                type="text"
                bind:value={name}
                required
                placeholder="e.g. Jane Smith"
                class="w-full px-5 py-4 rounded-2xl border-2 border-slate-100 focus:border-hero/30 focus:ring-4 focus:ring-hero/5 outline-none transition-all placeholder:text-slate-300"
              />
            </div>
            <div class="space-y-2">
              <label for="email" class="block text-sm font-bold text-slate-700 ml-1">Email Address</label>
              <input
                id="email"
                type="email"
                bind:value={email}
                required
                placeholder="jane@example.com"
                class="w-full px-5 py-4 rounded-2xl border-2 border-slate-100 focus:border-hero/30 focus:ring-4 focus:ring-hero/5 outline-none transition-all placeholder:text-slate-300"
              />
            </div>
          </div>

          <div class="space-y-2">
            <label for="family" class="block text-sm font-bold text-slate-700 ml-1">Family Name</label>
            <input
              id="family"
              type="text"
              bind:value={familyName}
              required
              placeholder="e.g. The Smith Heroes"
              class="w-full px-5 py-4 rounded-2xl border-2 border-slate-100 focus:border-hero/30 focus:ring-4 focus:ring-hero/5 outline-none transition-all placeholder:text-slate-300"
            />
          </div>

          <div class="space-y-2">
            <label for="message" class="block text-sm font-bold text-slate-700 ml-1">Message (Optional)</label>
            <textarea
              id="message"
              bind:value={message}
              rows="3"
              placeholder="Tell us a bit about your family goals..."
              class="w-full px-5 py-4 rounded-2xl border-2 border-slate-100 focus:border-hero/30 focus:ring-4 focus:ring-hero/5 outline-none transition-all placeholder:text-slate-300 resize-none"
            ></textarea>
          </div>

          <button
            type="submit"
            disabled={loading}
            class="btn-primary w-full py-5 text-lg shadow-xl shadow-hero/20 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {#if loading}
              <div class="flex items-center justify-center gap-3">
                <svg class="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Submitting...
              </div>
            {:else}
              Submit Request
            {/if}
          </button>
        </form>

        <div class="mt-8 text-center">
          <p class="text-slate-500 text-sm">
            Already have access? <a href="/login" class="text-hero font-bold hover:underline">Log In</a>
          </p>
        </div>
      {/if}
    </div>
  </div>
</div>
