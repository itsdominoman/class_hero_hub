<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { api } from '$lib/api';

  type AssignmentCard = {
    id: number;
    role: string;
    school: { id: number; name: string; name_ar?: string | null };
    class_section?: { name?: string | null; code?: string | null } | null;
    subject_group?: { name?: string | null; code?: string | null } | null;
    branch?: { name?: string | null } | null;
    academic_year?: { name?: string | null } | null;
    grade_level?: { name?: string | null } | null;
    subject?: { name?: string | null } | null;
    valid_from: string;
  };

  let loading = $state(true);
  let allowed = $state(false);
  let error = $state<string | null>(null);
  let assignments = $state<AssignmentCard[]>([]);

  function titleFor(card: AssignmentCard) {
    if (card.role === 'homeroom') return card.class_section?.name || card.class_section?.code || $_('teach.homeroom');
    return card.subject_group?.name || card.subject_group?.code || $_('teach.subject');
  }

  function detailsFor(card: AssignmentCard) {
    return [card.subject?.name, card.grade_level?.name, card.branch?.name, card.academic_year?.name].filter(Boolean).join(' · ');
  }

  onMount(async () => {
    try {
      const me = await api.get('/me/v2');
      allowed = Boolean((me?.memberships || []).some((membership: any) => membership.role === 'teacher'));
      if (!allowed) {
        error = $_('teach.accessDenied');
        return;
      }
      const data = await api.get('/teach/dashboard');
      assignments = data.assignments || [];
    } catch (err: any) {
      if (err?.status === 401) {
        window.location.href = `/login?returnTo=${encodeURIComponent('/teach')}`;
        return;
      }
      error = err?.message || $_('teach.loadError');
    } finally {
      loading = false;
    }
  });
</script>

<svelte:head>
  <title>{$_('teach.title')}</title>
</svelte:head>

{#if loading}
  <section class="mx-auto max-w-5xl px-4 py-12">
    <div class="card p-8 text-center">
      <p class="text-sm font-semibold uppercase tracking-wide text-slate-500">{$_('common.loading')}</p>
    </div>
  </section>
{:else if !allowed}
  <section class="mx-auto max-w-3xl px-4 py-12">
    <div class="card p-8 text-center">
      <h1 class="text-2xl font-black text-slate-900">{$_('teach.accessDeniedTitle')}</h1>
      <p class="mt-3 text-slate-600">{error}</p>
    </div>
  </section>
{:else}
  <section class="mx-auto max-w-5xl px-4 py-8">
    <div class="border-b border-slate-200 pb-5">
      <p class="eyebrow">{$_('teach.eyebrow')}</p>
      <h1 class="mt-2 text-3xl font-black text-slate-900">{$_('teach.heading')}</h1>
    </div>

    {#if error}
      <div class="mt-5 rounded-lg border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">{error}</div>
    {/if}

    {#if assignments.length === 0}
      <div class="mt-6 rounded-lg border border-slate-200 bg-white p-8 text-center">
        <h2 class="text-xl font-black text-slate-900">{$_('teach.emptyTitle')}</h2>
        <p class="mt-2 text-slate-600">{$_('teach.emptyText')}</p>
      </div>
    {:else}
      <div class="mt-6 grid gap-4 md:grid-cols-2">
        {#each assignments as card}
          <article class="rounded-lg border border-slate-200 bg-white p-5">
            <div class="flex items-start justify-between gap-3">
              <div>
                <p class="text-xs font-semibold uppercase tracking-wide text-slate-400">{card.school.name}</p>
                <h2 class="mt-2 text-xl font-black text-slate-900">{titleFor(card)}</h2>
              </div>
              <span class="rounded-lg bg-slate-100 px-3 py-1 text-xs font-bold uppercase text-slate-600">{$_(`teach.roles.${card.role}`)}</span>
            </div>
            {#if detailsFor(card)}
              <p class="mt-3 text-sm font-medium text-slate-600">{detailsFor(card)}</p>
            {/if}
            <p class="mt-4 text-xs font-semibold uppercase tracking-wide text-slate-400">{$_('teach.activeFrom')} {card.valid_from}</p>
          </article>
        {/each}
      </div>
    {/if}
  </section>
{/if}
