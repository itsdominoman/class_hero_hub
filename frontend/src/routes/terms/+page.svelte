<script lang="ts">
  import { _ } from 'svelte-i18n';
</script>

<svelte:head>
  <title>{$_('terms.pageTitle')}</title>
</svelte:head>

<div class="max-w-4xl mx-auto px-4 py-16">
  <div class="card p-8 md:p-12">
    <h1 class="text-4xl font-black text-slate-900 mb-3">{$_('terms.heading')}</h1>
    <p class="text-sm font-bold uppercase tracking-[0.18em] text-slate-400 mb-8">{$_('terms.lastUpdated')}</p>

    <div class="prose prose-slate max-w-none space-y-8 text-slate-600">
      <p class="text-lg leading-relaxed">
        {$_('terms.intro')}
      </p>

      <section class="space-y-4">
        <h2 class="text-2xl font-bold text-slate-800">{$_('terms.section1Title')}</h2>
        <p>
          {$_('terms.section1Text')}
        </p>
      </section>

      <section class="space-y-4">
        <h2 class="text-2xl font-bold text-slate-800">{$_('terms.section2Title')}</h2>
        <p>
          {$_('terms.section2Text')}
        </p>
      </section>

      <section class="space-y-4">
        <h2 class="text-2xl font-bold text-slate-800">{$_('terms.section3Title')}</h2>
        <p>
          {$_('terms.section3Text')}
        </p>
      </section>

      <section class="space-y-4">
        <h2 class="text-2xl font-bold text-slate-800">{$_('terms.section4Title')}</h2>
        <p>
          {$_('terms.section4Text')}
        </p>
      </section>

      <section class="space-y-4">
        <h2 class="text-2xl font-bold text-slate-800">{$_('terms.section5Title')}</h2>
        <p>
          {$_('terms.section5Text1')}
        </p>
        <p>
          {$_('terms.section5Text2')}
        </p>
        <p>
          {$_('terms.section5Text3')}
        </p>
      </section>

      <section class="space-y-4">
        <h2 class="text-2xl font-bold text-slate-800">{$_('terms.section6Title')}</h2>
        <p>
          {$_('terms.section6Text')}
        </p>
      </section>

      <section class="space-y-4">
        <h2 class="text-2xl font-bold text-slate-800">{$_('terms.section7Title')}</h2>
        <p>
          {$_('terms.section7Text')}
        </p>
      </section>

      <section class="space-y-4">
        <h2 class="text-2xl font-bold text-slate-800">{$_('terms.section8Title')}</h2>
        <p>
          {$_('terms.section8Text')}
        </p>
      </section>

      <section class="space-y-4">
        <h2 class="text-2xl font-bold text-slate-800">{$_('terms.section9Title')}</h2>
        <p>
          {$_('terms.section9Text')}
        </p>
      </section>

      <section class="space-y-4">
        <h2 class="text-2xl font-bold text-slate-800">{$_('terms.section10Title')}</h2>
        <p>
          {$_('terms.section10Text')}
        </p>
      </section>

      <section class="space-y-4">
        <h2 class="text-2xl font-bold text-slate-800">{$_('terms.section11Title')}</h2>
        <p>
          {$_('terms.section11Text')}
        </p>
      </section>

      <section class="space-y-4">
        <h2 class="text-2xl font-bold text-slate-800">{$_('terms.section12Title')}</h2>
        <p>
          {$_('terms.section12Text')}
        </p>
      </section>

      <section class="space-y-4">
        <h2 class="text-2xl font-bold text-slate-800">{$_('terms.section13Title')}</h2>
        <p>
          {$_('terms.section13Text')}
          <a
            href="mailto:support@familyherohub.com"
            class="inline-block max-w-full whitespace-nowrap align-bottom text-sm font-bold text-hero hover:underline sm:text-base"
          >
            {$_('terms.contactEmail')}
          </a>.
        </p>
      </section>
    </div>
  </div>
</div>
