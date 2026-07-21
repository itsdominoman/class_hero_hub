<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { api } from '$lib/api';

  type Membership = { school_id: number; membership_id: number; school_name: string; role: string };
  type Severity = 'healthy' | 'attention' | 'critical';

  let membership = $state<Membership | null>(null);
  let data = $state<any>(null);
  let governance = $state<any>(null);
  let loading = $state(true);
  let error = $state('');

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
      [data, governance] = await Promise.all([
        api.get('/school/operations', options()),
        api.get('/school/governance', options())
      ]);
    } catch (caught: any) {
      error = caught?.message || $_('operationsPage.loadError');
    } finally {
      loading = false;
    }
  }

  let health = $derived(data?.health || null);
  let pendingJobs = $derived(
    Number(health?.jobs?.pending || 0) + Number(health?.jobs?.leased || 0) + Number(health?.jobs?.failed || 0)
  );
  let deadJobs = $derived(Number(health?.jobs?.dead || 0));
  let deadNotifications = $derived(Number(health?.notification_outbox?.dead || 0));

  function formatDuration(seconds: number | null | undefined) {
    if (seconds === null || seconds === undefined) return '';
    if (seconds < 60) return $_('operationsPage.seconds', { values: { count: Math.max(0, Math.round(seconds)) } });
    if (seconds < 3600) return $_('operationsPage.minutes', { values: { count: Math.round(seconds / 60) } });
    if (seconds < 86400) return $_('operationsPage.hours', { values: { count: Math.round(seconds / 3600) } });
    return $_('operationsPage.days', { values: { count: Math.round(seconds / 86400) } });
  }

  function severity(): Severity {
    if (!health) return 'attention';
    if (Number(health.archive_disk_used_percent || 0) >= 90 || deadJobs > 0 || deadNotifications > 0) return 'critical';
    return Object.values(health.alerts || {}).some(Boolean) ? 'attention' : 'healthy';
  }

  function storageSeverity(): Severity {
    const used = Number(health?.archive_disk_used_percent || 0);
    if (used >= 90) return 'critical';
    if (used >= 80) return 'attention';
    return 'healthy';
  }

  function severityLabel(value: Severity) {
    if (value === 'critical') return $_('operationsPage.critical');
    if (value === 'attention') return $_('operationsPage.attention');
    return $_('operationsPage.healthy');
  }

  function severityClasses(value: Severity) {
    if (value === 'critical') return 'border-red-200 bg-red-50 text-red-800';
    if (value === 'attention') return 'border-amber-200 bg-amber-50 text-amber-900';
    return 'border-emerald-200 bg-emerald-50 text-emerald-800';
  }

  function warnings() {
    const alerts = health?.alerts || {};
    const items: string[] = [];
    if (alerts.dead_jobs) items.push($_('operationsPage.warningDeadJobs'));
    if (alerts.dead_notifications) items.push($_('operationsPage.warningDeadNotifications'));
    if (alerts.worker_stale) items.push($_('operationsPage.warningWorker'));
    if (alerts.notification_backlog_old) items.push($_('operationsPage.warningBacklog'));
    if (alerts.archive_disk_high) items.push($_('operationsPage.warningStorage'));
    if (alerts.backup_marker_stale_or_missing) items.push($_('operationsPage.warningBackup'));
    if (alerts.database_pool_high) items.push($_('operationsPage.warningDatabase'));
    return items;
  }

  onMount(load);
</script>

<svelte:head><title>{$_('operationsPage.statusPageTitle')}</title></svelte:head>

