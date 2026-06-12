<script lang="ts">
  import { _ } from 'svelte-i18n';
</script>

<svelte:head>
  <title>{$_('contact.pageTitle')}</title>
</svelte:head>

<div class="max-w-4xl mx-auto px-4 py-16">
  <div class="card p-8 md:p-12 text-center">
    <h1 class="text-4xl font-black text-slate-900 mb-6">{$_('contact.heading')}</h1>
    <p class="text-xl text-slate-600 mb-12 leading-relaxed">
      {$_('contact.intro')}
    </p>

    <div class="space-y-8">
      <div>
        <h2 class="text-xs font-bold text-slate-400 uppercase tracking-wide mb-2">{$_('contact.emailSupport')}</h2>
        <a
          href="mailto:support@familyherohub.com"
          class="inline-block max-w-full whitespace-nowrap font-bold leading-tight text-hero hover:underline"
          style="font-size: clamp(0.78rem, 3.5vw, 1.25rem);"
        >
          {$_('contact.emailAddress')}
        </a>
      </div>

      <div class="pt-8 border-t border-slate-100">
        <p class="text-slate-500 mb-4 leading-relaxed">
          {$_('contact.privacyNote1')}
        </p>
        <p class="text-slate-500 leading-relaxed">
          {$_('contact.privacyNote2')}
        </p>
      </div>
    </div>
  </div>
</div>
