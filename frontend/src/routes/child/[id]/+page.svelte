<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/state';
  import { api } from '$lib/api';
  import {
    ArrowRight,
    BadgeCheck,
    Clock3,
    Gift,
    History,
    PiggyBank,
    Sparkles,
    Star,
    Trophy
  } from 'lucide-svelte';

  type PetStage = 'egg' | 'hatchling' | 'cub' | 'hero' | 'beast';

  type ChildSummary = {
    child: {
      id: number;
      display_name: string;
      avatar_name: string | null;
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

  type LedgerTransaction = {
    jar: string;
    transaction_type: string;
    points: number;
    description: string;
    created_at: string;
  };

  type RedemptionRequest = {
    id: number;
    child_id: number;
    points: number;
    title: string;
    description: string;
    status: 'pending' | 'approved' | 'rejected';
    parent_note: string | null;
    created_at: string;
    reviewed_at: string | null;
  };

  type Reward = {
    id: number;
    title: string;
    description: string | null;
    icon: string | null;
    points: number;
    is_active: boolean;
  };

  type ErrorKind = 'not-linked' | 'wrong-child' | 'not-found' | 'server-error';

  let childId = $derived(page.params.id);
  let childIdNumber = $derived(Number(childId));

  let summary = $state(null as ChildSummary | null);
  let ledger = $state([] as LedgerTransaction[]);
  let redemptions = $state([] as RedemptionRequest[]);
  let rewards = $state([] as Reward[]);
  let accessMode = $state<'parent' | 'child'>('parent');
  let loading = $state(true);
  let error = $state(null as string | null);
  let errorKind = $state(null as ErrorKind | null);
  let linkedChildName = $state('');
  let submitting = $state(false);
  let submittingRewardId = $state<number | null>(null);
  let statusMessage = $state('');
  let statusTone = $state<'success' | 'error' | 'info'>('success');
  let customRewardTitle = $state('');
  let customRewardPoints = $state(1);

  const PET_STAGES: Record<PetStage, { label: string; emoji: string }> = {
    egg: { label: 'Egg', emoji: '🥚' },
    hatchling: { label: 'Hatchling', emoji: '🐣' },
    cub: { label: 'Cub', emoji: '🦊' },
    hero: { label: 'Hero', emoji: '🦸' },
    beast: { label: 'Beast', emoji: '🐉' }
  };

  const ACTIVITY_LABELS: Record<string, string> = {
    award: 'Earned',
    penalty: 'Lost',
    adjustment: 'Adjusted',
    savings_deposit: 'Saved',
    savings_withdrawal: 'Unsaved',
    redemption_hold: 'Reward requested',
    redemption_rejected: 'Request returned',
    redemption_approved: 'Reward approved'
  };

  const ACTIVITY_TONES: Record<string, string> = {
    award: 'gain',
    penalty: 'loss',
    adjustment: 'adjustment',
    savings_deposit: 'savings',
    savings_withdrawal: 'savings',
    redemption_hold: 'hold',
    redemption_rejected: 'release',
    redemption_approved: 'approved'
  };

  const rewardOptions = $derived(
    rewards
      .filter((reward) => reward.is_active && reward.points > 0)
      .sort((a, b) => a.points - b.points)
  );

  const pendingRequests = $derived(
    redemptions
      .filter((request) => request.child_id === childIdNumber && request.status === 'pending')
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
  );

  const recentActivity = $derived(
    ledger.slice(0, 8)
  );

  const avatarLabel = $derived(summary?.child.avatar_name?.trim() || '');
  const stageIcon = $derived(summary ? PET_STAGES[summary.pet_progress.current_stage].emoji : PET_STAGES.egg.emoji);
  const stageInfo = $derived(summary ? PET_STAGES[summary.pet_progress.current_stage] : PET_STAGES.egg);
  const progressToNextStage = $derived(summary
    ? (() => {
        const thresholds: Record<PetStage, number> = {
          egg: 0,
          hatchling: 50,
          cub: 150,
          hero: 300,
          beast: 600
        };
        const order: PetStage[] = ['egg', 'hatchling', 'cub', 'hero', 'beast'];
        const index = order.indexOf(summary.pet_progress.current_stage);
        const nextStage = index < order.length - 1 ? order[index + 1] : null;
        if (!nextStage) return 100;
        return Math.min(100, Math.round((summary.pet_progress.lifetime_points / thresholds[nextStage]) * 100));
      })()
    : 0
  );

  function setStatus(message: string, tone: 'success' | 'error' | 'info' = 'success') {
    statusMessage = message;
    statusTone = tone;
  }

  function formatPoints(points: number) {
    return `${points > 0 ? '+' : ''}${points}`;
  }

  function formatDate(value: string) {
    return new Date(value).toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric'
    });
  }

  function formatDateTime(value: string) {
    return new Date(value).toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit'
    });
  }

  function getActivityTone(tx: LedgerTransaction) {
    if (tx.transaction_type === 'award') return 'gain';
    if (tx.transaction_type === 'penalty') return 'loss';
    if (tx.transaction_type === 'adjustment') return tx.points >= 0 ? 'gain' : 'loss';
    return ACTIVITY_TONES[tx.transaction_type] ?? 'neutral';
  }

  function getActivityLabel(tx: LedgerTransaction) {
    if (tx.transaction_type === 'adjustment') {
      return tx.points >= 0 ? 'Adjusted up' : 'Adjusted down';
    }
    return ACTIVITY_LABELS[tx.transaction_type] ?? 'Activity';
  }

  function getActivityBadgeClass(tx: LedgerTransaction) {
    const tone = getActivityTone(tx);
    if (tone === 'gain') return 'bg-savings/10 text-savings border-savings/20';
    if (tone === 'loss') return 'bg-penalty/10 text-penalty border-penalty/20';
    if (tone === 'savings') return 'bg-hero/10 text-hero border-hero/20';
    if (tone === 'hold') return 'bg-reward/10 text-reward border-reward/20';
    if (tone === 'release') return 'bg-slate-100 text-slate-500 border-slate-200';
    if (tone === 'approved') return 'bg-slate-900 text-white border-slate-900';
    return 'bg-slate-100 text-slate-500 border-slate-200';
  }

  function rewardShortfall(points: number) {
    if (!summary) return 0;
    return Math.max(0, points - summary.available_spending);
  }

  const isAuthError = (message: string) =>
    message.toLowerCase().includes('not authenticated') ||
    message.toLowerCase().includes('invalid token') ||
    message.toLowerCase().includes('child session') ||
    message.toLowerCase().includes('invalid child session') ||
    message.toLowerCase().includes('child session missing');

  const isNotFoundError = (message: string) =>
    message.toLowerCase().includes('not found');

  async function loadData() {
    try {
      loading = true;
      error = null;
      errorKind = null;
      linkedChildName = '';

      try {
        const childSummary = await api.get('/child/me');
        accessMode = 'child';

        if (Number(childId) !== childSummary.child.id) {
          linkedChildName = childSummary.child.display_name;
          errorKind = 'wrong-child';
          error = `This device is linked to ${childSummary.child.display_name}, not this child profile.`;
          summary = null;
          ledger = [];
          redemptions = [];
          rewards = [];
          return;
        }

        const [activity, childRedemptions, childRewards] = await Promise.all([
          api.get('/child/ledger?period=month'),
          api.get('/child/redemptions'),
          api.get('/child/rewards')
        ]);

        summary = childSummary;
        ledger = activity;
        redemptions = childRedemptions;
        rewards = childRewards;
      } catch (childError) {
        if (!(childError instanceof Error) || !isAuthError(childError.message)) {
          throw childError;
        }

        accessMode = 'parent';
        try {
          const [childSummary, activity, allRedemptions, allRewards] = await Promise.all([
            api.get(`/children/${childId}`),
            api.get(`/children/${childId}/ledger?period=month`),
            api.get('/redemptions'),
            api.get('/rewards')
          ]);

          summary = childSummary;
          ledger = activity;
          redemptions = allRedemptions;
          rewards = allRewards;
        } catch (parentError) {
          const message = parentError instanceof Error ? parentError.message : 'Unable to load child dashboard';
          if (isAuthError(message)) {
            errorKind = 'not-linked';
            error = 'This device is not linked yet.';
          } else if (isNotFoundError(message)) {
            errorKind = 'not-found';
            error = 'Child profile not found.';
          } else {
            errorKind = 'server-error';
            error = message;
          }
          summary = null;
          ledger = [];
          redemptions = [];
          rewards = [];
        }
      }
    } catch (e) {
      errorKind = 'server-error';
      error = e instanceof Error ? e.message : 'Failed to load dashboard';
      summary = null;
      ledger = [];
      redemptions = [];
      rewards = [];
    } finally {
      loading = false;
    }
  }

  async function requestReward(title: string, points: number, description: string) {
    if (!summary || points < 1) return;
    if (points > summary.available_spending) {
      setStatus('That reward costs more points than you have right now.', 'error');
      return;
    }

    try {
      submitting = true;
      const requestPath = accessMode === 'child'
        ? '/child/redemptions'
        : `/children/${childId}/redemptions`;
      await api.post(requestPath, {
        title,
        points,
        description
      });
      customRewardTitle = '';
      customRewardPoints = 1;
      setStatus('Request sent. A parent will review it soon.', 'success');
      await loadData();
    } catch (e) {
      setStatus(e instanceof Error ? e.message : 'Could not send the reward request.', 'error');
    } finally {
      submitting = false;
    }
  }

  async function requestPresetReward(reward: Reward) {
    if (!summary) return;
    try {
      submittingRewardId = reward.id;
      await requestReward(
        reward.title,
        reward.points,
        reward.description?.trim() || 'Requested from the child dashboard'
      );
    } finally {
      submittingRewardId = null;
    }
  }

  async function submitCustomRequest(e: SubmitEvent) {
    e.preventDefault();
    await requestReward(
      customRewardTitle.trim(),
      customRewardPoints,
      'Requested from the child dashboard'
    );
  }

  onMount(loadData);
