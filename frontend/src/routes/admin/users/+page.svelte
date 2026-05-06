<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import {
    ArrowLeft,
    ArrowRight,
    RefreshCcw,
    Search,
    ShieldAlert,
    ShieldCheck,
    Users,
    UserX,
    RotateCcw,
    PauseCircle,
    PlayCircle,
    Eye,
    Filter
  } from 'lucide-svelte';

  type AdminUser = {
    normalized_email: string;
    email: string | null;
    parent_user_id: number | null;
    name: string | null;
    family_id: number | null;
    family_status: string | null;
    family_suspended_at: string | null;
    family_suspend_reason: string | null;
    family_restored_at: string | null;
    family_restored_by_parent_id: number | null;
    family_orphaned: boolean;
    user_status: string;
    approval_status: string | null;
    source: string | null;
    approved_at: string | null;
    revoked_at: string | null;
    restored_at: string | null;
    restored_by_parent_id: number | null;
    last_login_at: string | null;
    created_at: string | null;
    children_count: number;
    coparents_count: number;
    registration_request_id: number | null;
    registration_request_status: string | null;
    registration_request_family_name: string | null;
    registration_request_message: string | null;
    is_bootstrap_admin: boolean;
    can_revoke: boolean;
    can_revoke_reason: string | null;
    can_restore: boolean;
    can_suspend_family: boolean;
    can_restore_family: boolean;
    google_sub_masked: string | null;
  };

  type AdminUsersResponse = {
    items: AdminUser[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
  };

  type PendingAction =
    | { type: 'revoke'; user: AdminUser; reason: string }
    | { type: 'restore'; user: AdminUser }
    | { type: 'suspend-family'; user: AdminUser; reason: string }
    | { type: 'restore-family'; user: AdminUser };

  let users = $state<AdminUser[]>([]);
  let loading = $state(true);
  let error = $state<string | null>(null);
  let total = $state(0);
  let page = $state(1);
  let pageSize = $state(25);
  let totalPages = $state(1);
  let searchInput = $state('');
  let appliedSearch = $state('');
  let statusFilter = $state('all');
  let sourceFilter = $state('all');
  let familyStatusFilter = $state('all');
  let sortBy = $state('created_at');
  let sortDir = $state('desc');
  let selectedUser = $state<AdminUser | null>(null);
  let pendingAction = $state<PendingAction | null>(null);
  let actionReason = $state('');
  let actionLoading = $state(false);

  const statusOptions = [
    { value: 'all', label: 'All statuses' },
    { value: 'active', label: 'Active' },
    { value: 'revoked', label: 'Revoked' },
    { value: 'bootstrap', label: 'Bootstrap admin' },
    { value: 'suspended', label: 'Family suspended' },
    { value: 'invited', label: 'Invited' },
    { value: 'registration-approved', label: 'Registration approved' },
    { value: 'approved-only', label: 'Approved only' }
  ];

  const sourceOptions = [
    { value: 'all', label: 'All sources' },
    { value: 'bootstrap', label: 'Bootstrap' },
    { value: 'invite', label: 'Invite' },
    { value: 'registration_request', label: 'Registration request' },
    { value: 'manual_admin', label: 'Manual admin' }
  ];

  const familyStatusOptions = [
    { value: 'all', label: 'All family states' },
    { value: 'active', label: 'Family active' },
    { value: 'suspended', label: 'Family suspended' }
  ];

  const sortOptions = [
    { value: 'created_at', label: 'Newest' },
    { value: 'last_login_at', label: 'Last login' },
    { value: 'email', label: 'Email' },
    { value: 'name', label: 'Name' },
    { value: 'status', label: 'Status' },
    { value: 'family_status', label: 'Family status' },
    { value: 'family_id', label: 'Family ID' }
  ];

  const pageSizeOptions = [10, 25, 50, 100];

  function formatDate(value: string | null) {
    if (!value) return 'Never';
    return new Date(value).toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit'
    });
  }

  function formatDateShort(value: string | null) {
    if (!value) return '—';
    return new Date(value).toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  }

  function badgeClass(kind: string) {
    if (kind === 'bootstrap') return 'bg-slate-900 text-white';
    if (kind === 'active') return 'bg-emerald-100 text-emerald-700 border-emerald-200';
    if (kind === 'revoked') return 'bg-rose-100 text-rose-700 border-rose-200';
    if (kind === 'suspended') return 'bg-amber-100 text-amber-800 border-amber-200';
    if (kind === 'invite') return 'bg-indigo-100 text-indigo-700 border-indigo-200';
    if (kind === 'registration_request') return 'bg-hero/10 text-hero border-hero/20';
    if (kind === 'manual_admin') return 'bg-sky-100 text-sky-700 border-sky-200';
    return 'bg-slate-100 text-slate-600 border-slate-200';
  }

  function userStatusLabel(user: AdminUser) {
    if (user.is_bootstrap_admin) return 'Bootstrap Admin';
    if (user.user_status === 'suspended') return 'Family Suspended';
    if (user.user_status === 'revoked') return 'Revoked';
    return 'Active';
  }

  function sourceLabel(user: AdminUser) {
    if (!user.source) return 'Unknown';
    if (user.source === 'registration_request') return 'Registration Approved';
    if (user.source === 'manual_admin') return 'Manual Admin';
    if (user.source === 'legacy_bootstrap_migration') return 'Legacy Approved';
    return user.source.replace('_', ' ');
  }

  function revokeUnavailableLabel(user: AdminUser) {
    if (user.can_revoke_reason === 'only_active_parent') return 'Only active parent';
    if (user.can_revoke_reason === 'already_revoked') return 'Already revoked';
    if (user.can_revoke_reason === 'no_parent_user') return 'No parent record';
    return 'Revoke unavailable';
  }

  function revokeUnavailableHelp(user: AdminUser) {
    if (user.can_revoke_reason === 'only_active_parent') return 'Suspend family instead';
    if (user.can_revoke_reason === 'already_revoked') return 'Use restore if access should return';
    if (user.can_revoke_reason === 'no_parent_user') return 'Approve or invite the account first';
    return 'No safe individual revoke action is available';
  }

  function familyLabel(user: AdminUser) {
    if (!user.family_id) return 'No family';
    if (user.family_status === 'suspended') return `Family ${user.family_id} suspended`;
    if (user.family_orphaned) return `Family ${user.family_id} needs attention`;
    return `Family ${user.family_id}`;
  }

  function summaryText(user: AdminUser) {
    const children = `${user.children_count} child${user.children_count === 1 ? '' : 'ren'}`;
    const parents = `${user.coparents_count} coparent${user.coparents_count === 1 ? '' : 's'}`;
    return `${children} • ${parents}`;
  }

  function buildQueryParams() {
    const params = new URLSearchParams();
    params.set('page', String(page));
    params.set('page_size', String(pageSize));
    params.set('sort_by', sortBy);
    params.set('sort_dir', sortDir);
    if (appliedSearch.trim()) params.set('search', appliedSearch.trim());
    if (statusFilter !== 'all') params.set('status', statusFilter);
    if (sourceFilter !== 'all') params.set('source', sourceFilter);
    if (familyStatusFilter !== 'all') params.set('family_status', familyStatusFilter);
    return params.toString();
  }

  async function loadUsers() {
    loading = true;
    error = null;
    try {
      const response = await api.get(`/admin/users?${buildQueryParams()}`);
      const data = response as AdminUsersResponse;
      users = data.items ?? [];
      total = data.total ?? 0;
      page = data.page ?? page;
      pageSize = data.page_size ?? pageSize;
      totalPages = data.total_pages ?? 1;
      if (!selectedUser && users.length > 0) {
        selectedUser = users[0];
      } else if (selectedUser) {
        const refreshed = users.find((user) => user.normalized_email === selectedUser?.normalized_email);
        selectedUser = refreshed || selectedUser;
      }
    } catch (err: any) {
      error = err.message || 'Failed to load users';
      users = [];
    } finally {
      loading = false;
    }
  }

  function applyFilters() {
    appliedSearch = searchInput;
    page = 1;
    loadUsers();
  }

  function resetFilters() {
    searchInput = '';
    appliedSearch = '';
    statusFilter = 'all';
    sourceFilter = 'all';
    familyStatusFilter = 'all';
    sortBy = 'created_at';
    sortDir = 'desc';
    pageSize = 25;
    page = 1;
    loadUsers();
  }

  function openUser(user: AdminUser) {
    selectedUser = user;
  }

  function openAction(action: PendingAction) {
    pendingAction = action;
    actionReason = '';
  }

  function closeAction() {
    pendingAction = null;
    actionReason = '';
  }

  async function submitAction() {
    if (!pendingAction) return;
    actionLoading = true;
    try {
      if (pendingAction.type === 'revoke') {
        await api.post(`/admin/users/${encodeURIComponent(pendingAction.user.normalized_email)}/revoke`, {
          revoke_reason: actionReason.trim() || null
        });
      } else if (pendingAction.type === 'restore') {
        await api.post(`/admin/users/${encodeURIComponent(pendingAction.user.normalized_email)}/restore`, {});
      } else if (pendingAction.type === 'suspend-family') {
        await api.post(`/admin/families/${pendingAction.user.family_id}/suspend`, {
          suspend_reason: actionReason.trim() || null
        });
      } else if (pendingAction.type === 'restore-family') {
        await api.post(`/admin/families/${pendingAction.user.family_id}/restore`, {});
      }

      await loadUsers();
      const refreshed = users.find((user) => user.normalized_email === pendingAction?.user.normalized_email);
      if (refreshed) {
        selectedUser = refreshed;
      }
      closeAction();
    } catch (err: any) {
      alert(err.message || 'Action failed');
    } finally {
      actionLoading = false;
    }
  }

  function previousPage() {
    if (page <= 1) return;
    page -= 1;
    loadUsers();
  }

  function nextPage() {
    if (page >= totalPages) return;
    page += 1;
    loadUsers();
  }

  onMount(loadUsers);
