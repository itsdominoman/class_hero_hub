<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';

  let requests = $state([]);
  let loading = $state(true);
  let error = $state('');
  let processingId = $state(null);

  async function loadRequests() {
    loading = true;
    try {
      requests = await api.get('/admin/registration-requests');
    } catch (err: any) {
      error = err.message || 'Failed to load requests';
    } finally {
      loading = false;
    }
  }

  async function approveRequest(id: number) {
    if (!confirm('Are you sure you want to approve this request?')) return;
    processingId = id;
    try {
      await api.post(`/admin/registration-requests/${id}/approve`);
      await loadRequests();
    } catch (err: any) {
      alert(err.message || 'Failed to approve request');
    } finally {
      processingId = null;
    }
  }

  async function rejectRequest(id: number) {
    const reason = prompt('Please enter a rejection reason (optional):');
    if (reason === null) return;
    
    processingId = id;
    try {
      await api.post(`/admin/registration-requests/${id}/reject`, {
        rejection_reason: reason
      });
      await loadRequests();
    } catch (err: any) {
      alert(err.message || 'Failed to reject request');
    } finally {
      processingId = null;
    }
  }

  onMount(loadRequests);

  function formatDate(dateStr: string) {
    return new Date(dateStr).toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }
</script>

<div class="max-w-6xl mx-auto px-4 py-8">
  <div class="flex items-center justify-between mb-8">
    <div>
      <h1 class="text-3xl font-black text-slate-900">Registration Requests</h1>
      <p class="text-slate-500">Review and manage access requests for Family Hero Hub.</p>
    </div>
    <button onclick={loadRequests} class="btn-secondary flex items-center gap-2">
      <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/></svg>
      Refresh
    </button>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-20">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-hero"></div>
    </div>
  {:else if error}
    <div class="bg-rose-50 border-2 border-rose-100 text-rose-600 p-6 rounded-2xl text-center">
      <p class="font-bold mb-2">Error loading requests</p>
      <p class="text-sm">{error}</p>
    </div>
  {:else if requests.length === 0}
    <div class="bg-slate-50 border-2 border-dashed border-slate-200 p-20 rounded-3xl text-center">
      <p class="text-slate-400 font-medium">No registration requests found.</p>
    </div>
  {:else}
    <div class="grid gap-6">
      {#each requests as req}
        <div class="card p-6 flex flex-col md:flex-row md:items-center justify-between gap-6 transition-all {req.status === 'pending' ? 'border-hero/20 bg-hero/[0.02]' : ''}">
          <div class="space-y-1">
            <div class="flex items-center gap-3 mb-2">
              <span class="px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider
                {req.status === 'pending' ? 'bg-hero/10 text-hero' : ''}
                {req.status === 'approved' ? 'bg-emerald-100 text-emerald-600' : ''}
                {req.status === 'rejected' ? 'bg-slate-100 text-slate-500' : ''}
              ">
                {req.status}
              </span>
              <span class="text-xs text-slate-400 font-medium">{formatDate(req.created_at)}</span>
            </div>
            <h3 class="text-xl font-bold text-slate-900">{req.name}</h3>
            <p class="text-slate-600 font-medium">{req.email}</p>
            <p class="text-sm text-slate-500">Family: <span class="text-slate-700 font-bold">{req.family_name}</span></p>
            {#if req.message}
              <div class="mt-4 p-4 bg-white/50 border border-slate-100 rounded-xl text-sm text-slate-600 italic">
                "{req.message}"
              </div>
            {/if}
          </div>

          {#if req.status === 'pending'}
            <div class="flex items-center gap-3">
              <button
                onclick={() => rejectRequest(req.id)}
                disabled={processingId === req.id}
                class="btn-secondary text-rose-600 hover:bg-rose-50 hover:border-rose-100 border-transparent py-3 px-6"
              >
                Reject
              </button>
              <button
                onclick={() => approveRequest(req.id)}
                disabled={processingId === req.id}
                class="btn-primary py-3 px-8 shadow-lg shadow-hero/20"
              >
                {#if processingId === req.id}
                  Approving...
                {:else}
                  Approve Access
                {/if}
              </button>
            </div>
          {:else if req.status === 'approved'}
            <div class="text-right">
              <p class="text-xs text-slate-400 font-bold uppercase tracking-widest mb-1">Approved On</p>
              <p class="text-sm text-emerald-600 font-bold">{formatDate(req.approved_at)}</p>
            </div>
          {:else if req.status === 'rejected'}
            <div class="text-right">
              <p class="text-xs text-slate-400 font-bold uppercase tracking-widest mb-1">Rejected On</p>
              <p class="text-sm text-slate-500 font-bold">{formatDate(req.rejected_at)}</p>
              {#if req.rejection_reason}
                <p class="text-xs text-slate-400 mt-1 max-w-[200px] truncate" title={req.rejection_reason}>
                  Reason: {req.rejection_reason}
                </p>
              {/if}
            </div>
          {/if}
        </div>
      {/each}
    </div>
  {/if}
</div>
