<script lang="ts">
  import { onMount } from 'svelte';
  import { _, locale } from 'svelte-i18n';
  import { api } from '$lib/api';
  import { sortRedemptions } from '$lib/redemptions';
  import { Check, X, Clock, Trophy, ChevronLeft, RefreshCcw } from 'lucide-svelte';

  let redemptions = $state<any[]>([]);
  let loading = $state(true);
  let error = $state<string | null>(null);
  let processingRedemptionsById = $state<Record<number, 'approve' | 'reject'>>({});

  // Pending first (newest on top), then resolved (most recently reviewed first).
  const sortedRedemptions = $derived(sortRedemptions(redemptions));

  async function loadRedemptions() {
    try {
      loading = true;
      redemptions = await api.get('/redemptions');
    } catch (e) {
      error = $_('redemptions.errorLoad');
    } finally {
      loading = false;
    }
  }

  onMount(loadRedemptions);

  function getStatusLabel(status: string) {
    switch (status) {
      case 'pending':
        return $_('common.pending');
      case 'approved':
        return $_('redemptions.statusApproved');
      case 'rejected':
        return $_('redemptions.statusRejected');
      default:
        return $_('redemptions.statusUnknown');
    }
  }

  function formatCreatedAt(createdAt: string) {
    return new Date(createdAt).toLocaleDateString($locale || 'en');
  }

  async function processRedemption(id: number, action: 'approve' | 'reject', event?: Event) {
    if (processingRedemptionsById[id] != null) return;

    const payload: { parent_note?: string } = {};

    if (action === 'reject') {
      const note = window.prompt($_('common.rejectionReasonPrompt'));
      if (note === null) return;

      const trimmedNote = note.trim();
      if (trimmedNote) {
        payload.parent_note = trimmedNote;
      }
    }

    const trigger = event?.currentTarget as HTMLButtonElement | null;
    const actionGroup = trigger?.closest('[data-redemption-actions]') as HTMLElement | null;
    processingRedemptionsById = { ...processingRedemptionsById, [id]: action };
    if (trigger) trigger.disabled = true;
    actionGroup?.querySelectorAll('button').forEach((button) => {
      (button as HTMLButtonElement).disabled = true;
    });
    try {
      await api.post(`/redemptions/${id}/${action}`, payload);
      await loadRedemptions();
    } catch (e) {
      alert($_('redemptions.errorActionFailed'));
    } finally {
      const { [id]: _released, ...remaining } = processingRedemptionsById;
      processingRedemptionsById = remaining;
    }
  }
</script>