</script>

<div class="min-h-screen bg-[#fffaf4] pb-16 overflow-x-hidden">
  {#if loading}
    <div class="flex justify-center py-40">
      <div class="flex flex-col items-center gap-4">
        <div class="animate-spin w-14 h-14 border-4 border-hero border-t-transparent rounded-full"></div>
        <p class="text-xs font-black uppercase tracking-[0.3em] text-slate-400">Loading dashboard</p>
      </div>
    </div>
  {:else if error}
    <div class="max-w-xl mx-auto px-4 py-24">
      <div class="card bg-white p-8 md:p-10 text-center border border-red-100 shadow-xl">
        <div class="w-16 h-16 rounded-2xl bg-red-100 text-red-600 flex items-center justify-center mx-auto mb-6">
          <History size={30} />
        </div>
        <h1 class="text-2xl md:text-3xl font-black text-slate-900 mb-2">
          {errorKind === 'not-linked'
            ? 'This device is not linked yet'
            : errorKind === 'wrong-child'
              ? `This device is linked to ${linkedChildName || 'another child'}`
              : errorKind === 'not-found'
                ? 'Child profile not found'
                : 'Dashboard unavailable'}
        </h1>
        <p class="text-slate-600 mb-6 break-words">{error}</p>
        {#if errorKind === 'wrong-child'}
          <a href="/parent" class="btn-secondary inline-flex w-full items-center justify-center px-6 py-4 rounded-2xl mb-3">
            Back to parent dashboard
          </a>
        {/if}
        <button type="button" class="btn-hero px-6 py-4 rounded-2xl" onclick={loadData}>Try again</button>
      </div>
    </div>
  {:else if summary}
    <section class="border-b border-[#f0e4d7] bg-[linear-gradient(180deg,#fffaf4_0%,#ffffff_100%)]">
      <div class="max-w-7xl mx-auto px-4 py-10 md:py-12">
        <div class="grid gap-8 lg:grid-cols-[minmax(0,1.3fr)_minmax(320px,0.7fr)] items-center">
          <div class="space-y-6">
            <div class="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-hero/10 text-hero border border-hero/20 text-xs font-black uppercase tracking-[0.22em]">
              <Sparkles size={14} />
              Kid dashboard
            </div>

            <div class="flex flex-col sm:flex-row sm:items-center gap-5">
                <div class="w-24 h-24 md:w-28 md:h-28 rounded-[2rem] bg-white border-4 border-white shadow-[0_16px_40px_-18px_rgba(0,0,0,0.35)] flex items-center justify-center text-slate-900 overflow-hidden">
                  <div class="w-full h-full bg-gradient-to-br from-[#ffe7cb] via-[#fff] to-[#dff7ee] flex flex-col items-center justify-center text-slate-900">
                    <div class="text-4xl md:text-5xl leading-none">{stageIcon}</div>
                    <div class="mt-1 px-2 text-center text-[10px] font-black uppercase tracking-[0.18em] text-slate-500 break-words">
                      {stageInfo.label}
                    </div>
                  </div>
                </div>

              <div class="min-w-0">
                <h1 class="text-4xl md:text-6xl font-black text-slate-950 tracking-tight break-words">
                  {summary.child.display_name}
                </h1>
                <p class="text-slate-600 font-medium mt-2 max-w-2xl">
                  Keep earning points, pick rewards you can afford, and watch your hero grow.
                </p>
                <div class="mt-4 flex flex-wrap gap-3">
                  <span class="inline-flex items-center gap-2 px-3 py-2 rounded-full bg-slate-900 text-white text-xs font-black uppercase tracking-[0.2em]">
                    <BadgeCheck size={14} />
                    {stageInfo.label} stage
                  </span>
                  <span class="inline-flex items-center gap-2 px-3 py-2 rounded-full bg-white text-slate-700 border border-slate-200 text-xs font-black uppercase tracking-[0.2em]">
                    {accessMode === 'child' ? 'Child session' : 'Parent preview'}
                  </span>
                  {#if avatarLabel}
                    <span class="inline-flex items-center gap-2 px-3 py-2 rounded-full bg-white text-slate-700 border border-slate-200 text-xs font-black uppercase tracking-[0.2em]">
                      Avatar: {avatarLabel}
                    </span>
                  {/if}
                </div>
              </div>
            </div>

            {#if statusMessage}
              <div class={`rounded-2xl px-4 py-3 text-sm font-bold border ${statusTone === 'success' ? 'bg-savings/10 text-savings border-savings/20' : statusTone === 'error' ? 'bg-red-50 text-red-700 border-red-100' : 'bg-slate-100 text-slate-700 border-slate-200'}`}>
                {statusMessage}
              </div>
            {/if}
          </div>

          <div class="card bg-white p-6 md:p-8 shadow-xl border border-slate-100">
            <div class="flex items-center justify-between mb-5">
              <div>
                <p class="text-[10px] font-black uppercase tracking-[0.25em] text-slate-400">Current points</p>
                <p class="text-4xl md:text-5xl font-black text-slate-950 mt-1">{summary.spending_balance}</p>
              </div>
              <div class="w-14 h-14 rounded-2xl bg-hero/10 text-hero flex items-center justify-center">
                <Star size={28} fill="currentColor" />
              </div>
            </div>

            <div class="space-y-4">
              <div>
                <div class="flex items-center justify-between text-xs font-black uppercase tracking-[0.22em] text-slate-400 mb-2">
                  <span>Next stage</span>
                  <span>{summary.pet_progress.lifetime_points} lifetime</span>
                </div>
                <div class="h-4 rounded-full bg-slate-100 overflow-hidden">
                  <div class="h-full rounded-full bg-gradient-to-r from-hero to-[#ff8d59]" style={`width: ${progressToNextStage}%`}></div>
                </div>
              </div>

              <div class="grid grid-cols-2 gap-3">
                <div class="rounded-2xl bg-[#fff8e9] border border-[#f4e3b2] p-4">
                  <p class="text-[10px] font-black uppercase tracking-[0.22em] text-[#b98612]">Savings</p>
                  <p class="text-2xl font-black text-slate-950 mt-1">{summary.savings_balance}</p>
                </div>
                <div class="rounded-2xl bg-[#f0fbf7] border border-[#cdeee2] p-4">
                  <p class="text-[10px] font-black uppercase tracking-[0.22em] text-savings">Available</p>
                  <p class="text-2xl font-black text-slate-950 mt-1">{summary.available_spending}</p>
                </div>
              </div>

              <div class="grid grid-cols-2 gap-3">
                <div class="rounded-2xl bg-slate-50 border border-slate-200 p-4">
                  <p class="text-[10px] font-black uppercase tracking-[0.22em] text-slate-400">Locked savings</p>
                  <p class="text-xl font-black text-slate-950 mt-1">{summary.locked_savings}</p>
                </div>
                <div class="rounded-2xl bg-[#fff1f1] border border-[#f0c6c6] p-4">
                  <p class="text-[10px] font-black uppercase tracking-[0.22em] text-penalty">Pending HP</p>
                  <p class="text-xl font-black text-slate-950 mt-1">{summary.pending_redemptions}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <main class="max-w-7xl mx-auto px-4 pt-8 md:pt-10">
      <div class="grid gap-8 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]">
        <div class="space-y-8">
          <section class="card bg-white p-6 md:p-8 border border-slate-100 shadow-xl">
            <div class="flex items-center justify-between gap-4 mb-6">
              <div>
                <p class="text-[10px] font-black uppercase tracking-[0.25em] text-slate-400 mb-2">Reward ideas</p>
                <h2 class="text-2xl md:text-3xl font-black text-slate-950">Choose a reward</h2>
              </div>
              <div class="inline-flex items-center gap-2 px-3 py-2 rounded-full bg-slate-100 text-slate-700 text-xs font-black uppercase tracking-[0.22em]">
                <Gift size={14} />
                {rewardOptions.length} available
              </div>
            </div>

            {#if rewardOptions.length > 0}
              <div class="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-4">
                {#each rewardOptions as reward}
                  {@const affordable = reward.points <= summary.available_spending}
                  <div class={`rounded-[1.75rem] border p-4 md:p-5 flex flex-col gap-4 min-w-0 ${affordable ? 'border-slate-200 bg-[#fffefb]' : 'border-slate-200 bg-slate-50 opacity-80'}`}>
                    <div class="flex items-start justify-between gap-3">
                      <div class="min-w-0 flex-1">
                        <h3 class="text-lg font-black text-slate-950 break-words">{reward.title}</h3>
                        <p class="text-sm text-slate-600 mt-1 break-words line-clamp-2">{reward.description || 'A reward your parents can approve.'}</p>
                      </div>
                      <div class={`shrink-0 rounded-2xl px-3 py-2 text-xs font-black uppercase tracking-[0.15em] border whitespace-nowrap leading-none ${affordable ? 'bg-savings/10 text-savings border-savings/20' : 'bg-slate-100 text-slate-400 border-slate-200'}`}>
                        {reward.points} HP
                      </div>
                    </div>

                    <div class="flex flex-col gap-2">
                      <span class="inline-flex w-fit items-center rounded-full px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.16em] leading-none whitespace-nowrap bg-slate-100 text-slate-500">
                        {affordable ? 'Affordable now' : `Need ${rewardShortfall(reward.points)} more`}
                      </span>
                      <button
                        type="button"
                        disabled={!affordable || submittingRewardId === reward.id}
                        onclick={() => requestPresetReward(reward)}
                        class="inline-flex w-full max-w-full justify-center items-center gap-2 rounded-2xl px-3 py-2.5 text-[10px] sm:text-xs font-black uppercase tracking-[0.18em] bg-hero text-white shadow-lg shadow-hero/20 disabled:opacity-50 disabled:shadow-none shrink-0"
                      >
                        {submittingRewardId === reward.id ? 'Sending...' : 'Request'}
                        <ArrowRight size={12} />
                      </button>
                    </div>
                  </div>
                {/each}
              </div>
            {:else}
              <div class="rounded-[1.75rem] border border-dashed border-slate-200 bg-slate-50 p-6 text-center">
                <p class="text-sm font-black uppercase tracking-[0.22em] text-slate-400">No rewards yet</p>
                <p class="text-sm text-slate-500 mt-2">You can still ask for a custom reward below.</p>
              </div>
            {/if}
          </section>

          <section class="card bg-white p-6 md:p-8 border border-slate-100 shadow-xl">
            <div class="flex items-center justify-between gap-4 mb-6">
              <div>
                <p class="text-[10px] font-black uppercase tracking-[0.25em] text-slate-400 mb-2">Custom request</p>
                <h2 class="text-2xl md:text-3xl font-black text-slate-950">Ask for something else</h2>
              </div>
              <div class="w-12 h-12 rounded-2xl bg-reward/10 text-reward flex items-center justify-center">
                <Trophy size={22} />
              </div>
            </div>

            <form class="grid gap-4 md:grid-cols-[minmax(0,1.4fr)_minmax(0,120px)_auto] items-end" onsubmit={submitCustomRequest}>
              <label class="block min-w-0">
                <span class="block text-[10px] font-black uppercase tracking-[0.22em] text-slate-400 mb-2">Reward name</span>
                <input
                  type="text"
                  bind:value={customRewardTitle}
                  placeholder="Movie night, extra screen time, dessert..."
                  class="w-full rounded-2xl border-2 border-slate-200 bg-slate-50 px-4 py-4 text-slate-900 font-bold focus:outline-none focus:border-hero/30"
                />
              </label>

              <label class="block">
                <span class="block text-[10px] font-black uppercase tracking-[0.22em] text-slate-400 mb-2">Points</span>
                <input
                  type="number"
                  min="1"
                  max={Math.max(1, summary.available_spending)}
                  bind:value={customRewardPoints}
                  class="w-full rounded-2xl border-2 border-slate-200 bg-slate-50 px-4 py-4 text-slate-900 font-bold focus:outline-none focus:border-hero/30"
                />
              </label>

              <button
                type="submit"
                disabled={submitting || !customRewardTitle.trim() || customRewardPoints < 1 || customRewardPoints > summary.available_spending}
                class="inline-flex w-full justify-center items-center gap-2 rounded-2xl bg-hero px-5 py-4 text-white font-black uppercase tracking-[0.22em] shadow-lg shadow-hero/20 disabled:opacity-50 md:w-auto"
              >
                {submitting ? 'Sending...' : 'Send'}
                <ArrowRight size={16} />
              </button>
            </form>
          </section>

          <section class="card bg-white p-6 md:p-8 border border-slate-100 shadow-xl">
            <div class="flex items-center justify-between gap-4 mb-6">
              <div>
                <p class="text-[10px] font-black uppercase tracking-[0.25em] text-slate-400 mb-2">Recent activity</p>
                <h2 class="text-2xl md:text-3xl font-black text-slate-950">Points log</h2>
              </div>
              <div class="inline-flex items-center gap-2 px-3 py-2 rounded-full bg-slate-100 text-slate-700 text-xs font-black uppercase tracking-[0.22em]">
                <Clock3 size={14} />
                Latest entries
              </div>
            </div>

            {#if recentActivity.length > 0}
              <div class="space-y-3">
                {#each recentActivity as tx}
                  <div class="rounded-[1.5rem] border p-4 md:p-5 flex flex-col sm:flex-row sm:items-start gap-4 min-w-0 bg-[#fffefb]">
                    <div class={`shrink-0 w-14 h-14 rounded-2xl border flex flex-col items-center justify-center text-xs font-black uppercase tracking-[0.15em] ${getActivityBadgeClass(tx)}`}>
                      <span class="text-base leading-none">{formatPoints(tx.points)}</span>
                      <span>HP</span>
                    </div>
                    <div class="min-w-0 flex-1">
                      <div class="flex flex-wrap items-center gap-2 mb-2">
                        <span class="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.22em] text-slate-500">
                          {getActivityLabel(tx)}
                        </span>
                        <span class="text-[10px] font-black uppercase tracking-[0.2em] text-slate-300">{formatDate(tx.created_at)}</span>
                      </div>
                      <p class="font-black text-slate-950 break-words">{tx.description}</p>
                      <p class="text-xs text-slate-500 mt-1 uppercase tracking-[0.18em]">{tx.jar} jar</p>
                    </div>
                  </div>
                {/each}
              </div>
            {:else}
              <div class="rounded-[1.5rem] border border-dashed border-slate-200 bg-slate-50 p-8 text-center">
                <p class="text-sm font-black uppercase tracking-[0.22em] text-slate-400">No activity yet</p>
                <p class="text-sm text-slate-500 mt-2">Your points log will appear here once chores and rewards start coming in.</p>
              </div>
            {/if}
          </section>
        </div>

        <aside class="space-y-8">
          <section class="card bg-white p-6 md:p-8 border border-slate-100 shadow-xl">
            <div class="flex items-center justify-between gap-4 mb-6">
              <div>
                <p class="text-[10px] font-black uppercase tracking-[0.25em] text-slate-400 mb-2">Pending</p>
                <h2 class="text-2xl font-black text-slate-950">Waiting requests</h2>
              </div>
              <div class="w-12 h-12 rounded-2xl bg-hero/10 text-hero flex items-center justify-center">
                <BadgeCheck size={22} />
              </div>
            </div>

            {#if pendingRequests.length > 0}
              <div class="space-y-3">
                {#each pendingRequests as request}
                  <div class="rounded-[1.5rem] border border-hero/20 bg-hero/5 p-4">
                    <div class="flex items-start justify-between gap-3">
                      <div class="min-w-0">
                        <h3 class="font-black text-slate-950 break-words">{request.title}</h3>
                        <p class="text-sm text-slate-600 mt-1 break-words">{request.description || 'Waiting for approval.'}</p>
                      </div>
                      <span class="shrink-0 rounded-2xl bg-white px-3 py-2 text-xs font-black uppercase tracking-[0.2em] text-hero border border-hero/20">
                        {request.points} HP
                      </span>
                    </div>
                    <p class="text-[10px] font-black uppercase tracking-[0.22em] text-slate-400 mt-3 break-words">
                      Requested {formatDateTime(request.created_at)}
                    </p>
                  </div>
                {/each}
              </div>
            {:else}
              <div class="rounded-[1.5rem] border border-dashed border-slate-200 bg-slate-50 p-6 text-center">
                <p class="text-sm font-black uppercase tracking-[0.22em] text-slate-400">Nothing waiting</p>
                <p class="text-sm text-slate-500 mt-2">Reward requests that need approval will show here.</p>
              </div>
            {/if}
          </section>

          <section class="card bg-gradient-to-br from-[#f3efff] via-[#eef2ff] to-[#f8f8ff] text-slate-900 p-6 md:p-8 shadow-2xl relative overflow-hidden border border-slate-200">
            <div class="absolute inset-0 bg-gradient-to-br from-hero/20 via-transparent to-transparent"></div>
            <div class="relative z-10">
              <div class="flex items-center gap-3 mb-5">
                <div class="w-12 h-12 rounded-2xl bg-white/80 border border-slate-200 flex items-center justify-center text-slate-700">
                  <PiggyBank size={22} />
                </div>
                <div>
                  <p class="text-[10px] font-black uppercase tracking-[0.25em] text-slate-600">Bank</p>
                  <h2 class="text-2xl font-black text-slate-950">Savings snapshot</h2>
                </div>
              </div>
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div class="rounded-2xl bg-white/80 border border-slate-200 p-4">
                  <p class="text-[10px] font-black uppercase tracking-[0.2em] text-slate-600">Total saved</p>
                  <p class="text-3xl font-black mt-1 text-slate-950">{summary.savings_balance}</p>
                </div>
                <div class="rounded-2xl bg-white/80 border border-slate-200 p-4">
                  <p class="text-[10px] font-black uppercase tracking-[0.2em] text-slate-600">Unlocked</p>
                  <p class="text-3xl font-black mt-1 text-slate-950">{summary.available_savings}</p>
                </div>
              </div>
              <p class="text-sm text-slate-700 mt-5 leading-relaxed">
                Keep earning points to unlock more choices for future rewards.
              </p>
            </div>
          </section>
        </aside>
      </div>
    </main>
  {:else}
    <div class="flex justify-center py-32">
      <p class="text-slate-400 font-black uppercase tracking-[0.28em]">Child not found</p>
    </div>
  {/if}
</div>

<style>
  :global(.card) {
    border-radius: 2rem;
    box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.08);
  }

  .text-hero {
    color: #ff5a5f;
  }

  .text-savings {
    color: #00a699;
  }

  .text-reward {
    color: #fc642d;
  }

  .text-penalty {
    color: #d64545;
  }

  .bg-hero {
    background: #ff5a5f;
  }

  .bg-penalty {
    background: #d64545;
  }

  .bg-savings {
    background: #00a699;
  }

  .bg-reward {
    background: #fc642d;
  }

  .shadow-hero\/20 {
    box-shadow: 0 10px 20px -5px rgba(255, 90, 95, 0.2);
  }

  .line-clamp-2 {
    display: -webkit-box;
    line-clamp: 2;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
</style>
