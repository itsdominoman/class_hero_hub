<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { _ } from 'svelte-i18n';
  import { ArrowLeft, BookOpen, Camera, Megaphone, Star, Users } from 'lucide-svelte';
  import { api } from '$lib/api';
  import { initialsFromStudentName } from '$lib/guardianDisplay';

  type Ref = { id: number; name?: string | null; name_ar?: string | null };
  type Student = {
    id: number;
    first_name: string;
    last_name: string;
    preferred_name?: string | null;
    display_name: string;
    name_ar?: string | null;
    avatar_id?: number | null;
    avatar_url_256?: string | null;
    points_total: number;
  };
  type Detail = {
    assignment: {
      id: number;
      role: 'homeroom' | 'subject';
      target_type: 'class_section' | 'subject_group';
      school: Ref;
      class_section?: Ref | null;
      subject_group?: Ref | null;
      subject?: Ref | null;
      branch?: Ref | null;
      academic_year?: Ref | null;
      grade_level?: Ref | null;
    };
    student_count: number;
    students: Student[];
  };
  type Category = { id: number; type: 'positive' | 'needs_work'; label: string; points_value: number };

  let loading = $state(true);
  let error = $state<string | null>(null);
  let detail = $state<Detail | null>(null);
  let failedImages = $state<Record<number, boolean>>({});
  let announcementModalOpen = $state(false);
  let announcementTitle = $state('');
  let announcementBody = $state('');
  let announcementFiles = $state<FileList | null>(null);
  let announcementSaving = $state(false);
  let announcementError = $state<string | null>(null);
  let announcementPublished = $state(false);
  let pointsModalOpen = $state(false);
  let categories = $state<Category[]>([]);
  let pointType = $state<'positive' | 'needs_work'>('positive');
  let categoryId = $state('');
  let selectedStudents = $state<number[]>([]);
  let pointNote = $state('');
  let pointsSaving = $state(false);
  let pointsError = $state<string | null>(null);
  let pointsSuccess = $state<string | null>(null);

  function classTitle() {
    const assignment = detail?.assignment;
    if (!assignment) return '';
    return assignment.subject_group?.name || assignment.class_section?.name || assignment.subject?.name || $_('teach.subject');
  }

  function markImageFailed(studentId: number) {
    failedImages = { ...failedImages, [studentId]: true };
  }

  function schoolOptions(schoolId: number): RequestInit {
    return { headers: { 'X-School-Id': String(schoolId) } };
  }

  async function openPointsModal() {
    if (!detail) return;
    pointsError = null;
    pointsSuccess = null;
    pointsModalOpen = true;
    try {
      const data = await api.get(`/teach/behaviour/categories?school_id=${detail.assignment.school.id}`);
      categories = data?.categories || [];
      categoryId = String(categories.find((row) => row.type === pointType)?.id || '');
    } catch (err: any) {
      pointsError = err?.message || $_('teach.points.loadError');
    }
  }

  function closePointsModal() {
    if (!pointsSaving) pointsModalOpen = false;
  }

  function choosePointType(value: 'positive' | 'needs_work') {
    pointType = value;
    categoryId = String(categories.find((row) => row.type === value)?.id || '');
  }

  function toggleStudent(studentId: number) {
    selectedStudents = selectedStudents.includes(studentId) ? selectedStudents.filter((id) => id !== studentId) : [...selectedStudents, studentId];
  }

  function selectWholeClass() {
    selectedStudents = detail?.students.map((student) => student.id) || [];
  }

  function clearStudentSelection() {
    selectedStudents = [];
  }

  async function submitPoints() {
    if (!detail || pointsSaving || !selectedStudents.length || !categoryId) return;
    pointsSaving = true;
    pointsError = null;
    try {
      const result = await api.post('/teach/behaviour/events', { school_id: detail.assignment.school.id, student_ids: selectedStudents, category_id: Number(categoryId), note: pointNote || null });
      const savedCount = result.created;
      detail = await api.get(`/teach/assignments/${$page.params.id}`);
      pointsSuccess = savedCount === 1
        ? $_('teach.points.successOne')
        : $_('teach.points.successMany', { values: { count: savedCount } });
      selectedStudents = [];
      pointNote = '';
      pointsModalOpen = false;
    } catch (err: any) {
      pointsError = err?.message || $_('teach.points.saveError');
    } finally {
      pointsSaving = false;
    }
  }

  function openAnnouncementModal() {
    announcementError = null;
    announcementModalOpen = true;
  }

  function closeAnnouncementModal() {
    if (announcementSaving) return;
    announcementModalOpen = false;
    announcementError = null;
  }

  function handleAnnouncementFiles(event: Event) {
    announcementFiles = (event.target as HTMLInputElement).files;
  }

  async function publishAnnouncement() {
    const assignment = detail?.assignment;
    if (!assignment) return;

    const targetId = assignment.target_type === 'subject_group'
      ? assignment.subject_group?.id
      : assignment.class_section?.id;
    if (!targetId) {
      announcementError = $_('teach.announcements.saveError');
      return;
    }

    announcementSaving = true;
    announcementError = null;
    try {
      const created = await api.post(
        '/school/announcements',
        {
          title: announcementTitle,
          body: announcementBody,
          audience_type: assignment.target_type,
          class_section_id: assignment.target_type === 'class_section' ? targetId : null,
          subject_group_id: assignment.target_type === 'subject_group' ? targetId : null
        },
        schoolOptions(assignment.school.id)
      );
      for (const file of Array.from(announcementFiles || [])) {
        const formData = new FormData();
        formData.append('file', file);
        await api.upload(`/teach/announcements/${created.id}/attachments`, formData, schoolOptions(assignment.school.id));
      }
      announcementTitle = '';
      announcementBody = '';
      announcementFiles = null;
      announcementPublished = true;
      announcementModalOpen = false;
    } catch (err: any) {
      announcementError = err?.message || $_('teach.announcements.saveError');
    } finally {
      announcementSaving = false;
    }
  }

  onMount(async () => {
    try {
      detail = await api.get(`/teach/assignments/${$page.params.id}`);
    } catch (err: any) {
      if (err?.status === 401) {
        window.location.href = `/login?returnTo=${encodeURIComponent($page.url.pathname)}`;
        return;
      }
      error = err?.message || $_('teach.classDetail.loadError');
    } finally {
      loading = false;
    }
  });
