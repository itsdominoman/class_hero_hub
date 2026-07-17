<script lang="ts">
  import { _, locale } from 'svelte-i18n';
  import { studentAcademicLabel } from '$lib/messaging/presentation';
  import type { MessagingMembership, RecipientResults } from '$lib/messaging/types';

  let {
    membership,
    recipients,
    loading = false,
    creating = false,
    onclose,
    onsearch,
    onstudent,
    onstaff
  }: {
    membership: MessagingMembership;
    recipients: RecipientResults;
    loading?: boolean;
    creating?: boolean;
    onclose: () => void;
    onsearch: (query: string) => void;
    onstudent: (studentId: number) => void;
    onstaff: (membershipId: number) => void;
  } = $props();

  let query = $state('');
  let searchTimer: ReturnType<typeof setTimeout> | null = null;
  let searchInput: HTMLInputElement;
  const arabic = $derived($locale === 'ar');

  function relationshipLabel(value: string | null | undefined) {
    return value && ['mother', 'father', 'guardian', 'other'].includes(value)
      ? $_(`messaging.relationships.${value}`)
      : '';
  }

  $effect(() => {
    searchInput?.focus();
    return () => {
      if (searchTimer) clearTimeout(searchTimer);
    };
  });

  function updateSearch() {
    if (searchTimer) clearTimeout(searchTimer);
    searchTimer = setTimeout(() => onsearch(query), 250);
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape') onclose();
  }
</script>

<div class="fixed inset-0 z-[120] grid place-items-end bg-slate-950/50 p-0 sm:place-items-center sm:p-4" role="presentation" onkeydown={handleKeydown}>
  <button type="button" class="absolute inset-0 h-full w-full" aria-label={$_('messaging.closeCompose')} onclick={onclose}></button>
  <div class="relative flex max-h-[88dvh] w-full max-w-2xl flex-col rounded-t-3xl bg-white shadow-2xl sm:rounded-3xl" role="dialog" aria-modal="true" aria-labelledby="compose-title">
    <header class="flex items-center justify-between border-b border-slate-200 px-5 py-4">
      <div>
        <h2 id="compose-title" class="text-lg font-extrabold text-slate-900">{$_('messaging.newConversation')}</h2>
        <p dir="auto" class="mt-0.5 text-xs font-semibold text-slate-500">{membership.school_name}</p>
      </div>
      <button type="button" class="grid h-10 w-10 place-items-center rounded-xl text-xl text-slate-500 hover:bg-slate-100" aria-label={$_('messaging.closeCompose')} onclick={onclose}>×</button>
    </header>
    <div class="border-b border-slate-100 p-4">
      <label for="recipient-search" class="sr-only">{$_('messaging.searchRecipients')}</label>
      <input
        bind:this={searchInput}
        bind:value={query}
        oninput={updateSearch}
        id="recipient-search"
        type="search"
        placeholder={$_('messaging.searchRecipients')}
        class="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none focus:border-hero focus:ring-2 focus:ring-hero/15"
      />
    </div>
    <div class="min-h-0 flex-1 overflow-y-auto p-4">
      {#if loading}
        <p class="py-12 text-center text-sm font-semibold text-slate-500">{$_('messaging.loadingRecipients')}</p>
      {:else}
        <div>
          <h3 class="px-2 text-xs font-extrabold uppercase tracking-wide text-slate-400">{$_('messaging.studentsAndGuardians')}</h3>
          {#if recipients.students.length === 0}
            <p class="px-2 py-5 text-sm text-slate-500">{$_('messaging.noRecipientMatches')}</p>
          {:else}
            <ul class="mt-2 space-y-1">
              {#each recipients.students as student (student.student_id)}
                <li>
                  <button type="button" disabled={creating} onclick={() => onstudent(student.student_id)} class="w-full rounded-2xl px-3 py-3 text-start hover:bg-emerald-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-hero disabled:opacity-50">
                    <span dir="auto" class="block text-sm font-bold text-slate-900">{student.display_name}{studentAcademicLabel(student, arabic) ? ` · ${studentAcademicLabel(student, arabic)}` : ''}</span>
                    <span dir="auto" class="mt-0.5 block text-xs text-slate-500">
                      {student.guardian_details?.length
                        ? student.guardian_details.map((guardian) => [guardian.display_name, relationshipLabel(guardian.relationship)].filter(Boolean).join(' · ')).join(', ')
                        : student.guardian_names.length ? student.guardian_names.join(', ') : $_('messaging.guardianAvailable')}
                    </span>
                  </button>
                </li>
              {/each}
            </ul>
          {/if}
        </div>

        {#if membership.role === 'school_admin'}
          <div class="mt-6 border-t border-slate-100 pt-5">
            <h3 class="px-2 text-xs font-extrabold uppercase tracking-wide text-slate-400">{$_('messaging.staff')}</h3>
            {#if recipients.staff.length === 0}
              <p class="px-2 py-5 text-sm text-slate-500">{$_('messaging.noStaffMatches')}</p>
            {:else}
              <ul class="mt-2 space-y-1">
                {#each recipients.staff as staff (staff.membership_id)}
                  <li>
                    <button type="button" disabled={creating} onclick={() => onstaff(staff.membership_id)} class="w-full rounded-2xl px-3 py-3 text-start hover:bg-emerald-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-hero disabled:opacity-50">
                      <span dir="auto" class="block text-sm font-bold text-slate-900">{staff.display_name}</span>
                      <span class="mt-0.5 block text-xs text-slate-500">{staff.role === 'school_admin' ? $_('messaging.schoolAdministrator') : $_('messaging.teacher')}</span>
                    </button>
                  </li>
                {/each}
              </ul>
            {/if}
          </div>
        {/if}
      {/if}
    </div>
  </div>
</div>
