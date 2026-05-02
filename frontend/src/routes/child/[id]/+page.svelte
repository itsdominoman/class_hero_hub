<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/state';
  import { api } from '$lib/api';
  import { Star, PiggyBank, Trophy, History, Lock, Unlock, ChevronLeft, Sparkles, TrendingUp } from 'lucide-svelte';

  type PetStage = 'egg' | 'hatchling' | 'cub' | 'hero' | 'beast';
  type ChildSummary = {
    child: {
      display_name: string;
    };
    spending_balance: number;
    savings_balance: number;
    locked_savings: number;
    available_savings: number;
    available_spending: number;
    pending_redemptions: number;
    pet_progress: {
      current_stage: PetStage;
      lifetime_points: number;
    };
  };
  type LedgerSummary = {
    gained: number;
    lost: number;
    spent: number;
    net: number;
    saved_in: number;
    saved_out: number;
    held: number;
    released: number;
    transaction_count: number;
  };
  type LedgerTransaction = {
    jar: string;
    transaction_type: string;
    points: number;
    description: string;
    created_at: string;
  };

  let childId = $derived(page.params.id);
  let summary = $state(null as ChildSummary | null);
  let ledgerSummary = $state(null as LedgerSummary | null);
  let ledger = $state([] as LedgerTransaction[]);
  let loading = $state(true);
  let error = $state(null as string | null);
  let selectedPeriod = $state<'day' | 'week' | 'month'>('week');

  // Form states
  let rewardTitle = $state('');
  let rewardPoints = $state(1);
  let submitting = $state(false);

  const periodOptions: Array<{ value: 'day' | 'week' | 'month'; label: string }> = [
    { value: 'day', label: 'Day' },
    { value: 'week', label: 'Week' },
    { value: 'month', label: 'Month' }
  ];

  const activityLabels: Record<string, string> = {
    award: 'Earned points',
    penalty: 'Lost points',
    savings_deposit: 'Moved to savings',
    savings_withdrawal: 'Moved from savings',
    redemption_hold: 'Held for reward',
    redemption_rejected: 'Hold released',
    redemption_approved: 'Spent points',
    adjustment: 'Adjustment'
  };

  async function loadData() {
    try {
      loading = true;
      error = null;
      const [childSummary, periodSummary, periodLedger] = await Promise.all([
        api.get(`/children/${childId}`),
        api.get(`/children/${childId}/ledger/summary?period=${selectedPeriod}`),
        api.get(`/children/${childId}/ledger?period=${selectedPeriod}`)
      ]);
      summary = childSummary;
      ledgerSummary = periodSummary;
      ledger = periodLedger;
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load data';
    } finally {
      loading = false;
    }
  }

  onMount(loadData);

  async function setPeriod(period: 'day' | 'week' | 'month') {
    if (selectedPeriod === period) return;
    selectedPeriod = period;
    await loadData();
  }

  async function handleRedeem(e: SubmitEvent) {
    e.preventDefault();
    if (!rewardTitle || rewardPoints < 1) return;

    try {
      submitting = true;
      await api.post(`/children/${childId}/redemptions`, {
        title: rewardTitle,
        points: rewardPoints,
        description: 'Requested from child dashboard'
      });
      rewardTitle = '';
      rewardPoints = 1;
      await loadData();
      alert('Redemption request sent to parents!');
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Redemption failed');
    } finally {
      submitting = false;
    }
  }

  async function handleSavingsDeposit() {
    const amount = window.prompt('How many points to move to savings?');
    if (!amount || isNaN(parseInt(amount))) return;

    try {
      await api.post(`/children/${childId}/savings/deposit`, {
        points: parseInt(amount),
        description: 'Self-deposit from dashboard'
      });
      await loadData();
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Deposit failed');
    }
  }

  const getPetEmoji = (stage: PetStage) => {
    switch (stage) {
      case 'egg': return '🥚';
      case 'hatchling': return '🐣';
      case 'cub': return '🦊';
      case 'hero': return '🦸';
      case 'beast': return '🐉';
      default: return '🥚';
    }
  };

  const PET_THRESHOLDS: Record<PetStage, number> = {
    egg: 0,
    hatchling: 50,
    cub: 150,
    hero: 300,
    beast: 600
  };

  const getNextThreshold = (stage: PetStage) => {
    const stages: PetStage[] = ['egg', 'hatchling', 'cub', 'hero', 'beast'];
    const idx = stages.indexOf(stage);
    if (idx < stages.length - 1) {
      return PET_THRESHOLDS[stages[idx + 1]];
    }
    return null;
  };

  const getActivityLabel = (tx: LedgerTransaction) => {
    if (tx.transaction_type === 'adjustment') {
      return tx.points >= 0 ? 'Earned points' : 'Lost points';
    }
    return activityLabels[tx.transaction_type] ?? tx.transaction_type;
  };

  const getActivityTone = (tx: LedgerTransaction) => {
    if (tx.transaction_type === 'penalty' || (tx.transaction_type === 'adjustment' && tx.points < 0)) return 'loss';
    if (tx.transaction_type === 'redemption_hold') return 'hold';
    if (tx.transaction_type === 'redemption_rejected') return 'release';
    if (tx.transaction_type === 'redemption_approved') return 'spent';
    if (tx.transaction_type === 'savings_deposit' || tx.transaction_type === 'savings_withdrawal') return 'savings';
    return tx.points >= 0 ? 'gain' : 'loss';
  };

  const getActivityCardClass = (tx: LedgerTransaction) => {
    const tone = getActivityTone(tx);
    if (tone === 'savings') return 'bg-savings/5 border-savings/20 text-savings';
    if (tone === 'hold') return 'bg-hero/5 border-hero/20 text-hero';
    if (tone === 'release') return 'bg-slate-50 border-slate-200 text-slate-500';
    if (tone === 'spent') return 'bg-slate-900 border-slate-900 text-white';
    return tx.points > 0 ? 'bg-savings/5 border-savings/20 text-savings' : 'bg-penalty/5 border-penalty/20 text-penalty';
  };

  const formatPoints = (points: number) => `${points > 0 ? '+' : ''}${points}`;

  let nextThreshold = $derived(summary ? getNextThreshold(summary.pet_progress.current_stage) : null);
  let progressPercent = $derived(summary && nextThreshold ? Math.min(100, (summary.pet_progress.lifetime_points / nextThreshold) * 100) : 100);
