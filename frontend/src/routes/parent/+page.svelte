<script lang="ts">
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';
  import { locale } from 'svelte-i18n';
  import { getPublicSiteCopy } from '$lib/publicSite';

  let copy = $derived(getPublicSiteCopy($locale).pages.familyConnection);

  onMount(() => {
    void goto('/family-connection', { replaceState: true });
  });
</script>

<svelte:head>
  <title>{copy.pageTitle}</title>
</svelte:head>

<section class="mx-auto max-w-3xl px-4 py-12 sm:py-16" aria-labelledby="family-connection-title">
  <div class="rounded-3xl border border-violet-100 bg-white p-6 shadow-sm sm:p-8">
    <p class="text-sm font-black uppercase tracking-[0.16em] text-violet-700">{copy.eyebrow}</p>
    <h1 id="family-connection-title" class="mt-3 text-3xl font-black text-slate-950">{copy.heading}</h1>
    <p class="mt-4 text-base leading-7 text-slate-600">{copy.intro}</p>
    <a class="btn-hero mt-6 inline-flex rounded-xl px-5 py-3" href="/family-connection">Family Hero Hub</a>
  </div>
</section>
