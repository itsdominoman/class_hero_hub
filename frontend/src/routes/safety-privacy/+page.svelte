<script lang="ts">
  import { _ } from 'svelte-i18n';
</script>

<svelte:head>
  <title>{$_('safetyPrivacy.heading')} | Family Hero Hub</title>
</svelte:head>

<div class="max-w-5xl mx-auto px-4 py-16">
  <div class="mb-12">
    <p class="text-xs font-black uppercase tracking-[0.2em] text-hero">{$_('safetyPrivacy.eyebrow')}</p>
    <h1 class="mt-3 text-4xl md:text-5xl font-black text-slate-900">{$_('safetyPrivacy.heading')}</h1>
    <p class="mt-5 max-w-3xl text-lg leading-relaxed text-slate-600">
      {$_('safetyPrivacy.intro')}
    </p>
  </div>

  <div class="grid gap-5 md:grid-cols-2">
    <section class="card p-6 md:p-8">
      <h2 class="text-2xl font-black text-slate-900">{$_('safetyPrivacy.card1Title')}</h2>
      <p class="mt-4 leading-relaxed text-slate-600">
        {$_('safetyPrivacy.card1Text')}
      </p>
    </section>

    <section class="card p-6 md:p-8">
      <h2 class="text-2xl font-black text-slate-900">{$_('safetyPrivacy.card2Title')}</h2>
      <p class="mt-4 leading-relaxed text-slate-600">
        {$_('safetyPrivacy.card2Text')}
      </p>
    </section>

    <section class="card p-6 md:p-8">
      <h2 class="text-2xl font-black text-slate-900">{$_('safetyPrivacy.card3Title')}</h2>
      <p class="mt-4 leading-relaxed text-slate-600">
        {$_('safetyPrivacy.card3Text')}
      </p>
    </section>

    <section class="card p-6 md:p-8">
      <h2 class="text-2xl font-black text-slate-900">{$_('safetyPrivacy.card4Title')}</h2>
      <p class="mt-4 leading-relaxed text-slate-600">
        {$_('safetyPrivacy.card4Text')}
      </p>
    </section>

    <section class="card p-6 md:p-8">
      <h2 class="text-2xl font-black text-slate-900">{$_('safetyPrivacy.card5Title')}</h2>
      <p class="mt-4 leading-relaxed text-slate-600">
        {$_('safetyPrivacy.card5Text')}
      </p>
    </section>

    <section class="card p-6 md:p-8">
      <h2 class="text-2xl font-black text-slate-900">{$_('safetyPrivacy.card6Title')}</h2>
      <p class="mt-4 leading-relaxed text-slate-600">
        {$_('safetyPrivacy.card6Text')}
      </p>
    </section>

    <section class="card p-6 md:p-8">
      <h2 class="text-2xl font-black text-slate-900">{$_('safetyPrivacy.card7Title')}</h2>
      <p class="mt-4 leading-relaxed text-slate-600">
        {$_('safetyPrivacy.card7Text')}
      </p>
    </section>

    <section class="card p-6 md:p-8 md:col-span-2">
      <h2 class="text-2xl font-black text-slate-900">{$_('safetyPrivacy.card8Title')}</h2>
      <div class="mt-4 space-y-4 leading-relaxed text-slate-600">
        <p>{$_('safetyPrivacy.card8Paragraph1')}</p>
        <p>{$_('safetyPrivacy.card8Paragraph2')}</p>
        <p>{$_('safetyPrivacy.card8Paragraph3')}</p>
        <p>{$_('safetyPrivacy.card8Paragraph4')}</p>
      </div>
    </section>

    <section class="card p-6 md:p-8 !bg-slate-900 text-white">
      <h2 class="text-2xl font-black">{$_('safetyPrivacy.contactHeading')}</h2>
      <p class="mt-4 leading-relaxed text-slate-300">
        {$_('safetyPrivacy.contactText')}
      </p>
      <a href="/contact" class="mt-6 inline-flex font-black text-hero hover:underline">{$_('safetyPrivacy.contactLink')}</a>
    </section>
  </div>
</div>
