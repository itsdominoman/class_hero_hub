<script lang="ts">
  import { _ } from 'svelte-i18n';
</script>

<svelte:head>
  <title>{$_('school.title')}</title>
</svelte:head>

<section class="mx-auto max-w-3xl px-4 py-12">
  <div class="card p-8">
    <p class="eyebrow">{$_('school.eyebrow')}</p>
    <h1 class="mt-3 text-3xl font-black text-slate-900">{$_('school.heading')}</h1>
    <p class="mt-4 text-lg leading-relaxed text-slate-600">{$_('school.intro')}</p>
  </div>
</section>
