<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';

  type Membership = { school_id: number; membership_id: number; school_name: string; role: string };
  let membership = $state<Membership | null>(null);
  let data = $state<any>(null);
  let loading = $state(true);
  let error = $state('');
  let reason = $state('');
  let targetId = $state('');
  let confirmationId = $state('');
  let saving = $state(false);

  function options() {
    return membership ? { headers: { 'X-School-Id': String(membership.school_id), 'X-Membership-Id': String(membership.membership_id) } } : {};
  }

  async function load() {
    loading = true;
    error = '';
    try {
      const me = await api.get('/me');
      membership = (me.memberships || []).find((row: Membership) => row.role === 'school_admin') || null;
      if (!membership) throw new Error('School administrator access is required.');
      data = await api.get('/school/governance', options());
    } catch (caught: any) {
      error = caught?.message || 'Unable to load governance.';
    } finally {
      loading = false;
    }
  }

  async function transfer() {
    if (!targetId || targetId !== confirmationId) {
      error = 'Select and confirm the same administrator.';
      return;
    }
    saving = true;
    error = '';
    try {
      await api.post('/school/governance/transfer', {
        target_membership_id: Number(targetId),
        confirmation_membership_id: Number(confirmationId),
        reason
      }, options());
      reason = '';
      targetId = confirmationId = '';
      await load();
    } catch (caught: any) {
      error = caught?.message || 'Transfer failed.';
    } finally {
      saving = false;
    }
  }

  onMount(load);
</script>

<svelte:head><title>Messaging governance | Class Hero Hub</title></svelte:head>

<section class="mx-auto max-w-5xl px-4 py-8">
  <p class="eyebrow">Messaging governance / حوكمة الرسائل</p>
  <h1 class="mt-2 text-3xl font-black text-slate-900">System Owner / المالك التشغيلي للنظام</h1>
  <p class="mt-2 max-w-3xl text-slate-600">The school-nominated operational lead for Class Hero Hub. This title does not imply principalship or legal ownership. / المسؤول التشغيلي الذي تعيّنه المدرسة لمنصة Class Hero Hub، ولا يعني هذا المسمى ملكية قانونية أو منصب مدير المدرسة.</p>

  {#if error}<div class="mt-5 rounded-xl border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">{error}</div>{/if}
  {#if loading}<div class="card mt-6 p-6">Loading…</div>
  {:else if data}
    {#if data.recovery_required}<div class="mt-6 rounded-xl border border-amber-300 bg-amber-50 p-5"><strong>Emergency recovery required / يلزم الاسترداد الطارئ</strong><p class="mt-2 text-sm text-amber-900">{data.recovery_guidance}</p></div>{/if}
    <div class="mt-6 grid gap-5 lg:grid-cols-2">
      <article class="card p-6">
        <h2 class="text-lg font-black text-slate-900">Current System Owner / المالك التشغيلي الحالي</h2>
        {#if data.owner}
          <p class="mt-4 text-xl font-bold text-slate-900">{data.owner.display_name}</p>
          <p class="mt-1 text-sm text-slate-500">Active school administrator · version {data.owner_version}</p>
        {:else}<p class="mt-4 text-slate-600">No active owner is available.</p>{/if}
      </article>
      <article class="card p-6">
        <h2 class="text-lg font-black text-slate-900">Transfer authority / نقل الصلاحية</h2>
        <p class="mt-2 text-sm text-slate-600">Only the current System Owner may transfer this responsibility to another active school administrator. The action is audited.</p>
        <label class="mt-4 block text-sm font-bold">New administrator
          <select class="mt-1 w-full rounded-xl border border-slate-300 p-3" bind:value={targetId}>
            <option value="">Choose…</option>
            {#each data.staff.filter((row: any) => row.role === 'school_admin' && row.membership_status === 'active' && row.membership_id !== data.owner?.membership_id) as row}
              <option value={String(row.membership_id)}>{row.display_name}</option>
            {/each}
          </select>
        </label>
        <label class="mt-3 block text-sm font-bold">Confirm the administrator
          <select class="mt-1 w-full rounded-xl border border-slate-300 p-3" bind:value={confirmationId}>
            <option value="">Choose again…</option>
            {#each data.staff.filter((row: any) => row.role === 'school_admin' && row.membership_status === 'active' && row.membership_id !== data.owner?.membership_id) as row}
              <option value={String(row.membership_id)}>{row.display_name}</option>
            {/each}
          </select>
        </label>
        <label class="mt-3 block text-sm font-bold">Reason / السبب
          <textarea class="mt-1 min-h-24 w-full rounded-xl border border-slate-300 p-3" bind:value={reason} minlength="8" maxlength="2000"></textarea>
        </label>
        <button class="btn-hero mt-4 rounded-xl px-5 py-3" disabled={saving || !data.is_current_owner} onclick={transfer}>Transfer / نقل</button>
      </article>
    </div>
    <article class="card mt-6 overflow-hidden p-6">
      <h2 class="text-lg font-black text-slate-900">Administrator roster / سجل المسؤولين</h2>
      <div class="mt-4 overflow-x-auto"><table class="w-full text-left text-sm"><thead><tr class="border-b"><th class="p-2">Name</th><th class="p-2">Role</th><th class="p-2">Status</th></tr></thead><tbody>
        {#each data.staff as row}<tr class="border-b border-slate-100"><td class="p-2 font-semibold">{row.display_name}</td><td class="p-2">{row.role === 'school_admin' ? 'School administrator' : 'Teacher'}</td><td class="p-2">{row.membership_status}</td></tr>{/each}
      </tbody></table></div>
    </article>
  {/if}
</section>
