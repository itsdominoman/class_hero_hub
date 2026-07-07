<script lang="ts">
  import { _ } from 'svelte-i18n';
</script>

<svelte:head>
  <title>{$_('contact.pageTitle')}</title>
</svelte:head>

<section class="mx-auto max-w-4xl px-4 py-16">
  <p class="text-xs font-bold uppercase tracking-wide text-hero">{$_('common.copyTodo')}</p>
  <h1 class="mt-3 text-4xl font-black text-slate-900">{$_('contact.heading')}</h1>
  <p class="mt-5 text-lg leading-relaxed text-slate-600">{$_('contact.intro')}</p>
  <div class="card mt-8 p-6">
    <h2 class="text-xs font-bold uppercase tracking-wide text-slate-400">{$_('contact.emailSupport')}</h2>
    <a class="mt-2 inline-flex text-lg font-bold text-hero hover:underline" href="mailto:support@familyherohub.com">
      {$_('contact.emailAddress')}
    </a>
  </div>
</section>
