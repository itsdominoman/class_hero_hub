<script lang="ts">
  import { onMount } from 'svelte';
  import { _, locale } from 'svelte-i18n';
  import { api } from '$lib/api';
  import TimeZoneSelector from '$lib/components/TimeZoneSelector.svelte';

  type SchoolRow = {
    id: number;
    name: string;
    status: string;
    created_at: string;
    counts: { memberships_by_role: Record<string, number>; students: number };
    setup_flags: { has_school_admin: boolean; students_configured: boolean };
  };

  let schools = $state<SchoolRow[]>([]);
  let loading = $state(true);
  let error = $state<string | null>(null);
  let showCreate = $state(false);
  let saving = $state(false);
  let formTimezoneValid = $state(true);
  let form = $state({
    name: '',
    name_ar: '',
    timezone: 'Asia/Muscat',
    locale_default: 'en',
    admin_email: ''
  });

  const formatDate = (value: string) => new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value));
  const roleCount = (school: SchoolRow, role: string) => school.counts?.memberships_by_role?.[role] || 0;

  async function loadSchools() {
    loading = true;
    error = null;
    try {
      schools = await api.get('/platform/schools');
    } catch (err: any) {
      error = err?.message || $_('platform.loadError');
    } finally {
      loading = false;
    }
  }

  async function createSchool() {
    if (!formTimezoneValid) return;
    saving = true;
    error = null;
    try {
      const created = await api.post('/platform/schools', {
        name: form.name,
        name_ar: form.name_ar || null,
        timezone: form.timezone,
        locale_default: form.locale_default,
        admin_email: form.admin_email
      });
      schools = [created, ...schools];
      showCreate = false;
      form = { name: '', name_ar: '', timezone: 'Asia/Muscat', locale_default: 'en', admin_email: '' };
      formTimezoneValid = true;
    } catch (err: any) {
      error = err?.message || $_('platform.createError');
    } finally {
      saving = false;
    }
  }

  onMount(loadSchools);
</script>

<section class="mx-auto max-w-7xl px-4 py-10">
  <div class="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
    <div>
      <p class="eyebrow">{$_('platform.eyebrow')}</p>
      <h1 class="mt-2 text-3xl font-black text-slate-900">{$_('platform.heading')}</h1>
      <p class="mt-2 max-w-2xl text-slate-600">{$_('platform.intro')}</p>
    </div>
    <button class="btn-hero rounded-xl px-5 py-3" onclick={() => (showCreate = true)}>{$_('platform.createSchool')}</button>
  </div>

  {#if error}
    <div class="mt-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">{error}</div>
  {/if}

  <div class="mt-8 overflow-hidden rounded-lg border border-slate-200 bg-white">
    {#if loading}
      <div class="p-8 text-center text-sm font-semibold uppercase tracking-wide text-slate-500">{$_('common.loading')}</div>
    {:else if schools.length === 0}
      <div class="p-8 text-center text-slate-600">{$_('platform.emptySchools')}</div>
    {:else}
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-slate-200 text-sm">
          <thead class="bg-slate-50 text-left text-xs font-bold uppercase tracking-wide text-slate-500">
            <tr>
              <th class="px-4 py-3">{$_('platform.schoolName')}</th>
              <th class="px-4 py-3">{$_('platform.status')}</th>
              <th class="px-4 py-3">{$_('platform.admins')}</th>
              <th class="px-4 py-3">{$_('platform.students')}</th>
              <th class="px-4 py-3">{$_('platform.created')}</th>
              <th class="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            {#each schools as school}
              <tr class="hover:bg-slate-50">
                <td class="px-4 py-4 font-bold text-slate-900">{school.name}</td>
                <td class="px-4 py-4">
                  <span class="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-bold text-slate-700">{$_(`platform.statuses.${school.status}`)}</span>
                </td>
                <td class="px-4 py-4 text-slate-700">{roleCount(school, 'school_admin')}</td>
                <td class="px-4 py-4 text-slate-700">{school.counts.students}</td>
                <td class="px-4 py-4 text-slate-500">{formatDate(school.created_at)}</td>
                <td class="px-4 py-4 text-right">
                  <a class="font-bold text-hero hover:text-hero-dark" href={`/platform/${school.id}`}>{$_('platform.open')}</a>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </div>
</section>

{#if showCreate}
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 px-4 py-6">
    <form class="w-full max-w-lg rounded-lg bg-white p-6 shadow-xl" onsubmit={(event) => { event.preventDefault(); createSchool(); }}>
      <div class="flex items-start justify-between gap-4">
        <div>
          <h2 class="text-xl font-black text-slate-900">{$_('platform.createSchool')}</h2>
          <p class="mt-1 text-sm text-slate-500">{$_('platform.createHelp')}</p>
        </div>
        <button type="button" class="btn-secondary min-h-0 rounded-lg px-3 py-2" onclick={() => (showCreate = false)}>{$_('platform.close')}</button>
      </div>

      <div class="mt-6 grid gap-4">
        <label class="grid gap-2 text-sm font-bold text-slate-700">
          {$_('platform.schoolName')}
          <input required bind:value={form.name} class="rounded-lg border border-slate-300 px-3 py-3 font-medium" />
        </label>
        <label class="grid gap-2 text-sm font-bold text-slate-700">
          {$_('platform.schoolNameAr')}
          <input bind:value={form.name_ar} class="rounded-lg border border-slate-300 px-3 py-3 font-medium" />
        </label>
        <div class="grid gap-4 sm:grid-cols-2">
          <TimeZoneSelector
            id="new-school-timezone"
            label={$_('platform.timezone')}
            locale={$locale || 'en'}
            placeholder={$_('timezoneSelector.searchPlaceholder')}
            help={$_('timezoneSelector.help')}
            noResults={$_('timezoneSelector.noResults')}
            invalid={$_('timezoneSelector.invalid')}
            bind:value={form.timezone}
            bind:valid={formTimezoneValid}
          />
          <label class="grid gap-2 text-sm font-bold text-slate-700">
            {$_('platform.localeDefault')}
            <select bind:value={form.locale_default} class="rounded-lg border border-slate-300 px-3 py-3 font-medium">
              <option value="en">English</option>
              <option value="ar">العربية</option>
            </select>
          </label>
        </div>
        <label class="grid gap-2 text-sm font-bold text-slate-700">
          {$_('platform.adminEmail')}
          <input required type="email" bind:value={form.admin_email} class="rounded-lg border border-slate-300 px-3 py-3 font-medium" />
        </label>
      </div>

      <div class="mt-6 flex justify-end gap-3">
        <button type="button" class="btn-secondary rounded-lg px-4 py-3" onclick={() => (showCreate = false)}>{$_('platform.cancel')}</button>
        <button disabled={saving || !formTimezoneValid} class="btn-hero rounded-lg px-4 py-3 disabled:opacity-60">{saving ? $_('platform.saving') : $_('platform.createSchool')}</button>
      </div>
    </form>
  </div>
{/if}
