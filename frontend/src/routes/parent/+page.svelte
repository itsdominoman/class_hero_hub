<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
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
    points_total: number;
    recent_point_events: PointEvent[];
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
  type PointEvent = { id: number; category_label: string; type: 'positive' | 'needs_work'; points_delta: number; note?: string | null; teacher_name?: string | null; created_at?: string | null; class_section_name?: string | null; subject_name?: string | null; subject_code?: string | null; duty_context?: 'break' | 'lunch' | 'playground' | 'hallway' | 'assembly' | 'bus' | 'general_duty' | null; context_type?: 'class' | 'subject' | 'duty' | 'general' };
  type HomeworkItem = { id: number; item_type: 'homework' | 'diary'; title: string; body?: string; preview?: string; audience_type: 'class_section' | 'subject_group'; class_section_name?: string | null; subject_group_name?: string | null; due_at?: string | null; created_at?: string | null; attachment_count: number; attachments: AnnouncementAttachment[]; resource_links: { url: string; label?: string | null }[] };

  function pointContext(event: PointEvent) {
    const parts: string[] = [];
    if (event.subject_name) {
      parts.push(event.subject_name);
      if (event.subject_code && !event.subject_name.toLocaleLowerCase().includes(event.subject_code.toLocaleLowerCase())) parts.push(event.subject_code);
      if (event.class_section_name) parts.push(event.class_section_name);
    } else if (event.duty_context) {
      parts.push($_(`parent.points.duty.${event.duty_context}`));
    } else if (event.class_section_name) {
      parts.push(event.class_section_name);
    }
    return parts;
  }

  type CalendarItem = {
    id: string;
    kind: 'event' | 'homework_due';
    event_id?: number;
    homework_item_id?: number;
    title: string;
    body?: string | null;
    event_type: string;
    audience_type: 'school' | 'class_section' | 'subject_group';
    class_section_name?: string | null;
    subject_group_name?: string | null;
    starts_at: string;
    ends_at?: string | null;
    all_day: boolean;
  };

  type UpdatePhoto = { id: number; original_filename: string };
  type UpdatePost = {
    id: number;
    body?: string;
    preview?: string;
    author_name?: string | null;
    audience_type: 'class_section' | 'subject_group';
    class_section_name?: string | null;
    subject_group_name?: string | null;
    created_at?: string | null;
    photo_count: number;
    photos: UpdatePhoto[];
  };

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
  let pointsChild = $state<Child | null>(null);
  let homeworkItems = $state<HomeworkItem[]>([]);
  let completedHomework = $state<HomeworkItem[]>([]);
  let completedLoaded = $state(false);
  let homeworkTab = $state<'active' | 'completed'>('active');
  let homeworkOpen = $state(false);
  let selectedHomework = $state<HomeworkItem | null>(null);
  let selectedDone = $state(false);
  let homeworkLoading = $state(false);
  let homeworkDoneSaving = $state(false);
  let updates = $state<UpdatePost[]>([]);
  let calendarItems = $state<CalendarItem[]>([]);
  let calendarOpen = $state(false);
  let updatesOpen = $state(false);
  let selectedUpdate = $state<UpdatePost | null>(null);
  let updateLoading = $state(false);
  let lightboxPhoto = $state<{ url: string; alt: string } | null>(null);
  let updatePhotoLoadStates = $state<Record<string, 'loaded' | 'failed'>>({});
  let lightboxPhotoState = $state<'loading' | 'loaded' | 'failed'>('loading');
  let dashboardRequestInFlight = false;
  let dashboardRefreshQueued = false;
  let dashboardPollTimer: ReturnType<typeof setTimeout> | null = null;

  function markAvatarFailed(studentId: number) {
    failedAvatars = { ...failedAvatars, [studentId]: true };
  }

  async function loadDashboard(showLoading = true) {
    if (dashboardRequestInFlight) {
      if (!showLoading && document.visibilityState === 'visible') dashboardRefreshQueued = true;
      return;
    }
    dashboardRequestInFlight = true;
    if (showLoading) {
      loading = true;
      error = null;
    }
    try {
      const [me, dashboard, announcementData, homeworkData, updateData, calendarData] = await Promise.all([
        api.get('/me'),
        api.get('/guardian/dashboard'),
        api.get('/guardian/announcements'),
        api.get('/guardian/homework'),
        api.get('/guardian/updates'),
        api.get('/guardian/calendar')
      ]);
      identity = me;
      children = dashboard?.children || [];
      announcements = announcementData?.announcements || [];
      unreadCount = announcementData?.unread_count || 0;
      homeworkItems = homeworkData?.items || [];
      updates = updateData?.items || [];
      calendarItems = calendarData?.items || [];
    } catch (err: any) {
      if (showLoading) {
        error = err?.message || $_('parent.failedLoad');
        identity = null;
        children = [];
        announcements = [];
        unreadCount = 0;
        homeworkItems = [];
        updates = [];
        calendarItems = [];
      }
    } finally {
      if (showLoading) loading = false;
      dashboardRequestInFlight = false;
      if (dashboardRefreshQueued && document.visibilityState === 'visible') {
        dashboardRefreshQueued = false;
        void loadDashboard(false);
      }
    }
  }

  function clearDashboardPolling() {
    if (!dashboardPollTimer) return;
    clearTimeout(dashboardPollTimer);
    dashboardPollTimer = null;
  }

  function scheduleDashboardPolling() {
    clearDashboardPolling();
    if (document.visibilityState !== 'visible') return;
    dashboardPollTimer = setTimeout(async () => {
      await loadDashboard(false);
      scheduleDashboardPolling();
    }, 60_000);
  }

  function handleVisibilityChange() {
    if (document.visibilityState === 'visible') {
      void loadDashboard(false);
      scheduleDashboardPolling();
      return;
    }
    dashboardRefreshQueued = false;
    clearDashboardPolling();
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

  function formatDateTime(value?: string | null) {
    if (!value) return '';
    return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
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

  function updateContext(post: UpdatePost) {
    return post.audience_type === 'subject_group'
      ? post.subject_group_name || $_('parent.updates.subjectAudience')
      : post.class_section_name || $_('parent.updates.classAudience');
  }
  function updatePhotoUrl(post: UpdatePost, photo: UpdatePhoto) {
    return `/api/guardian/updates/${post.id}/photos/${photo.id}/view`;
  }
  function updatePhotoThumbnailUrl(post: UpdatePost, photo: UpdatePhoto) {
    return `/api/guardian/updates/${post.id}/photos/${photo.id}/thumbnail`;
  }
  function updatePhotoKey(post: UpdatePost, photo: UpdatePhoto) { return `${post.id}:${photo.id}`; }
  function updatePhotoLoaded(post: UpdatePost, photo: UpdatePhoto) {
    updatePhotoLoadStates = { ...updatePhotoLoadStates, [updatePhotoKey(post, photo)]: 'loaded' };
  }
  function updatePhotoFailed(post: UpdatePost, photo: UpdatePhoto) {
    updatePhotoLoadStates = { ...updatePhotoLoadStates, [updatePhotoKey(post, photo)]: 'failed' };
  }
  function openUpdates() { updatesOpen = true; selectedUpdate = null; }
  function closeUpdates() { updatesOpen = false; selectedUpdate = null; }
  async function openUpdatePost(post: UpdatePost) {
    selectedUpdate = post; updateLoading = true;
    try { selectedUpdate = await api.get(`/guardian/updates/${post.id}`); }
    catch (err: any) { error = err?.message || $_('parent.updates.loadError'); }
    finally { updateLoading = false; }
  }
  function openLightbox(post: UpdatePost, photo: UpdatePhoto) {
    lightboxPhoto = { url: updatePhotoUrl(post, photo), alt: photo.original_filename };
    lightboxPhotoState = 'loading';
  }

  function calendarContext(item: CalendarItem) {
    if (item.audience_type === 'subject_group') return item.subject_group_name || $_('parent.homework.subjectAudience');
    if (item.audience_type === 'class_section') return item.class_section_name || $_('parent.homework.classAudience');
    return $_('calendar.schoolWide');
  }
  function formatEventDate(item: CalendarItem) {
    const options: Intl.DateTimeFormatOptions = item.all_day ? { dateStyle: 'medium' } : { dateStyle: 'medium', timeStyle: 'short' };
    let label = new Intl.DateTimeFormat(undefined, options).format(new Date(item.starts_at));
    if (item.ends_at && !item.all_day) label += ` – ${new Intl.DateTimeFormat(undefined, { timeStyle: 'short' }).format(new Date(item.ends_at))}`;
    return label;
  }
  function compactCalendarItems() {
    const sevenDaysFromNow = Date.now() + 7 * 24 * 60 * 60 * 1000;
    const inNextWeek = calendarItems.filter((item) => new Date(item.starts_at).getTime() <= sevenDaysFromNow);
    return (inNextWeek.length ? inNextWeek : calendarItems).slice(0, 3);
  }
  function openCalendar() { calendarOpen = true; }
  function closeCalendar() { calendarOpen = false; }
  async function openCalendarHomework(item: CalendarItem) {
    if (!item.homework_item_id) return;
    calendarOpen = false;
    homeworkOpen = true;
    homeworkTab = 'active';
    selectedDone = false;
    homeworkLoading = true;
    try { selectedHomework = await api.get(`/guardian/homework/${item.homework_item_id}`); }
    catch (err: any) { error = err?.message || $_('parent.homework.loadError'); homeworkOpen = false; }
    finally { homeworkLoading = false; }
  }

  function homeworkContext(item: HomeworkItem) { return item.audience_type === 'subject_group' ? item.subject_group_name || $_('parent.homework.subjectAudience') : item.class_section_name || $_('parent.homework.classAudience'); }
  function openHomeworkList() { homeworkOpen = true; selectedHomework = null; homeworkTab = 'active'; }
  function closeHomeworkList() { homeworkOpen = false; selectedHomework = null; }
  async function loadCompletedHomework() {
    try { completedHomework = (await api.get('/guardian/homework?status=completed'))?.items || []; completedLoaded = true; }
    catch (err: any) { error = err?.message || $_('parent.homework.loadError'); }
  }
  async function switchHomeworkTab(tab: 'active' | 'completed') {
    homeworkTab = tab; selectedHomework = null;
    if (tab === 'completed' && !completedLoaded) await loadCompletedHomework();
  }
  async function openHomeworkItem(item: HomeworkItem, done: boolean) {
    selectedHomework = item; selectedDone = done; homeworkLoading = true;
    try { selectedHomework = await api.get(`/guardian/homework/${item.id}`); }
    catch (err: any) { error = err?.message || $_('parent.homework.loadError'); }
    finally { homeworkLoading = false; }
  }
  async function markHomeworkDone() {
    if (!selectedHomework || homeworkDoneSaving) return;
    homeworkDoneSaving = true;
    try {
      await api.post(`/guardian/homework/${selectedHomework.id}/done`);
      homeworkItems = homeworkItems.filter((item) => item.id !== selectedHomework?.id);
      completedLoaded = false; selectedHomework = null;
    } catch (err: any) { error = err?.message || $_('parent.homework.doneError'); }
    finally { homeworkDoneSaving = false; }
  }
  async function markHomeworkNotDone() {
    if (!selectedHomework || homeworkDoneSaving) return;
    homeworkDoneSaving = true;
    try {
      await api.delete(`/guardian/homework/${selectedHomework.id}/done`);
      completedHomework = completedHomework.filter((item) => item.id !== selectedHomework?.id);
      homeworkItems = (await api.get('/guardian/homework'))?.items || [];
      selectedHomework = null;
    } catch (err: any) { error = err?.message || $_('parent.homework.notDoneError'); }
    finally { homeworkDoneSaving = false; }
  }

  onMount(() => {
    void loadDashboard();
    document.addEventListener('visibilitychange', handleVisibilityChange);
    scheduleDashboardPolling();
  });

  onDestroy(() => {
    clearDashboardPolling();
    document.removeEventListener('visibilitychange', handleVisibilityChange);
  });
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
              <button type="button" class="mt-4 flex w-full items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-3 py-2 text-left transition hover:border-violet-300 hover:bg-violet-50" onclick={() => pointsChild = child}>
                <span class={`text-lg font-black ${child.points_total > 0 ? 'text-emerald-600' : child.points_total < 0 ? 'text-amber-700' : 'text-slate-500'}`}>{child.points_total > 0 ? '+' : ''}{child.points_total} {$_('parent.points.pts')}</span>
                <span class="text-sm font-bold text-violet-700">{$_('parent.points.viewHistory')}</span>
              </button>
            </div>
          {/each}
        </div>
      {/if}

      <div class="mt-8 grid min-w-0 gap-4 sm:grid-cols-2">
        <button type="button" class="w-full min-w-0 rounded-lg border border-slate-200 p-5 text-left transition hover:bg-slate-50 sm:col-span-2" onclick={openInbox}>
          <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
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
            <span class="btn-secondary shrink-0 rounded-lg px-4 py-2 text-center text-sm">{$_('parent.announcements.open')}</span>
          </div>
        </button>
        <button type="button" class="w-full min-w-0 rounded-2xl border border-amber-100 bg-amber-50/40 p-5 text-left transition hover:border-amber-300 sm:col-span-2" onclick={openHomeworkList}>
          <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"><div class="min-w-0"><p class="font-bold text-slate-900">{$_('parent.panels.homework')}</p><p class="mt-1 text-sm text-slate-500">{$_('parent.homework.count', { values: { count: homeworkItems.length } })}</p>{#if homeworkItems[0]}<p class="mt-2 truncate text-sm font-semibold text-slate-700">{homeworkItems[0].title}{homeworkItems[0].due_at ? ` · ${formatDate(homeworkItems[0].due_at)}` : ''}</p>{/if}</div><span class="btn-secondary shrink-0 rounded-lg px-4 py-2 text-center text-sm">{$_('parent.homework.open')}</span></div>
        </button>
        <button type="button" class="w-full min-w-0 rounded-2xl border border-sky-100 bg-sky-50/40 p-5 text-left transition hover:border-sky-300 sm:col-span-2" onclick={openUpdates}>
          <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div class="min-w-0">
              <p class="font-bold text-slate-900">{$_('parent.panels.classUpdates')}</p>
              <p class="mt-1 text-sm text-slate-500">{updates.length === 0 ? $_('parent.updates.empty') : $_('parent.updates.count', { values: { count: updates.length } })}</p>
              {#if updates[0]}
                <p class="mt-2 line-clamp-2 break-words text-sm font-semibold text-slate-700">{updates[0].preview}</p>
                <p class="mt-1 text-xs text-slate-500">{updateContext(updates[0])} · {formatDate(updates[0].created_at)}{updates[0].photo_count ? ` · ${$_('parent.updates.photoCount', { values: { count: updates[0].photo_count } })}` : ''}</p>
              {/if}
            </div>
            <span class="btn-secondary shrink-0 rounded-lg px-4 py-2 text-center text-sm">{$_('parent.updates.open')}</span>
          </div>
        </button>
        <button type="button" class="w-full min-w-0 rounded-2xl border border-indigo-100 bg-indigo-50/40 p-5 text-left transition hover:border-indigo-300 sm:col-span-2" onclick={openCalendar}>
          <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div class="min-w-0">
              <p class="font-bold text-slate-900">{$_('calendar.upcoming')}</p>
              {#if calendarItems.length === 0}
                <p class="mt-1 text-sm text-slate-500">{$_('calendar.empty')}</p>
              {:else}
                {#each compactCalendarItems() as item (item.id)}
                  <p class="mt-2 break-words text-sm text-slate-700">{#if item.kind === 'homework_due'}<span class="font-bold">{$_('calendar.types.homework_due')} · </span>{/if}{item.title} · {formatEventDate(item)}</p>
                {/each}
              {/if}
            </div>
            <span class="btn-secondary shrink-0 rounded-lg px-4 py-2 text-center text-sm">{$_('calendar.open')}</span>
          </div>
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

{#if homeworkOpen}
  <div class="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/50 sm:items-center sm:p-4" role="dialog" aria-modal="true" aria-labelledby="guardian-homework-title">
    <div class="max-h-[92vh] w-full max-w-2xl overflow-y-auto overflow-x-hidden rounded-t-2xl bg-white p-5 shadow-xl sm:rounded-2xl sm:p-6">
      {#if !selectedHomework}
        <div class="flex items-start justify-between gap-3"><h2 id="guardian-homework-title" class="text-2xl font-black text-slate-900">{$_('parent.panels.homework')}</h2><button class="btn-secondary rounded-lg px-3 py-2" type="button" onclick={closeHomeworkList}>{$_('parent.homework.close')}</button></div>
        <div class="mt-5 grid grid-cols-2 gap-2 rounded-xl bg-slate-100 p-1"><button type="button" class={`rounded-lg px-3 py-2 text-sm font-black ${homeworkTab === 'active' ? 'bg-white text-amber-800 shadow-sm' : 'text-slate-600'}`} onclick={() => switchHomeworkTab('active')}>{$_('parent.homework.active')}</button><button type="button" class={`rounded-lg px-3 py-2 text-sm font-black ${homeworkTab === 'completed' ? 'bg-white text-amber-800 shadow-sm' : 'text-slate-600'}`} onclick={() => switchHomeworkTab('completed')}>{$_('parent.homework.completed')}</button></div>
        {#if (homeworkTab === 'active' ? homeworkItems : completedHomework).length === 0}<p class="mt-6 text-sm text-slate-500">{homeworkTab === 'active' ? $_('parent.homework.empty') : $_('parent.homework.completedEmpty')}</p>{:else}<div class="mt-4 divide-y divide-slate-100 rounded-xl border border-slate-200">{#each (homeworkTab === 'active' ? homeworkItems : completedHomework) as item}<button type="button" class="block w-full p-4 text-left hover:bg-slate-50" onclick={() => openHomeworkItem(item, homeworkTab === 'completed')}><div class="flex items-start justify-between gap-3"><div class="min-w-0"><p class="font-bold text-slate-900">{item.title}</p><p class="mt-1 text-xs font-semibold text-slate-500">{item.item_type === 'homework' ? $_('parent.homework.types.homework') : $_('parent.homework.types.diary')} · {homeworkContext(item)}</p>{#if item.due_at}<p class="mt-2 text-sm font-bold text-amber-700">{$_('parent.homework.due')}: {formatDateTime(item.due_at)}</p>{/if}<p class="mt-2 line-clamp-2 text-sm text-slate-600">{item.preview}</p></div>{#if item.attachment_count}<span class="shrink-0 rounded-full bg-amber-100 px-2 py-1 text-xs font-bold text-amber-800">{item.attachment_count}</span>{/if}</div></button>{/each}</div>{/if}
      {:else}
        <div class="flex items-start justify-between gap-3"><div class="min-w-0"><button type="button" class="text-sm font-bold text-hero" onclick={() => selectedHomework = null}>{$_('parent.homework.back')}</button><p class="mt-2 text-xs font-bold uppercase text-slate-500">{selectedHomework.item_type === 'homework' ? $_('parent.homework.types.homework') : $_('parent.homework.types.diary')} · {homeworkContext(selectedHomework)}</p><h2 class="mt-2 break-words text-2xl font-black text-slate-900">{selectedHomework.title}</h2></div><button class="btn-secondary shrink-0 rounded-lg px-3 py-2" type="button" onclick={closeHomeworkList}>{$_('parent.homework.close')}</button></div>
        {#if homeworkLoading && !selectedHomework.body}<p class="mt-6 text-sm text-slate-500">{$_('common.loading')}</p>{:else}{#if selectedHomework.due_at}<p class="mt-5 rounded-xl bg-amber-50 p-3 text-sm font-bold text-amber-800">{$_('parent.homework.due')}: {formatDateTime(selectedHomework.due_at)}</p>{/if}<div class="mt-5 whitespace-pre-wrap break-words text-slate-700">{selectedHomework.body || selectedHomework.preview}</div>{#if selectedHomework.resource_links?.length}<div class="mt-6"><h3 class="text-sm font-black uppercase text-slate-500">{$_('parent.homework.resourceLinks')}</h3><div class="mt-2 grid gap-2">{#each selectedHomework.resource_links as link}<a class="break-all rounded-xl border border-sky-100 bg-sky-50 p-3 text-sm font-bold text-sky-800" href={link.url} target="_blank" rel="noopener noreferrer">{link.label || $_('parent.homework.openLink')}</a>{/each}</div></div>{/if}{#if selectedHomework.attachments?.length}<div class="mt-6"><h3 class="text-sm font-black uppercase text-slate-500">{$_('parent.homework.attachments')}</h3><div class="mt-2 divide-y divide-slate-100 rounded-xl border border-slate-200">{#each selectedHomework.attachments as attachment}<div class="flex flex-col gap-2 p-3 sm:flex-row sm:items-center sm:justify-between"><p class="break-all text-sm font-semibold">{attachmentLabel(attachment)}</p><a class="btn-secondary rounded-lg px-3 py-2 text-center text-sm" href={`/api/guardian/homework/${selectedHomework.id}/attachments/${attachment.id}/download`}>{$_('parent.homework.download')}</a></div>{/each}</div></div>{/if}{#if selectedDone}<button type="button" class="mt-7 w-full rounded-xl border border-slate-300 bg-white px-4 py-3 font-black text-slate-700 disabled:opacity-50" disabled={homeworkDoneSaving} onclick={markHomeworkNotDone}>{homeworkDoneSaving ? $_('parent.homework.markingDone') : $_('parent.homework.markNotDone')}</button>{:else}<button type="button" class="mt-7 w-full rounded-xl bg-emerald-600 px-4 py-3 font-black text-white disabled:opacity-50" disabled={homeworkDoneSaving} onclick={markHomeworkDone}>{homeworkDoneSaving ? $_('parent.homework.markingDone') : $_('parent.homework.markDone')}</button>{/if}{/if}
      {/if}
    </div>
  </div>
{/if}

{#if updatesOpen}
  <div class="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/50 sm:items-center sm:p-4" role="dialog" aria-modal="true" aria-labelledby="guardian-updates-title">
    <div class="max-h-[92vh] w-full max-w-2xl overflow-y-auto overflow-x-hidden rounded-t-2xl bg-white p-5 shadow-xl sm:rounded-2xl sm:p-6">
      {#if !selectedUpdate}
        <div class="flex items-start justify-between gap-3"><h2 id="guardian-updates-title" class="text-2xl font-black text-slate-900">{$_('parent.panels.classUpdates')}</h2><button class="btn-secondary rounded-lg px-3 py-2" type="button" onclick={closeUpdates}>{$_('parent.updates.close')}</button></div>
        {#if updates.length === 0}
          <p class="mt-6 text-sm text-slate-500">{$_('parent.updates.empty')}</p>
        {:else}
          <div class="mt-5 max-h-[74vh] divide-y divide-slate-100 overflow-y-auto rounded-xl border border-slate-200">
            {#each updates.slice(0, 20) as post (post.id)}
              <article class="p-4">
                <button type="button" class="block w-full text-left" onclick={() => openUpdatePost(post)}>
                  <p class="text-xs font-bold uppercase tracking-wide text-sky-700">{updateContext(post)}</p>
                  <p class="mt-2 line-clamp-3 whitespace-pre-wrap break-words text-sm text-slate-700">{post.preview}</p>
                  <p class="mt-2 text-xs text-slate-500">{formatDateTime(post.created_at)}{post.author_name ? ` · ${post.author_name}` : ''}</p>
                </button>
                {#if post.photos?.length}
                  <div class="mt-3 flex gap-2 overflow-x-auto">
                    {#each post.photos as photo (photo.id)}
                      {@const photoState = updatePhotoLoadStates[updatePhotoKey(post, photo)]}
                      <button type="button" class="relative h-20 w-20 shrink-0 overflow-hidden rounded-lg border border-slate-200 bg-slate-100" onclick={() => openLightbox(post, photo)}>
                        {#if photoState === 'failed'}
                          <span class="absolute inset-0 flex items-center justify-center p-1 text-center text-[10px] font-semibold text-slate-500">{$_('parent.updates.photoLoadError')}</span>
                        {:else if photoState !== 'loaded'}
                          <span class="absolute inset-0 flex items-center justify-center p-1 text-center text-[10px] font-semibold text-slate-500">{$_('parent.updates.photoLoading')}</span>
                        {/if}
                        <img src={updatePhotoThumbnailUrl(post, photo)} alt={photo.original_filename} loading="lazy" class={`h-full w-full object-cover transition-opacity ${photoState === 'loaded' ? 'opacity-100' : 'opacity-0'}`} onload={() => updatePhotoLoaded(post, photo)} onerror={() => updatePhotoFailed(post, photo)} />
                      </button>
                    {/each}
                  </div>
                {/if}
              </article>
            {/each}
          </div>
        {/if}
      {:else}
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <button type="button" class="text-sm font-bold text-hero" onclick={() => selectedUpdate = null}>{$_('parent.updates.back')}</button>
            <p class="mt-2 text-xs font-bold uppercase tracking-wide text-sky-700">{updateContext(selectedUpdate)}</p>
            <p class="mt-1 text-sm text-slate-500">{formatDateTime(selectedUpdate.created_at)}{selectedUpdate.author_name ? ` · ${selectedUpdate.author_name}` : ''}</p>
          </div>
          <button class="btn-secondary shrink-0 rounded-lg px-3 py-2" type="button" onclick={closeUpdates}>{$_('parent.updates.close')}</button>
        </div>
        {#if updateLoading && !selectedUpdate.body}
          <p class="mt-6 text-sm text-slate-500">{$_('common.loading')}</p>
        {:else}
          <div class="mt-5 whitespace-pre-wrap break-words text-slate-700">{selectedUpdate.body || selectedUpdate.preview}</div>
          {#if selectedUpdate.photos?.length}
            <div class="mt-5 grid grid-cols-2 gap-2 sm:grid-cols-3">
              {#each selectedUpdate.photos as photo (photo.id)}
                {@const photoState = updatePhotoLoadStates[updatePhotoKey(selectedUpdate, photo)]}
                <button type="button" class="relative aspect-square overflow-hidden rounded-xl border border-slate-200 bg-slate-100" onclick={() => openLightbox(selectedUpdate!, photo)}>
                  {#if photoState === 'failed'}
                    <span class="absolute inset-0 flex items-center justify-center p-2 text-center text-xs font-semibold text-slate-500">{$_('parent.updates.photoLoadError')}</span>
                  {:else if photoState !== 'loaded'}
                    <span class="absolute inset-0 flex items-center justify-center p-2 text-center text-xs font-semibold text-slate-500">{$_('parent.updates.photoLoading')}</span>
                  {/if}
                  <img src={updatePhotoThumbnailUrl(selectedUpdate, photo)} alt={photo.original_filename} loading="lazy" class={`h-full w-full object-cover transition-opacity ${photoState === 'loaded' ? 'opacity-100' : 'opacity-0'}`} onload={() => updatePhotoLoaded(selectedUpdate!, photo)} onerror={() => updatePhotoFailed(selectedUpdate!, photo)} />
                </button>
              {/each}
            </div>
          {:else}
            <p class="mt-5 text-sm text-slate-500">{$_('parent.updates.noPhotos')}</p>
          {/if}
        {/if}
      {/if}
    </div>
  </div>
{/if}

{#if calendarOpen}
  <div class="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/50 sm:items-center sm:p-4" role="dialog" aria-modal="true" aria-labelledby="guardian-calendar-title">
    <div class="max-h-[92vh] w-full max-w-2xl overflow-y-auto overflow-x-hidden rounded-t-2xl bg-white p-5 shadow-xl sm:rounded-2xl sm:p-6">
      <div class="flex items-start justify-between gap-3">
        <h2 id="guardian-calendar-title" class="text-2xl font-black text-slate-900">{$_('calendar.upcoming')}</h2>
        <button class="btn-secondary rounded-lg px-3 py-2" type="button" onclick={closeCalendar}>{$_('calendar.close')}</button>
      </div>
      {#if calendarItems.length === 0}
        <p class="mt-6 text-sm text-slate-500">{$_('calendar.empty')}</p>
      {:else}
        <div class="mt-5 max-h-[74vh] divide-y divide-slate-100 overflow-y-auto rounded-xl border border-slate-200">
          {#each calendarItems as item (item.id)}
            {#if item.kind === 'homework_due'}
              <button type="button" class="block w-full p-4 text-left hover:bg-slate-50" onclick={() => openCalendarHomework(item)}>
                <span class="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-bold text-amber-800">{$_(`calendar.types.${item.event_type}`)}</span>
                <p class="mt-1 break-words font-bold text-slate-900">{item.title}</p>
                <p class="mt-1 text-sm text-slate-500">{formatEventDate(item)} · {calendarContext(item)}</p>
              </button>
            {:else}
              <div class="p-4">
                <p class="break-words font-bold text-slate-900">{item.title}</p>
                <p class="mt-1 text-sm text-slate-500">{formatEventDate(item)} · {calendarContext(item)}</p>
                {#if item.body}<p class="mt-2 whitespace-pre-wrap break-words text-sm text-slate-600">{item.body}</p>{/if}
              </div>
            {/if}
          {/each}
        </div>
      {/if}
    </div>
  </div>
{/if}

{#if lightboxPhoto}
  <div class="fixed inset-0 z-[60] flex items-center justify-center bg-slate-950/90 p-4" role="dialog" aria-modal="true">
    <button type="button" class="absolute end-4 top-4 rounded-lg bg-white/10 px-4 py-2 font-bold text-white" onclick={() => lightboxPhoto = null}>{$_('parent.updates.close')}</button>
    <button type="button" class="relative flex min-h-40 max-h-full max-w-full items-center justify-center" onclick={() => lightboxPhoto = null}>
      {#if lightboxPhotoState === 'failed'}
        <span class="rounded-xl bg-white/10 p-4 text-center text-sm font-semibold text-white">{$_('parent.updates.photoLoadError')}</span>
      {:else if lightboxPhotoState !== 'loaded'}
        <span class="absolute rounded-xl bg-white/10 p-4 text-center text-sm font-semibold text-white">{$_('parent.updates.photoLoading')}</span>
      {/if}
      <img src={lightboxPhoto.url} alt={lightboxPhoto.alt} class={`max-h-[88vh] max-w-full rounded-xl object-contain transition-opacity ${lightboxPhotoState === 'loaded' ? 'opacity-100' : 'opacity-0'}`} onload={() => lightboxPhotoState = 'loaded'} onerror={() => lightboxPhotoState = 'failed'} />
    </button>
  </div>
{/if}

{#if pointsChild}
  <div class="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/50 sm:items-center sm:p-4" role="dialog" aria-modal="true" aria-labelledby="points-title">
    <div class="max-h-[92vh] w-full max-w-2xl overflow-y-auto overflow-x-hidden rounded-t-2xl bg-white p-5 shadow-xl sm:rounded-2xl sm:p-6">
      <div class="flex items-start justify-between gap-3"><div class="min-w-0"><p class="text-sm font-bold uppercase tracking-wide text-violet-600">{$_('parent.panels.points')}</p><h2 id="points-title" class="mt-1 truncate text-2xl font-black text-slate-900">{pointsChild.display_name}</h2></div><button type="button" class="btn-secondary shrink-0 rounded-lg px-3 py-2" onclick={() => pointsChild = null}>{$_('parent.points.close')}</button></div>
      <div class="mt-5 rounded-xl bg-slate-50 p-4"><p class="text-sm font-bold text-slate-500">{$_('parent.points.currentTotal')}</p><p class={`mt-1 text-3xl font-black ${pointsChild.points_total > 0 ? 'text-emerald-600' : pointsChild.points_total < 0 ? 'text-amber-700' : 'text-slate-600'}`}>{pointsChild.points_total > 0 ? '+' : ''}{pointsChild.points_total} {$_('parent.points.pts')}</p></div>
      {#if pointsChild.recent_point_events.length === 0}
        <p class="mt-5 text-sm text-slate-500">{$_('parent.points.noHistory')}</p>
      {:else}
        <div class="mt-5 divide-y divide-slate-100 rounded-xl border border-slate-200">
          {#each pointsChild.recent_point_events as event}
            <article class="p-4"><div class="flex items-start justify-between gap-3"><div class="min-w-0"><p class={`font-bold ${event.type === 'positive' ? 'text-emerald-700' : 'text-amber-700'}`}>{event.category_label}</p><p class="mt-1 text-xs text-slate-500">{[formatDateTime(event.created_at), event.teacher_name, ...pointContext(event)].filter(Boolean).join(' · ')}</p></div><span class={`shrink-0 text-lg font-black ${event.points_delta > 0 ? 'text-emerald-600' : 'text-amber-700'}`}>{event.points_delta > 0 ? '+' : ''}{event.points_delta}</span></div>{#if event.note}<p class="mt-3 whitespace-pre-wrap break-words text-sm text-slate-600">{event.note}</p>{/if}</article>
          {/each}
        </div>
      {/if}
    </div>
  </div>
{/if}
