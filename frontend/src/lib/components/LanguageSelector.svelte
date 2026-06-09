<script lang="ts">
  import { _ } from 'svelte-i18n';
  import { locale } from 'svelte-i18n';
  import { setLanguage, type SupportedLocale } from '$lib/i18n';

  function handleChange(event: Event) {
    const value = (event.currentTarget as HTMLSelectElement).value as SupportedLocale;
    setLanguage(value);
  }
</script>

<label class="block rounded-xl border border-slate-100 bg-slate-50 px-3 py-3">
  <span class="block text-[10px] font-black uppercase tracking-[0.12em] text-slate-400 sm:tracking-[0.14em]">
    {$_('language.label')}
  </span>
  <select
    class="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-bold text-slate-900 focus:border-hero/30 focus:outline-none"
    value={$locale || 'en'}
    onchange={handleChange}
  >
    <option value="en">{$_('language.english')}</option>
    <option value="ar">{$_('language.arabic')}</option>
  </select>
  <span class="mt-2 block text-[10px] font-semibold leading-relaxed text-slate-500">
    {$_('language.help')}
  </span>
</label>