<section class="mx-auto max-w-6xl px-4 py-8">
  <p class="eyebrow">{$_('operationsPage.statusEyebrow')}</p>
  <div class="mt-2 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
    <div class="min-w-0">
      <h1 class="text-3xl font-black text-slate-900">{$_('operationsPage.statusTitle')}</h1>
      <p class="mt-2 max-w-3xl text-slate-600">{$_('operationsPage.statusIntro')}</p>
    </div>
    <button class="btn-secondary min-h-12 shrink-0 rounded-xl px-4 py-2" onclick={load}>{$_('operationsPage.refresh')}</button>
  </div>

  {#if error}
    <div class="mt-5 rounded-xl border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">{error}</div>
  {/if}
  {#if loading}
    <div class="card mt-6 p-6">{$_('common.loading')}…</div>
  {:else if health}
    <article class={`mt-6 rounded-2xl border p-6 ${severityClasses(severity())}`}>
      <p class="text-xs font-black uppercase tracking-wide opacity-80">{$_('operationsPage.overallStatus')}</p>
      <p class="mt-2 text-3xl font-black">{severityLabel(severity())}</p>
    </article>

    <div class="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <article class={`rounded-2xl border p-5 ${severityClasses(storageSeverity())}`}>
        <h2 class="text-sm font-black">{$_('operationsPage.storageUsage')}</h2>
        <p class="mt-2 text-2xl font-black">{Number(health.archive_disk_used_percent || 0).toFixed(1)}%</p>
        <p class="mt-2 text-sm">{$_('operationsPage.storageFull', { values: { percent: Number(health.archive_disk_used_percent || 0).toFixed(1) } })}</p>
      </article>

      <article class={`rounded-2xl border p-5 ${severityClasses(health.alerts?.backup_marker_stale_or_missing ? 'attention' : 'healthy')}`}>
        <h2 class="text-sm font-black">{$_('operationsPage.backupFreshness')}</h2>
        <p class="mt-3 text-sm font-bold leading-6">
          {health.backup_marker_age_seconds === null
            ? $_('operationsPage.backupMissing')
            : $_('operationsPage.backupSuccess', { values: { age: formatDuration(health.backup_marker_age_seconds) } })}
        </p>
      </article>

      <article class={`rounded-2xl border p-5 ${severityClasses(health.alerts?.worker_stale ? 'attention' : 'healthy')}`}>
        <h2 class="text-sm font-black">{$_('operationsPage.workerHealth')}</h2>
        <p class="mt-3 text-sm font-bold leading-6">
          {health.alerts?.worker_stale
            ? $_('operationsPage.workersUnhealthy')
            : $_('operationsPage.workersHealthy', { values: { count: health.worker_heartbeats?.length || 0 } })}
        </p>
      </article>

      <article class="card p-5">
        <h2 class="text-sm font-black text-slate-600">{$_('operationsPage.pendingJobs')}</h2>
        <p class="mt-2 text-3xl font-black text-slate-900">{pendingJobs}</p>
      </article>

      <article class={`rounded-2xl border p-5 ${severityClasses(deadJobs ? 'critical' : 'healthy')}`}>
        <h2 class="text-sm font-black">{$_('operationsPage.deadJobs')}</h2>
        <p class="mt-2 text-3xl font-black">{deadJobs}</p>
        <p class="mt-2 text-sm">{deadJobs ? $_('operationsPage.failedJobs', { values: { count: deadJobs } }) : $_('operationsPage.noFailedJobs')}</p>
      </article>

      <article class={`rounded-2xl border p-5 ${severityClasses(deadNotifications ? 'critical' : 'healthy')}`}>
        <h2 class="text-sm font-black">{$_('operationsPage.notificationHealth')}</h2>
        <p class="mt-3 text-sm font-bold leading-6">
          {deadNotifications
            ? $_('operationsPage.notificationsUnhealthy', { values: { count: deadNotifications } })
            : $_('operationsPage.notificationsHealthy')}
        </p>
      </article>
    </div>

    <article class="card mt-5 p-6">
      <h2 class="text-lg font-black text-slate-900">{$_('operationsPage.actionRequired')}</h2>
      {#if warnings().length}
        <ul class="mt-3 list-disc space-y-2 ps-5 text-sm leading-6 text-slate-700">
          {#each warnings() as warning}<li>{warning}</li>{/each}
        </ul>
      {:else}
        <p class="mt-3 text-sm text-slate-600">{$_('operationsPage.noWarnings')}</p>
      {/if}
    </article>

    {#if governance?.is_current_owner}
      <div class="mt-5 flex justify-end">
        <a href="/school/operations/advanced" class="btn-secondary inline-flex min-h-12 items-center rounded-xl px-4 py-2">{$_('operationsPage.advancedLink')} →</a>
      </div>
    {/if}
  {/if}
</section>
