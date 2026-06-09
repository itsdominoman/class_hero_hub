<script lang="ts">
  import { _ } from 'svelte-i18n';

  const cards = [
    ['parentGuide.card1Title', 'parentGuide.card1Text'],
    ['parentGuide.card2Title', 'parentGuide.card2Text'],
    ['parentGuide.card3Title', 'parentGuide.card3Text'],
    ['parentGuide.card4Title', 'parentGuide.card4Text'],
    ['parentGuide.card5Title', 'parentGuide.card5Text'],
    ['parentGuide.card6Title', 'parentGuide.card6Text'],
    ['parentGuide.card7Title', 'parentGuide.card7Text'],
    ['parentGuide.card8Title', 'parentGuide.card8Text']
  ];
</script>

<svelte:head>
  <title>{$_('parentGuide.pageTitle')}</title>
</svelte:head>

<div class="max-w-5xl mx-auto px-4 py-16">
  <div class="mb-12">
    <p class="text-xs font-black uppercase tracking-[0.2em] text-hero">{$_('parentGuide.eyebrow')}</p>
    <h1 class="mt-3 text-4xl md:text-5xl font-black text-slate-900">{$_('parentGuide.heading')}</h1>
    <p class="mt-5 max-w-3xl text-lg leading-relaxed text-slate-600">
      {$_('parentGuide.intro')}
    </p>
  </div>

  <div class="grid gap-5 md:grid-cols-2">
    {#each cards as item}
      <section class="card p-6">
        <h2 class="text-xl font-black text-slate-900">{$_(item[0])}</h2>
        <p class="mt-3 leading-relaxed text-slate-600">{$_(item[1])}</p>
      </section>
    {/each}
  </div>

  <div class="mt-8 rounded-3xl border border-slate-200 bg-slate-50 p-5 text-slate-600 leading-relaxed">
    {$_('parentGuide.note1')}
  </div>

  <div class="mt-5 rounded-3xl border border-slate-200 bg-slate-50 p-5 text-slate-600 leading-relaxed">
    {$_('parentGuide.note2')}
  </div>

  <div class="mt-10 flex flex-wrap gap-3">
    <a href="/faq" class="btn-secondary inline-flex items-center justify-center rounded-2xl px-5 py-4">{$_('parentGuide.faqCta')}</a>
    <a href="/safety-privacy" class="btn-secondary inline-flex items-center justify-center rounded-2xl px-5 py-4">{$_('parentGuide.safetyPrivacyCta')}</a>
    <a href="/contact" class="btn-hero inline-flex items-center justify-center rounded-2xl px-5 py-4">{$_('parentGuide.contactCta')}</a>
  </div>
</div>
