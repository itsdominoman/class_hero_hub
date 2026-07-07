<script lang="ts">
  import { _ } from 'svelte-i18n';
</script>

<svelte:head>
  <title>{$_('admin.title')}</title>
</svelte:head>

<section class="mx-auto max-w-4xl px-4 py-16">
  <div class="card p-8">
    <p class="text-sm font-bold uppercase tracking-wide text-hero">{$_('admin.eyebrow')}</p>
    <h1 class="mt-3 text-3xl font-black text-slate-900">{$_('admin.heading')}</h1>
    <p class="mt-4 text-lg leading-relaxed text-slate-600">{$_('admin.intro')}</p>
  </div>
</section>