</script>

<div class="max-w-6xl mx-auto px-4 py-8 space-y-6">
  <div class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
    <div class="space-y-2">
      <div class="flex items-center gap-3">
        <div class="inline-flex h-11 w-11 items-center justify-center rounded-2xl bg-hero/10 text-hero">
          <Users size={20} />
        </div>
        <div>
          <h1 class="text-3xl font-black text-slate-900">User Access</h1>
          <p class="text-slate-500">Revoke individual parents or suspend entire families without deleting data.</p>
        </div>
      </div>
      <p class="text-sm text-slate-500">
        Bootstrap admins are protected. Family suspension blocks all parents and children until restored.
      </p>
    </div>

    <div class="flex flex-wrap items-center gap-3">
      <button onclick={loadUsers} class="btn-secondary flex items-center gap-2">
        <RefreshCcw size={16} />
        Refresh
      </button>
    </div>
  </div>

  <form class="card p-4 space-y-4" onsubmit={(event) => { event.preventDefault(); applyFilters(); }}>
    <div class="grid gap-3 lg:grid-cols-[1.4fr_repeat(5,minmax(0,1fr))]">
      <label class="flex items-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-3">
        <Search size={16} class="text-slate-400" />
        <input
          bind:value={searchInput}
          type="search"
          placeholder="Search name, email, family id, or request note"
          class="w-full bg-transparent text-sm outline-none placeholder:text-slate-400"
        />
      </label>

      <label class="flex flex-col gap-1">
        <span class="text-xs font-semibold uppercase tracking-widest text-slate-400">Status</span>
        <select bind:value={statusFilter} class="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm">
          {#each statusOptions as option}
            <option value={option.value}>{option.label}</option>
          {/each}
        </select>
      </label>

      <label class="flex flex-col gap-1">
        <span class="text-xs font-semibold uppercase tracking-widest text-slate-400">Source</span>
        <select bind:value={sourceFilter} class="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm">
          {#each sourceOptions as option}
            <option value={option.value}>{option.label}</option>
          {/each}
        </select>
      </label>

      <label class="flex flex-col gap-1">
        <span class="text-xs font-semibold uppercase tracking-widest text-slate-400">Family</span>
        <select bind:value={familyStatusFilter} class="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm">
          {#each familyStatusOptions as option}
            <option value={option.value}>{option.label}</option>
          {/each}
        </select>
      </label>

      <label class="flex flex-col gap-1">
        <span class="text-xs font-semibold uppercase tracking-widest text-slate-400">Sort</span>
        <select bind:value={sortBy} class="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm">
          {#each sortOptions as option}
            <option value={option.value}>{option.label}</option>
          {/each}
        </select>
      </label>

      <label class="flex flex-col gap-1">
        <span class="text-xs font-semibold uppercase tracking-widest text-slate-400">Direction</span>
        <select bind:value={sortDir} class="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm">
          <option value="desc">Descending</option>
          <option value="asc">Ascending</option>
        </select>
      </label>

      <label class="flex flex-col gap-1">
        <span class="text-xs font-semibold uppercase tracking-widest text-slate-400">Page size</span>
        <select bind:value={pageSize} class="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm">
          {#each pageSizeOptions as option}
            <option value={option}>{option}</option>
          {/each}
        </select>
      </label>
    </div>

    <div class="flex flex-wrap items-center gap-3">
      <button type="submit" class="btn-primary flex items-center gap-2">
        <Filter size={16} />
        Apply filters
      </button>
      <button type="button" onclick={resetFilters} class="btn-secondary">
        Clear
      </button>
      <span class="text-sm text-slate-500">
        {total} matching user{total === 1 ? '' : 's'}
      </span>
    </div>
  </form>

  {#if loading}
    <div class="card p-10 flex justify-center">
      <div class="h-10 w-10 animate-spin rounded-full border-4 border-slate-200 border-t-hero"></div>
    </div>
  {:else if error}
    <div class="card border-rose-100 bg-rose-50 p-6 text-rose-700">
      <p class="font-bold">Unable to load users</p>
      <p class="text-sm">{error}</p>
    </div>
  {:else if users.length === 0}
    <div class="card border-dashed border-slate-200 p-10 text-center text-slate-500">
      <p class="font-semibold">No users found.</p>
      <p class="mt-1 text-sm">Adjust the search or filters to find a user.</p>
    </div>
  {:else}
    <div class="grid gap-4">
      {#each users as user}
        <div class="card p-5 space-y-4">
          <div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
            <div class="space-y-2">
              <div class="flex flex-wrap items-center gap-2">
                <span class={`rounded-full border px-3 py-1 text-xs font-bold uppercase tracking-wider ${badgeClass(user.user_status === 'bootstrap' ? 'bootstrap' : user.user_status)}`}>
                  {userStatusLabel(user)}
                </span>
                {#if user.is_bootstrap_admin}
                  <span class="rounded-full border border-slate-200 bg-slate-900 px-3 py-1 text-xs font-bold uppercase tracking-wider text-white">
                    Protected
                  </span>
                {/if}
                {#if user.family_status}
                  <span class={`rounded-full border px-3 py-1 text-xs font-bold uppercase tracking-wider ${badgeClass(user.family_status)}`}>
                    {user.family_status === 'suspended' ? 'Family Suspended' : 'Family Active'}
                  </span>
                {/if}
                {#if user.family_orphaned}
                  <span class="inline-flex items-center gap-2 rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-bold uppercase tracking-wider text-amber-800">
                    <ShieldAlert size={14} />
                    No active parent
                  </span>
                {/if}
                {#if user.source}
                  <span class={`rounded-full border px-3 py-1 text-xs font-bold uppercase tracking-wider ${badgeClass(user.source)}`}>
                    {sourceLabel(user)}
                  </span>
                {/if}
              </div>

              <div>
                <h2 class="text-xl font-black text-slate-900">
                  {user.name || user.email || user.normalized_email}
                </h2>
                <p class="text-sm text-slate-500">{user.email || user.normalized_email}</p>
                <p class="mt-1 text-xs text-slate-400">Normalized: {user.normalized_email}</p>
              </div>
            </div>

            <div class="flex flex-wrap gap-2">
              <button onclick={() => openUser(user)} class="btn-secondary flex items-center gap-2">
                <Eye size={16} />
                View details
              </button>
              {#if user.can_revoke}
                <button
                  onclick={() => openAction({ type: 'revoke', user, reason: '' })}
                  class="btn-secondary border-rose-200 text-rose-700 hover:bg-rose-50 flex items-center gap-2"
                >
                  <UserX size={16} />
                  Revoke Parent
                </button>
              {:else if user.is_bootstrap_admin}
                <span class="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-400">
                  Protected bootstrap admin
                </span>
              {:else if user.family_id && user.can_revoke_reason === 'only_active_parent'}
                <span class="inline-flex items-center gap-2 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-800">
                  <ShieldAlert size={16} />
                  Only active parent
                </span>
                <span class="text-xs font-medium text-slate-500">Suspend family instead</span>
              {:else if user.family_orphaned}
                <span class="inline-flex items-center gap-2 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-800">
                  <ShieldAlert size={16} />
                  No active parent
                </span>
                <span class="text-xs font-medium text-slate-500">Restore a parent or suspend family</span>
              {:else if !user.can_revoke}
                <span class="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-400">
                  {revokeUnavailableLabel(user)}
                </span>
                <span class="text-xs font-medium text-slate-500">{revokeUnavailableHelp(user)}</span>
              {/if}

              {#if user.can_restore}
                <button
                  onclick={() => openAction({ type: 'restore', user })}
                  class="btn-secondary flex items-center gap-2"
                >
                  <RotateCcw size={16} />
                  Restore Parent
                </button>
              {/if}

              {#if user.can_suspend_family}
                <button
                  onclick={() => openAction({ type: 'suspend-family', user, reason: '' })}
                  class="btn-secondary border-amber-200 text-amber-800 hover:bg-amber-50 flex items-center gap-2"
                >
                  <PauseCircle size={16} />
                  Suspend Family
                </button>
              {:else if user.can_restore_family}
                <button
                  onclick={() => openAction({ type: 'restore-family', user })}
                  class="btn-secondary flex items-center gap-2"
                >
                  <PlayCircle size={16} />
                  Restore Family
                </button>
              {/if}
            </div>
          </div>

          <div class="grid gap-3 text-sm text-slate-600 md:grid-cols-2 xl:grid-cols-4">
            <div class="rounded-2xl bg-slate-50 p-4">
              <p class="text-xs font-bold uppercase tracking-widest text-slate-400">Family</p>
              <p class="mt-1 font-semibold text-slate-900">{familyLabel(user)}</p>
              <p class="text-xs text-slate-500">{summaryText(user)}</p>
            </div>
            <div class="rounded-2xl bg-slate-50 p-4">
              <p class="text-xs font-bold uppercase tracking-widest text-slate-400">Last login</p>
              <p class="mt-1 font-semibold text-slate-900">{formatDate(user.last_login_at)}</p>
              <p class="text-xs text-slate-500">Joined {formatDateShort(user.created_at)}</p>
            </div>
            <div class="rounded-2xl bg-slate-50 p-4">
              <p class="text-xs font-bold uppercase tracking-widest text-slate-400">Approval</p>
              <p class="mt-1 font-semibold text-slate-900">{user.approval_status || 'None'}</p>
              <p class="text-xs text-slate-500">Approved {formatDateShort(user.approved_at)}</p>
            </div>
            <div class="rounded-2xl bg-slate-50 p-4">
              <p class="text-xs font-bold uppercase tracking-widest text-slate-400">Status</p>
              <p class="mt-1 font-semibold text-slate-900">{user.user_status}</p>
              <p class="text-xs text-slate-500">Revoked {formatDateShort(user.revoked_at)}</p>
            </div>
          </div>
        </div>
      {/each}
    </div>

    <div class="flex flex-col gap-3 rounded-3xl border border-slate-200 bg-white px-4 py-3 md:flex-row md:items-center md:justify-between">
      <p class="text-sm text-slate-500">
        Page {page} of {totalPages}
      </p>
      <div class="flex items-center gap-2">
        <button class="btn-secondary flex items-center gap-2" onclick={previousPage} disabled={page <= 1}>
          <ArrowLeft size={16} />
          Previous
        </button>
        <button class="btn-secondary flex items-center gap-2" onclick={nextPage} disabled={page >= totalPages}>
          Next
          <ArrowRight size={16} />
        </button>
      </div>
    </div>
  {/if}

  {#if selectedUser}
    <div class="card p-6 space-y-4">
      <div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <p class="text-xs font-bold uppercase tracking-widest text-slate-400">Selected user</p>
          <h3 class="text-2xl font-black text-slate-900">{selectedUser.name || selectedUser.email || selectedUser.normalized_email}</h3>
          <p class="text-sm text-slate-500">{selectedUser.email || selectedUser.normalized_email}</p>
        </div>
        <div class="flex flex-wrap gap-2">
          <span class={`rounded-full border px-3 py-1 text-xs font-bold uppercase tracking-wider ${badgeClass(selectedUser.user_status === 'bootstrap' ? 'bootstrap' : selectedUser.user_status)}`}>
            {userStatusLabel(selectedUser)}
          </span>
          {#if selectedUser.family_status}
            <span class={`rounded-full border px-3 py-1 text-xs font-bold uppercase tracking-wider ${badgeClass(selectedUser.family_status)}`}>
              {selectedUser.family_status === 'suspended' ? 'Family Suspended' : 'Family Active'}
            </span>
            {#if selectedUser.family_orphaned}
              <span class="inline-flex items-center gap-2 rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-bold uppercase tracking-wider text-amber-800">
                <ShieldAlert size={14} />
                No active parent
              </span>
            {/if}
          {/if}
        </div>
      </div>

      <div class="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <div class="rounded-2xl bg-slate-50 p-4">
          <p class="text-xs font-bold uppercase tracking-widest text-slate-400">Family ID</p>
          <p class="mt-1 font-semibold text-slate-900">{selectedUser.family_id ?? 'None'}</p>
          <p class="text-xs text-slate-500">Children: {selectedUser.children_count} • Coparents: {selectedUser.coparents_count}</p>
        </div>
        <div class="rounded-2xl bg-slate-50 p-4">
          <p class="text-xs font-bold uppercase tracking-widest text-slate-400">Google Sub</p>
          <p class="mt-1 font-semibold text-slate-900">{selectedUser.google_sub_masked ?? 'Hidden'}</p>
        </div>
        <div class="rounded-2xl bg-slate-50 p-4">
          <p class="text-xs font-bold uppercase tracking-widest text-slate-400">Registration request</p>
          <p class="mt-1 font-semibold text-slate-900">{selectedUser.registration_request_status || 'None'}</p>
          <p class="text-xs text-slate-500">{selectedUser.registration_request_family_name || 'No family name on request'}</p>
        </div>
        <div class="rounded-2xl bg-slate-50 p-4">
          <p class="text-xs font-bold uppercase tracking-widest text-slate-400">Dates</p>
          <p class="mt-1 text-sm text-slate-600">Created {formatDate(selectedUser.created_at)}</p>
          <p class="text-sm text-slate-600">Last login {formatDate(selectedUser.last_login_at)}</p>
        </div>
      </div>

      {#if selectedUser.registration_request_message}
        <div class="rounded-2xl border border-slate-200 bg-white p-4">
          <p class="text-xs font-bold uppercase tracking-widest text-slate-400">Request note</p>
          <p class="mt-2 whitespace-pre-wrap text-sm text-slate-600">{selectedUser.registration_request_message}</p>
        </div>
      {/if}

      <div class="flex flex-wrap gap-2">
        {#if selectedUser.can_revoke}
          <button onclick={() => openAction({ type: 'revoke', user: selectedUser, reason: '' })} class="btn-secondary border-rose-200 text-rose-700 hover:bg-rose-50">
            Revoke parent
          </button>
        {:else if selectedUser.is_bootstrap_admin}
          <span class="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-400">
            Protected bootstrap admin
          </span>
        {:else if selectedUser.family_id && selectedUser.can_revoke_reason === 'only_active_parent'}
          <span class="inline-flex items-center gap-2 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-800">
            <ShieldAlert size={16} />
            Only active parent
          </span>
          <span class="text-xs font-medium text-slate-500">Suspend family instead</span>
        {:else if selectedUser.family_orphaned}
          <span class="inline-flex items-center gap-2 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-800">
            <ShieldAlert size={16} />
            No active parent
          </span>
          <span class="text-xs font-medium text-slate-500">Restore a parent or suspend family</span>
        {:else if !selectedUser.can_revoke}
          <span class="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-400">
            {revokeUnavailableLabel(selectedUser)}
          </span>
          <span class="text-xs font-medium text-slate-500">{revokeUnavailableHelp(selectedUser)}</span>
        {/if}
        {#if selectedUser.can_restore}
          <button onclick={() => openAction({ type: 'restore', user: selectedUser })} class="btn-secondary">
            Restore parent
          </button>
        {/if}
        {#if selectedUser.can_suspend_family}
          <button onclick={() => openAction({ type: 'suspend-family', user: selectedUser, reason: '' })} class="btn-secondary border-amber-200 text-amber-800 hover:bg-amber-50">
            Suspend family
          </button>
        {/if}
        {#if selectedUser.can_restore_family}
          <button onclick={() => openAction({ type: 'restore-family', user: selectedUser })} class="btn-secondary">
            Restore family
          </button>
        {/if}
      </div>
    </div>
  {/if}
</div>

{#if pendingAction}
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 px-4 py-6">
    <div class="card w-full max-w-lg p-6 shadow-2xl">
      <div class="flex items-start justify-between gap-4">
        <div>
          <p class="text-xs font-bold uppercase tracking-widest text-slate-400">Confirm action</p>
          <h3 class="mt-1 text-2xl font-black text-slate-900">
            {#if pendingAction.type === 'revoke'}
              Revoke parent access
            {:else if pendingAction.type === 'restore'}
              Restore parent access
            {:else if pendingAction.type === 'suspend-family'}
              Suspend family account
            {:else}
              Restore family account
            {/if}
          </h3>
        </div>
        <button class="btn-secondary" onclick={closeAction}>Close</button>
      </div>

      <div class="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
        <p class="font-semibold text-slate-900">
          {pendingAction.user.name || pendingAction.user.email || pendingAction.user.normalized_email}
        </p>
        <p>{pendingAction.user.email || pendingAction.user.normalized_email}</p>
        <p>Family ID: {pendingAction.user.family_id ?? 'None'}</p>
        {#if pendingAction.type === 'revoke'}
          <p class="mt-2 text-rose-700">This will block only this parent. Data is not deleted.</p>
        {:else if pendingAction.type === 'suspend-family'}
          <p class="mt-2 text-amber-800">This blocks all parents and children in the family. Data is not deleted.</p>
        {/if}
      </div>

      {#if pendingAction.type === 'revoke' || pendingAction.type === 'suspend-family'}
        <label class="mt-4 block space-y-2">
          <span class="text-xs font-bold uppercase tracking-widest text-slate-400">
            {pendingAction.type === 'revoke' ? 'Revoke reason' : 'Suspend reason'}
          </span>
          <textarea
            bind:value={actionReason}
            rows="4"
            class="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none transition focus:border-hero"
            placeholder="Optional reason for the admin record"
          ></textarea>
        </label>
      {/if}

      <div class="mt-6 flex flex-wrap justify-end gap-3">
        <button class="btn-secondary" onclick={closeAction}>Cancel</button>
        <button
          class="btn-primary flex items-center gap-2"
          onclick={submitAction}
          disabled={actionLoading}
        >
          {#if actionLoading}
            Working...
          {:else}
            Confirm
          {/if}
        </button>
      </div>
    </div>
  </div>
{/if}
