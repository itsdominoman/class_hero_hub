<script lang="ts">
  import { ArrowRight, CheckCircle2, Mail, ShieldCheck } from 'lucide-svelte';
  import type { PublicPageCopy } from '$lib/publicSite';

  let { page, article = false } = $props<{ page: PublicPageCopy; article?: boolean }>();
</script>

<svelte:head>
  <title>{page.pageTitle}</title>
  <meta name="description" content={page.metaDescription} />
  <meta property="og:title" content={page.pageTitle} />
  <meta property="og:description" content={page.metaDescription} />
  <meta property="og:type" content="website" />
  <meta property="og:image" content="https://class.familyherohub.com/chh-logo-master.png" />
  <meta name="twitter:card" content="summary" />
</svelte:head>

<div class="public-surface">
  <section class="relative overflow-hidden border-b border-slate-200/70 bg-slate-950 text-white">
    <div class="public-orb public-orb-one"></div>
    <div class="public-orb public-orb-two"></div>
    <div class="relative mx-auto max-w-7xl px-4 py-16 sm:py-20 lg:py-24">
      <div class="max-w-4xl text-start">
        <p class="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-4 py-2 text-xs font-bold uppercase tracking-[0.16em] text-violet-200">
          <span class="h-2 w-2 rounded-full bg-emerald-400"></span>
          {page.eyebrow}
        </p>
        <h1 class="mt-6 max-w-4xl text-4xl font-black leading-[1.02] tracking-tight sm:text-5xl lg:text-6xl">
          {page.heading}
        </h1>
        <p class="mt-6 max-w-3xl text-lg leading-relaxed text-slate-300 sm:text-xl">
          {page.intro}
        </p>
        {#if page.highlights?.length}
          <div class="mt-8 flex flex-wrap gap-3" aria-label={page.eyebrow}>
            {#each page.highlights as highlight}
              <span class="rounded-full border border-white/15 bg-white/5 px-4 py-2 text-sm font-semibold text-slate-200">
                {highlight}
              </span>
            {/each}
          </div>
        {/if}
      </div>
    </div>
  </section>

  <div class={article ? 'mx-auto max-w-4xl px-4 py-14 sm:py-18' : 'mx-auto max-w-7xl px-4 py-14 sm:py-18'}>
    <div class={article ? 'space-y-5' : 'grid gap-5 md:grid-cols-2'}>
      {#each page.sections as section, index}
        <section
          class={article
            ? 'rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm sm:p-8'
            : 'group rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm transition duration-300 hover:-translate-y-1 hover:border-violet-200 hover:shadow-xl hover:shadow-violet-950/5 sm:p-8'}
        >
          <div class="flex items-start gap-4">
            <div class="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-violet-100 font-black text-violet-700">
              {String(index + 1).padStart(2, '0')}
            </div>
            <div class="min-w-0">
              <h2 class="text-xl font-black leading-tight text-slate-900 sm:text-2xl">{section.title}</h2>
              <p class="mt-3 leading-relaxed text-slate-600">{section.text}</p>
              {#if section.bullets?.length}
                <ul class="mt-5 space-y-3">
                  {#each section.bullets as item}
                    <li class="flex items-start gap-3 text-sm leading-relaxed text-slate-700 sm:text-base">
                      <CheckCircle2 class="mt-0.5 h-5 w-5 shrink-0 text-emerald-600" aria-hidden="true" />
                      <span>{item}</span>
                    </li>
                  {/each}
                </ul>
              {/if}
            </div>
          </div>
        </section>
      {/each}
    </div>

    {#if page.notice}
      <aside class="mt-8 rounded-[1.75rem] border border-violet-200 bg-violet-50 p-6 sm:p-8" aria-labelledby="public-page-notice">
        <div class="flex items-start gap-4">
          <div class="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-violet-700 text-white">
            <ShieldCheck class="h-6 w-6" aria-hidden="true" />
          </div>
          <div>
            <h2 id="public-page-notice" class="text-xl font-black text-slate-900">{page.notice.title}</h2>
            <p class="mt-2 leading-relaxed text-slate-700">{page.notice.text}</p>
          </div>
        </div>
      </aside>
    {/if}
  </div>

  <section class="px-4 pb-6 pt-2 sm:pb-10">
    <div class="relative mx-auto max-w-7xl overflow-hidden rounded-[2rem] bg-gradient-to-br from-violet-700 via-violet-600 to-indigo-700 px-6 py-10 text-white shadow-2xl shadow-violet-900/20 sm:px-10 sm:py-12 lg:px-14">
      <div class="absolute -right-20 -top-24 h-64 w-64 rounded-full bg-white/10 blur-2xl"></div>
      <div class="relative grid gap-8 lg:grid-cols-[1fr_auto] lg:items-center">
        <div class="max-w-3xl text-start">
          <h2 class="text-3xl font-black leading-tight sm:text-4xl">{page.cta.heading}</h2>
          <p class="mt-4 text-lg leading-relaxed text-violet-100">{page.cta.text}</p>
        </div>
        <div class="flex flex-col gap-3 sm:flex-row lg:flex-col">
          <a class="inline-flex min-h-12 items-center justify-center gap-2 rounded-2xl bg-white px-6 py-3 font-bold text-violet-800 shadow-lg transition hover:bg-violet-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-white" href={page.cta.href}>
            {#if page.cta.href.startsWith('mailto:')}
              <Mail class="h-5 w-5" aria-hidden="true" />
            {/if}
            {page.cta.label}
            <ArrowRight class="h-5 w-5 rtl:rotate-180" aria-hidden="true" />
          </a>
          {#if page.cta.secondaryLabel && page.cta.secondaryHref}
            <a class="inline-flex min-h-12 items-center justify-center rounded-2xl border border-white/25 bg-white/10 px-6 py-3 font-bold text-white transition hover:bg-white/15 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-white" href={page.cta.secondaryHref}>
              {page.cta.secondaryLabel}
            </a>
          {/if}
        </div>
      </div>
    </div>
  </section>
</div>
