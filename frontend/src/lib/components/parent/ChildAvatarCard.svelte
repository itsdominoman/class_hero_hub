<script lang="ts">
  import { ArrowRight, Clock3, Coins, PiggyBank, Star } from "lucide-svelte";
  import { getAvatarAsset } from "$lib/avatars";

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
  };

  let {
    childSummary,
    href = "",
    allowanceEnabled = false,
    ...rest
  } = $props<{
    childSummary: ChildSummary;
    href?: string;
    allowanceEnabled?: boolean;
  }>();

  const avatar = $derived(getAvatarAsset(childSummary.child.avatar_name));
  const currentPoints = $derived(Math.max(0, Number(childSummary.spending_balance) || 0));
  const availablePoints = $derived(Math.max(0, Number(childSummary.available_spending) || currentPoints));
  const savedPoints = $derived(Math.max(0, Number(childSummary.savings_balance) || 0));
  const lockedSavings = $derived(Math.max(0, Number(childSummary.locked_savings) || 0));
  const pendingRedemptions = $derived(Math.max(0, Number(childSummary.pending_redemptions) || 0));
</script>

<a
  href={href}
  {...rest}
  class="group flex h-full min-w-0 flex-col overflow-hidden rounded-[2rem] border border-slate-200 bg-white p-5 shadow-[0_18px_50px_-28px_rgba(15,23,42,0.35)] transition duration-200 hover:-translate-y-0.5 hover:shadow-[0_24px_60px_-28px_rgba(124,58,237,0.32)]"
  aria-label={`Open ${childSummary.child.display_name} dashboard`}
>
  <div class="flex min-w-0 items-start gap-4">
    <div class="relative shrink-0">
      <div class="flex h-16 w-16 items-center justify-center rounded-[1.4rem] bg-gradient-to-br from-hero/15 via-white to-slate-50 p-1 shadow-inner ring-1 ring-white/80 sm:h-18 sm:w-18">
        <img
          src={avatar.path}
          alt={`Avatar for ${avatar.label}`}
          class="h-full w-full rounded-[1.1rem] object-cover"
          loading="lazy"
        />
      </div>
      <div class="absolute -bottom-1 -right-1 rounded-full bg-white p-1 shadow-md">
        <div class="flex h-7 w-7 items-center justify-center rounded-full bg-hero text-white">
          <Star size={13} fill="currentColor" />
        </div>
      </div>
    </div>

    <div class="min-w-0 flex-1">
      <div class="flex min-w-0 items-start justify-between gap-3">
        <h3 class="truncate text-xl font-black tracking-tight text-slate-950">
          {childSummary.child.display_name}
        </h3>
        <span class="rounded-full bg-slate-100 px-3 py-1.5 text-[10px] font-black uppercase tracking-[0.18em] text-slate-500">
          {avatar.label}
        </span>
      </div>

      <div class="mt-4 grid grid-cols-2 gap-3">
        <div class="rounded-2xl bg-slate-50 px-3 py-3">
          <p class="text-[10px] font-black uppercase tracking-[0.18em] text-slate-400">
            Current points
          </p>
          <p class="mt-2 text-2xl font-black tracking-tight text-slate-950">
            {currentPoints}
          </p>
        </div>
        <div class="rounded-2xl bg-hero/5 px-3 py-3">
          <p class="text-[10px] font-black uppercase tracking-[0.18em] text-hero">
            Available now
          </p>
          <p class="mt-2 text-2xl font-black tracking-tight text-slate-950">
            {availablePoints}
          </p>
        </div>
      </div>

      {#if savedPoints > 0}
        <p class="mt-3 text-sm font-medium text-slate-500">
          Saved balance: <span class="font-black text-slate-900">{savedPoints}</span>
        </p>
      {:else}
        <p class="mt-3 text-sm font-medium text-slate-500">
          Saved balance: <span class="font-black text-slate-900">0</span>
        </p>
      {/if}

      <div class="mt-4 flex flex-wrap gap-2">
        {#if pendingRedemptions > 0}
          <span class="inline-flex items-center gap-2 rounded-full bg-amber-100 px-3 py-2 text-[10px] font-black uppercase tracking-[0.16em] text-amber-700">
            <Clock3 size={13} />
            {pendingRedemptions} pending
          </span>
        {/if}

        {#if lockedSavings > 0}
          <span class="inline-flex items-center gap-2 rounded-full bg-savings/10 px-3 py-2 text-[10px] font-black uppercase tracking-[0.16em] text-savings">
            <PiggyBank size={13} />
            Locked savings
          </span>
        {/if}

        {#if allowanceEnabled}
          <span class="inline-flex items-center gap-2 rounded-full bg-amber-100 px-3 py-2 text-[10px] font-black uppercase tracking-[0.16em] text-amber-700">
            <Coins size={13} />
            Allowance on
          </span>
        {/if}

        {#if pendingRedemptions === 0 && lockedSavings === 0 && !allowanceEnabled}
          <span class="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-2 text-[10px] font-black uppercase tracking-[0.16em] text-slate-500">
            <Star size={13} />
            Ready
          </span>
        {/if}
      </div>
    </div>
  </div>

  <div class="mt-auto flex items-center justify-between gap-3 pt-5">
    <p class="text-[10px] font-black uppercase tracking-[0.22em] text-slate-400">
      Open child dashboard
    </p>
    <div class="flex h-11 w-11 items-center justify-center rounded-full bg-slate-900 text-white transition group-hover:translate-x-0.5">
      <ArrowRight size={16} />
    </div>
  </div>
</a>