<div class="bg-slate-50 min-h-dvh max-w-full overflow-x-hidden pb-[calc(5rem+var(--safe-bottom))]">
  <div class="bg-white border-b border-slate-200 mb-12">
    <div class="max-w-4xl mx-auto px-3 sm:px-4 py-6 md:py-8">
      <a href="/parent" class="inline-flex items-center gap-2 text-slate-400 hover:text-hero font-bold text-xs uppercase tracking-wide mb-6 transition-colors">
        <ChevronLeft size={16} /> {$_('redemptions.backToParentDashboard')}
      </a>
      <h1 class="text-3xl sm:text-4xl font-black text-slate-900 tracking-tight flex items-center gap-3 sm:gap-4">
        <div class="w-11 h-11 sm:w-12 sm:h-12 bg-reward/10 text-reward rounded-2xl flex shrink-0 items-center justify-center">
          <Trophy size={24} />
        </div>
        {$_('redemptions.title')}
      </h1>
    </div>
  </div>

  <div class="max-w-4xl mx-auto px-3 sm:px-4">
    {#if loading}
      <div class="flex justify-center py-20">
        <div class="animate-spin w-12 h-12 border-4 border-hero border-t-transparent rounded-full"></div>
      </div>
    {:else if error}
      <div class="card bg-red-50 p-8 text-red-600 font-bold text-center border-red-100">{error}</div>
    {:else if redemptions.length === 0}
      <div class="card p-10 md:p-20 text-center bg-white border-dashed border-4 border-slate-100 shadow-none">
        <p class="text-slate-300 font-semibold uppercase tracking-wide">{$_('redemptions.noRequests')}</p>
      </div>
    {:else}
      <div class="space-y-6">
        {#each sortedRedemptions as r}
          <div class="card p-5 sm:p-6 md:p-8 flex flex-col md:flex-row md:items-center gap-5 md:gap-8 bg-white transition-all
            {r.status === 'pending' ? 'border-l-8 border-hero shadow-xl' : 'opacity-60 grayscale-[0.5]'}">
            
            <div class="flex-1 min-w-0">
              <div class="flex flex-wrap items-center gap-3 mb-3">
                <span class="text-[10px] font-bold uppercase tracking-wide px-3 py-1 rounded-full
                  {r.status === 'pending' ? 'bg-hero/10 text-hero' : 
                   r.status === 'approved' ? 'bg-savings/10 text-savings' : 'bg-slate-100 text-slate-500'}">
                  {getStatusLabel(r.status)}
                </span>
                <span class="text-[10px] font-bold text-slate-400 flex items-center gap-1 uppercase tracking-wide">
                  <Clock size={12} /> {formatCreatedAt(r.created_at)}
                </span>
                <span class="text-[10px] font-bold text-slate-500 uppercase tracking-wide">
                  {$_('redemptions.requestedBy', { values: { childName: r.child_name || `#${r.child_id}` } })}
                </span>
              </div>
              <h3 class="text-xl sm:text-2xl font-bold text-slate-900 mb-1 break-words">{r.title}</h3>
              <p class="text-slate-600 font-medium mb-4 break-words">{r.description || $_('common.noDescriptionProvided')}</p>
              
              <div class="flex items-center gap-2 text-hero font-bold text-xl">
                <Trophy size={20} /> {$_('redemptions.points', { values: { points: r.points } })}
              </div>
            </div>

            {#if r.status === 'pending'}
              <div class="grid grid-cols-1 gap-3 shrink-0 sm:grid-cols-2 md:flex md:flex-col" data-redemption-actions>
                <button 
                  onclick={(e) => processRedemption(r.id, 'approve', e)}
                  disabled={processingRedemptionsById[r.id] != null}
                  class="w-full md:w-40 py-4 bg-savings text-white rounded-2xl font-bold uppercase tracking-wide text-xs flex items-center justify-center gap-2 shadow-lg shadow-savings/20 hover:scale-[1.02] transition-all disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {#if processingRedemptionsById[r.id] === 'approve'}
                    <RefreshCcw size={18} class="animate-spin" />
                  {:else}
                    <Check size={18} />
                  {/if}
                  {$_('common.approve')}
                </button>
                <button 
                  onclick={(e) => processRedemption(r.id, 'reject', e)}
                  disabled={processingRedemptionsById[r.id] != null}
                  class="w-full md:w-40 py-4 bg-white border-2 border-slate-100 text-slate-400 rounded-2xl font-bold uppercase tracking-wide text-xs flex items-center justify-center gap-2 hover:border-penalty hover:text-penalty transition-all disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {#if processingRedemptionsById[r.id] === 'reject'}
                    <RefreshCcw size={18} class="animate-spin" />
                  {:else}
                    <X size={18} />
                  {/if}
                  {$_('common.reject')}
                </button>
              </div>
            {:else}
              <div class="text-left md:text-right shrink-0 min-w-0">
                {#if r.parent_note}
                  <p class="text-[10px] font-bold text-slate-300 uppercase tracking-wide mb-1">{$_('redemptions.parentNote')}</p>
                  <p class="text-sm italic text-slate-500 max-w-full md:max-w-[200px] break-words">{r.parent_note}</p>
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
  .text-hero { color: #7C3AED; }
  .text-savings { color: #10B981; }
  .bg-savings { background: #10B981; }
  .text-reward { color: #F59E0B; }
</style>
