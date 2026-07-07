<script lang="ts">
  import { _ } from 'svelte-i18n';
</script>

<svelte:head>
  <title>{$_('privacyPolicy.pageTitle')}</title>
</svelte:head>

<section class="mx-auto max-w-4xl px-4 py-16">
  <p class="text-xs font-bold uppercase tracking-wide text-hero">{$_('common.copyTodo')}</p>
  <h1 class="mt-3 text-4xl font-black text-slate-900">{$_('privacyPolicy.heading')}</h1>
  <p class="mt-5 text-lg leading-relaxed text-slate-600">{$_('privacyPolicy.intro')}</p>
  <div class="card mt-8 p-6">
    <h2 class="text-2xl font-bold text-slate-900">{$_('privacyPolicy.placeholderHeading')}</h2>
    <p class="mt-3 text-slate-600">{$_('privacyPolicy.placeholderText')}</p>
  </div>
</section>
