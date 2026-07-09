<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/state';
  import { _ } from 'svelte-i18n';
  import { api } from '$lib/api';
  import LanguageSelector from '$lib/components/LanguageSelector.svelte';

  type Preview = { school_name: string; school_name_ar?: string | null; auth_required: boolean };
  type Details = { student_first_name: string; class_section_name?: string | null; relationship: string; already_linked?: boolean };

  let code = $state('');
  let preview = $state<Preview | null>(null);
  let details = $state<Details | null>(null);
  let signedIn = $state(false);
  let relationship = $state('guardian');
  let success = $state(false);
  let loading = $state(false);
  let error = $state<string | null>(null);

  function returnTo() {
    return `/join?c=${encodeURIComponent(code)}`;
  }

  async function loadPreview() {
    if (!code.trim()) return;
    loading = true;
    error = null;
    preview = null;
    details = null;
    try {
      preview = await api.get(`/join/guardian?c=${encodeURIComponent(code)}`);
      try {
        await api.get('/me');
        signedIn = true;
        details = await api.get(`/join/guardian/details?c=${encodeURIComponent(code)}`);
        relationship = details?.relationship || 'guardian';
      } catch {
        signedIn = false;
      }
    } catch (err: any) {
      error = err?.message || $_('join.invalid');
    } finally {
      loading = false;
    }
  }

  function signIn() {
    window.location.href = `/login?returnTo=${encodeURIComponent(returnTo())}`;
  }

  async function confirmLink() {
    loading = true;
    error = null;
    try {
      await api.post('/join/guardian/confirm', { code, relationship });
      success = true;
    } catch (err: any) {
      error = err?.message || $_('join.invalid');
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    code = page.url.searchParams.get('c') || '';
    if (code) void loadPreview();
  });
</script>

<svelte:head>
  <title>{$_('join.title')}</title>
</svelte:head>

<div class="min-h-[calc(100dvh-5rem)] bg-slate-50 px-3 py-8">
  <div class="mx-auto max-w-md rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
    <div class="flex justify-end">
      <LanguageSelector compact />
    </div>

    {#if success}
      <h1 class="mt-4 text-2xl font-black text-slate-900">{$_('join.successTitle')}</h1>
      <p class="mt-3 text-slate-600">{$_('join.successText')}</p>
      <a href="/parent" class="btn-hero mt-5 block w-full rounded-lg px-4 py-3 text-center">{$_('join.goToDashboard')}</a>
    {:else}
      <h1 class="mt-4 text-2xl font-black text-slate-900">{$_('join.title')}</h1>
      <form class="mt-5 flex gap-2" onsubmit={(event) => { event.preventDefault(); loadPreview(); }}>
        <input class="min-w-0 flex-1 rounded-lg border border-slate-200 px-3 py-2 font-mono" bind:value={code} placeholder="CHH-7K3M-92QT" />
        <button class="btn-hero rounded-lg px-4 py-2" disabled={loading}>{$_('join.checkCode')}</button>
      </form>

      {#if error}
        <p class="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-700">{error}</p>
      {/if}

      {#if preview}
        <div class="mt-5 rounded-lg border border-slate-100 bg-slate-50 p-4">
          <p class="text-sm text-slate-600">{$_('join.safeIntro')}</p>
          <p class="mt-2 text-lg font-black text-slate-900">{preview.school_name}</p>
          {#if !signedIn}
            <button class="btn-hero mt-4 w-full rounded-lg px-4 py-3" onclick={signIn}>{$_('join.continue')}</button>
          {/if}
        </div>
      {/if}

      {#if signedIn && details}
        <div class="mt-5 rounded-lg border border-slate-200 p-4">
          <p class="text-sm text-slate-600">{$_('join.confirmIntro')}</p>
          <p class="mt-2 text-xl font-black text-slate-900">{details.student_first_name}</p>
          <p class="mt-1 text-sm text-slate-500">{details.class_section_name || $_('join.noClass')}</p>
          <label class="mt-4 block text-sm font-bold text-slate-700">
            {$_('join.relationship')}
            <select class="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2" bind:value={relationship}>
              <option value="mother">{$_('join.relationships.mother')}</option>
              <option value="father">{$_('join.relationships.father')}</option>
              <option value="guardian">{$_('join.relationships.guardian')}</option>
              <option value="other">{$_('join.relationships.other')}</option>
            </select>
          </label>
          <button class="btn-hero mt-4 w-full rounded-lg px-4 py-3" disabled={loading} onclick={confirmLink}>{$_('join.confirm')}</button>
        </div>
      {/if}
    {/if}
  </div>
</div>
