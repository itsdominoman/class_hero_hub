<script lang="ts">
  import { _ } from 'svelte-i18n';
</script>

<svelte:head>
  <title>{$_('privacyPolicy.pageTitle')}</title>
</svelte:head>

<div class="max-w-4xl mx-auto px-4 py-16">
  <div class="card p-8 md:p-12">
    <h1 class="text-4xl font-black text-slate-900 mb-3">{$_('privacyPolicy.heading')}</h1>
    <p class="text-sm font-bold uppercase tracking-[0.18em] text-slate-400 mb-8">{$_('privacyPolicy.lastUpdated')}</p>

    <div class="prose prose-slate max-w-none space-y-8 text-slate-600">
      <p class="text-lg leading-relaxed">
        {$_('privacyPolicy.intro')}
      </p>

      <section class="space-y-4">
        <h2 class="text-2xl font-bold text-slate-800">{$_('privacyPolicy.section1Title')}</h2>
        <p>
          {$_('privacyPolicy.section1Text')}
        </p>
      </section>

      <section class="space-y-4">
        <h2 class="text-2xl font-bold text-slate-800">{$_('privacyPolicy.section2Title')}</h2>
        <p>{$_('privacyPolicy.section2Intro')}</p>
        <ul class="list-disc pl-6 space-y-2">
          <li><strong>{$_('privacyPolicy.collectItem1Label')}</strong> {$_('privacyPolicy.collectItem1Text')}</li>
          <li><strong>{$_('privacyPolicy.collectItem2Label')}</strong> {$_('privacyPolicy.collectItem2Text')}</li>
          <li><strong>{$_('privacyPolicy.collectItem3Label')}</strong> {$_('privacyPolicy.collectItem3Text')}</li>
          <li><strong>{$_('privacyPolicy.collectItem4Label')}</strong> {$_('privacyPolicy.collectItem4Text')}</li>
          <li><strong>{$_('privacyPolicy.collectItem5Label')}</strong> {$_('privacyPolicy.collectItem5Text')}</li>
          <li><strong>{$_('privacyPolicy.collectItem6Label')}</strong> {$_('privacyPolicy.collectItem6Text')}</li>
        </ul>
      </section>

      <section class="space-y-4">
        <h2 class="text-2xl font-bold text-slate-800">{$_('privacyPolicy.section3Title')}</h2>
        <p>{$_('privacyPolicy.section3Intro')}</p>
        <ul class="list-disc pl-6 space-y-2">
          <li>{$_('privacyPolicy.useItem1')}</li>
          <li>{$_('privacyPolicy.useItem2')}</li>
          <li>{$_('privacyPolicy.useItem3')}</li>
          <li>{$_('privacyPolicy.useItem4')}</li>
          <li>{$_('privacyPolicy.useItem5')}</li>
        </ul>
      </section>

      <section class="space-y-4">
        <h2 class="text-2xl font-bold text-slate-800">{$_('privacyPolicy.section4Title')}</h2>
        <p>
          {$_('privacyPolicy.section4Text')}
        </p>
      </section>

      <section class="space-y-4">
        <h2 class="text-2xl font-bold text-slate-800">{$_('privacyPolicy.section5Title')}</h2>
        <p>
          {$_('privacyPolicy.section5Text')}
        </p>
      </section>

      <section class="space-y-4">
        <h2 class="text-2xl font-bold text-slate-800">{$_('privacyPolicy.section6Title')}</h2>
        <p>
          {$_('privacyPolicy.section6Text')}
        </p>
      </section>

      <section class="space-y-4">
        <h2 class="text-2xl font-bold text-slate-800">{$_('privacyPolicy.section7Title')}</h2>
        <p>
          {$_('privacyPolicy.section7Text')}
        </p>
      </section>

      <section class="space-y-4">
        <h2 class="text-2xl font-bold text-slate-800">{$_('privacyPolicy.section8Title')}</h2>
        <p>
          {$_('privacyPolicy.section8Text')}
        </p>
      </section>

      <section class="space-y-4">
        <h2 class="text-2xl font-bold text-slate-800">{$_('privacyPolicy.section9Title')}</h2>
        <p>
          {$_('privacyPolicy.section9Text')}
        </p>
      </section>

      <section class="space-y-4">
        <h2 class="text-2xl font-bold text-slate-800">{$_('privacyPolicy.section10Title')}</h2>
        <p>
          {$_('privacyPolicy.section10Text')}
        </p>
      </section>

      <section class="space-y-4">
        <h2 class="text-2xl font-bold text-slate-800">{$_('privacyPolicy.section11Title')}</h2>
        <p>{$_('privacyPolicy.section11Text1')}</p>
        <p>{$_('privacyPolicy.section11Text2')}</p>
        <p>{$_('privacyPolicy.section11Text3')}</p>
        <p>{$_('privacyPolicy.section11Text4')}</p>
      </section>

      <section class="space-y-4">
        <h2 class="text-2xl font-bold text-slate-800">{$_('privacyPolicy.section12Title')}</h2>
        <p>{$_('privacyPolicy.section12Intro')}</p>
        <ul class="list-disc pl-6 space-y-2">
          <li>{$_('privacyPolicy.choice1')}</li>
          <li>{$_('privacyPolicy.choice2')}</li>
          <li>{$_('privacyPolicy.choice3')}</li>
          <li>{$_('privacyPolicy.choice4')}</li>
        </ul>
      </section>

      <section class="space-y-4">
        <h2 class="text-2xl font-bold text-slate-800">{$_('privacyPolicy.section13Title')}</h2>
        <p>
          {$_('privacyPolicy.section13Text')}
          <a
            href="mailto:support@familyherohub.com"
            class="inline-block max-w-full whitespace-nowrap align-bottom text-sm font-bold text-hero hover:underline sm:text-base"
          >
            {$_('privacyPolicy.contactEmail')}
          </a>.
        </p>
      </section>
    </div>
  </div>
</div>
