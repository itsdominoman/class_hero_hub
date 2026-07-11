<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { CalendarDays, Search, Star } from 'lucide-svelte';
  import { api } from '$lib/api';
  import { initialsFromStudentName } from '$lib/guardianDisplay';

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
  type AnnouncementAttachment = {
    id: number;
    original_filename: string;
    content_type: string;
    size_bytes: number;
  };
  type Announcement = {
    id: number;
    school_id: number;
    title: string;
    body: string;
    audience_type: 'school' | 'class_section' | 'subject_group';
    class_section_name?: string | null;
    subject_group_name?: string | null;
    created_at?: string | null;
    attachment_count: number;
    attachments: AnnouncementAttachment[];
    status: string;
  };
  type CalendarItem = {
    id: string;
    kind: 'event' | 'homework_due';
    event_id?: number;
    homework_item_id?: number;
    school_id: number;
    title: string;
    body?: string | null;
    event_type: string;
    audience_type: 'school' | 'class_section' | 'subject_group';
    class_section_name?: string | null;
    subject_group_name?: string | null;
    starts_at: string;
    ends_at?: string | null;
    all_day: boolean;
    can_manage?: boolean;
  };
  type SchoolRef = { id: number; name: string; name_ar?: string | null };
  type Category = { id: number; type: 'positive' | 'needs_work'; label: string; points_value: number };
  type SearchStudent = {
    id: number; display_name: string; first_name: string; last_name: string; preferred_name?: string | null;
    name_ar?: string | null; avatar_url_256?: string | null; points_total: number;
    class_section?: string | null; grade_level?: string | null;
  };

  let loading = $state(true);
  let allowed = $state(false);
  let error = $state<string | null>(null);
  let assignments = $state<AssignmentCard[]>([]);
  let announcements = $state<Announcement[]>([]);
  let announcementTitle = $state('');
  let announcementBody = $state('');
  let announcementAudience = $state('');
  let announcementFiles = $state<FileList | null>(null);
  let announcementSaving = $state(false);
  let announcementSuccess = $state(false);
  let viewingAnnouncement = $state<Announcement | null>(null);
  let editingAnnouncement = $state<Announcement | null>(null);
  let announcementModal = $state<'closed' | 'create' | 'manage' | 'detail' | 'edit'>('closed');
  let calendarModal = $state<'closed' | 'list' | 'create' | 'edit'>('closed');
  let calendarItems = $state<CalendarItem[]>([]);
  let calendarSchoolId = $state('');
  let calendarError = $state<string | null>(null);
  let calendarNotice = $state<string | null>(null);
  let calendarSaving = $state(false);
  let editingEvent = $state<CalendarItem | null>(null);
  let eventAudience = $state('');
  let eventTitle = $state('');
  let eventBody = $state('');
  let eventStartsAt = $state('');
  let eventEndsAt = $state('');
  let eventAllDay = $state(false);
  let teacherSchools = $state<SchoolRef[]>([]);
  let studentModal = $state<'closed' | 'open'>('closed');
  let searchSchoolId = $state('');
  let searchText = $state('');
  let searchResults = $state<SearchStudent[]>([]);
  let selectedStudents = $state<SearchStudent[]>([]);
  let searching = $state(false);
  let searchError = $state<string | null>(null);
  let failedSearchImages = $state<Record<number, boolean>>({});
  let categories = $state<Category[]>([]);
  let pointType = $state<'positive' | 'needs_work'>('positive');
  let categoryId = $state('');
  let pointNote = $state('');
  let pointsSaving = $state(false);
  let pointsSuccess = $state<string | null>(null);
  let searchTimer: ReturnType<typeof setTimeout> | null = null;

  function titleFor(card: AssignmentCard) {
    if (card.role === 'homeroom') return card.class_section?.name || card.class_section?.code || $_('teach.homeroom');
    return card.subject_group?.name || card.subject_group?.code || $_('teach.subject');
  }

  function detailsFor(card: AssignmentCard) {
    return [card.subject?.name, card.grade_level?.name, card.branch?.name, card.academic_year?.name].filter(Boolean).join(' · ');
  }

  function audienceOptions() {
    return assignments
      .map((card) => {
        const targetId = card.target_type === 'subject_group' ? card.subject_group?.id : card.class_section?.id;
        if (!targetId) return null;
        return {
          id: String(card.id),
          label: `${card.school.name} · ${titleFor(card)}`,
          school_id: card.school.id,
          audience_type: card.target_type === 'subject_group' ? 'subject_group' : 'class_section',
          class_section_id: card.target_type === 'class_section' ? targetId : null,
          subject_group_id: card.target_type === 'subject_group' ? targetId : null
        };
      })
      .filter(Boolean) as {
        id: string;
        label: string;
        school_id: number;
        audience_type: 'class_section' | 'subject_group';
        class_section_id: number | null;
        subject_group_id: number | null;
      }[];
  }

  function selectedAudience() {
    return audienceOptions().find((option) => option.id === announcementAudience) || null;
  }

  function schoolOptions(schoolId: number): RequestInit {
    return { headers: { 'X-School-Id': String(schoolId) } };
  }

  async function openStudentModal() {
    studentModal = 'open';
    searchError = null;
    pointsSuccess = null;
    if (!searchSchoolId && teacherSchools.length) searchSchoolId = String(teacherSchools[0].id);
    try {
      const data = await api.get(`/teach/behaviour/categories?school_id=${searchSchoolId}`);
      categories = data?.categories || [];
      categoryId = String(categories.find((row) => row.type === pointType)?.id || '');
    } catch (err: any) {
      searchError = err?.message || $_('teach.points.loadError');
    }
  }

  function closeStudentModal() {
    if (pointsSaving) return;
    studentModal = 'closed';
  }

  async function changeSearchSchool() {
    searchResults = [];
    selectedStudents = [];
    searchText = '';
    await openStudentModal();
  }

  function queueStudentSearch() {
    if (searchTimer) clearTimeout(searchTimer);
    searchError = null;
    if (searchText.trim().length < 2) {
      searchResults = [];
      searching = false;
      return;
    }
    searchTimer = setTimeout(runStudentSearch, 300);
  }

  async function runStudentSearch() {
    const query = searchText.trim();
    if (query.length < 2 || !searchSchoolId) return;
    searching = true;
    try {
      const data = await api.get(`/teach/students/search?school_id=${searchSchoolId}&q=${encodeURIComponent(query)}`);
      if (query === searchText.trim()) searchResults = data?.students || [];
    } catch (err: any) {
      searchError = err?.message || $_('teach.studentSearch.searchError');
    } finally {
      searching = false;
    }
  }

  function toggleSearchStudent(student: SearchStudent) {
    selectedStudents = selectedStudents.some((row) => row.id === student.id)
      ? selectedStudents.filter((row) => row.id !== student.id)
      : [...selectedStudents, student];
  }

  function choosePointType(value: 'positive' | 'needs_work') {
    pointType = value;
    categoryId = String(categories.find((row) => row.type === value)?.id || '');
  }

  async function submitDutyPoints() {
    if (pointsSaving || !selectedStudents.length || !categoryId || !searchSchoolId) return;
    pointsSaving = true;
    searchError = null;
    try {
      const result = await api.post('/teach/behaviour/events', {
        school_id: Number(searchSchoolId), student_ids: selectedStudents.map((row) => row.id),
        category_id: Number(categoryId), note: pointNote || null
      });
      pointsSuccess = result.created === 1 ? $_('teach.points.successOne') : $_('teach.points.successMany', { values: { count: result.created } });
      selectedStudents = [];
      searchResults = [];
      searchText = '';
      pointNote = '';
      studentModal = 'closed';
    } catch (err: any) {
      searchError = err?.message || $_('teach.points.saveError');
    } finally {
      pointsSaving = false;
    }
  }

  async function loadAnnouncements() {
    const audience = selectedAudience() || audienceOptions()[0];
    if (!audience) {
      announcements = [];
      return;
    }
    const data = await api.get('/teach/announcements', schoolOptions(audience.school_id));
    announcements = (data?.announcements || []).filter((announcement: Announcement) => announcement.audience_type !== 'school');
  }

  function announcementContext(announcement: Announcement) {
    if (announcement.audience_type === 'subject_group') return announcement.subject_group_name || $_('teach.announcements.subjectAudience');
    if (announcement.audience_type === 'class_section') return announcement.class_section_name || $_('teach.announcements.classAudience');
    return $_('teach.announcements.schoolAudience');
  }

  function formatDate(value?: string | null) {
    if (!value) return '';
    return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value));
  }

  function handleAnnouncementFiles(event: Event) {
    announcementFiles = (event.target as HTMLInputElement).files;
  }

  function openManageMode() {
    announcementModal = 'manage';
    viewingAnnouncement = null;
  }

  function closeAnnouncementModal() {
    announcementModal = 'closed';
    viewingAnnouncement = null;
    editingAnnouncement = null;
  }

  function openCreateMode() {
    announcementSuccess = false;
    announcementModal = 'create';
    viewingAnnouncement = null;
  }

  function backToList() {
    announcementModal = 'manage';
    viewingAnnouncement = null;
    editingAnnouncement = null;
  }

  function viewAnnouncement(announcement: Announcement) {
    viewingAnnouncement = announcement;
    announcementModal = 'detail';
  }

  function attachmentLabel(attachment: AnnouncementAttachment) {
    const sizeKb = Math.max(1, Math.round((attachment.size_bytes || 0) / 1024));
    return `${attachment.original_filename} · ${sizeKb} KB`;
  }

  async function downloadAttachment(announcement: Announcement, attachment: AnnouncementAttachment) {
    try {
      const blob = await api.download(
        `/teach/announcements/${announcement.id}/attachments/${attachment.id}/download`,
        schoolOptions(announcement.school_id)
      );
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = attachment.original_filename;
      link.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      error = err?.message || $_('teach.announcements.downloadError');
    }
  }

  async function publishAnnouncement() {
    const audience = selectedAudience();
    if (!audience) return;
    announcementSaving = true;
    error = null;
    try {
      const created = await api.post(
        '/school/announcements',
        {
          title: announcementTitle,
          body: announcementBody,
          audience_type: audience.audience_type,
          class_section_id: audience.class_section_id,
          subject_group_id: audience.subject_group_id
        },
        schoolOptions(audience.school_id)
      );
      for (const file of Array.from(announcementFiles || [])) {
        const formData = new FormData();
        formData.append('file', file);
        await api.upload(`/teach/announcements/${created.id}/attachments`, formData, schoolOptions(audience.school_id));
      }
      announcementTitle = '';
      announcementBody = '';
      announcementFiles = null;
      announcementSuccess = true;
      await loadAnnouncements();
      closeAnnouncementModal();
    } catch (err: any) {
      error = err?.message || $_('teach.announcements.saveError');
    } finally {
      announcementSaving = false;
    }
  }

  function startEditAnnouncement(announcement: Announcement) {
    editingAnnouncement = announcement;
    announcementTitle = announcement.title;
    announcementBody = announcement.body;
    error = null;
    announcementModal = 'edit';
  }

  async function saveAnnouncementEdit() {
    if (!editingAnnouncement || announcementSaving) return;
    announcementSaving = true;
    error = null;
    try {
      const updated = await api.patch(
        `/teach/announcements/${editingAnnouncement.id}`,
        { title: announcementTitle, body: announcementBody },
        schoolOptions(editingAnnouncement.school_id)
      );
      announcementTitle = '';
      announcementBody = '';
      editingAnnouncement = null;
      viewingAnnouncement = updated;
      announcementModal = 'detail';
      await loadAnnouncements();
    } catch (err: any) {
      error = err?.message || $_('teach.announcements.updateError');
    } finally {
      announcementSaving = false;
    }
  }

  function calendarAudienceOptions() {
    return audienceOptions().filter((option) => String(option.school_id) === calendarSchoolId);
  }

  function toDatetimeLocal(iso?: string | null): string {
    if (!iso) return '';
    const parsed = new Date(iso);
    return new Date(parsed.getTime() - parsed.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
  }

  function toDateInput(iso?: string | null): string {
    return toDatetimeLocal(iso).slice(0, 10);
  }

  function changeEventAllDay() {
    if (eventAllDay) {
      eventStartsAt = eventStartsAt.slice(0, 10);
      eventEndsAt = '';
    } else if (eventStartsAt.length === 10) {
      eventStartsAt = `${eventStartsAt}T00:00`;
    }
  }

  function calendarContext(item: CalendarItem) {
    if (item.audience_type === 'subject_group') return item.subject_group_name || $_('teach.announcements.subjectAudience');
    if (item.audience_type === 'class_section') return item.class_section_name || $_('teach.announcements.classAudience');
    return $_('calendar.schoolWide');
  }

  function formatEventDate(item: CalendarItem) {
    const options: Intl.DateTimeFormatOptions = item.all_day ? { dateStyle: 'medium' } : { dateStyle: 'medium', timeStyle: 'short' };
    let label = new Intl.DateTimeFormat(undefined, options).format(new Date(item.starts_at));
    if (item.ends_at && !item.all_day) label += ` – ${new Intl.DateTimeFormat(undefined, { timeStyle: 'short' }).format(new Date(item.ends_at))}`;
    return label;
  }

  async function loadCalendar() {
    if (!calendarSchoolId) return;
    try {
      calendarItems = (await api.get('/teach/calendar', schoolOptions(Number(calendarSchoolId))))?.items || [];
      calendarError = null;
    } catch (err: any) {
      calendarError = err?.message || $_('calendar.loadError');
    }
  }

  async function openCalendarModal() {
    calendarError = null;
    calendarNotice = null;
    editingEvent = null;
    if (!calendarSchoolId) calendarSchoolId = String(teacherSchools[0]?.id || '');
    calendarModal = 'list';
    await loadCalendar();
  }

  function closeCalendarModal() {
    if (calendarSaving) return;
    calendarModal = 'closed';
    editingEvent = null;
  }

  async function changeCalendarSchool() {
    calendarItems = [];
    await loadCalendar();
  }

  function openEventCreate() {
    eventTitle = '';
    eventBody = '';
    eventStartsAt = '';
    eventEndsAt = '';
    eventAllDay = true;
    eventAudience = calendarAudienceOptions()[0]?.id || '';
    editingEvent = null;
    calendarError = null;
    calendarModal = 'create';
  }

  function openEventEdit(item: CalendarItem) {
    editingEvent = item;
    eventTitle = item.title;
    eventBody = item.body || '';
    eventStartsAt = item.all_day ? toDateInput(item.starts_at) : toDatetimeLocal(item.starts_at);
    eventEndsAt = item.all_day ? '' : toDatetimeLocal(item.ends_at);
    eventAllDay = item.all_day;
    calendarError = null;
    calendarModal = 'edit';
  }

  function eventPayload() {
    return {
      title: eventTitle,
      body: eventBody || null,
      starts_at: new Date(eventAllDay ? `${eventStartsAt}T00:00` : eventStartsAt).toISOString(),
      ends_at: !eventAllDay && eventEndsAt ? new Date(eventEndsAt).toISOString() : null,
      all_day: eventAllDay
    };
  }

  async function saveEvent() {
    if (calendarSaving || !eventStartsAt) return;
    calendarSaving = true;
    calendarError = null;
    try {
      if (editingEvent) {
        await api.patch(`/school/calendar/${editingEvent.event_id}`, eventPayload(), schoolOptions(editingEvent.school_id));
        calendarNotice = $_('calendar.updated');
      } else {
        const audience = calendarAudienceOptions().find((option) => option.id === eventAudience);
        if (!audience) return;
        await api.post(
          '/school/calendar',
          { ...eventPayload(), audience_type: audience.audience_type, class_section_id: audience.class_section_id, subject_group_id: audience.subject_group_id },
          schoolOptions(audience.school_id)
        );
        calendarNotice = $_('calendar.created');
      }
      editingEvent = null;
      calendarModal = 'list';
      await loadCalendar();
    } catch (err: any) {
      calendarError = err?.message || $_('calendar.saveError');
    } finally {
      calendarSaving = false;
    }
  }

  async function archiveEvent(item: CalendarItem) {
    if (calendarSaving || item.kind !== 'event') return;
    calendarSaving = true;
    calendarError = null;
    try {
      await api.delete(`/school/calendar/${item.event_id}`, schoolOptions(item.school_id));
      calendarNotice = $_('calendar.archived');
      await loadCalendar();
    } catch (err: any) {
      calendarError = err?.message || $_('calendar.archiveError');
    } finally {
      calendarSaving = false;
    }
  }

  async function archiveAnnouncement(announcement: Announcement) {
    const audience = selectedAudience();
    if (!audience) return;
    announcementSaving = true;
    error = null;
    try {
      await api.delete(`/teach/announcements/${announcement.id}`, schoolOptions(audience.school_id));
      await loadAnnouncements();
    } catch (err: any) {
      error = err?.message || $_('teach.announcements.archiveError');
    } finally {
      announcementSaving = false;
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
      teacherSchools = data.schools || [];
      searchSchoolId = String(teacherSchools[0]?.id || '');
      if (audienceOptions().length) {
        announcementAudience = audienceOptions()[0].id;
        await loadAnnouncements();
      }
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
  <section class="mx-auto max-w-5xl px-4 py-8 pb-24 md:pb-8">
    <div class="border-b border-slate-200 pb-5">
      <p class="eyebrow">{$_('teach.eyebrow')}</p>
      <h1 class="mt-2 text-3xl font-black text-slate-900">{$_('teach.heading')}</h1>
    </div>

    <div class="mt-4 flex flex-wrap items-center gap-3">
      <button type="button" class="btn-hero inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm shadow-md" onclick={openStudentModal}><Search size={17} aria-hidden="true" />{$_('teach.studentSearch.find')}</button>
      <button type="button" class="btn-hero rounded-lg px-4 py-2 text-sm" onclick={openManageMode}>{$_('teach.announcements.title')}</button>
      <button type="button" class="btn-secondary inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm" onclick={openCalendarModal}><CalendarDays size={17} aria-hidden="true" />{$_('calendar.title')}</button>
    </div>

    {#if pointsSuccess}
      <div class="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm font-semibold text-emerald-700">{pointsSuccess}</div>
    {/if}

    {#if announcementSuccess}
      <div class="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm font-semibold text-emerald-700">{$_('teach.announcements.created')}</div>
    {/if}

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
            <a class="btn-hero mt-5 inline-flex rounded-lg px-4 py-2 text-sm" href={`/teach/assignments/${card.id}`}>
              {$_('teach.openClass')}
            </a>
          </article>
        {/each}
      </div>
    {/if}

  </section>
{/if}

{#if studentModal === 'open'}
  <div class="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/50 sm:items-center sm:p-4" role="dialog" aria-modal="true" aria-labelledby="find-student-title">
    <div class="max-h-[94vh] w-full max-w-3xl overflow-y-auto overflow-x-hidden rounded-t-2xl bg-white p-5 shadow-xl sm:rounded-2xl sm:p-6">
      <div class="flex items-start justify-between gap-3">
        <div><h2 id="find-student-title" class="text-2xl font-black text-slate-900">{$_('teach.studentSearch.title')}</h2><p class="mt-1 text-sm font-semibold text-slate-500">{$_('teach.studentSearch.subtitle')}</p></div>
        <button type="button" class="btn-secondary rounded-lg px-3 py-2" disabled={pointsSaving} onclick={closeStudentModal}>{$_('teach.points.close')}</button>
      </div>

      {#if searchError}<div class="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-700">{searchError}</div>{/if}
      {#if teacherSchools.length > 1}
        <label class="mt-4 grid gap-1 text-sm font-bold text-slate-700">{$_('teach.studentSearch.school')}<select class="rounded-lg border border-slate-200 px-3 py-2" bind:value={searchSchoolId} onchange={changeSearchSchool}>{#each teacherSchools as school}<option value={school.id}>{school.name}</option>{/each}</select></label>
      {/if}
      <label class="mt-4 grid gap-1 text-sm font-bold text-slate-700">{$_('teach.studentSearch.searchLabel')}
        <div class="relative"><Search class="absolute left-3 top-3 text-slate-400" size={18} aria-hidden="true" /><input class="w-full rounded-xl border border-slate-200 py-2.5 pl-10 pr-3" maxlength="120" bind:value={searchText} oninput={queueStudentSearch} placeholder={$_('teach.studentSearch.placeholder')} /></div>
      </label>
      <p class="mt-1 text-xs font-semibold text-slate-400">{searching ? $_('teach.studentSearch.searching') : searchText.trim().length < 2 ? $_('teach.studentSearch.minimum') : $_('teach.studentSearch.resultCount', { values: { count: searchResults.length } })}</p>

      {#if selectedStudents.length}
        <div class="mt-4 rounded-xl border border-violet-200 bg-violet-50 p-3"><div class="flex items-center justify-between gap-2"><p class="text-sm font-black text-violet-800">{$_('teach.studentSearch.selected', { values: { count: selectedStudents.length } })}</p><button type="button" class="text-xs font-black text-violet-700" onclick={() => selectedStudents = []}>{$_('teach.points.clearSelection')}</button></div><div class="mt-2 flex flex-wrap gap-2">{#each selectedStudents as student}<button type="button" class="rounded-full bg-white px-3 py-1 text-xs font-bold text-slate-700 ring-1 ring-violet-200" onclick={() => toggleSearchStudent(student)}>{student.display_name} ×</button>{/each}</div></div>
      {/if}

      <div class="mt-3 grid max-h-64 gap-2 overflow-y-auto sm:grid-cols-2">
        {#each searchResults as student (student.id)}
          <button type="button" aria-pressed={selectedStudents.some((row) => row.id === student.id)} class={`flex min-w-0 items-center gap-3 rounded-xl border p-3 text-left ${selectedStudents.some((row) => row.id === student.id) ? 'border-violet-500 bg-violet-50' : 'border-slate-200 hover:border-violet-300'}`} onclick={() => toggleSearchStudent(student)}>
            <div class="relative h-12 w-12 shrink-0 overflow-hidden rounded-xl bg-gradient-to-b from-violet-50 to-sky-50"><span class="absolute inset-0 flex items-center justify-center font-black text-hero">{initialsFromStudentName(student)}</span>{#if student.avatar_url_256 && !failedSearchImages[student.id]}<img src={student.avatar_url_256} alt="" class="relative h-full w-full object-contain" onerror={() => failedSearchImages = { ...failedSearchImages, [student.id]: true }} />{/if}</div>
            <span class="min-w-0 flex-1"><strong class="block truncate text-sm text-slate-900">{student.display_name}</strong><small class="block truncate font-semibold text-slate-500">{[student.grade_level, student.class_section].filter(Boolean).join(' · ') || $_('teach.studentSearch.noClass')}</small></span>
            <span class={`shrink-0 text-xs font-black ${student.points_total < 0 ? 'text-amber-700' : 'text-emerald-600'}`}>{student.points_total > 0 ? '+' : ''}{student.points_total} {$_('teach.points.pts')}</span>
          </button>
        {/each}
      </div>

      <div class="mt-5 grid grid-cols-2 gap-2"><button type="button" class={`rounded-xl px-4 py-3 font-black ${pointType === 'positive' ? 'bg-emerald-600 text-white' : 'bg-emerald-50 text-emerald-700'}`} onclick={() => choosePointType('positive')}>{$_('teach.points.positive')}</button><button type="button" class={`rounded-xl px-4 py-3 font-black ${pointType === 'needs_work' ? 'bg-amber-500 text-white' : 'bg-amber-50 text-amber-800'}`} onclick={() => choosePointType('needs_work')}>{$_('teach.points.needsWork')}</button></div>
      <form class="mt-4 grid gap-3" onsubmit={(event) => { event.preventDefault(); submitDutyPoints(); }}>
        <label class="grid gap-1 text-sm font-bold text-slate-700">{$_('teach.points.category')}<select class="rounded-lg border border-slate-200 px-3 py-2" required bind:value={categoryId}>{#each categories.filter((row) => row.type === pointType) as category}<option value={category.id}>{category.label} ({category.points_value > 0 ? '+' : ''}{category.points_value})</option>{/each}</select></label>
        <label class="grid gap-1 text-sm font-bold text-slate-700">{$_('teach.points.note')}<textarea class="min-h-20 rounded-lg border border-slate-200 px-3 py-2" maxlength="500" bind:value={pointNote}></textarea></label>
        <button type="submit" class="btn-hero inline-flex items-center justify-center gap-2 rounded-lg px-4 py-3" disabled={pointsSaving || !selectedStudents.length || !categoryId}><Star size={18} aria-hidden="true" />{pointsSaving ? $_('teach.points.saving') : selectedStudents.length === 1 ? $_('teach.points.saveForOne') : $_('teach.points.saveForMany', { values: { count: selectedStudents.length } })}</button>
      </form>
    </div>
  </div>
{/if}

{#if announcementModal !== 'closed'}
  <div class="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/50 p-0 sm:items-center sm:p-4" role="dialog" aria-modal="true" aria-labelledby="teach-announcements-title">
    <div class="max-h-[92vh] w-full max-w-2xl overflow-y-auto rounded-t-lg bg-white p-5 shadow-xl sm:rounded-lg sm:p-6">
      {#if announcementModal === 'detail' && viewingAnnouncement}
        <div class="flex items-start justify-between gap-4">
          <div class="min-w-0">
            <button type="button" class="text-sm font-bold text-hero" onclick={backToList}>{$_('teach.announcements.back')}</button>
            <p class="mt-2 text-xs font-bold uppercase tracking-wide text-slate-500">{announcementContext(viewingAnnouncement)}</p>
            <h2 id="teach-announcements-title" class="mt-2 text-2xl font-black text-slate-900">{viewingAnnouncement.title}</h2>
            <p class="mt-2 text-sm text-slate-500">{formatDate(viewingAnnouncement.created_at)}</p>
          </div>
          <div class="flex shrink-0 gap-2">
            {#if viewingAnnouncement.status === 'published'}
              <button type="button" class="btn-secondary rounded-lg px-3 py-2 text-sm" onclick={() => viewingAnnouncement && startEditAnnouncement(viewingAnnouncement)}>{$_('teach.announcements.edit')}</button>
            {/if}
            <button type="button" class="rounded-lg border border-slate-200 px-3 py-2 text-sm font-bold text-slate-600" onclick={closeAnnouncementModal}>{$_('teach.announcements.close')}</button>
          </div>
        </div>

        <div class="mt-6 whitespace-pre-wrap text-base leading-relaxed text-slate-700">{viewingAnnouncement.body}</div>

        {#if viewingAnnouncement.attachments?.length}
          <div class="mt-6">
            <h3 class="text-sm font-black uppercase tracking-wide text-slate-500">{$_('teach.announcements.attachmentList')}</h3>
            <div class="mt-3 divide-y divide-slate-100 rounded-lg border border-slate-100">
              {#each viewingAnnouncement.attachments as attachment}
                <div class="flex flex-col gap-2 p-3 sm:flex-row sm:items-center sm:justify-between">
                  <p class="break-all text-sm font-semibold text-slate-800">{attachmentLabel(attachment)}</p>
                  <button type="button" class="btn-secondary rounded-lg px-3 py-2 text-center text-sm" onclick={() => viewingAnnouncement && downloadAttachment(viewingAnnouncement, attachment)}>
                    {$_('teach.announcements.download')}
                  </button>
                </div>
              {/each}
            </div>
          </div>
        {/if}
      {:else if announcementModal === 'edit' && editingAnnouncement}
        <div class="flex items-start justify-between gap-4">
          <h2 id="teach-announcements-title" class="text-xl font-black text-slate-900">{$_('teach.announcements.edit')}</h2>
          <button type="button" class="rounded-lg border border-slate-200 px-3 py-2 text-sm font-bold text-slate-600" disabled={announcementSaving} onclick={closeAnnouncementModal}>{$_('teach.announcements.close')}</button>
        </div>

        {#if error}
          <div class="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-700">{error}</div>
        {/if}

        <form class="mt-4 grid gap-3" onsubmit={(event) => { event.preventDefault(); saveAnnouncementEdit(); }}>
          <p class="rounded-lg border border-slate-100 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-600">{announcementContext(editingAnnouncement)}</p>
          <input class="rounded-lg border border-slate-200 px-3 py-2" required maxlength="160" bind:value={announcementTitle} placeholder={$_('teach.announcements.titlePlaceholder')} />
          <textarea class="min-h-32 rounded-lg border border-slate-200 px-3 py-2" required maxlength="10000" bind:value={announcementBody} placeholder={$_('teach.announcements.bodyPlaceholder')}></textarea>
          <div class="flex items-center gap-3">
            <button type="submit" class="btn-hero rounded-lg px-4 py-2" disabled={announcementSaving}>{$_('teach.announcements.saveChanges')}</button>
            <button type="button" class="btn-secondary rounded-lg px-4 py-2" disabled={announcementSaving} onclick={backToList}>{$_('teach.announcements.cancel')}</button>
          </div>
        </form>
      {:else if announcementModal === 'create'}
        <div class="flex items-start justify-between gap-4">
          <h2 id="teach-announcements-title" class="text-xl font-black text-slate-900">{$_('teach.announcements.title')}</h2>
          <button type="button" class="rounded-lg border border-slate-200 px-3 py-2 text-sm font-bold text-slate-600" onclick={closeAnnouncementModal}>{$_('teach.announcements.close')}</button>
        </div>

        {#if error}
          <div class="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-700">{error}</div>
        {/if}

        <form class="mt-4 grid gap-3" onsubmit={(event) => { event.preventDefault(); publishAnnouncement(); }}>
          <label class="block text-sm font-semibold text-slate-700">
            {$_('teach.announcements.audience')}
            <select class="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 font-normal" bind:value={announcementAudience} onchange={loadAnnouncements}>
              {#each audienceOptions() as option}
                <option value={option.id}>{option.label}</option>
              {/each}
            </select>
          </label>
          <input class="rounded-lg border border-slate-200 px-3 py-2" required maxlength="160" bind:value={announcementTitle} placeholder={$_('teach.announcements.titlePlaceholder')} />
          <textarea class="min-h-32 rounded-lg border border-slate-200 px-3 py-2" required maxlength="10000" bind:value={announcementBody} placeholder={$_('teach.announcements.bodyPlaceholder')}></textarea>
          <input class="rounded-lg border border-slate-200 px-3 py-2 text-sm" type="file" multiple accept=".pdf,.doc,.docx,.jpg,.jpeg,.png,.webp,.txt,application/pdf,image/jpeg,image/png,image/webp,text/plain" onchange={handleAnnouncementFiles} />
          <div class="flex items-center gap-3">
            <button type="submit" class="btn-hero rounded-lg px-4 py-2" disabled={announcementSaving}>{announcementSaving ? $_('teach.announcements.publishing') : $_('teach.announcements.publish')}</button>
            <button type="button" class="btn-secondary rounded-lg px-4 py-2" disabled={announcementSaving} onclick={closeAnnouncementModal}>{$_('teach.announcements.cancel')}</button>
          </div>
        </form>
      {:else if announcementModal === 'manage'}
        <div class="flex items-start justify-between gap-4">
          <h2 id="teach-announcements-title" class="text-2xl font-black text-slate-900">{$_('teach.announcements.manageTitle')}</h2>
          <button type="button" class="rounded-lg border border-slate-200 px-3 py-2 text-sm font-bold text-slate-600" onclick={closeAnnouncementModal}>{$_('teach.announcements.close')}</button>
        </div>

        {#if audienceOptions().length > 0}
          <button type="button" class="btn-hero mt-4 rounded-lg px-4 py-2" onclick={openCreateMode}>{$_('teach.announcements.create')}</button>
        {:else}
          <p class="mt-4 text-sm text-slate-500">{$_('teach.announcements.noAudience')}</p>
        {/if}

        <div class="mt-4 max-h-[60vh] divide-y divide-slate-100 overflow-y-auto rounded-lg border border-slate-100">
          {#each announcements as announcement}
            <div class="flex flex-col gap-2 p-3 sm:flex-row sm:items-center sm:justify-between">
              <button type="button" class="min-w-0 flex-1 text-left" onclick={() => viewAnnouncement(announcement)}>
                <p class="truncate font-bold text-slate-900">{announcement.title}</p>
                <p class="mt-1 text-sm text-slate-500">{announcementContext(announcement)} · {formatDate(announcement.created_at)} · {$_('teach.announcements.attachments', { values: { count: announcement.attachment_count } })}</p>
              </button>
              {#if announcement.status === 'published'}
                <div class="flex shrink-0 gap-2">
                  <button type="button" class="btn-secondary rounded-lg px-3 py-2 text-sm" disabled={announcementSaving} onclick={() => startEditAnnouncement(announcement)}>{$_('teach.announcements.edit')}</button>
                  <button type="button" class="btn-secondary rounded-lg px-3 py-2 text-sm" disabled={announcementSaving} onclick={() => archiveAnnouncement(announcement)}>{$_('teach.announcements.archive')}</button>
                </div>
              {/if}
            </div>
          {:else}
            <p class="p-3 text-sm text-slate-500">{$_('teach.announcements.empty')}</p>
          {/each}
        </div>
      {/if}
    </div>
  </div>
{/if}

{#if calendarModal !== 'closed'}
  <div class="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/50 p-0 sm:items-center sm:p-4" role="dialog" aria-modal="true" aria-labelledby="teach-calendar-title">
    <div class="max-h-[92vh] w-full max-w-2xl overflow-y-auto rounded-t-lg bg-white p-5 shadow-xl sm:rounded-lg sm:p-6">
      <div class="flex items-start justify-between gap-4">
        <h2 id="teach-calendar-title" class="text-2xl font-black text-slate-900">{calendarModal === 'create' ? $_('calendar.create') : calendarModal === 'edit' ? $_('calendar.edit') : $_('calendar.schoolCalendar')}</h2>
        <button type="button" class="rounded-lg border border-slate-200 px-3 py-2 text-sm font-bold text-slate-600" disabled={calendarSaving} onclick={closeCalendarModal}>{$_('calendar.close')}</button>
      </div>

      {#if calendarError}
        <div class="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-700">{calendarError}</div>
      {/if}

      {#if calendarModal === 'list'}
        {#if calendarNotice}
          <div class="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm font-semibold text-emerald-700">{calendarNotice}</div>
        {/if}
        {#if teacherSchools.length > 1}
          <label class="mt-4 grid gap-1 text-sm font-bold text-slate-700">{$_('calendar.school')}<select class="rounded-lg border border-slate-200 px-3 py-2" bind:value={calendarSchoolId} onchange={changeCalendarSchool}>{#each teacherSchools as school}<option value={String(school.id)}>{school.name}</option>{/each}</select></label>
        {/if}
        {#if calendarAudienceOptions().length > 0}
          <button type="button" class="btn-hero mt-4 rounded-lg px-4 py-2" onclick={openEventCreate}>{$_('calendar.create')}</button>
        {/if}
        <p class="mt-4 text-xs font-black uppercase tracking-wide text-slate-500">{$_('calendar.upcoming')}</p>
        <div class="mt-2 max-h-[60vh] divide-y divide-slate-100 overflow-y-auto rounded-lg border border-slate-100">
          {#each calendarItems as item (item.id)}
            <div class="flex flex-col gap-2 p-3 sm:flex-row sm:items-center sm:justify-between">
              <div class="min-w-0">
                <p class="mt-1 break-words font-bold text-slate-900">{item.title}</p>
                <p class="mt-1 text-sm text-slate-500">{formatEventDate(item)} · {calendarContext(item)}</p>
                {#if item.body}<p class="mt-1 line-clamp-2 break-words text-sm text-slate-600">{item.body}</p>{/if}
              </div>
              {#if item.kind === 'event' && item.can_manage}
                <div class="flex shrink-0 gap-2">
                  <button type="button" class="btn-secondary rounded-lg px-3 py-2 text-sm" disabled={calendarSaving} onclick={() => openEventEdit(item)}>{$_('calendar.edit')}</button>
                  <button type="button" class="btn-secondary rounded-lg px-3 py-2 text-sm" disabled={calendarSaving} onclick={() => archiveEvent(item)}>{$_('calendar.archive')}</button>
                </div>
              {/if}
            </div>
          {:else}
            <p class="p-3 text-sm text-slate-500">{$_('calendar.empty')}</p>
          {/each}
        </div>
      {:else}
        <form class="mt-4 grid gap-3" onsubmit={(event) => { event.preventDefault(); saveEvent(); }}>
          {#if !editingEvent}
            <label class="block text-sm font-semibold text-slate-700">
              {$_('calendar.audience')}
              <select class="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 font-normal" bind:value={eventAudience}>
                {#each calendarAudienceOptions() as option}
                  <option value={option.id}>{option.label}</option>
                {/each}
              </select>
            </label>
          {/if}
          <input class="rounded-lg border border-slate-200 px-3 py-2" required maxlength="160" bind:value={eventTitle} placeholder={$_('calendar.titleField')} />
          <textarea class="min-h-24 rounded-lg border border-slate-200 px-3 py-2" maxlength="10000" bind:value={eventBody} placeholder={$_('calendar.details')}></textarea>
          <label class="flex items-center gap-2 text-sm font-bold text-slate-700"><input type="checkbox" bind:checked={eventAllDay} onchange={changeEventAllDay} />{$_('calendar.allDay')}</label>
          {#if eventAllDay}
            <label class="grid max-w-sm gap-1 text-sm font-bold text-slate-700">{$_('calendar.date')}<input type="date" class="rounded-lg border border-slate-200 px-3 py-2" required bind:value={eventStartsAt} /></label>
          {:else}
            <div class="grid gap-3 sm:grid-cols-2"><label class="grid gap-1 text-sm font-bold text-slate-700">{$_('calendar.starts')}<input type="datetime-local" class="rounded-lg border border-slate-200 px-3 py-2" required bind:value={eventStartsAt} /></label><label class="grid gap-1 text-sm font-bold text-slate-700">{$_('calendar.ends')}<input type="datetime-local" class="rounded-lg border border-slate-200 px-3 py-2" bind:value={eventEndsAt} /></label></div>
          {/if}
          <div class="flex items-center gap-3">
            <button type="submit" class="btn-hero rounded-lg px-4 py-2" disabled={calendarSaving}>{calendarSaving ? $_('calendar.saving') : $_('calendar.save')}</button>
            <button type="button" class="btn-secondary rounded-lg px-4 py-2" disabled={calendarSaving} onclick={() => { calendarModal = 'list'; editingEvent = null; }}>{$_('calendar.cancel')}</button>
          </div>
        </form>
      {/if}
    </div>
  </div>
{/if}
