<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { _, locale } from 'svelte-i18n';
  import { api } from '$lib/api';

  type Membership = {
    school_id: number;
    membership_id: number;
    school_name: string;
    role: string;
  };
  type Staff = {
    membership_id: number;
    school_id: number;
    role: string;
    status: string;
    revoked_at?: string | null;
    user: { id: number; email: string; name?: string | null; name_ar?: string | null; status?: string };
  };
  type DepartmentAssignment = {
    id: number;
    membership_id: number;
    responsibility: 'head' | 'member';
    valid_from: string;
    valid_to?: string | null;
    is_open: boolean;
    staff?: Staff | null;
  };
  type Department = {
    id: number;
    code: string;
    name: string;
    name_ar?: string | null;
    sort_order: number;
    status: 'active' | 'archived';
    assignments: DepartmentAssignment[];
  };

  const roleOptions = ['principal', 'deputy_principal', 'head_of_department', 'support_staff', 'teacher'] as const;

  let loading = $state(true);
  let busy = $state('');
  let membership = $state<Membership | null>(null);
  let staff = $state<Staff[]>([]);
  let departments = $state<Department[]>([]);
  let error = $state('');
  let notice = $state('');
  let search = $state('');
  let includeInactive = $state(false);
  let searchTimer: ReturnType<typeof setTimeout> | null = null;

  let inviteEmail = $state('');
  let inviteRole = $state<(typeof roleOptions)[number]>('principal');

  let editingDepartmentId = $state<number | null>(null);
  let departmentCode = $state('');
  let departmentName = $state('');
  let departmentNameAr = $state('');
  let departmentSortOrder = $state('0');

  let assignmentDepartmentId = $state('');
  let assignmentMembershipId = $state('');
  let assignmentResponsibility = $state<'head' | 'member'>('member');
  let assignmentValidFrom = $state(today());
  let assignmentValidTo = $state('');

  let activeStaff = $derived(staff.filter((row) => row.status === 'active' && !row.revoked_at));
  let eligibleAssignmentStaff = $derived(
    activeStaff.filter((row) => assignmentResponsibility !== 'head' || row.role === 'head_of_department')
  );

  function today() {
    const now = new Date();
    const local = new Date(now.getTime() - now.getTimezoneOffset() * 60_000);
    return local.toISOString().slice(0, 10);
  }

  function options(): RequestInit {
    if (!membership) return {};
    return {
      headers: {
        'X-School-Id': String(membership.school_id),
        'X-Membership-Id': String(membership.membership_id)
      }
    };
  }

  function message(caught: any, fallback: string) {
    return caught?.message || caught?.detail || fallback;
  }

  function showError(value: string) {
    error = value;
    notice = '';
  }

  function showNotice(value: string) {
    notice = value;
    error = '';
  }

  function roleLabel(role: string) {
    return $_(`staffManagement.roles.${role}`);
  }

  function staffName(row?: Staff | null) {
    if (!row) return '—';
    return ($locale === 'ar' ? row.user.name_ar || row.user.name : row.user.name || row.user.name_ar) || row.user.email;
  }

  function departmentNameForDisplay(row: Department) {
    return ($locale === 'ar' ? row.name_ar || row.name : row.name || row.name_ar) || row.code;
  }

  function dateLabel(value?: string | null) {
    if (!value) return $_('staffManagement.openEnded');
    const parsed = new Date(`${value}T00:00:00`);
    return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleDateString($locale || undefined);
  }

  async function init() {
    loading = true;
    try {
      const me = await api.get('/me/v2');
      membership = (me?.memberships || []).find((row: Membership) => row.role === 'school_admin') || null;
      if (!membership) return;
      await loadAll();
    } catch (caught: any) {
      if (caught?.status === 401) {
        window.location.href = `/login?returnTo=${encodeURIComponent('/school/staff')}`;
        return;
      }
      showError(message(caught, $_('staffManagement.loadError')));
    } finally {
      loading = false;
    }
  }

  async function loadAll() {
    await Promise.all([loadStaff(), loadDepartments()]);
  }

  async function loadStaff() {
    if (!membership) return;
    const params = new URLSearchParams();
    const term = search.trim();
    if (term) params.set('search', term);
    if (includeInactive) params.set('include_deactivated', 'true');
    const payload = await api.get(`/school/staff${params.size ? `?${params}` : ''}`, options());
    staff = payload?.staff || [];
  }

  async function loadDepartments() {
    if (!membership) return;
    departments = await api.get('/school/departments?include_ended_assignments=true', options());
    if (!assignmentDepartmentId && departments.length) assignmentDepartmentId = String(departments[0].id);
  }

  function queueSearch() {
    if (searchTimer) clearTimeout(searchTimer);
    const term = search.trim();
    if (term.length === 1 && !/^\d+$/.test(term)) return;
    searchTimer = setTimeout(async () => {
      try {
        await loadStaff();
      } catch (caught: any) {
        showError(message(caught, $_('staffManagement.loadError')));
      }
    }, 300);
  }

  async function changeInactiveFilter() {
    try {
      await loadStaff();
    } catch (caught: any) {
      showError(message(caught, $_('staffManagement.loadError')));
    }
  }

  async function sendInvite() {
    if (!inviteEmail.trim()) return showError($_('staffManagement.emailRequired'));
    busy = 'invite';
    try {
      const result = await api.post(
        '/school/staff/invites',
        { email: inviteEmail.trim(), role: inviteRole },
        options()
      );
      showNotice(result?.warning || $_('staffManagement.inviteSent', { values: { role: roleLabel(inviteRole) } }));
      inviteEmail = '';
    } catch (caught: any) {
      showError(message(caught, $_('staffManagement.inviteError')));
    } finally {
      busy = '';
    }
  }

  function editDepartment(row: Department) {
    editingDepartmentId = row.id;
    departmentCode = row.code;
    departmentName = row.name;
    departmentNameAr = row.name_ar || '';
    departmentSortOrder = String(row.sort_order || 0);
  }

  function resetDepartmentForm() {
    editingDepartmentId = null;
    departmentCode = '';
    departmentName = '';
    departmentNameAr = '';
    departmentSortOrder = '0';
  }

  function departmentPayload(status: 'active' | 'archived' = 'active') {
    return {
      code: departmentCode.trim(),
      name: departmentName.trim(),
      name_ar: departmentNameAr.trim() || null,
      sort_order: Number(departmentSortOrder) || 0,
      status
    };
  }

  async function saveDepartment() {
    if (!departmentCode.trim() || !departmentName.trim()) return showError($_('staffManagement.departmentRequired'));
    busy = 'department';
    try {
      const payload = departmentPayload();
      if (editingDepartmentId) {
        await api.put(`/school/departments/${editingDepartmentId}`, payload, options());
      } else {
        await api.post('/school/departments', payload, options());
      }
      showNotice($_(editingDepartmentId ? 'staffManagement.departmentUpdated' : 'staffManagement.departmentCreated'));
      resetDepartmentForm();
      await loadDepartments();
    } catch (caught: any) {
      showError(message(caught, $_('staffManagement.departmentError')));
    } finally {
      busy = '';
    }
  }

  async function archiveDepartment(row: Department) {
    if (!confirm($_('staffManagement.archiveConfirm', { values: { department: departmentNameForDisplay(row) } }))) return;
    busy = `archive-${row.id}`;
    try {
      await api.put(
        `/school/departments/${row.id}`,
        { code: row.code, name: row.name, name_ar: row.name_ar || null, sort_order: row.sort_order, status: 'archived' },
        options()
      );
      showNotice($_('staffManagement.departmentArchived'));
      await loadDepartments();
    } catch (caught: any) {
      showError(message(caught, $_('staffManagement.departmentError')));
    } finally {
      busy = '';
    }
  }

  async function assignDepartment() {
    if (!assignmentDepartmentId || !assignmentMembershipId || !assignmentValidFrom) {
      return showError($_('staffManagement.assignmentRequired'));
    }
    busy = 'assignment';
    try {
      await api.post(
        `/school/departments/${assignmentDepartmentId}/assignments`,
        {
          membership_id: Number(assignmentMembershipId),
          responsibility: assignmentResponsibility,
          valid_from: assignmentValidFrom,
          valid_to: assignmentValidTo || null
        },
        options()
      );
      showNotice($_('staffManagement.assignmentCreated'));
      assignmentMembershipId = '';
      assignmentValidTo = '';
      await loadDepartments();
    } catch (caught: any) {
      showError(message(caught, $_('staffManagement.assignmentError')));
    } finally {
      busy = '';
    }
  }

  function changeResponsibility() {
    const selected = activeStaff.find((row) => String(row.membership_id) === assignmentMembershipId);
    if (assignmentResponsibility === 'head' && selected?.role !== 'head_of_department') assignmentMembershipId = '';
  }

  async function closeAssignment(row: DepartmentAssignment) {
    if (!confirm($_('staffManagement.closeConfirm'))) return;
    busy = `close-${row.id}`;
    try {
      await api.post(`/school/department-assignments/${row.id}/close`, { valid_to: today() }, options());
      showNotice($_('staffManagement.assignmentClosed'));
      await loadDepartments();
    } catch (caught: any) {
      showError(message(caught, $_('staffManagement.assignmentError')));
    } finally {
      busy = '';
    }
  }

  onMount(init);
  onDestroy(() => searchTimer && clearTimeout(searchTimer));
