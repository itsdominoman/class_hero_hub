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
    avatar_id: number | null;
    avatar_url_128: string | null;
    school_id: number;
    school_name: string | null;
    class_section_name: string | null;
    grade_level_name: string | null;
    relationship: string | null;
    link_status: string;
    email_matched_contact: boolean | null;
  };
  type AnnouncementAttachment = {
    id: number;
    original_filename: string;
    content_type: string;
    size_bytes: number;
  };
  type Announcement = {
    id: number;
    title: string;
    body?: string;
    preview?: string;
    school_name?: string | null;
    author_name?: string | null;
    audience_type: 'school' | 'class_section' | 'subject_group';
    class_section_name?: string | null;
    subject_group_name?: string | null;
    created_at?: string | null;
    attachment_count: number;
    attachments: AnnouncementAttachment[];
    is_read: boolean;
  };
  type PointEvent = { id: number; category_label: string; type: 'positive' | 'needs_work'; points_delta: number; note?: string | null; teacher_name?: string | null; created_at?: string | null };
  type ChildPoints = { student_id: number; display_name: string; total: number; recent_events: PointEvent[] };

  let identity = $state<Identity | null>(null);
  let children = $state<Child[]>([]);
  let announcements = $state<Announcement[]>([]);
  let unreadCount = $state(0);
  let inboxOpen = $state(false);
  let selectedAnnouncement = $state<Announcement | null>(null);
  let announcementLoading = $state(false);
  let loading = $state(true);
  let error = $state<string | null>(null);
  let failedAvatars = $state<Record<number, boolean>>({});
  let childPoints = $state<ChildPoints[]>([]);
  let pointsOpen = $state(false);

  function markAvatarFailed(studentId: number) {
    failedAvatars = { ...failedAvatars, [studentId]: true };
  }

  async function loadDashboard() {
    loading = true;
      error = null;
    try {
      const [me, dashboard, announcementData, pointsData] = await Promise.all([
        api.get('/me'),
        api.get('/guardian/dashboard'),
        api.get('/guardian/announcements'),
        api.get('/guardian/points')
      ]);
      identity = me;
      children = dashboard?.children || [];
      announcements = announcementData?.announcements || [];
      unreadCount = announcementData?.unread_count || 0;
      childPoints = pointsData?.children || [];
    } catch (err: any) {
      error = err?.message || $_('parent.failedLoad');
      identity = null;
      children = [];
      announcements = [];
      unreadCount = 0;
    } finally {
      loading = false;
    }
  }

  function relationshipLabel(relationship: string | null) {
    if (!relationship) return $_('join.relationships.guardian');
    return $_(`join.relationships.${relationship}`);
  }

  function announcementContext(announcement: Announcement) {
    if (announcement.audience_type === 'class_section') return announcement.class_section_name || $_('parent.announcements.classAudience');
    if (announcement.audience_type === 'subject_group') return announcement.subject_group_name || $_('parent.announcements.subjectAudience');
    return announcement.school_name || $_('parent.announcements.schoolAudience');
  }

  function formatDate(value?: string | null) {
    if (!value) return '';
    return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value));
  }

  function attachmentLabel(attachment: AnnouncementAttachment) {
    const sizeKb = Math.max(1, Math.round((attachment.size_bytes || 0) / 1024));
    return `${attachment.original_filename} · ${sizeKb} KB`;
  }

  function openInbox() {
    inboxOpen = true;
    selectedAnnouncement = null;
  }

  function closeInbox() {
    inboxOpen = false;
    selectedAnnouncement = null;
  }

  async function openAnnouncement(announcement: Announcement) {
    selectedAnnouncement = announcement;
    announcementLoading = true;
    try {
      const detail = await api.get(`/guardian/announcements/${announcement.id}`);
      selectedAnnouncement = detail;
      if (!announcement.is_read) {
        announcements = announcements.map((row) => (row.id === announcement.id ? { ...row, is_read: true } : row));
        unreadCount = Math.max(0, unreadCount - 1);
      }
    } catch (err: any) {
      error = err?.message || $_('parent.announcements.loadError');
    } finally {
      announcementLoading = false;
    }
  }

  function backToInbox() {
    selectedAnnouncement = null;
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
                <div class="relative flex h-14 w-14 shrink-0 items-center justify-center overflow-hidden rounded-2xl bg-hero/10 text-lg font-black text-hero">
                  <span>{child.initials || initialsFromStudentName(child)}</span>
                  {#if child.avatar_url_128 && !failedAvatars[child.student_id]}
                    <img
                      src={child.avatar_url_128}
                      alt=""
                      width="128"
                      height="128"
                      loading="lazy"
                      class="absolute inset-0 h-full w-full bg-gradient-to-b from-violet-50 to-sky-50 object-contain"
                      onerror={() => markAvatarFailed(child.student_id)}
                    />
                  {/if}
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
        <button type="button" class="rounded-lg border border-slate-200 p-5 text-left transition hover:bg-slate-50 sm:col-span-2" onclick={openInbox}>
          <div class="flex items-center justify-between gap-3">
            <div class="min-w-0">
              <p class="font-bold text-slate-900">{$_('parent.panels.announcements')}</p>
              <p class="mt-1 text-sm text-slate-500">
                {#if unreadCount > 0}
                  <span class="font-bold text-hero">{$_('parent.announcements.unreadCount', { values: { count: unreadCount } })}</span>
                {:else}
                  {$_('parent.announcements.allCaughtUp')}
                {/if}
              </p>
              {#if announcements[0]}
                <p class="mt-2 truncate text-sm text-slate-600">{announcements[0].title} · {formatDate(announcements[0].created_at)}</p>
              {/if}
            </div>
            <span class="btn-secondary shrink-0 rounded-lg px-4 py-2 text-sm">{$_('parent.announcements.open')}</span>
          </div>
        </button>
        <div class="rounded-2xl border border-dashed border-slate-200 p-5">
          <p class="font-bold text-slate-900">{$_('parent.panels.classUpdates')}</p>
          <p class="mt-1 text-sm text-slate-500">{$_('parent.panels.comingSoon')}</p>
        </div>
        <div class="rounded-2xl border border-dashed border-slate-200 p-5">
          <p class="font-bold text-slate-900">{$_('parent.panels.homework')}</p>
          <p class="mt-1 text-sm text-slate-500">{$_('parent.panels.comingSoon')}</p>
        </div>
        <button type="button" class="rounded-2xl border border-slate-200 p-5 text-left hover:bg-slate-50" onclick={() => pointsOpen = true}>
          <p class="font-bold text-slate-900">{$_('parent.panels.points')}</p>
          {#if childPoints.length}<div class="mt-2 flex flex-wrap gap-2">{#each childPoints as child}<span class="rounded-full bg-violet-50 px-3 py-1 text-sm font-black text-violet-700">{child.display_name}: {child.total}</span>{/each}</div>{:else}<p class="mt-1 text-sm text-slate-500">{$_('parent.points.empty')}</p>{/if}
        </button>
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

{#if inboxOpen}
  <div class="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/50 p-0 sm:items-center sm:p-4" role="dialog" aria-modal="true" aria-labelledby="announcement-title">
    <div class="max-h-[92vh] w-full max-w-2xl overflow-y-auto rounded-t-lg bg-white p-5 shadow-xl sm:rounded-lg sm:p-6">
      {#if !selectedAnnouncement}
        <div class="flex items-start justify-between gap-4">
          <h2 id="announcement-title" class="text-2xl font-black text-slate-900">{$_('parent.announcements.inboxTitle')}</h2>
          <button type="button" class="rounded-lg border border-slate-200 px-3 py-2 text-sm font-bold text-slate-600" onclick={closeInbox}>{$_('parent.announcements.close')}</button>
        </div>

        {#if announcements.length === 0}
          <p class="mt-6 text-sm text-slate-500">{$_('parent.announcements.empty')}</p>
        {:else}
          <div class="mt-5 max-h-[70vh] divide-y divide-slate-100 overflow-y-auto rounded-lg border border-slate-100">
            {#each announcements as announcement}
              <button
                type="button"
                class={`block w-full p-4 text-left hover:bg-slate-50 ${announcement.is_read ? 'opacity-60' : 'bg-hero/5'}`}
                onclick={() => openAnnouncement(announcement)}
              >
                <div class="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                  <div class="min-w-0">
                    <div class="flex items-center gap-2">
                      {#if !announcement.is_read}
                        <span class="h-2 w-2 shrink-0 rounded-full bg-hero"></span>
                      {/if}
                      <p class="truncate font-bold text-slate-900">{announcement.title}</p>
                    </div>
                    <p class="mt-1 text-sm text-slate-500">{announcementContext(announcement)} · {formatDate(announcement.created_at)}</p>
                    <p class="mt-2 line-clamp-2 text-sm text-slate-600">{announcement.preview}</p>
                  </div>
                  {#if announcement.attachment_count > 0}
                    <span class="shrink-0 rounded-full bg-hero/10 px-3 py-1 text-xs font-bold text-hero">
                      {$_('parent.announcements.attachments', { values: { count: announcement.attachment_count } })}
                    </span>
                  {/if}
                </div>
              </button>
            {/each}
          </div>
        {/if}
      {:else}
        <div class="flex items-start justify-between gap-4">
          <div class="min-w-0">
            <button type="button" class="text-sm font-bold text-hero" onclick={backToInbox}>{$_('parent.announcements.back')}</button>
            <p class="mt-2 text-xs font-bold uppercase tracking-wide text-slate-500">{announcementContext(selectedAnnouncement)}</p>
            <h2 class="mt-2 text-2xl font-black text-slate-900">{selectedAnnouncement.title}</h2>
            <p class="mt-2 text-sm text-slate-500">
              {formatDate(selectedAnnouncement.created_at)}
              {#if selectedAnnouncement.author_name}
                · {selectedAnnouncement.author_name}
              {/if}
            </p>
          </div>
          <button type="button" class="rounded-lg border border-slate-200 px-3 py-2 text-sm font-bold text-slate-600" onclick={closeInbox}>{$_('parent.announcements.close')}</button>
        </div>

        {#if announcementLoading && !selectedAnnouncement.body}
          <p class="mt-6 text-sm font-semibold text-slate-500">{$_('common.loading')}</p>
        {:else}
          <div class="mt-6 whitespace-pre-wrap text-base leading-relaxed text-slate-700">{selectedAnnouncement.body || selectedAnnouncement.preview}</div>
          {#if selectedAnnouncement.attachments?.length}
            <div class="mt-6">
              <h3 class="text-sm font-black uppercase tracking-wide text-slate-500">{$_('parent.announcements.attachmentList')}</h3>
              <div class="mt-3 divide-y divide-slate-100 rounded-lg border border-slate-100">
                {#each selectedAnnouncement.attachments as attachment}
                  <div class="flex flex-col gap-2 p-3 sm:flex-row sm:items-center sm:justify-between">
                    <p class="break-all text-sm font-semibold text-slate-800">{attachmentLabel(attachment)}</p>
                    <a
                      class="btn-secondary rounded-lg px-3 py-2 text-center text-sm"
                      href={`/api/guardian/announcements/${selectedAnnouncement.id}/attachments/${attachment.id}/download`}
                    >
                      {$_('parent.announcements.download')}
                    </a>
                  </div>
                {/each}
              </div>
            </div>
          {/if}
        {/if}
      {/if}
    </div>
  </div>
{/if}

{#if pointsOpen}
  <div class="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/50 sm:items-center sm:p-4" role="dialog" aria-modal="true" aria-labelledby="points-title">
    <div class="max-h-[92vh] w-full max-w-2xl overflow-y-auto rounded-t-2xl bg-white p-5 shadow-xl sm:rounded-2xl sm:p-6"><div class="flex items-start justify-between gap-3"><h2 id="points-title" class="text-2xl font-black text-slate-900">{$_('parent.panels.points')}</h2><button type="button" class="btn-secondary rounded-lg px-3 py-2" onclick={() => pointsOpen = false}>{$_('parent.points.close')}</button></div>
      {#if childPoints.length === 0}<p class="mt-6 text-slate-500">{$_('parent.points.empty')}</p>{/if}
      {#each childPoints as child}<section class="mt-5"><div class="flex items-center justify-between"><h3 class="font-black text-slate-900">{child.display_name}</h3><span class="rounded-full bg-violet-100 px-3 py-1 font-black text-violet-700">{$_('parent.points.total')}: {child.total}</span></div>{#if child.recent_events.length === 0}<p class="mt-3 text-sm text-slate-500">{$_('parent.points.noHistory')}</p>{:else}<div class="mt-3 divide-y divide-slate-100 rounded-xl border border-slate-200">{#each child.recent_events as event}<article class="p-3"><div class="flex items-start justify-between gap-3"><div><p class={`font-bold ${event.type === 'positive' ? 'text-emerald-700' : 'text-amber-700'}`}>{event.category_label}</p><p class="mt-1 text-xs text-slate-500">{formatDate(event.created_at)}{event.teacher_name ? ` · ${event.teacher_name}` : ''}</p></div><span class={`font-black ${event.points_delta > 0 ? 'text-emerald-600' : 'text-amber-600'}`}>{event.points_delta > 0 ? '+' : ''}{event.points_delta}</span></div>{#if event.note}<p class="mt-2 whitespace-pre-wrap text-sm text-slate-600">{event.note}</p>{/if}</article>{/each}</div>{/if}</section>{/each}
    </div>
  </div>
{/if}
