<script lang="ts">
  import { ArrowRight, HelpCircle } from 'lucide-svelte';
  import { locale } from 'svelte-i18n';
  import { getPublicSiteCopy } from '$lib/publicSite';

  let copy = $derived(getPublicSiteCopy($locale).faq);
</script>

<svelte:head>
  <title>{copy.pageTitle}</title>
  <meta name="description" content={copy.metaDescription} />
  <meta property="og:title" content={copy.pageTitle} />
  <meta property="og:description" content={copy.metaDescription} />
  <meta property="og:type" content="website" />
  <meta property="og:image" content="https://class.familyherohub.com/chh-logo-master.png" />
  <meta name="twitter:card" content="summary" />
</svelte:head>

<div class="public-surface">
  <section class="relative overflow-hidden bg-slate-950 text-white">
    <div class="public-orb public-orb-one"></div>
    <div class="public-orb public-orb-two"></div>
    <div class="relative mx-auto max-w-7xl px-4 py-16 sm:py-20 lg:py-24">
      <div class="max-w-4xl text-start">
        <p class="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-4 py-2 text-xs font-bold uppercase tracking-[0.16em] text-violet-200">
          <HelpCircle class="h-4 w-4" aria-hidden="true" />
          {copy.eyebrow}
        </p>
        <h1 class="mt-6 text-4xl font-black leading-tight tracking-tight sm:text-5xl lg:text-6xl">{copy.heading}</h1>
        <p class="mt-6 max-w-3xl text-lg leading-relaxed text-slate-300 sm:text-xl">{copy.intro}</p>
      </div>
    </div>
  </section>

  <section class="mx-auto max-w-5xl px-4 py-14 sm:py-18" aria-label={copy.heading}>
    <div class="space-y-4">
      {#each copy.items as item, index}
        <details class="group rounded-[1.5rem] border border-slate-200 bg-white p-5 shadow-sm open:border-violet-200 open:shadow-lg sm:p-6">
          <summary class="flex cursor-pointer list-none items-start gap-4 text-start marker:hidden">
            <span class="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-violet-100 text-sm font-black text-violet-700">
              {String(index + 1).padStart(2, '0')}
            </span>
            <span class="flex-1 pt-1 text-lg font-black leading-tight text-slate-900 sm:text-xl">{item.question}</span>
            <span class="pt-1 text-2xl font-light leading-none text-violet-600 transition group-open:rotate-45" aria-hidden="true">+</span>
          </summary>
          <p class="mt-4 ps-[3.25rem] leading-relaxed text-slate-600">{item.answer}</p>
        </details>
      {/each}
    </div>
  </section>

  <section class="px-4 pb-10">
    <div class="mx-auto max-w-5xl rounded-[2rem] bg-gradient-to-br from-violet-700 to-indigo-700 p-8 text-start text-white shadow-2xl shadow-violet-900/20 sm:p-10">
      <h2 class="text-3xl font-black">{copy.ctaHeading}</h2>
      <p class="mt-3 max-w-2xl text-lg leading-relaxed text-violet-100">{copy.ctaText}</p>
      <a class="mt-6 inline-flex min-h-12 items-center justify-center gap-2 rounded-2xl bg-white px-6 py-3 font-bold text-violet-800 transition hover:bg-violet-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-white" href="/contact">
        {copy.ctaLabel}
        <ArrowRight class="h-5 w-5 rtl:rotate-180" aria-hidden="true" />
      </a>
    </div>
  </section>
</div>
