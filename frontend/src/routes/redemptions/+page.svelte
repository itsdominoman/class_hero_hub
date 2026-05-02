<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import { Check, X, Clock, Trophy, ChevronLeft } from 'lucide-svelte';

  let redemptions = $state([]);
  let loading = $state(true);
  let error = $state(null);

  async function loadRedemptions() {
    try {
      loading = true;
      redemptions = await api.get('/redemptions');
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load redemptions';
    } finally {
      loading = false;
    }
  }

  onMount(loadRedemptions);

  async function processRedemption(id, action) {
    try {
      const note = action === 'reject' ? window.prompt('Reason for rejection?') : 'Approved';
      await api.post(`/redemptions/${id}/${action}`, {
        parent_note: note || ''
      });
      await loadRedemptions();
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Action failed');
    }
  }
</script>

<div class="bg-slate-50 min-h-screen pb-20">
  <div class="bg-white border-b border-slate-200 mb-12">
    <div class="max-w-4xl mx-auto px-4 py-8">
      <a href="/parent" class="inline-flex items-center gap-2 text-slate-400 hover:text-hero font-black text-xs uppercase tracking-widest mb-6 transition-colors">
        <ChevronLeft size={16} /> Back to Dashboard
      </a>
      <h1 class="text-4xl font-black text-slate-900 tracking-tight flex items-center gap-4">
        <div class="w-12 h-12 bg-reward/10 text-reward rounded-2xl flex items-center justify-center">
          <Trophy size={24} />
        </div>
        Redemption Requests
      </h1>
    </div>
  </div>

  <div class="max-w-4xl mx-auto px-4">
    {#if loading}
      <div class="flex justify-center py-20">
        <div class="animate-spin w-12 h-12 border-4 border-hero border-t-transparent rounded-full"></div>
      </div>
    {:else if error}
      <div class="card bg-red-50 p-8 text-red-600 font-bold text-center border-red-100">{error}</div>
    {:else if redemptions.length === 0}
      <div class="card p-20 text-center bg-white border-dashed border-4 border-slate-100 shadow-none">
        <p class="text-slate-300 font-black uppercase tracking-[0.3em]">No requests found</p>
      </div>
    {:else}
      <div class="space-y-6">
        {#each redemptions as r}
          <div class="card p-8 flex flex-col md:flex-row md:items-center gap-8 bg-white transition-all 
            {r.status === 'pending' ? 'border-l-8 border-hero shadow-xl' : 'opacity-60 grayscale-[0.5]'}">
            
            <div class="flex-1">
              <div class="flex items-center gap-3 mb-3">
                <span class="text-[10px] font-black uppercase tracking-widest px-3 py-1 rounded-full
                  {r.status === 'pending' ? 'bg-hero/10 text-hero' : 
                   r.status === 'approved' ? 'bg-savings/10 text-savings' : 'bg-slate-100 text-slate-500'}">
                  {r.status}
                </span>
                <span class="text-[10px] font-bold text-slate-400 flex items-center gap-1 uppercase tracking-widest">
                  <Clock size={12} /> {new Date(r.created_at).toLocaleDateString()}
                </span>
              </div>
              <h3 class="text-2xl font-black text-slate-900 mb-1">{r.title}</h3>
              <p class="text-slate-600 font-medium mb-4">{r.description || 'No description provided.'}</p>
              
              <div class="flex items-center gap-2 text-hero font-black text-xl">
                <Trophy size={20} /> {r.points} HP
              </div>
            </div>

            {#if r.status === 'pending'}
              <div class="flex flex-col gap-3 shrink-0">
                <button 
                  onclick={() => processRedemption(r.id, 'approve')}
                  class="w-full md:w-40 py-4 bg-savings text-white rounded-2xl font-black uppercase tracking-widest text-xs flex items-center justify-center gap-2 shadow-lg shadow-savings/20 hover:scale-[1.02] transition-all"
                >
                  <Check size={18} /> Approve
                </button>
                <button 
                  onclick={() => processRedemption(r.id, 'reject')}
                  class="w-full md:w-40 py-4 bg-white border-2 border-slate-100 text-slate-400 rounded-2xl font-black uppercase tracking-widest text-xs flex items-center justify-center gap-2 hover:border-penalty hover:text-penalty transition-all"
                >
                  <X size={18} /> Reject
                </button>
              </div>
            {:else}
              <div class="text-right shrink-0">
                {#if r.parent_note}
                  <p class="text-[10px] font-black text-slate-300 uppercase tracking-widest mb-1">Parent Note</p>
                  <p class="text-sm italic text-slate-500 max-w-[200px]">{r.parent_note}</p>
                {/if}
              </div>
            {/if}
          </div>
        {/each}
      </div>
    {/if}
  </div>
</div>

<style>
  :global(.card) {
    border-radius: 2rem;
    box-shadow: 0 10px 30px -10px rgba(0,0,0,0.05);
  }
  .text-hero { color: #FF5A5F; }
  .text-savings { color: #00A699; }
  .bg-hero { background: #FF5A5F; }
  .bg-savings { background: #00A699; }
  .text-reward { color: #FC642D; }
</style>
