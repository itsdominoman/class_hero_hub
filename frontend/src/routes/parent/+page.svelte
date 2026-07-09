<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { api } from '$lib/api';
  import { initialsFromStudentName } from '$lib/guardianDisplay';

  type Identity = {
    id?: number;
    email?: string | null;
    name?: string | null;
  };

  type Child = {
    student_id: number;
    first_name: string;
    last_name: string;
    display_name: string;
    initials: string;
    school_id: number;
    school_name: string | null;
    class_section_name: string | null;
    grade_level_name: string | null;
    relationship: string | null;
    link_status: string;
    email_matched_contact: boolean | null;
  };

  let identity = $state<Identity | null>(null);
  let children = $state<Child[]>([]);
  let loading = $state(true);
  let error = $state<string | null>(null);

  async function loadDashboard() {
    loading = true;
    error = null;
    try {
      identity = await api.get('/me');
      const dashboard = await api.get('/guardian/dashboard');
      children = dashboard?.children || [];
    } catch (err: any) {
      error = err?.message || $_('parent.failedLoad');
      identity = null;
      children = [];
    } finally {
      loading = false;
    }
  }

  function relationshipLabel(relationship: string | null) {
    if (!relationship) return $_('join.relationships.guardian');
    return $_(`join.relationships.${relationship}`);
  }

  onMount(loadDashboard);
</script>

<svelte:head>
  <title>{$_('parent.title')}</title>
</svelte:head>

<div class="mx-auto max-w-3xl px-4 py-12">
  {#if loading}
    <div class="card p-8 text-center">
      <p class="text-sm font-semibold uppercase tracking-wide text-slate-500">{$_('common.loading')}</p>
    </div>
  {:else if error}
    <div class="card p-8 text-center">
      <h1 class="text-3xl font-black text-slate-900">{$_('parent.loginRequired')}</h1>
      <p class="mt-3 text-slate-600">{error}</p>
      <a href="/login" class="btn-hero mt-6 inline-flex rounded-2xl px-6 py-3">{$_('parent.goToLogin')}</a>
    </div>
  {:else}
    <section class="card p-8">
      <p class="text-sm font-bold uppercase tracking-wide text-hero">{$_('parent.eyebrow')}</p>
      <h1 class="mt-3 text-3xl font-black text-slate-900">
        {$_('parent.welcomeHeading', { values: { name: identity?.name || identity?.email || '' } })}
      </h1>

      {#if children.length === 0}
        <p class="mt-4 text-lg leading-relaxed text-slate-600">{$_('parent.emptyStateText')}</p>
      {:else}
        <p class="mt-4 text-lg leading-relaxed text-slate-600">{$_('parent.childrenIntro')}</p>

        <div class="mt-6 grid gap-4 sm:grid-cols-2">
          {#each children as child (child.student_id)}
            <div class="rounded-2xl border border-slate-200 bg-slate-50 p-5">
              <div class="flex items-center gap-3">
                <div class="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-hero/10 text-lg font-black text-hero">
                  {child.initials || initialsFromStudentName(child)}
                </div>
                <div class="min-w-0">
                  <p class="truncate font-bold text-slate-900">{child.display_name}</p>
                  <p class="text-sm text-slate-500">{relationshipLabel(child.relationship)}</p>
                </div>
              </div>
              <div class="mt-4 space-y-1 text-sm text-slate-600">
                {#if child.school_name}
                  <p>{child.school_name}</p>
                {/if}
                {#if child.class_section_name || child.grade_level_name}
                  <p>{[child.grade_level_name, child.class_section_name].filter(Boolean).join(' · ')}</p>
                {/if}
              </div>
            </div>
          {/each}
        </div>
      {/if}

      <div class="mt-8 grid gap-4 sm:grid-cols-2">
        <div class="rounded-2xl border border-dashed border-slate-200 p-5">
          <p class="font-bold text-slate-900">{$_('parent.panels.announcements')}</p>
          <p class="mt-1 text-sm text-slate-500">{$_('parent.panels.comingSoon')}</p>
        </div>
        <div class="rounded-2xl border border-dashed border-slate-200 p-5">
          <p class="font-bold text-slate-900">{$_('parent.panels.classUpdates')}</p>
          <p class="mt-1 text-sm text-slate-500">{$_('parent.panels.comingSoon')}</p>
        </div>
        <div class="rounded-2xl border border-dashed border-slate-200 p-5">
          <p class="font-bold text-slate-900">{$_('parent.panels.homework')}</p>
          <p class="mt-1 text-sm text-slate-500">{$_('parent.panels.comingSoon')}</p>
        </div>
        <div class="rounded-2xl border border-dashed border-slate-200 p-5">
          <p class="font-bold text-slate-900">{$_('parent.panels.points')}</p>
          <p class="mt-1 text-sm text-slate-500">{$_('parent.panels.comingSoon')}</p>
        </div>
      </div>

      {#if children.length === 0}
        <div class="mt-8 rounded-2xl border border-slate-200 bg-slate-50 p-5">
          <p class="text-sm text-slate-600">{$_('parent.emptyStateHelp')}</p>
        </div>
      {/if}

      {#if identity?.email || identity?.name}
        <div class="mt-8 rounded-2xl border border-slate-200 bg-slate-50 p-5">
          <p class="text-xs font-bold uppercase tracking-wide text-slate-400">{$_('parent.signedInAs')}</p>
          <p class="mt-2 font-bold text-slate-900">{identity.name || identity.email}</p>
          {#if identity.name && identity.email}
            <p class="mt-1 text-sm text-slate-500">{identity.email}</p>
          {/if}
        </div>
      {/if}
    </section>
  {/if}
</div>
