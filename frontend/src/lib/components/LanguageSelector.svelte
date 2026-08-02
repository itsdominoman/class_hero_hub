<script lang="ts">
  import { Globe2 } from 'lucide-svelte';
  import { _, locale } from 'svelte-i18n';
  import { setLanguage, type SupportedLocale } from '$lib/i18n';

  let { compact = false, navigation = false } = $props<{ compact?: boolean; navigation?: boolean }>();

  function handleChange(event: Event) {
    const value = (event.currentTarget as HTMLSelectElement).value as SupportedLocale;
    setLanguage(value);
  }
</script>

<label
  data-testid="language-selector"
  class={navigation
    ? 'inline-flex shrink-0 items-center gap-1.5 rounded-xl border border-slate-200 bg-white p-1.5 text-xs shadow-sm'
    : compact
      ? 'inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-2 text-xs shadow-sm'
      : 'block rounded-xl border border-slate-100 bg-slate-50 px-3 py-3'}
>
  {#if navigation}
    <Globe2 data-testid="language-globe" class="h-4 w-4 shrink-0 text-slate-500" aria-hidden="true" />
    <span class="sr-only">{$_('language.label')}</span>
  {:else}
    <span class={compact ? 'inline-flex items-center gap-1.5 font-semibold uppercase tracking-wide text-slate-400' : 'inline-flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400'}>
      <Globe2 data-testid="language-globe" class={compact ? 'h-3.5 w-3.5 shrink-0 text-slate-500' : 'h-4 w-4 shrink-0 text-slate-500'} aria-hidden="true" />
      {$_('language.label')}
    </span>
  {/if}
  <select
    aria-label={$_('language.label')}
    class={navigation
      ? 'max-w-[5.75rem] rounded-lg border border-slate-200 bg-white px-1.5 py-1.5 text-xs font-bold text-slate-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-hero'
      : compact
        ? 'rounded-full border border-slate-200 bg-white px-2 py-1 text-xs font-bold text-slate-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-hero'
        : 'mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-bold text-slate-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-hero'}
    value={$locale || 'en'}
    onchange={handleChange}
  >
    <option value="en" lang="en" dir="ltr">English</option>
    <option value="ar" lang="ar" dir="rtl">العربية</option>
  </select>
  {#if !compact && !navigation}
    <span class="mt-2 block text-[10px] font-semibold leading-relaxed text-slate-500">
      {$_('language.help')}
    </span>
  {/if}
</label>
