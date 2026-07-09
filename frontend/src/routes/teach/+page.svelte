<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { api } from '$lib/api';
  import { rosterPathForAssignment } from '$lib/teachRoster.js';

  type AssignmentCard = {
    id: number;
    role: string;
    target_type?: 'class_section' | 'subject_group';
    school: { id: number; name: string; name_ar?: string | null };
    class_section?: { id: number; name?: string | null; code?: string | null } | null;
    subject_group?: { id: number; name?: string | null; code?: string | null } | null;
    branch?: { name?: string | null } | null;
    academic_year?: { name?: string | null } | null;
    grade_level?: { name?: string | null } | null;
    subject?: { name?: string | null } | null;
    valid_from: string;
  };
  type RosterStudent = {
    id: number;
    display_name: string;
    first_name: string;
    last_name: string;
    preferred_name?: string | null;
    name_ar?: string | null;
  };
  type Roster = { students: RosterStudent[] };

  let loading = $state(true);
  let allowed = $state(false);
  let error = $state<string | null>(null);
  let assignments = $state<AssignmentCard[]>([]);
  let openRosterId = $state<number | null>(null);
  let rosterLoading = $state(false);
  let rosters = $state<Record<number, Roster>>({});

  function titleFor(card: AssignmentCard) {
    if (card.role === 'homeroom') return card.class_section?.name || card.class_section?.code || $_('teach.homeroom');
    return card.subject_group?.name || card.subject_group?.code || $_('teach.subject');
  }

  function detailsFor(card: AssignmentCard) {
    return [card.subject?.name, card.grade_level?.name, card.branch?.name, card.academic_year?.name].filter(Boolean).join(' · ');
  }

  async function toggleRoster(card: AssignmentCard) {
    if (openRosterId === card.id) {
      openRosterId = null;
      return;
    }
    openRosterId = card.id;
    if (rosters[card.id]) return;
    rosterLoading = true;
    error = null;
    try {
      const path = rosterPathForAssignment(card);
      if (!path) throw new Error($_('teach.rosterLoadError'));
      rosters = { ...rosters, [card.id]: await api.get(path) };
    } catch (err: any) {
      error = err?.message || $_('teach.rosterLoadError');
    } finally {
      rosterLoading = false;
    }
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
      <button type="button" class="btn-secondary mt-4 rounded-lg px-3 py-2 text-sm" onclick={() => toggleRoster(card)}>
              {openRosterId === card.id ? $_('teach.hideRoster') : $_('teach.viewRoster')}
            </button>
            {#if openRosterId === card.id}
              <div class="mt-4 rounded-lg border border-slate-100 bg-slate-50 p-3">
                {#if rosterLoading && !rosters[card.id]}
                  <p class="text-sm text-slate-500">{$_('common.loading')}</p>
                {:else if !rosters[card.id] || rosters[card.id].students.length === 0}
                  <p class="text-sm text-slate-500">{card.subject_group ? $_('teach.emptySubjectRoster') : $_('teach.emptyRoster')}</p>
                {:else}
                  <div class="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
                    {#each rosters[card.id].students as student}
                      <div class="p-3">
                        <p class="font-semibold text-slate-900">{student.display_name}</p>
                        {#if student.name_ar}
                          <p class="mt-1 text-sm text-slate-500">{student.name_ar}</p>
                        {/if}
                      </div>
                    {/each}
                  </div>
                {/if}
              </div>
            {/if}
          </article>
        {/each}
      </div>
    {/if}
  </section>
{/if}
