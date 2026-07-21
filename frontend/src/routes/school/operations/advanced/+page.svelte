<script lang="ts">
  import { onMount } from 'svelte';
  import { _, locale } from 'svelte-i18n';
  import { api } from '$lib/api';

  type Membership = { school_id: number; membership_id: number; school_name: string; role: string };

  let membership = $state<Membership | null>(null);
  let data = $state<any>(null);
  let loading = $state(true);
  let busy = $state(false);
  let error = $state('');
  let notice = $state('');
  let reason = $state('');
  let consequenceConfirmed = $state(false);

  function options() {
    return membership
      ? { headers: { 'X-School-Id': String(membership.school_id), 'X-Membership-Id': String(membership.membership_id) } }
      : {};
  }

  async function load() {
    loading = true;
    error = '';
    try {
      const me = await api.get('/me');
      membership = (me.memberships || []).find((row: Membership) => row.role === 'school_admin') || null;
      if (!membership) throw new Error($_('operationsPage.adminRequired'));
      data = await api.get('/school/operations/advanced', options());
    } catch (caught: any) {
      error = caught?.status === 403 ? $_('operationsPage.advancedRequired') : caught?.message || $_('operationsPage.advancedLoadError');
      data = null;
    } finally {
      loading = false;
    }
  }

  async function start(path: string, body: any = { reason }) {
    if (busy || reason.trim().length < 8 || !consequenceConfirmed) return;
    busy = true;
    error = '';
    notice = '';
    try {
      await api.post(path, body, options());
      reason = '';
      consequenceConfirmed = false;
      notice = $_('operationsPage.operationQueued');
      await load();
    } catch (caught: any) {
      error = caught?.message || $_('operationsPage.operationFailed');
    } finally {
      busy = false;
    }
  }

  function latestPreview() {
    return data?.jobs?.find((row: any) => row.job_type === 'retention_preview' && row.state === 'succeeded');
  }

  function jobType(value: string) {
    const key = `operationsPage.jobTypes.${value}`;
    const translated = $_(key);
    return translated === key ? value.replaceAll('_', ' ') : translated;
  }

  function stateLabel(value: string) {
    const key = `operationsPage.states.${value}`;
    const translated = $_(key);
    return translated === key ? value.replaceAll('_', ' ') : translated;
  }

  function formatDate(value: string | null | undefined) {
    if (!value) return '—';
    return new Intl.DateTimeFormat($locale === 'ar' ? 'ar' : 'en', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
  }

  function formatBytes(value: number) {
    const units = $locale === 'ar' ? ['بايت', 'ك.ب', 'م.ب', 'غ.ب'] : ['bytes', 'KB', 'MB', 'GB'];
    let amount = Number(value || 0);
    let index = 0;
    while (amount >= 1024 && index < units.length - 1) {
      amount /= 1024;
      index += 1;
    }
    return `${amount.toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
  }

  function ruleValue(key: string, value: unknown) {
    if (typeof value === 'boolean') return value ? $_('operationsPage.yes') : $_('operationsPage.no');
    if (typeof value === 'number' && key.endsWith('_minutes')) return $_('operationsPage.minutes', { values: { count: value } });
    if (typeof value === 'number' && key.endsWith('_days')) return $_('operationsPage.days', { values: { count: value } });
    return String(value);
  }

  function readableProgress(progress: Record<string, unknown> | null | undefined) {
    if (!progress) return [];
    const visible = new Set([
      'messages', 'message_body_bytes', 'held_messages_excluded', 'photos', 'photo_bytes', 'voice_notes', 'voice_bytes',
      'messages_disposed', 'photos_archived', 'voice_notes_archived', 'size_bytes'
    ]);
    return Object.entries(progress)
      .filter(([key]) => visible.has(key))
      .map(([key, value]) => ({
        label: $_(`operationsPage.results.${key}`),
        value: key.endsWith('_bytes') ? formatBytes(Number(value || 0)) : String(value)
      }));
  }

  let canAct = $derived(reason.trim().length >= 8 && consequenceConfirmed && !busy);
  let actionableJobs = $derived((data?.jobs || []).filter((row: any) => ['pending', 'failed', 'dead', 'leased'].includes(row.state)));

  onMount(load);
</script>

<svelte:head><title>{$_('operationsPage.advancedPageTitle')}</title></svelte:head>

<section class="mx-auto max-w-6xl px-4 py-8">
  <p class="eyebrow">{$_('operationsPage.advancedEyebrow')}</p>
  <div class="mt-2 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
    <div class="min-w-0">
      <h1 class="text-3xl font-black text-slate-900">{$_('operationsPage.advancedTitle')}</h1>
      <p class="mt-2 max-w-3xl text-slate-600">{$_('operationsPage.advancedIntro')}</p>
    </div>
    <button class="btn-secondary min-h-12 shrink-0 rounded-xl px-4 py-2" onclick={load}>{$_('operationsPage.refresh')}</button>
  </div>

  {#if error}<div class="mt-5 rounded-xl border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">{error}</div>{/if}
  {#if notice}<div class="mt-5 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm font-semibold text-emerald-800">{notice}</div>{/if}

  {#if loading}
    <div class="card mt-6 p-6">{$_('common.loading')}…</div>
  {:else if data}
    <article class="card mt-6 p-6">
      <h2 class="text-xl font-black text-slate-900">{$_('operationsPage.retentionPolicy')}</h2>
      {#if data.active_retention_policy}
        <p class="mt-2 text-sm font-bold text-slate-600">
          {$_('operationsPage.policyVersion', { values: { version: data.active_retention_policy.version } })}
          · {$_('operationsPage.effective', { values: { date: formatDate(data.active_retention_policy.effective_at) } })}
        </p>
        <dl class="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {#each Object.entries(data.active_retention_policy.rules) as [key, value]}
            <div class="min-w-0 rounded-xl border border-slate-200 bg-slate-50 p-4">
              <dt class="text-xs font-bold leading-5 text-slate-500">{$_(`operationsPage.rules.${key}`)}</dt>
              <dd class="mt-1 break-words font-black text-slate-900">{ruleValue(key, value)}</dd>
            </div>
          {/each}
        </dl>
        <details class="mt-5 rounded-xl border border-slate-200 bg-slate-950 text-slate-100">
          <summary class="min-h-12 cursor-pointer px-4 py-3 text-sm font-bold">{$_('operationsPage.technicalDetails')}</summary>
          <pre class="max-w-full whitespace-pre-wrap break-all border-t border-slate-700 p-4 text-xs">{JSON.stringify(data.active_retention_policy, null, 2)}</pre>
        </details>
      {:else}
        <p class="mt-3 text-sm text-slate-600">{$_('operationsPage.noPolicy')}</p>
      {/if}
    </article>

    <article class="card mt-6 p-6">
      <h2 class="text-xl font-black text-slate-900">{$_('operationsPage.durableJobs')}</h2>
      {#if data.jobs.length}
        <div class="mt-4 grid gap-3">
          {#each data.jobs as row}
            <div class="min-w-0 rounded-xl border border-slate-200 p-4">
              <div class="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                <div class="min-w-0">
                  <h3 class="break-words font-black text-slate-900">{jobType(row.job_type)}</h3>
                  <p class="mt-1 text-sm text-slate-500">{formatDate(row.created_at)} · {$_('operationsPage.attempts')}: {row.attempt_count}</p>
                </div>
                <span class="w-fit rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-700">{stateLabel(row.state)}</span>
              </div>
              {#if row.last_error_code}
                <p class="mt-3 break-words rounded-lg bg-red-50 p-3 text-sm font-semibold text-red-800">{$_('operationsPage.lastError')}: {row.last_error_code}</p>
              {:else if readableProgress(row.progress).length}
                <dl class="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                  {#each readableProgress(row.progress) as result}
                    <div class="rounded-lg bg-slate-50 p-3"><dt class="text-xs text-slate-500">{result.label}</dt><dd class="mt-1 font-bold text-slate-900">{result.value}</dd></div>
                  {/each}
                </dl>
              {:else}
                <p class="mt-3 text-sm text-slate-500">{$_('operationsPage.noResult')}</p>
              {/if}
              <details class="mt-3 rounded-lg border border-slate-200 bg-slate-50">
                <summary class="min-h-12 cursor-pointer px-3 py-3 text-xs font-bold text-slate-600">{$_('operationsPage.technicalDetails')}</summary>
                <pre class="max-w-full whitespace-pre-wrap break-all border-t border-slate-200 p-3 text-xs text-slate-700">{JSON.stringify(row, null, 2)}</pre>
              </details>
            </div>
          {/each}
        </div>
      {:else}
        <p class="mt-3 text-sm text-slate-600">{$_('operationsPage.noJobs')}</p>
      {/if}
    </article>

    <article class="card mt-6 p-6">
      <h2 class="text-xl font-black text-slate-900">{$_('operationsPage.failedNotifications')}</h2>
      {#if data.failed_notifications.length}
        <div class="mt-4 grid gap-3 sm:grid-cols-2">
          {#each data.failed_notifications as row}
            <div class="min-w-0 rounded-xl border border-slate-200 p-4">
              <p class="font-black text-slate-900">{stateLabel(row.state)}</p>
              <p class="mt-1 break-all text-xs text-slate-500">{row.event_id}</p>
              {#if row.last_error_code}<p class="mt-2 break-words text-sm text-red-700">{$_('operationsPage.lastError')}: {row.last_error_code}</p>{/if}
            </div>
          {/each}
        </div>
      {:else}
        <p class="mt-3 text-sm text-slate-600">{$_('operationsPage.noFailedNotifications')}</p>
      {/if}
    </article>

    <details class="mt-6 rounded-2xl border border-amber-300 bg-amber-50">
      <summary class="min-h-14 cursor-pointer px-5 py-4 text-lg font-black text-amber-950">{$_('operationsPage.advancedActions')}</summary>
      <div class="border-t border-amber-200 p-5">
        <p class="text-sm leading-6 text-amber-950">{$_('operationsPage.advancedActionsHelp')}</p>
        <label class="mt-4 block text-sm font-black text-slate-900">
          {$_('operationsPage.operatorReason')}
          <span class="mt-1 block text-xs font-normal text-slate-600">{$_('operationsPage.operatorReasonHelp')}</span>
          <textarea class="mt-2 min-h-24 w-full rounded-xl border border-amber-300 bg-white p-3" bind:value={reason} minlength="8" maxlength="2000"></textarea>
        </label>
        <label class="mt-4 flex min-h-12 items-start gap-3 rounded-xl border border-amber-300 bg-white p-4 text-sm font-bold text-slate-800">
          <input class="mt-1 h-5 w-5 shrink-0" type="checkbox" bind:checked={consequenceConfirmed} />
          <span>{$_('operationsPage.consequence')}</span>
        </label>

        <div class="mt-5 grid gap-3 sm:grid-cols-2">
          <button class="btn-secondary min-h-12 rounded-xl px-4 py-3" disabled={!canAct} onclick={() => start('/school/operations/retention/preview')}>{$_('operationsPage.preview')}</button>
          <button class="min-h-12 rounded-xl border border-red-300 bg-white px-4 py-3 font-bold text-red-800" disabled={!canAct} onclick={() => start('/school/operations/archive')}>{$_('operationsPage.archive')}</button>
          {#if latestPreview()}
            <div class="rounded-xl border border-red-300 bg-white p-4 sm:col-span-2">
              <p class="text-sm leading-6 text-red-900">{$_('operationsPage.executeHelp')}</p>
              <button class="mt-3 min-h-12 rounded-xl bg-red-700 px-4 py-3 font-black text-white disabled:opacity-50" disabled={!canAct} onclick={() => start('/school/operations/retention/execute', { reason, preview_job_id: latestPreview().id, preview_sha256: latestPreview().progress.preview_sha256 })}>{$_('operationsPage.execute')}</button>
            </div>
          {/if}
        </div>

        {#if actionableJobs.length || data.failed_notifications.length}
          <h3 class="mt-7 text-lg font-black text-slate-900">{$_('operationsPage.queueActions')}</h3>
          <div class="mt-3 grid gap-3">
            {#each actionableJobs as row}
              <div class="flex flex-col gap-3 rounded-xl border border-amber-200 bg-white p-4 sm:flex-row sm:items-center sm:justify-between">
                <div class="min-w-0"><p class="break-words font-bold text-slate-900">{jobType(row.job_type)}</p><p class="mt-1 text-xs text-slate-500">{stateLabel(row.state)} · {formatDate(row.created_at)}</p></div>
                <div class="flex flex-wrap gap-2">
                  {#if row.state === 'failed' || row.state === 'dead'}<button class="btn-secondary min-h-11 rounded-lg px-3 py-2 text-sm" disabled={!canAct} onclick={() => start(`/school/operations/jobs/${row.id}/retry`)}>{$_('operationsPage.retry')}</button>{/if}
                  <button class="min-h-11 rounded-lg border border-red-300 px-3 py-2 text-sm font-bold text-red-800" disabled={!canAct} onclick={() => start(`/school/operations/jobs/${row.id}/cancel`)}>{$_('operationsPage.cancel')}</button>
                </div>
              </div>
            {/each}
            {#each data.failed_notifications as row}
              <div class="flex flex-col gap-3 rounded-xl border border-amber-200 bg-white p-4 sm:flex-row sm:items-center sm:justify-between">
                <p class="min-w-0 break-all text-sm font-bold text-slate-900">{row.event_id}</p>
                <div class="flex flex-wrap gap-2">
                  <button class="btn-secondary min-h-11 rounded-lg px-3 py-2 text-sm" disabled={!canAct} onclick={() => start('/school/operations/notifications/retry', { reason, target_ids: [row.event_id] })}>{$_('operationsPage.retry')}</button>
                  <button class="min-h-11 rounded-lg border border-red-300 px-3 py-2 text-sm font-bold text-red-800" disabled={!canAct} onclick={() => start('/school/operations/notifications/cancel', { reason, target_ids: [row.event_id] })}>{$_('operationsPage.cancel')}</button>
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    </details>
  {/if}
</section>
