<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';

  type Membership = { school_id: number; membership_id: number; school_name: string; role: string };
  let membership = $state<Membership | null>(null);
  let data = $state<any>(null);
  let loading = $state(true);
  let error = $state('');
  let reason = $state('Messaging operations review approved by the System Owner.');

  function options() { return membership ? { headers: { 'X-School-Id': String(membership.school_id), 'X-Membership-Id': String(membership.membership_id) } } : {}; }
  async function load() {
    loading = true; error = '';
    try {
      const me = await api.get('/me');
      membership = (me.memberships || []).find((row: Membership) => row.role === 'school_admin') || null;
      if (!membership) throw new Error('School administrator access is required.');
      data = await api.get('/school/operations', options());
    } catch (caught: any) { error = caught?.message || 'Unable to load operations.'; }
    finally { loading = false; }
  }
  async function start(path: string, body: any = { reason }) {
    error = '';
    try { await api.post(path, body, options()); await load(); }
    catch (caught: any) { error = caught?.message || 'Operation failed.'; }
  }
  function latestPreview() { return data?.jobs?.find((row: any) => row.job_type === 'retention_preview' && row.state === 'succeeded'); }
  onMount(load);
</script>

<svelte:head><title>Messaging operations | Class Hero Hub</title></svelte:head>
<section class="mx-auto max-w-6xl px-4 py-8">
  <p class="eyebrow">Messaging operations / عمليات الرسائل</p>
  <div class="mt-2 flex flex-wrap items-end justify-between gap-3"><div><h1 class="text-3xl font-black text-slate-900">Production health and retention</h1><p class="mt-2 text-slate-600">School-scoped queue health, retention previews, verified archival, and explicit operator actions.</p></div><button class="btn-secondary rounded-xl px-4 py-2" onclick={load}>Refresh / تحديث</button></div>
  {#if error}<div class="mt-5 rounded-xl border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">{error}</div>{/if}
  {#if loading}<div class="card mt-6 p-6">Loading…</div>
  {:else if data}
    <div class="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <div class="card p-5"><p class="text-xs font-bold uppercase text-slate-500">Dead jobs</p><p class="mt-2 text-3xl font-black">{data.health.jobs.dead || 0}</p></div>
      <div class="card p-5"><p class="text-xs font-bold uppercase text-slate-500">Dead notifications</p><p class="mt-2 text-3xl font-black">{data.health.notification_outbox.dead || 0}</p></div>
      <div class="card p-5"><p class="text-xs font-bold uppercase text-slate-500">Oldest backlog</p><p class="mt-2 text-3xl font-black">{data.health.oldest_notification_age_seconds}s</p></div>
      <div class="card p-5"><p class="text-xs font-bold uppercase text-slate-500">Archive disk</p><p class="mt-2 text-3xl font-black">{data.health.archive_disk_used_percent}%</p></div>
    </div>
    <article class="card mt-6 p-6">
      <h2 class="text-xl font-black">Retention controls / ضوابط الاحتفاظ</h2>
      <p class="mt-2 text-sm text-slate-600">Execution is unavailable until a completed preview is confirmed with its exact SHA-256 value. Active legal holds are rechecked in every bounded batch.</p>
      <label class="mt-4 block text-sm font-bold">Operator reason / سبب الإجراء<textarea class="mt-1 min-h-20 w-full rounded-xl border border-slate-300 p-3" bind:value={reason}></textarea></label>
      <div class="mt-4 flex flex-wrap gap-3">
        <button class="btn-secondary rounded-xl px-4 py-2" onclick={() => start('/school/operations/retention/preview')}>Create dry-run preview</button>
        <button class="btn-secondary rounded-xl px-4 py-2" onclick={() => start('/school/operations/archive')}>Archive eligible media</button>
        {#if latestPreview()}<button class="rounded-xl bg-red-700 px-4 py-2 font-bold text-white" onclick={() => start('/school/operations/retention/execute', { reason, preview_job_id: latestPreview().id, preview_sha256: latestPreview().progress.preview_sha256 })}>Execute confirmed preview</button>{/if}
      </div>
      {#if data.active_retention_policy}<pre class="mt-4 overflow-x-auto rounded-xl bg-slate-950 p-4 text-xs text-slate-100">Policy v{data.active_retention_policy.version} · effective {data.active_retention_policy.effective_at}\n{JSON.stringify(data.active_retention_policy.rules, null, 2)}</pre>{/if}
    </article>
    <article class="card mt-6 overflow-hidden p-6"><h2 class="text-xl font-black">Durable jobs / المهام الدائمة</h2><div class="mt-4 overflow-x-auto"><table class="w-full text-left text-sm"><thead><tr class="border-b"><th class="p-2">Type</th><th class="p-2">State</th><th class="p-2">Attempts</th><th class="p-2">Created</th><th class="p-2">Result</th></tr></thead><tbody>{#each data.jobs as row}<tr class="border-b border-slate-100"><td class="p-2 font-semibold">{row.job_type.replaceAll('_', ' ')}</td><td class="p-2">{row.state}</td><td class="p-2">{row.attempt_count}</td><td class="p-2">{new Date(row.created_at).toLocaleString()}</td><td class="max-w-sm p-2 text-xs">{row.last_error_code || JSON.stringify(row.progress)}</td></tr>{/each}</tbody></table></div></article>
    {#if data.failed_notifications.length}<article class="card mt-6 p-6"><h2 class="text-xl font-black">Failed notifications / الإشعارات المتعثرة</h2>{#each data.failed_notifications as row}<div class="mt-3 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 p-3"><div><strong>{row.state}</strong><p class="text-xs text-slate-500">{row.event_id} · {row.last_error_code || 'unknown error'}</p></div><button class="btn-secondary rounded-lg px-3 py-2" onclick={() => start('/school/operations/notifications/retry', { reason, target_ids: [row.event_id] })}>Retry safely</button></div>{/each}</article>{/if}
  {/if}
</section>