</script>

<svelte:head><title>{$_('staffManagement.pageTitle')}</title></svelte:head>

<main class="mx-auto max-w-7xl px-4 py-8">
  <a class="text-sm font-bold text-hero hover:underline" href="/school">← {$_('staffManagement.back')}</a>
  <p class="mt-6 text-xs font-black uppercase tracking-[0.18em] text-hero">{$_('staffManagement.eyebrow')}</p>
  <h1 class="mt-2 text-3xl font-black text-slate-950">{$_('staffManagement.title')}</h1>
  <p class="mt-2 max-w-3xl text-sm leading-6 text-slate-600">{$_('staffManagement.intro')}</p>

  {#if error}<div class="mt-5 rounded-xl border border-red-200 bg-red-50 p-4 text-sm font-bold text-red-700" role="alert">{error}</div>{/if}
  {#if notice}<div class="mt-5 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm font-bold text-emerald-800" role="status">{notice}</div>{/if}

  {#if loading}
    <div class="card mt-6 p-6">{$_('common.loading')}…</div>
  {:else if !membership}
    <div class="card mt-6 p-6 text-sm font-bold text-red-700">{$_('staffManagement.accessDenied')}</div>
  {:else}
    <section class="mt-7 grid gap-5 lg:grid-cols-[minmax(0,1.4fr)_minmax(20rem,0.8fr)]">
      <div class="card p-5 sm:p-6">
        <div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 class="text-xl font-black text-slate-950">{$_('staffManagement.staffTitle')}</h2>
            <p class="mt-1 text-sm text-slate-600">{$_('staffManagement.staffHelp')}</p>
          </div>
          <label class="flex items-center gap-2 text-sm font-semibold text-slate-600">
            <input type="checkbox" bind:checked={includeInactive} onchange={changeInactiveFilter} />
            {$_('staffManagement.includeInactive')}
          </label>
        </div>
        <label class="mt-5 block">
          <span class="text-sm font-bold text-slate-700">{$_('staffManagement.search')}</span>
          <input class="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" type="search" bind:value={search} oninput={queueSearch} placeholder={$_('staffManagement.searchPlaceholder')} />
        </label>
        <div class="mt-4 overflow-x-auto rounded-xl border border-slate-200">
          <table class="min-w-full divide-y divide-slate-200 text-sm">
            <thead class="bg-slate-50 text-xs font-black uppercase tracking-wide text-slate-500">
              <tr><th class="px-3 py-3 text-start">{$_('staffManagement.person')}</th><th class="px-3 py-3 text-start">{$_('staffManagement.role')}</th><th class="px-3 py-3 text-start">{$_('staffManagement.status')}</th></tr>
            </thead>
            <tbody class="divide-y divide-slate-100 bg-white">
              {#each staff as row}
                <tr>
                  <td class="px-3 py-3"><p class="font-bold text-slate-900">{staffName(row)}</p><p class="text-xs text-slate-500">{row.user.email} · #{row.membership_id}</p></td>
                  <td class="px-3 py-3 font-semibold text-slate-700">{roleLabel(row.role)}</td>
                  <td class="px-3 py-3"><span class={`rounded-full px-2 py-1 text-xs font-bold ${row.status === 'active' && !row.revoked_at ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-600'}`}>{row.status === 'active' && !row.revoked_at ? $_('staffManagement.active') : $_('staffManagement.inactive')}</span></td>
                </tr>
              {:else}
                <tr><td colspan="3" class="px-3 py-8 text-center text-slate-500">{$_('staffManagement.noStaff')}</td></tr>
              {/each}
            </tbody>
          </table>
        </div>
      </div>

      <div class="card p-5 sm:p-6">
        <h2 class="text-xl font-black text-slate-950">{$_('staffManagement.inviteTitle')}</h2>
        <p class="mt-1 text-sm text-slate-600">{$_('staffManagement.inviteHelp')}</p>
        <label class="mt-5 block"><span class="text-sm font-bold text-slate-700">{$_('staffManagement.email')}</span><input class="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" type="email" bind:value={inviteEmail} autocomplete="email" /></label>
        <label class="mt-4 block"><span class="text-sm font-bold text-slate-700">{$_('staffManagement.role')}</span><select class="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" bind:value={inviteRole}>{#each roleOptions as role}<option value={role}>{roleLabel(role)}</option>{/each}</select></label>
        <button class="btn-hero mt-5 w-full rounded-xl" type="button" disabled={busy === 'invite'} onclick={sendInvite}>{busy === 'invite' ? $_('common.loading') : $_('staffManagement.sendInvite')}</button>
      </div>
    </section>

    <section class="mt-7 card p-5 sm:p-6">
      <h2 class="text-xl font-black text-slate-950">{$_('staffManagement.departmentsTitle')}</h2>
      <p class="mt-1 max-w-3xl text-sm text-slate-600">{$_('staffManagement.departmentsHelp')}</p>
      <div class="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        <label><span class="text-sm font-bold text-slate-700">{$_('staffManagement.code')}</span><input class="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" bind:value={departmentCode} /></label>
        <label class="xl:col-span-2"><span class="text-sm font-bold text-slate-700">{$_('staffManagement.name')}</span><input class="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" bind:value={departmentName} /></label>
        <label><span class="text-sm font-bold text-slate-700">{$_('staffManagement.nameAr')}</span><input class="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" dir="rtl" bind:value={departmentNameAr} /></label>
        <label><span class="text-sm font-bold text-slate-700">{$_('staffManagement.sortOrder')}</span><input class="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" type="number" bind:value={departmentSortOrder} /></label>
      </div>
      <div class="mt-4 flex flex-wrap gap-2">
        <button class="btn-hero rounded-xl" type="button" disabled={busy === 'department'} onclick={saveDepartment}>{editingDepartmentId ? $_('staffManagement.saveDepartment') : $_('staffManagement.addDepartment')}</button>
        {#if editingDepartmentId}<button class="btn-secondary rounded-xl" type="button" onclick={resetDepartmentForm}>{$_('common.cancel')}</button>{/if}
      </div>
    </section>

    <section class="mt-7 card p-5 sm:p-6">
      <h2 class="text-xl font-black text-slate-950">{$_('staffManagement.assignmentTitle')}</h2>
      <p class="mt-1 max-w-3xl text-sm text-slate-600">{$_('staffManagement.assignmentHelp')}</p>
      <div class="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        <label><span class="text-sm font-bold text-slate-700">{$_('staffManagement.department')}</span><select class="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" bind:value={assignmentDepartmentId}>{#each departments as row}<option value={String(row.id)}>{departmentNameForDisplay(row)}</option>{/each}</select></label>
        <label><span class="text-sm font-bold text-slate-700">{$_('staffManagement.responsibility')}</span><select class="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" bind:value={assignmentResponsibility} onchange={changeResponsibility}><option value="member">{$_('staffManagement.member')}</option><option value="head">{$_('staffManagement.head')}</option></select></label>
        <label><span class="text-sm font-bold text-slate-700">{$_('staffManagement.person')}</span><select class="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" bind:value={assignmentMembershipId}><option value="">{$_('staffManagement.choosePerson')}</option>{#each eligibleAssignmentStaff as row}<option value={String(row.membership_id)}>{staffName(row)} · {roleLabel(row.role)}</option>{/each}</select></label>
        <label><span class="text-sm font-bold text-slate-700">{$_('staffManagement.validFrom')}</span><input class="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" type="date" bind:value={assignmentValidFrom} /></label>
        <label><span class="text-sm font-bold text-slate-700">{$_('staffManagement.validTo')}</span><input class="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" type="date" bind:value={assignmentValidTo} /></label>
      </div>
      <button class="btn-hero mt-4 rounded-xl" type="button" disabled={!departments.length || busy === 'assignment'} onclick={assignDepartment}>{$_('staffManagement.assign')}</button>
    </section>

    <section class="mt-7 grid gap-4 lg:grid-cols-2">
      {#each departments as row}
        <article class="card p-5 sm:p-6">
          <div class="flex items-start justify-between gap-3">
            <div><p class="text-xs font-black uppercase tracking-wide text-hero">{row.code}</p><h3 class="mt-1 text-xl font-black text-slate-950">{departmentNameForDisplay(row)}</h3>{#if row.name_ar && $locale !== 'ar'}<p class="mt-1 text-sm text-slate-500" dir="rtl">{row.name_ar}</p>{/if}</div>
            <div class="flex gap-2"><button class="btn-secondary rounded-lg px-3 py-2 text-sm" type="button" onclick={() => editDepartment(row)}>{$_('common.edit')}</button><button class="rounded-lg border border-red-200 px-3 py-2 text-sm font-bold text-red-700" type="button" disabled={busy === `archive-${row.id}`} onclick={() => archiveDepartment(row)}>{$_('common.archive')}</button></div>
          </div>
          <div class="mt-5 divide-y divide-slate-100 rounded-xl border border-slate-200">
            {#each row.assignments as assignment}
              <div class="flex flex-col gap-3 p-3 sm:flex-row sm:items-center sm:justify-between">
                <div><p class="font-bold text-slate-900">{staffName(assignment.staff)}</p><p class="text-xs text-slate-500">{assignment.responsibility === 'head' ? $_('staffManagement.head') : $_('staffManagement.member')} · {dateLabel(assignment.valid_from)} – {dateLabel(assignment.valid_to)}</p></div>
                {#if assignment.is_open}<button class="btn-secondary rounded-lg px-3 py-2 text-sm" type="button" disabled={busy === `close-${assignment.id}`} onclick={() => closeAssignment(assignment)}>{$_('staffManagement.closeAssignment')}</button>{:else}<span class="text-xs font-bold text-slate-400">{$_('staffManagement.ended')}</span>{/if}
              </div>
            {:else}
              <p class="p-4 text-sm text-slate-500">{$_('staffManagement.noAssignments')}</p>
            {/each}
          </div>
        </article>
      {:else}
        <div class="card p-6 text-sm text-slate-500 lg:col-span-2">{$_('staffManagement.noDepartments')}</div>
      {/each}
    </section>
  {/if}
</main>
