<script lang="ts">
  import { _ } from 'svelte-i18n';
  import { CheckCircle2, ChevronLeft, LockKeyhole } from 'lucide-svelte';
  import { accessSummaryKey } from '$lib/safeguarding/presentation';
  import type { SafeguardingContext, SafeguardingMembership } from '$lib/safeguarding/types';

  let {
    title,
    subtitle,
    context,
    memberships = [],
    membership = null,
    backHref = '',
    onMembershipChange
  } = $props<{
    title: string;
    subtitle: string;
    context: SafeguardingContext | null;
    memberships?: SafeguardingMembership[];
    membership?: SafeguardingMembership | null;
    backHref?: string;
    onMembershipChange?: (event: Event) => void;
  }>();
</script>

<header class="min-w-0 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
  <div class="flex min-w-0 flex-wrap items-start justify-between gap-3">
    <div class="min-w-0 flex-1">
      {#if backHref}
        <a class="mb-2 inline-flex min-h-10 items-center gap-1 rounded-lg text-sm font-bold text-amber-800 hover:text-amber-950" href={backHref} data-testid="safeguarding-back">
          <ChevronLeft class="h-4 w-4 rtl:rotate-180" aria-hidden="true" />
          {$_('safeguarding.back')}
        </a>
      {/if}
      <h1 class="break-words text-2xl font-black tracking-tight text-slate-950 sm:text-3xl">{title}</h1>
      <p class="mt-1 max-w-3xl text-sm leading-5 text-slate-600">{subtitle}</p>
    </div>

    {#if memberships.length > 1 && membership && onMembershipChange}
      <label class="min-w-0 text-xs font-bold text-slate-700">
        <span class="mb-1 block">{$_('safeguarding.school')}</span>
        <select class="field min-w-0" value={membership.membership_id} onchange={onMembershipChange}>
          {#each memberships as row}<option value={row.membership_id}>{row.school_name}</option>{/each}
        </select>
      </label>
    {/if}
  </div>

  {#if context}
    <div class="mt-4 flex min-w-0 flex-wrap items-center gap-x-4 gap-y-2 border-t border-slate-100 pt-3 text-xs text-slate-600" data-testid="safeguarding-context-banner">
      <span class="inline-flex min-w-0 items-center gap-1.5 font-bold text-slate-800">
        <LockKeyhole class="h-4 w-4 shrink-0 text-amber-700" aria-hidden="true" />
        <span class="break-words">{context.school.name}</span>
      </span>
      <span class="inline-flex items-center gap-1.5">
        <CheckCircle2 class="h-4 w-4 shrink-0 text-emerald-600" aria-hidden="true" />
        {$_('safeguarding.auditedAccess')}
      </span>
      <span class="rounded-full bg-amber-50 px-2.5 py-1 font-bold text-amber-900">{$_(accessSummaryKey(context.permissions))}</span>
    </div>
  {/if}
</header>

<style>
  .field {
    width: 100%;
    max-width: 100%;
    border: 1px solid rgb(203 213 225);
    border-radius: 0.75rem;
    background: white;
    padding: 0.65rem 0.8rem;
    color: rgb(15 23 42);
  }
</style>
