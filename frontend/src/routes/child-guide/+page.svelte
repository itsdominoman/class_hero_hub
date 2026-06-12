<script lang="ts">
  import { _ } from 'svelte-i18n';

  const cards = [
    ['childGuide.card1Title', 'childGuide.card1Text'],
    ['childGuide.card2Title', 'childGuide.card2Text'],
    ['childGuide.card3Title', 'childGuide.card3Text'],
    ['childGuide.card4Title', 'childGuide.card4Text'],
    ['childGuide.card5Title', 'childGuide.card5Text'],
    ['childGuide.card6Title', 'childGuide.card6Text'],
    ['childGuide.card7Title', 'childGuide.card7Text']
  ];
</script>

<svelte:head>
  <title>{$_('childGuide.pageTitle')}</title>
</svelte:head>

<div class="max-w-5xl mx-auto px-4 py-16">
  <div class="mb-12">
    <p class="text-xs font-semibold uppercase tracking-wide text-savings">{$_('childGuide.eyebrow')}</p>
    <h1 class="mt-3 text-4xl md:text-5xl font-black text-slate-900">{$_('childGuide.heading')}</h1>
    <p class="mt-5 max-w-3xl text-lg leading-relaxed text-slate-600">
      {$_('childGuide.intro1')}
    </p>
    <p class="mt-5 max-w-3xl text-base leading-relaxed text-slate-600">
      {$_('childGuide.intro2')}
    </p>
    <p class="mt-4 max-w-3xl text-base leading-relaxed text-slate-600">
      {$_('childGuide.intro3')}
    </p>
  </div>

  <div class="grid gap-5 md:grid-cols-2">
    {#each cards as item}
      <section class="card p-6">
        <h2 class="text-xl font-bold text-slate-900">{$_(item[0])}</h2>
        <p class="mt-3 leading-relaxed text-slate-600">{$_(item[1])}</p>
      </section>
    {/each}
  </div>

  <div class="mt-10 rounded-3xl border border-slate-200 bg-slate-50 p-5 text-slate-600">
    {$_('childGuide.callout')}
  </div>

  <div class="mt-10 flex flex-wrap gap-3">
    <a href="/faq" class="btn-secondary inline-flex items-center justify-center rounded-2xl px-5 py-4">{$_('childGuide.faqCta')}</a>
    <a href="/safety-privacy" class="btn-secondary inline-flex items-center justify-center rounded-2xl px-5 py-4">{$_('childGuide.safetyPrivacyCta')}</a>
    <a href="/contact" class="btn-hero inline-flex items-center justify-center rounded-2xl px-5 py-4">{$_('childGuide.contactCta')}</a>
  </div>
</div>