</script>

<div class="bg-slate-50 min-h-screen pb-20">
  {#if loading}
    <div class="flex justify-center py-40">
      <div class="animate-spin w-16 h-16 border-4 border-hero border-t-transparent rounded-full"></div>
    </div>
  {:else if error}
    <div class="max-w-xl mx-auto px-4 py-40 text-center">
      <div class="card p-12 bg-white">
        <div class="w-20 h-20 bg-red-100 text-red-600 rounded-full flex items-center justify-center mx-auto mb-8">
          <History size={40} />
        </div>
        <p class="text-xl font-black text-slate-900 mb-2">Oops! Something went wrong</p>
        <p class="text-slate-500 mb-8">{error}</p>
        <button onclick={loadData} class="btn-hero w-full py-4 rounded-xl">Try Again</button>
      </div>
    </div>
  {:else if summary}
    <!-- Profile Header -->
    <div class="bg-white border-b border-slate-200 pt-8 pb-12">
      <div class="max-w-7xl mx-auto px-4">
        <a href="/parent" class="inline-flex items-center gap-2 text-slate-400 hover:text-hero font-black text-xs uppercase tracking-widest mb-8 transition-colors">
          <ChevronLeft size={16} /> Back to Dashboard
        </a>

        <div class="flex flex-col md:flex-row gap-10 items-center">
          <div class="relative group">
            <div class="absolute -inset-4 bg-gradient-to-tr from-hero to-hero-light rounded-[3.5rem] blur-xl opacity-20 group-hover:opacity-40 transition-opacity"></div>
            <div class="w-32 h-32 md:w-44 md:h-44 bg-white rounded-[3rem] border-4 border-white shadow-2xl flex items-center justify-center text-7xl md:text-8xl relative z-10">
              {getPetEmoji(summary.pet_progress.current_stage)}
              <div class="absolute -bottom-3 -right-3 bg-hero text-white px-4 py-1.5 rounded-2xl text-xs font-black uppercase tracking-widest shadow-xl border-4 border-white">
                Lvl. {Object.keys(PET_THRESHOLDS).indexOf(summary.pet_progress.current_stage) + 1}
              </div>
            </div>
          </div>
          
          <div class="flex-1 text-center md:text-left">
            <div class="flex flex-col md:flex-row md:items-center gap-4 mb-4">
              <h1 class="text-5xl md:text-7xl font-black text-slate-900 tracking-tighter">{summary.child.display_name}</h1>
              <div class="flex justify-center md:justify-start gap-2">
                <span class="px-4 py-2 bg-hero/10 text-hero rounded-xl font-black text-xs uppercase tracking-widest border border-hero/10">
                  {summary.pet_progress.current_stage} stage
                </span>
              </div>
            </div>
            
            <div class="flex flex-wrap items-center justify-center md:justify-start gap-6">
              <div class="flex items-center gap-2 text-slate-500 font-bold">
                <div class="w-8 h-8 bg-slate-100 rounded-lg flex items-center justify-center">
                  <TrendingUp size={16} />
                </div>
                <span class="text-sm tracking-tight">{summary.pet_progress.lifetime_points} Total Lifetime HP</span>
              </div>
              <div class="flex items-center gap-2 text-slate-500 font-bold">
                <div class="w-8 h-8 bg-slate-100 rounded-lg flex items-center justify-center text-reward">
                  <Star size={16} fill="currentColor" />
                </div>
                <span class="text-sm tracking-tight">Active Hero Status</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="max-w-7xl mx-auto px-4 -mt-8 relative z-20">
      <!-- Main Stats Grid -->
      <div class="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
        <div class="card p-8 bg-slate-900 text-white border-none shadow-2xl shadow-slate-900/20 group overflow-hidden">
          <div class="absolute top-0 right-0 w-32 h-32 bg-hero/20 rounded-full -mr-16 -mt-16 group-hover:scale-150 transition-transform duration-700"></div>
          <div class="relative z-10">
            <div class="flex justify-between items-start mb-6">
              <div class="w-12 h-12 bg-white/10 rounded-2xl flex items-center justify-center border border-white/10">
                <Star size={24} fill="white" />
              </div>
              <span class="text-[10px] font-black uppercase tracking-[0.2em] opacity-50">Spending Jar</span>
            </div>
            <p class="text-5xl font-black mb-1">{summary.spending_balance}</p>
            <p class="text-xs font-black opacity-50 uppercase tracking-[0.2em]">Hero Points</p>
          </div>
        </div>

        <div class="card p-8 bg-white border-none shadow-xl group overflow-hidden">
          <div class="absolute top-0 right-0 w-32 h-32 bg-savings/5 rounded-full -mr-16 -mt-16 group-hover:scale-150 transition-transform duration-700"></div>
          <div class="relative z-10">
            <div class="flex justify-between items-start mb-6">
              <div class="w-12 h-12 bg-savings/10 text-savings rounded-2xl flex items-center justify-center">
                <PiggyBank size={24} />
              </div>
              <span class="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">Savings Jar</span>
            </div>
            <p class="text-5xl font-black text-slate-900 mb-1">{summary.savings_balance}</p>
            <p class="text-xs font-black text-savings uppercase tracking-[0.2em]">Total Stored</p>
          </div>
        </div>

        <div class="card p-8 bg-white border-none shadow-xl">
          <div class="flex justify-between items-start mb-6">
            <div class="w-12 h-12 bg-slate-50 text-slate-400 rounded-2xl flex items-center justify-center">
              <Lock size={20} />
            </div>
            <span class="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">Locked</span>
          </div>
          <p class="text-4xl font-black text-slate-900 mb-1">{summary.locked_savings}</p>
          <p class="text-xs font-black text-slate-400 uppercase tracking-[0.2em]">Wait 30 Days</p>
        </div>

        <div class="card p-8 bg-white border-none shadow-xl">
          <div class="flex justify-between items-start mb-6">
            <div class="w-12 h-12 bg-slate-50 text-slate-400 rounded-2xl flex items-center justify-center">
              <Unlock size={20} />
            </div>
            <span class="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">Unlocked</span>
          </div>
          <p class="text-4xl font-black text-slate-900 mb-1">{summary.available_savings}</p>
          <p class="text-xs font-black text-slate-400 uppercase tracking-[0.2em]">Ready to use</p>
        </div>
      </div>

      <div class="grid lg:grid-cols-3 gap-10">
        <!-- Activity Feed -->
        <div class="lg:col-span-2 space-y-8">
          {#if ledgerSummary}
            <div class="grid grid-cols-2 xl:grid-cols-3 gap-3">
              <div class="card p-4 bg-white border-none shadow-md">
                <p class="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 mb-1">Gained</p>
                <p class="text-2xl font-black text-slate-900">{ledgerSummary.gained}</p>
                <p class="text-xs font-bold text-slate-500">Earned points</p>
              </div>
              <div class="card p-4 bg-white border-none shadow-md">
                <p class="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 mb-1">Lost</p>
                <p class="text-2xl font-black text-slate-900">{ledgerSummary.lost}</p>
                <p class="text-xs font-bold text-slate-500">Penalty + negative adjustments</p>
              </div>
              <div class="card p-4 bg-white border-none shadow-md">
                <p class="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 mb-1">Spent</p>
                <p class="text-2xl font-black text-slate-900">{ledgerSummary.spent}</p>
                <p class="text-xs font-bold text-slate-500">Finalized redemption spending</p>
              </div>
              <div class="card p-4 bg-white border-none shadow-md">
                <p class="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 mb-1">Net</p>
                <p class="text-2xl font-black text-slate-900">{ledgerSummary.net}</p>
                <p class="text-xs font-bold text-slate-500">Gained - lost - spent</p>
              </div>
              <div class="card p-4 bg-white border-none shadow-md">
                <p class="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 mb-1">Saved in</p>
                <p class="text-2xl font-black text-slate-900">{ledgerSummary.saved_in}</p>
                <p class="text-xs font-bold text-slate-500">Moved to savings</p>
              </div>
              <div class="card p-4 bg-white border-none shadow-md">
                <p class="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 mb-1">Saved out</p>
                <p class="text-2xl font-black text-slate-900">{ledgerSummary.saved_out}</p>
                <p class="text-xs font-bold text-slate-500">Moved from savings</p>
              </div>
              <div class="card p-4 bg-white border-none shadow-md">
                <p class="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 mb-1">Held</p>
                <p class="text-2xl font-black text-slate-900">{ledgerSummary.held}</p>
                <p class="text-xs font-bold text-slate-500">Held for reward</p>
              </div>
              <div class="card p-4 bg-white border-none shadow-md">
                <p class="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 mb-1">Released</p>
                <p class="text-2xl font-black text-slate-900">{ledgerSummary.released}</p>
                <p class="text-xs font-bold text-slate-500">Hold released</p>
              </div>
              <div class="card p-4 bg-white border-none shadow-md">
                <p class="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 mb-1">Transactions</p>
                <p class="text-2xl font-black text-slate-900">{ledgerSummary.transaction_count}</p>
                <p class="text-xs font-bold text-slate-500">Activity items in this period</p>
              </div>
            </div>
          {/if}

          <div class="card p-6 bg-white border-none shadow-md">
            <div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div class="flex items-center gap-3">
                <History size={32} class="text-hero" />
                <div>
                  <h2 class="text-3xl font-black text-slate-900 tracking-tight">Recent Activity</h2>
                  <p class="text-xs font-black uppercase tracking-[0.2em] text-slate-400">Filtered by calendar period</p>
                </div>
              </div>

              <div class="inline-flex rounded-2xl bg-slate-100 p-1">
                {#each periodOptions as option}
                  <button
                    type="button"
                    onclick={() => setPeriod(option.value)}
                    class={`px-4 py-2 rounded-xl text-xs font-black uppercase tracking-[0.2em] transition-all ${selectedPeriod === option.value ? 'bg-white text-hero shadow-sm' : 'text-slate-500 hover:text-slate-900'}`}
                  >
                    {option.label}
                  </button>
                {/each}
              </div>
            </div>
          </div>

          <div class="space-y-4">
            {#each ledger as tx}
              <div class="card p-6 flex items-center gap-6 bg-white hover:bg-slate-50/50 transition-all border-none shadow-md group">
                <div class={`w-16 h-16 rounded-2xl flex flex-col items-center justify-center border-2 ${getActivityCardClass(tx)}`}>
                  <span class="text-xl font-black">{formatPoints(tx.points)}</span>
                  <span class="text-[8px] font-black uppercase">HP</span>
                </div>
                <div class="flex-1">
                  <div class="flex flex-wrap items-center gap-2 mb-2">
                    <span class="text-[10px] font-black uppercase tracking-widest text-slate-500 bg-slate-100 px-2 py-0.5 rounded-lg">{getActivityLabel(tx)}</span>
                    <span class="text-[10px] font-black uppercase tracking-widest text-slate-300">{new Date(tx.created_at).toLocaleDateString()}</span>
                  </div>
                  <p class="text-lg font-black text-slate-900 leading-none mb-2">{tx.description}</p>
                  <div class="flex items-center gap-3">
                    <span class="text-[10px] font-black uppercase tracking-widest text-slate-400 bg-slate-100 px-2 py-0.5 rounded-lg">{tx.jar} jar</span>
                  </div>
                </div>
              </div>
            {:else}
              <div class="py-20 text-center card bg-white border-dashed border-4 border-slate-100 shadow-none">
                <p class="text-slate-300 font-black uppercase tracking-[0.3em]">No activity to show</p>
              </div>
            {/each}
          </div>
        </div>

        <!-- Sidebar Actions -->
        <div class="space-y-8">
          <!-- Pet Evolution Card -->
          <div class="card p-8 bg-white shadow-xl relative overflow-hidden group">
            <div class="absolute top-0 right-0 w-32 h-32 bg-hero/5 rounded-full -mr-16 -mt-16"></div>
            <h3 class="text-xl font-black text-slate-900 mb-6 flex items-center gap-2 relative z-10">
              <Sparkles size={20} class="text-hero" /> Evolution Progress
            </h3>
            
            {#if nextThreshold}
              <div class="mb-6 relative z-10">
                <div class="flex justify-between text-[10px] font-black uppercase tracking-widest text-slate-400 mb-3">
                  <span>Target: {nextThreshold} HP</span>
                  <span>{Math.round(progressPercent)}%</span>
                </div>
                <div class="h-6 bg-slate-100 rounded-2xl overflow-hidden p-1 shadow-inner">
                  <div 
                    class="h-full bg-gradient-to-r from-hero to-hero-light rounded-xl transition-all duration-1000 shadow-lg shadow-hero/20" 
                    style="width: {progressPercent}%"
                  ></div>
                </div>
              </div>
              <p class="text-sm text-slate-500 font-medium relative z-10">Earn {nextThreshold - summary.pet_progress.lifetime_points} more points to reach the next stage!</p>
            {:else}
              <div class="p-6 bg-hero rounded-3xl text-center shadow-xl shadow-hero/30 relative z-10">
                <div class="w-16 h-16 bg-white/20 rounded-2xl flex items-center justify-center mx-auto mb-4 text-3xl">🐉</div>
                <p class="text-white font-black uppercase tracking-widest text-xs">Ultimate Form Unlocked!</p>
              </div>
            {/if}
          </div>

          <!-- Quick Actions -->
          <div class="card p-8 bg-hero text-white shadow-2xl shadow-hero/30 relative overflow-hidden group">
            <div class="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full blur-3xl -mr-32 -mt-32"></div>
            <h3 class="text-2xl font-black mb-6 flex items-center gap-3 relative z-10">
              <Trophy size={28} /> Rewards
            </h3>
            <p class="text-white/80 text-sm font-medium mb-8 relative z-10 leading-relaxed">Ready to redeem your hard-earned points? Send a request to your parents!</p>
            <form onsubmit={handleRedeem} class="space-y-4 relative z-10">
              <input 
                type="text" 
                bind:value={rewardTitle}
                placeholder="I want to redeem..." 
                class="w-full px-5 py-4 rounded-2xl bg-white/10 border border-white/20 placeholder:text-white/40 focus:outline-none focus:bg-white/20 transition-all font-bold text-sm" 
              />
              <input 
                type="number" 
                bind:value={rewardPoints}
                min="1"
                placeholder="Cost in Hero Points" 
                class="w-full px-5 py-4 rounded-2xl bg-white/10 border border-white/20 placeholder:text-white/40 focus:outline-none focus:bg-white/20 transition-all font-bold text-sm" 
              />
              <button 
                type="submit"
                disabled={submitting}
                class="w-full py-5 bg-white text-hero rounded-2xl font-black uppercase tracking-[0.2em] text-xs hover:bg-slate-50 active:scale-95 transition-all shadow-xl shadow-hero-dark/20 disabled:opacity-50"
              >
                {submitting ? 'Sending...' : 'Send Request'}
              </button>
            </form>
          </div>

          <div class="card p-8 bg-white shadow-xl group border-2 border-transparent hover:border-savings/20 transition-all">
            <h3 class="text-xl font-black text-savings mb-4 flex items-center gap-2">
              <PiggyBank size={24} /> Savings Strategy
            </h3>
            <p class="text-sm text-slate-500 font-medium mb-8 leading-relaxed">Lock points in your savings jar for 30 days to build your future fortune!</p>
            <button 
              onclick={handleSavingsDeposit}
              class="w-full py-5 bg-savings text-white rounded-2xl font-black uppercase tracking-[0.2em] text-xs hover:bg-savings-dark active:scale-95 transition-all shadow-xl shadow-savings/20"
            >
              Deposit to Savings
            </button>
          </div>
        </div>
      </div>
    </div>
  {:else}
    <div class="flex justify-center py-40">
      <p class="text-slate-400 font-black uppercase tracking-widest">Child not found</p>
    </div>
  {/if}
</div>

<style>
  :global(.card) {
    border-radius: 2rem;
    box-shadow: 0 10px 30px -10px rgba(0,0,0,0.05);
  }
  .text-hero { color: #FF5A5F; }
  .text-savings { color: #00A699; }
  .text-reward { color: #FC642D; }
  .btn-hero { background: #FF5A5F; color: white; font-weight: 900; }
</style>