</script>

<svelte:head>
  <title>{classTitle() || $_('teach.classDetail.title')}</title>
</svelte:head>

<section class="min-h-screen bg-slate-50/70 pb-14">
  <div class="mx-auto max-w-6xl px-4 py-6 sm:py-8">
    <a href="/teach" class="inline-flex items-center gap-2 rounded-lg bg-white px-3 py-2 text-sm font-bold text-slate-700 shadow-sm ring-1 ring-slate-200 hover:text-hero">
      <ArrowLeft size={17} aria-hidden="true" />
      {$_('teach.classDetail.back')}
    </a>

    {#if loading}
      <div class="card mt-5 p-10 text-center text-sm font-semibold text-slate-500">{$_('common.loading')}</div>
    {:else if error || !detail}
      <div class="card mt-5 p-8 text-center">
        <h1 class="text-2xl font-black text-slate-900">{$_('teach.classDetail.unavailable')}</h1>
        <p class="mt-3 text-slate-600">{error}</p>
      </div>
    {:else}
      <header class="relative mt-5 overflow-hidden rounded-3xl bg-gradient-to-br from-violet-700 via-hero to-sky-500 p-6 text-white shadow-lg sm:p-8">
        <div class="absolute -right-12 -top-16 h-48 w-48 rounded-full bg-white/10"></div>
        <div class="absolute -bottom-20 right-24 h-44 w-44 rounded-full bg-amber-300/20"></div>
        <div class="relative max-w-3xl">
          <div class="flex flex-wrap items-center gap-2 text-xs font-black uppercase tracking-wider text-white/80">
            <span>{detail.assignment.school.name}</span>
            <span aria-hidden="true">•</span>
            <span>{$_(`teach.roles.${detail.assignment.role}`)}</span>
          </div>
          <h1 class="mt-3 text-3xl font-black sm:text-4xl">{classTitle()}</h1>
          {#if detail.assignment.subject?.name && detail.assignment.subject_group?.name !== detail.assignment.subject.name}
            <p class="mt-2 text-lg font-semibold text-white/90">{detail.assignment.subject.name}</p>
          {/if}
          <div class="mt-5 flex flex-wrap gap-x-5 gap-y-2 text-sm font-semibold text-white/90">
            {#if detail.assignment.grade_level?.name}<span>{detail.assignment.grade_level.name}</span>{/if}
            {#if detail.assignment.branch?.name}<span>{detail.assignment.branch.name}</span>{/if}
            {#if detail.assignment.academic_year?.name}<span>{detail.assignment.academic_year.name}</span>{/if}
            <span class="inline-flex items-center gap-1.5"><Users size={17} aria-hidden="true" /> {$_('teach.classDetail.studentCount', { values: { count: detail.student_count } })}</span>
          </div>
        </div>
      </header>

      <div class="mt-5 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <button type="button" class="flex min-h-20 items-center gap-3 rounded-2xl border border-violet-100 bg-white p-4 text-left shadow-sm hover:border-violet-300" onclick={openPointsModal}>
          <span class="rounded-xl bg-violet-100 p-2 text-violet-700"><Star size={21} aria-hidden="true" /></span>
          <span><strong class="block text-sm text-slate-900">{$_('teach.classDetail.actions.points')}</strong><small class="text-xs font-semibold text-violet-600">{$_('teach.points.open')}</small></span>
        </button>
        <button type="button" disabled class="flex min-h-20 items-center gap-3 rounded-2xl border border-sky-100 bg-white p-4 text-left shadow-sm disabled:cursor-default disabled:opacity-100">
          <span class="rounded-xl bg-sky-100 p-2 text-sky-700"><Camera size={21} aria-hidden="true" /></span>
          <span><strong class="block text-sm text-slate-900">{$_('teach.classDetail.actions.updates')}</strong><small class="text-xs font-semibold text-slate-400">{$_('teach.classDetail.comingSoon')}</small></span>
        </button>
        <button type="button" disabled class="flex min-h-20 items-center gap-3 rounded-2xl border border-amber-100 bg-white p-4 text-left shadow-sm disabled:cursor-default disabled:opacity-100">
          <span class="rounded-xl bg-amber-100 p-2 text-amber-700"><BookOpen size={21} aria-hidden="true" /></span>
          <span><strong class="block text-sm text-slate-900">{$_('teach.classDetail.actions.homework')}</strong><small class="text-xs font-semibold text-slate-400">{$_('teach.classDetail.comingSoon')}</small></span>
        </button>
        <button type="button" class="flex min-h-20 items-center gap-3 rounded-2xl border border-emerald-100 bg-white p-4 text-left shadow-sm hover:border-emerald-200" onclick={openAnnouncementModal}>
          <span class="rounded-xl bg-emerald-100 p-2 text-emerald-700"><Megaphone size={21} aria-hidden="true" /></span>
          <span><strong class="block text-sm text-slate-900">{$_('teach.classDetail.actions.announcements')}</strong><small class="text-xs font-semibold text-emerald-600">{announcementPublished ? $_('teach.announcements.created') : $_('teach.classDetail.createForClass')}</small></span>
        </button>
      </div>

      {#if announcementPublished}
        <div class="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm font-semibold text-emerald-700">{$_('teach.announcements.created')}</div>
      {/if}
      {#if pointsSuccess}<div class="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm font-semibold text-emerald-700">{pointsSuccess}</div>{/if}

      <div class="mt-8 flex items-end justify-between gap-4">
        <div>
          <p class="eyebrow">{$_('teach.classDetail.rosterEyebrow')}</p>
          <h2 class="mt-1 text-2xl font-black text-slate-900">{$_('teach.classDetail.students')}</h2>
        </div>
        <span class="rounded-full bg-white px-3 py-1 text-sm font-bold text-slate-500 ring-1 ring-slate-200">{detail.student_count}</span>
      </div>

      {#if detail.students.length === 0}
        <div class="mt-4 rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center text-slate-500">
          {detail.assignment.target_type === 'subject_group' ? $_('teach.emptySubjectRoster') : $_('teach.emptyRoster')}
        </div>
      {:else}
        <div class="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
          {#each detail.students as student (student.id)}
            <article class="group min-w-0 overflow-hidden rounded-2xl border border-slate-200 bg-white p-3 text-center shadow-sm transition hover:-translate-y-0.5 hover:border-violet-200 hover:shadow-md sm:p-4">
              <div class="relative mx-auto aspect-square w-full max-w-36 overflow-hidden rounded-2xl bg-gradient-to-b from-violet-50 to-sky-50">
                <div class="absolute inset-0 flex items-center justify-center text-3xl font-black text-hero">{initialsFromStudentName(student)}</div>
                {#if student.avatar_url_256 && !failedImages[student.id]}
                  <img
                    src={student.avatar_url_256}
                    alt=""
                    width="256"
                    height="256"
                    loading="lazy"
                    class="relative h-full w-full object-contain p-1"
                    onerror={() => markImageFailed(student.id)}
                  />
                {/if}
              </div>
              <h3 class="mt-3 truncate text-sm font-black text-slate-900 sm:text-base" title={student.display_name}>{student.display_name}</h3>
              <p class={`mt-1 text-xs font-black ${student.points_total > 0 ? 'text-emerald-600' : student.points_total < 0 ? 'text-amber-700' : 'text-slate-400'}`}>
                {student.points_total > 0 ? '+' : ''}{student.points_total} {$_('teach.points.pts')}
              </p>
              {#if student.name_ar}
                <p class="mt-0.5 truncate text-xs font-semibold text-slate-400" dir="auto">{student.name_ar}</p>
              {/if}
            </article>
          {/each}
        </div>
      {/if}
    {/if}
  </div>
</section>

{#if announcementModalOpen && detail}
  <div class="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/50 p-0 sm:items-center sm:p-4" role="dialog" aria-modal="true" aria-labelledby="class-announcement-title">
    <div class="max-h-[92vh] w-full max-w-2xl overflow-y-auto rounded-t-lg bg-white p-5 shadow-xl sm:rounded-lg sm:p-6">
      <div class="flex items-start justify-between gap-4">
        <h2 id="class-announcement-title" class="text-xl font-black text-slate-900">{$_('teach.announcements.title')}</h2>
        <button type="button" class="rounded-lg border border-slate-200 px-3 py-2 text-sm font-bold text-slate-600" disabled={announcementSaving} onclick={closeAnnouncementModal}>{$_('teach.announcements.close')}</button>
      </div>

      {#if announcementError}
        <div class="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-700">{announcementError}</div>
      {/if}

      <form class="mt-4 grid gap-3" onsubmit={(event) => { event.preventDefault(); publishAnnouncement(); }}>
        <p class="rounded-lg border border-emerald-100 bg-emerald-50 px-3 py-2 text-sm font-semibold text-slate-700">
          {$_('teach.announcements.audience')}: <span class="font-black">{classTitle()}</span>
        </p>
        <input class="rounded-lg border border-slate-200 px-3 py-2" required maxlength="160" bind:value={announcementTitle} placeholder={$_('teach.announcements.titlePlaceholder')} />
        <textarea class="min-h-32 rounded-lg border border-slate-200 px-3 py-2" required maxlength="10000" bind:value={announcementBody} placeholder={$_('teach.announcements.bodyPlaceholder')}></textarea>
        <input class="rounded-lg border border-slate-200 px-3 py-2 text-sm" type="file" multiple accept=".pdf,.doc,.docx,.jpg,.jpeg,.png,.webp,.txt,application/pdf,image/jpeg,image/png,image/webp,text/plain" onchange={handleAnnouncementFiles} />
        <div class="flex items-center gap-3">
          <button type="submit" class="btn-hero rounded-lg px-4 py-2" disabled={announcementSaving}>{announcementSaving ? $_('teach.announcements.publishing') : $_('teach.announcements.publish')}</button>
          <button type="button" class="btn-secondary rounded-lg px-4 py-2" disabled={announcementSaving} onclick={closeAnnouncementModal}>{$_('teach.announcements.cancel')}</button>
        </div>
      </form>
    </div>
  </div>
{/if}

{#if pointsModalOpen && detail}
  <div class="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/50 sm:items-center sm:p-4" role="dialog" aria-modal="true" aria-labelledby="award-points-title">
    <div class="max-h-[94vh] w-full max-w-3xl overflow-y-auto rounded-t-2xl bg-white p-5 shadow-xl sm:rounded-2xl sm:p-6">
      <div class="flex items-start justify-between gap-3"><div><h2 id="award-points-title" class="text-2xl font-black text-slate-900">{$_('teach.points.title')}</h2><p class="mt-1 text-sm font-semibold text-slate-500">{classTitle()}</p></div><button type="button" class="btn-secondary rounded-lg px-3 py-2" disabled={pointsSaving} onclick={closePointsModal}>{$_('teach.points.close')}</button></div>
      {#if pointsError}<div class="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-700">{pointsError}</div>{/if}
      <div class="mt-5 grid grid-cols-2 gap-2"><button type="button" class={`rounded-xl px-4 py-3 font-black ${pointType === 'positive' ? 'bg-emerald-600 text-white' : 'bg-emerald-50 text-emerald-700'}`} onclick={() => choosePointType('positive')}>{$_('teach.points.positive')}</button><button type="button" class={`rounded-xl px-4 py-3 font-black ${pointType === 'needs_work' ? 'bg-amber-500 text-white' : 'bg-amber-50 text-amber-800'}`} onclick={() => choosePointType('needs_work')}>{$_('teach.points.needsWork')}</button></div>
      <div class="mt-5 flex flex-wrap items-center justify-between gap-2">
        <p class="text-sm font-black text-slate-700">{$_('teach.points.selectStudents')} · {selectedStudents.length}</p>
        <div class="flex gap-2">
          <button type="button" class="rounded-lg border border-violet-200 bg-violet-50 px-3 py-2 text-sm font-black text-violet-700 disabled:opacity-50" disabled={detail.students.length === 0 || selectedStudents.length === detail.students.length} onclick={selectWholeClass}>{$_('teach.points.wholeClass')}</button>
          <button type="button" class="rounded-lg border border-slate-200 px-3 py-2 text-sm font-bold text-slate-600 disabled:opacity-50" disabled={selectedStudents.length === 0} onclick={clearStudentSelection}>{$_('teach.points.clearSelection')}</button>
        </div>
      </div>
      <div class="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4">{#each detail.students as student}<button type="button" aria-pressed={selectedStudents.includes(student.id)} class={`min-w-0 rounded-xl border p-3 text-left text-sm font-bold ${selectedStudents.includes(student.id) ? 'border-violet-500 bg-violet-50 text-violet-800' : 'border-slate-200 text-slate-700'}`} onclick={() => toggleStudent(student.id)}><span class="block truncate">{student.display_name}</span></button>{/each}</div>
      <form class="mt-5 grid gap-3" onsubmit={(event) => { event.preventDefault(); submitPoints(); }}><label class="grid gap-1 text-sm font-bold text-slate-700">{$_('teach.points.category')}<select class="rounded-lg border border-slate-200 px-3 py-2" required bind:value={categoryId}>{#each categories.filter((row) => row.type === pointType) as category}<option value={category.id}>{category.label} ({category.points_value > 0 ? '+' : ''}{category.points_value})</option>{/each}</select></label><label class="grid gap-1 text-sm font-bold text-slate-700">{$_('teach.points.note')}<textarea class="min-h-20 rounded-lg border border-slate-200 px-3 py-2" maxlength="500" bind:value={pointNote}></textarea></label><button type="submit" class="btn-hero rounded-lg px-4 py-3" disabled={pointsSaving || !selectedStudents.length || !categoryId}>{pointsSaving ? $_('teach.points.saving') : selectedStudents.length === 1 ? $_('teach.points.saveForOne') : $_('teach.points.saveForMany', { values: { count: selectedStudents.length } })}</button></form>
    </div>
  </div>
{/if}
