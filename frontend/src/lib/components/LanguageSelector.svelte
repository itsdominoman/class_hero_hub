<script lang="ts">
  import { Globe2 } from 'lucide-svelte';
  import { locale } from 'svelte-i18n';
  import { setLanguage, type SupportedLocale } from '$lib/i18n';

  let { compact = false, navigation = false } = $props<{ compact?: boolean; navigation?: boolean }>();

  function switchLanguage() {
    const nextLocale: SupportedLocale = $locale === 'ar' ? 'en' : 'ar';
    setLanguage(nextLocale);
  }
</script>

<button
  type="button"
  data-testid="language-selector"
  aria-label={$locale === 'ar' ? 'Switch to English' : 'التبديل إلى العربية'}
  onclick={switchLanguage}
  class={navigation
    ? 'inline-flex shrink-0 items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-bold text-slate-700 shadow-sm transition hover:border-hero/30 hover:text-hero focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-hero'
    : compact
      ? 'inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-2 text-xs font-bold text-slate-700 shadow-sm transition hover:border-hero/30 hover:text-hero focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-hero'
      : 'inline-flex w-full items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-3 text-sm font-bold text-slate-700 shadow-sm transition hover:border-hero/30 hover:text-hero focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-hero'}
>
  <Globe2 data-testid="language-globe" class="h-4 w-4 shrink-0 text-slate-500" aria-hidden="true" />
  <span lang={$locale === 'ar' ? 'en' : 'ar'} dir={$locale === 'ar' ? 'ltr' : 'rtl'}>
    {$locale === 'ar' ? 'English' : 'العربية'}
  </span>
</button>
