<script lang="ts">
  import { onMount, onDestroy, tick } from 'svelte';
  import { page } from '$app/stores';
  import { _ } from 'svelte-i18n';
  import { ArrowLeft, BookOpen, CalendarDays, Camera, Megaphone, Star, Users } from 'lucide-svelte';
  import { api } from '$lib/api';
  import { initialsFromStudentName } from '$lib/guardianDisplay';
  import {
    ProtectedUpdatePhotoCache,
    ProtectedUpdatePhotoClearedError,
    protectedUpdatePhotoKey,
    protectedUpdatePhotoPath
  } from '$lib/protected-update-photo';

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
  type QuickAction = { id: number; label: string; points_value: number };
  type QuickActions = { quick_actions: Record<'positive' | 'needs_work', QuickAction[]>; other_actions: Record<'positive' | 'needs_work', QuickAction[]> };
  type ResourceLink = { url: string; label?: string | null };
  type HomeworkItem = { id: number; item_type: 'homework' | 'diary'; title: string; body?: string; due_at?: string | null; status: 'active' | 'archived'; attachment_count: number; attachments?: { id: number; original_filename: string; size_bytes: number }[]; resource_links: ResourceLink[] };
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
  type UpdatePhoto = { id: number; original_filename: string };
  type UpdatePost = { id: number; body?: string; created_at?: string | null; status: 'active' | 'archived'; photo_count: number; photos: UpdatePhoto[] };

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
  let homeworkModalOpen = $state(false);
  let homeworkMode = $state<'create' | 'list'>('create');
  let homeworkType = $state<'homework' | 'diary'>('homework');
  let homeworkTitle = $state('');
  let homeworkBody = $state('');
  let homeworkDueAt = $state('');
  let homeworkFiles = $state<FileList | null>(null);
  let homeworkSaving = $state(false);
  let homeworkError = $state<string | null>(null);
  let homeworkNotice = $state<string | null>(null);
  let homeworkNoticeTimer: ReturnType<typeof setTimeout> | null = null;
  let homeworkAbortController = $state<AbortController | null>(null);
  let createdHomeworkId = $state<number | null>(null);
  let homeworkLinks = $state<ResourceLink[]>([]);
  let homeworkItems = $state<HomeworkItem[]>([]);
  let viewingHomework = $state<HomeworkItem | null>(null);
  let homeworkEditing = $state<HomeworkItem | null>(null);
  let homeworkListError = $state<string | null>(null);
  let updatesModalOpen = $state(false);
  let updatesMode = $state<'create' | 'list'>('create');
  let updateBody = $state('');
  let updatePhotos = $state<File[]>([]);
  let updatesSaving = $state(false);
  let updatesError = $state<string | null>(null);
  let updatesNotice = $state<string | null>(null);
  let updatesNoticeTimer: ReturnType<typeof setTimeout> | null = null;
  let updatesAbortController = $state<AbortController | null>(null);
  let createdUpdateId = $state<number | null>(null);
  let updateItems = $state<UpdatePost[]>([]);
  let viewingUpdate = $state<UpdatePost | null>(null);
  let updateEditing = $state<UpdatePost | null>(null);
  let updatesListError = $state<string | null>(null);
  let updatePhotoLoadStates = $state<Record<string, 'loading' | 'loaded' | 'failed'>>({});
  let updatePhotoObjectUrls = $state<Record<string, string>>({});
  let updatePhotoLightbox = $state<{ key: string; alt: string } | null>(null);
  const protectedPhotoCache = new ProtectedUpdatePhotoCache();
  let isNativeAndroid = $state(false);
  let updatePhotoPicking = $state(false);
  let calendarModalOpen = $state(false);
  let calendarMode = $state<'list' | 'create' | 'edit'>('list');
  let calendarItems = $state<CalendarItem[]>([]);
  let calendarError = $state<string | null>(null);
  let calendarNotice = $state<string | null>(null);
  let calendarSaving = $state(false);
  let editingEvent = $state<CalendarItem | null>(null);
  let eventTitle = $state('');
  let eventBody = $state('');
  let eventStartsAt = $state('');
  let eventEndsAt = $state('');
  let eventAllDay = $state(false);
  let pointsModalOpen = $state(false);
  let categories = $state<Category[]>([]);
  let pointType = $state<'positive' | 'needs_work'>('positive');
  let categoryId = $state('');
  let selectedStudents = $state<number[]>([]);
  let pointNote = $state('');
  let pointsSaving = $state(false);
  let pointsError = $state<string | null>(null);
  let pointsSuccess = $state<string | null>(null);
  let quickActions = $state<QuickActions | null>(null);
  let quickActionsLoading = $state(true);
  let quickActionsError = $state<string | null>(null);
  let quickAwardStudent = $state<Student | null>(null);
  let quickAwardMode = $state<'quick' | 'other_positive' | 'other_needs_work'>('quick');
  let quickAwardSaving = $state(false);
  let quickAwardError = $state<string | null>(null);
  let quickAwardNotice = $state<string | null>(null);
  let quickAwardDialog = $state<HTMLDivElement | undefined>(undefined);
  let quickAwardTrigger: HTMLButtonElement | undefined;

  async function loadQuickActions() {
    if (!detail) return;
    quickActionsLoading = true;
    quickActionsError = null;
    try {
      quickActions = await api.get(`/teach/behaviour/quick-actions?school_id=${detail.assignment.school.id}`);
    } catch (err: any) {
      quickActionsError = err?.message || $_('teach.quickAward.loadError');
    } finally {
      quickActionsLoading = false;
    }
  }

  async function openQuickAward(student: Student, trigger: HTMLButtonElement) {
    quickAwardTrigger = trigger;
    quickAwardStudent = student;
    quickAwardMode = 'quick';
    quickAwardError = null;
    await tick();
    quickAwardDialog?.focus();
  }

  function closeQuickAward() {
    if (quickAwardSaving) return;
    quickAwardStudent = null;
    quickAwardError = null;
    quickAwardMode = 'quick';
    void tick().then(() => quickAwardTrigger?.focus());
  }

  function quickAwardKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape') {
      event.preventDefault();
      closeQuickAward();
    }
  }

  function awardContext() {
    if (!detail) return null;
    return detail.assignment.target_type === 'subject_group'
      ? { context_type: 'subject', subject_group_id: detail.assignment.subject_group?.id }
      : { context_type: 'class', class_section_id: detail.assignment.class_section?.id };
  }

  function actionLabel(action: QuickAction, student: Student) {
    return $_('teach.quickAward.actionLabel', { values: { behaviour: action.label, student: student.display_name, points: action.points_value } });
  }

  async function submitQuickAward(action: QuickAction) {
    if (!detail || !quickAwardStudent || quickAwardSaving) return;
    const student = quickAwardStudent;
    const context = awardContext();
    if (!context) return;
    quickAwardSaving = true;
    quickAwardError = null;
    try {
      const result = await api.post('/teach/behaviour/events', {
        school_id: detail.assignment.school.id, student_ids: [student.id], category_id: action.id, note: null, ...context
      });
      const delta = result?.events?.[0]?.points_delta;
      if (typeof delta === 'number') {
        detail = { ...detail, students: detail.students.map((row) => row.id === student.id ? { ...row, points_total: row.points_total + delta } : row) };
      }
      quickAwardNotice = $_('teach.quickAward.success', { values: { behaviour: action.label, points: action.points_value } });
      quickAwardStudent = null;
      quickAwardMode = 'quick';
      void tick().then(() => quickAwardTrigger?.focus());
      void api.get(`/teach/assignments/${$page.params.id}`).then((fresh) => { detail = fresh; }).catch(() => undefined);
    } catch (err: any) {
      quickAwardError = err?.message || $_('teach.quickAward.saveError');
    } finally {
      quickAwardSaving = false;
    }
  }

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
      const target = detail.assignment.target_type === 'subject_group'
        ? { context_type: 'subject', subject_group_id: detail.assignment.subject_group?.id }
        : { context_type: 'class', class_section_id: detail.assignment.class_section?.id };
      const result = await api.post('/teach/behaviour/events', { school_id: detail.assignment.school.id, student_ids: selectedStudents, category_id: Number(categoryId), note: pointNote || null, ...target });
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

  function homeworkQuery() {
    const assignment = detail?.assignment;
    if (!assignment) return '';
    const key = assignment.target_type === 'subject_group' ? 'subject_group_id' : 'class_section_id';
    const value = assignment.target_type === 'subject_group' ? assignment.subject_group?.id : assignment.class_section?.id;
    return value ? `?${key}=${value}` : '';
  }
  async function loadHomeworkItems() {
    if (!detail) return;
    try { homeworkItems = (await api.get(`/teach/homework${homeworkQuery()}`, schoolOptions(detail.assignment.school.id)))?.items || []; }
    catch (err: any) { homeworkListError = err?.message || $_('teach.homework.loadError'); }
  }
  function setHomeworkNotice(message: string) {
    homeworkNotice = message;
    if (homeworkNoticeTimer) clearTimeout(homeworkNoticeTimer);
    homeworkNoticeTimer = setTimeout(() => { homeworkNotice = null; homeworkNoticeTimer = null; }, 5000);
  }
  onDestroy(() => {
    if (homeworkNoticeTimer) clearTimeout(homeworkNoticeTimer);
    if (updatesNoticeTimer) clearTimeout(updatesNoticeTimer);
    clearUpdatePhotoObjectUrls();
  });

  function updatesQuery() {
    const assignment = detail?.assignment;
    if (!assignment) return '';
    const key = assignment.target_type === 'subject_group' ? 'subject_group_id' : 'class_section_id';
    const value = assignment.target_type === 'subject_group' ? assignment.subject_group?.id : assignment.class_section?.id;
    return value ? `?${key}=${value}` : '';
  }
  function updatePhotoPath(post: UpdatePost, photo: UpdatePhoto, variant: 'thumbnail' | 'full') {
    return protectedUpdatePhotoPath(post.id, photo.id, variant);
  }
  function updatePhotoKey(post: UpdatePost, photo: UpdatePhoto, variant: 'thumbnail' | 'full' = 'thumbnail') {
    return protectedUpdatePhotoKey(post.id, photo.id, variant);
  }
  function updatePhotoUrl(post: UpdatePost, photo: UpdatePhoto) {
    return updatePhotoObjectUrls[updatePhotoKey(post, photo)];
  }
  function updatePhotoLoaded(post: UpdatePost, photo: UpdatePhoto) {
    updatePhotoLoadStates = { ...updatePhotoLoadStates, [updatePhotoKey(post, photo)]: 'loaded' };
  }
  function updatePhotoFailed(post: UpdatePost, photo: UpdatePhoto) {
    updatePhotoLoadStates = { ...updatePhotoLoadStates, [updatePhotoKey(post, photo)]: 'failed' };
  }
  function clearUpdatePhotoObjectUrls() {
    protectedPhotoCache.clear();
    updatePhotoObjectUrls = {};
    updatePhotoLoadStates = {};
  }
  async function loadProtectedUpdatePhoto(post: UpdatePost, photo: UpdatePhoto, variant: 'thumbnail' | 'full') {
    if (!detail) return;
    const key = updatePhotoKey(post, photo, variant);
    if (updatePhotoObjectUrls[key]) return;
    updatePhotoLoadStates = { ...updatePhotoLoadStates, [key]: 'loading' };
    try {
      const objectUrl = await protectedPhotoCache.load(
        key,
        updatePhotoPath(post, photo, variant),
        detail.assignment.school.id,
        api.download
      );
      updatePhotoObjectUrls = { ...updatePhotoObjectUrls, [key]: objectUrl };
      updatePhotoLoadStates = { ...updatePhotoLoadStates, [key]: 'loaded' };
    } catch (err: any) {
      if (err instanceof ProtectedUpdatePhotoClearedError) return;
      // Deliberately omit credentials, filenames, and raw URLs from diagnostics.
      console.warn('[CHH] Protected update photo fetch failed', {
        category: variant === 'thumbnail' ? 'teacher-update-photo-thumbnail' : 'teacher-update-photo-full',
        status: typeof err?.status === 'number' ? err.status : 'network-or-media'
      });
      updatePhotoLoadStates = { ...updatePhotoLoadStates, [key]: 'failed' };
    }
  }
  async function openUpdatePhoto(post: UpdatePost, photo: UpdatePhoto) {
    const key = updatePhotoKey(post, photo, 'full');
    updatePhotoLightbox = { key, alt: photo.original_filename };
    await loadProtectedUpdatePhoto(post, photo, 'full');
  }
  async function loadUpdateItems() {
    if (!detail) return;
    try { updateItems = (await api.get(`/teach/updates${updatesQuery()}`, schoolOptions(detail.assignment.school.id)))?.items || []; updatesListError = null; }
    catch (err: any) { updatesListError = err?.message || $_('teach.updates.loadError'); }
  }
  function setUpdatesNotice(message: string) {
    updatesNotice = message;
    if (updatesNoticeTimer) clearTimeout(updatesNoticeTimer);
    updatesNoticeTimer = setTimeout(() => { updatesNotice = null; updatesNoticeTimer = null; }, 5000);
  }
  function resetUpdateForm() { updateBody = ''; updatePhotos = []; createdUpdateId = null; }
  function openUpdatesModal() { updatesError = null; updatesNotice = null; viewingUpdate = null; updateEditing = null; updatesMode = 'create'; updatesModalOpen = true; }
  function closeUpdatesModal() {
    if (updatesSaving) {
      updatesAbortController?.abort();
      setUpdatesNotice(createdUpdateId ? $_('teach.updates.cancelledAfterCreate') : $_('teach.updates.cancelled'));
    }
    updatesSaving = false; updatesAbortController = null; updatesModalOpen = false; updatesError = null; updateEditing = null; resetUpdateForm();
  }
  const allowedPhotoExt = new Set(['jpg', 'jpeg', 'png', 'webp', 'heic', 'heif']);
  const photoMimeExt: Record<string, string> = { 'image/jpeg': 'jpg', 'image/png': 'png', 'image/webp': 'webp', 'image/heic': 'heic', 'image/heif': 'heif' };
  function photoExt(file: File) { return file.name.split('.').pop()?.toLowerCase() || ''; }
  // Shared by web file inputs and native Camera results: rejected batches are
  // dropped whole; accepted photos accumulate into updatePhotos (max 5 total).
  function addUpdatePhotos(picked: File[]) {
    if (!picked.length) return;
    updatesError = null;
    if (updatePhotos.length + picked.length > 5) updatesError = $_('teach.updates.maxPhotos');
    else if (picked.some((file) => !allowedPhotoExt.has(photoExt(file)) && !photoMimeExt[file.type])) updatesError = $_('teach.updates.fileTypeError');
    else if (picked.some((file) => file.size > 50 * 1024 * 1024)) updatesError = $_('teach.updates.fileSizeError');
    if (updatesError) return;
    // Camera captures can arrive without a filename extension; the backend
    // validates by extension, so give those files one from their MIME type.
    updatePhotos = [...updatePhotos, ...picked.map((file) => allowedPhotoExt.has(photoExt(file)) ? file : new File([file], `photo-${Date.now()}-${Math.floor(Math.random() * 1000)}.${photoMimeExt[file.type]}`, { type: file.type }))];
  }
  function handleUpdateFiles(event: Event) {
    const input = event.target as HTMLInputElement;
    const picked = Array.from(input.files || []);
    input.value = '';
    addUpdatePhotos(picked);
  }
  function isCameraCancellation(error: unknown) {
    const message = String((error as { message?: string })?.message || error || '').toLowerCase();
    return message.includes('cancel') || message.includes('dismiss');
  }
  async function detectNativeAndroid() {
    const { Capacitor } = await import('@capacitor/core');
    isNativeAndroid = Capacitor.isNativePlatform() && Capacitor.getPlatform() === 'android';
  }
  async function pickNativeUpdatePhoto(source: 'camera' | 'photos') {
    if (updatePhotoPicking) return;
    updatePhotoPicking = true;
    updatesError = null;
    try {
      const { Camera, CameraResultType, CameraSource } = await import('@capacitor/camera');
      const photo = await Camera.getPhoto({
        source: source === 'camera' ? CameraSource.Camera : CameraSource.Photos,
        resultType: CameraResultType.Uri,
        quality: 85,
        allowEditing: false
      });
      if (!photo.webPath) throw new Error('Camera did not return a photo URI.');
      const response = await fetch(photo.webPath);
      if (!response.ok) throw new Error('Could not read the selected photo.');
      const extension = photo.format === 'png' ? 'png' : photo.format === 'webp' ? 'webp' : 'jpg';
      const mimeType = extension === 'jpg' ? 'image/jpeg' : `image/${extension}`;
      const blob = await response.blob();
      addUpdatePhotos([new File([blob], `photo-${Date.now()}.${extension}`, { type: mimeType })]);
    } catch (err) {
      if (!isCameraCancellation(err)) updatesError = $_('teach.updates.cameraError');
    } finally {
      updatePhotoPicking = false;
    }
  }
  function removeUpdatePhoto(index: number) { updatePhotos = updatePhotos.filter((_, i) => i !== index); }
  async function publishUpdate() {
    const assignment = detail?.assignment;
    if (!assignment || updatesSaving) return;
    const targetId = assignment.target_type === 'subject_group' ? assignment.subject_group?.id : assignment.class_section?.id;
    if (!targetId) return;
    const files = updatePhotos;
    if (files.length > 5) { updatesError = $_('teach.updates.maxPhotos'); return; }
    const controller = new AbortController(); updatesAbortController = controller;
    updatesSaving = true; updatesError = null; createdUpdateId = null;
    try {
      const created = await api.post('/teach/updates', {
        body: updateBody,
        audience_type: assignment.target_type,
        class_section_id: assignment.target_type === 'class_section' ? targetId : null,
        subject_group_id: assignment.target_type === 'subject_group' ? targetId : null
      }, { ...schoolOptions(assignment.school.id), signal: controller.signal });
      createdUpdateId = created.id;
      for (const file of files) {
        const formData = new FormData(); formData.append('file', file);
        await api.upload(`/teach/updates/${created.id}/photos`, formData, { ...schoolOptions(assignment.school.id), signal: controller.signal });
      }
      resetUpdateForm(); setUpdatesNotice($_('teach.updates.created')); await loadUpdateItems(); updatesMode = 'list'; updatesModalOpen = true;
    } catch (err: any) {
      if (createdUpdateId) updatesError = err?.name === 'AbortError' ? $_('teach.updates.cancelledAfterCreate') : $_('teach.updates.photoFailed');
      else updatesError = err?.name === 'AbortError' ? $_('teach.updates.cancelled') : err?.message || $_('teach.updates.saveError');
    } finally { updatesSaving = false; updatesAbortController = null; }
  }
  async function openUpdateDetail(post: UpdatePost) {
    if (!detail) return;
    try {
      clearUpdatePhotoObjectUrls();
      const loadedUpdate = await api.get(`/teach/updates/${post.id}`, schoolOptions(detail.assignment.school.id));
      viewingUpdate = loadedUpdate;
      updatesMode = 'list';
      void Promise.all(loadedUpdate.photos.map((photo: UpdatePhoto) => loadProtectedUpdatePhoto(loadedUpdate, photo, 'thumbnail')));
    }
    catch (err: any) { updatesListError = err?.message || $_('teach.updates.loadError'); }
  }
  function startEditUpdate(post: UpdatePost) { updateEditing = post; updatesError = null; updatesNotice = null; updateBody = post.body || ''; }
  function cancelEditUpdate() { updateEditing = null; updatesError = null; resetUpdateForm(); }
  async function saveUpdateEdit() {
    if (!detail || !updateEditing || updatesSaving) return;
    updatesSaving = true; updatesError = null;
    try {
      const updated = await api.patch(`/teach/updates/${updateEditing.id}`, { body: updateBody }, schoolOptions(detail.assignment.school.id));
      viewingUpdate = updated; updateEditing = null; setUpdatesNotice($_('teach.updates.updated'));
      resetUpdateForm(); await loadUpdateItems();
    } catch (err: any) {
      updatesError = err?.message || $_('teach.updates.updateError');
    } finally { updatesSaving = false; }
  }
  async function archiveUpdate(post: UpdatePost) {
    if (!detail) return;
    try { await api.delete(`/teach/updates/${post.id}`, schoolOptions(detail.assignment.school.id)); viewingUpdate = null; setUpdatesNotice($_('teach.updates.archived')); await loadUpdateItems(); }
    catch (err: any) { updatesListError = err?.message || $_('teach.updates.archiveError'); }
  }
  function openHomeworkModal() { homeworkError = null; homeworkNotice = null; viewingHomework = null; homeworkEditing = null; homeworkMode = 'create'; homeworkModalOpen = true; }
  function openHomeworkManage() { homeworkError = null; homeworkNotice = null; viewingHomework = null; homeworkEditing = null; homeworkMode = 'list'; homeworkModalOpen = true; }
  function resetHomeworkForm() { homeworkType = 'homework'; homeworkTitle = ''; homeworkBody = ''; homeworkDueAt = ''; homeworkFiles = null; homeworkLinks = []; createdHomeworkId = null; }
  function closeHomeworkModal() {
    if (homeworkSaving) {
      homeworkAbortController?.abort();
      setHomeworkNotice(createdHomeworkId ? $_('teach.homework.cancelledAfterCreate') : $_('teach.homework.cancelled'));
    }
    homeworkSaving = false; homeworkAbortController = null; homeworkModalOpen = false; homeworkError = null; homeworkEditing = null; resetHomeworkForm();
  }
  function handleHomeworkFiles(event: Event) {
    const input = event.target as HTMLInputElement;
    const files = Array.from(input.files || []);
    const allowed = new Set(['pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'txt', 'csv', 'jpg', 'jpeg', 'png', 'webp']);
    homeworkError = null;
    if (files.length > 5) homeworkError = $_('teach.homework.maxFiles');
    else if (files.some((file) => ['heic', 'heif'].includes(file.name.split('.').pop()?.toLowerCase() || ''))) homeworkError = $_('teach.homework.heicError');
    else if (files.some((file) => !allowed.has(file.name.split('.').pop()?.toLowerCase() || ''))) homeworkError = $_('teach.homework.fileTypeError');
    else if (files.some((file) => file.size > 10 * 1024 * 1024)) homeworkError = $_('teach.homework.fileSizeError');
    if (homeworkError) { input.value = ''; homeworkFiles = null; } else homeworkFiles = input.files;
  }
  function addHomeworkLink() { if (homeworkLinks.length < 5) homeworkLinks = [...homeworkLinks, { url: '', label: '' }]; }
  function removeHomeworkLink(index: number) { homeworkLinks = homeworkLinks.filter((_, i) => i !== index); }
  async function openHomeworkDetail(item: HomeworkItem) {
    if (!detail) return;
    try { viewingHomework = await api.get(`/teach/homework/${item.id}`, schoolOptions(detail.assignment.school.id)); homeworkMode = 'list'; }
    catch (err: any) { homeworkListError = err?.message || $_('teach.homework.loadError'); }
  }
  async function archiveHomework(item: HomeworkItem) {
    if (!detail) return;
    try { await api.delete(`/teach/homework/${item.id}`, schoolOptions(detail.assignment.school.id)); viewingHomework = null; setHomeworkNotice($_('teach.homework.archived')); await loadHomeworkItems(); }
    catch (err: any) { homeworkListError = err?.message || $_('teach.homework.archiveError'); }
  }

  function homeworkLinksValid(): boolean {
    for (const link of homeworkLinks.filter((row) => row.url.trim())) {
      try {
        const parsed = new URL(link.url);
        const host = parsed.hostname.toLowerCase();
        if (parsed.protocol !== 'https:' || host === 'localhost' || host.endsWith('.local') || host.endsWith('.internal') || /^(127\.|10\.|192\.168\.|169\.254\.)/.test(host)) throw new Error('unsafe');
      } catch { homeworkError = $_('teach.homework.linkError'); return false; }
    }
    return true;
  }
  function homeworkLinksPayload() {
    return homeworkLinks.filter((link) => link.url.trim()).map((link) => ({ url: link.url.trim(), label: link.label?.trim() || null }));
  }
  function toDatetimeLocal(iso?: string | null): string {
    if (!iso) return '';
    const d = new Date(iso);
    return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
  }
  function toDateInput(iso?: string | null): string { return toDatetimeLocal(iso).slice(0, 10); }
  function changeEventAllDay() {
    if (eventAllDay) { eventStartsAt = eventStartsAt.slice(0, 10); eventEndsAt = ''; }
    else if (eventStartsAt.length === 10) eventStartsAt = `${eventStartsAt}T00:00`;
  }
  function startEditHomework(item: HomeworkItem) {
    homeworkEditing = item; homeworkError = null; homeworkNotice = null;
    homeworkType = item.item_type; homeworkTitle = item.title; homeworkBody = item.body || '';
    homeworkDueAt = toDatetimeLocal(item.due_at);
    homeworkLinks = (item.resource_links || []).map((link) => ({ url: link.url, label: link.label || '' }));
  }
  function cancelEditHomework() { homeworkEditing = null; homeworkError = null; resetHomeworkForm(); }
  async function saveHomeworkEdit() {
    if (!detail || !homeworkEditing || homeworkSaving) return;
    homeworkError = null;
    if (!homeworkLinksValid()) return;
    homeworkSaving = true;
    try {
      const updated = await api.patch(`/teach/homework/${homeworkEditing.id}`, {
        item_type: homeworkType, title: homeworkTitle, body: homeworkBody,
        due_at: homeworkDueAt ? new Date(homeworkDueAt).toISOString() : null,
        resource_links: homeworkLinksPayload()
      }, schoolOptions(detail.assignment.school.id));
      viewingHomework = updated; homeworkEditing = null; setHomeworkNotice($_('teach.homework.updated'));
      resetHomeworkForm(); await loadHomeworkItems();
    } catch (err: any) {
      homeworkError = err?.message || $_('teach.homework.updateError');
    } finally { homeworkSaving = false; }
  }

  async function publishHomework() {
    const assignment = detail?.assignment;
    if (!assignment || homeworkSaving) return;
    const targetId = assignment.target_type === 'subject_group' ? assignment.subject_group?.id : assignment.class_section?.id;
    if (!targetId) return;
    const files = Array.from(homeworkFiles || []);
    if (files.length > 5) { homeworkError = $_('teach.homework.maxFiles'); return; }
    if (!homeworkLinksValid()) return;
    const controller = new AbortController(); homeworkAbortController = controller;
    homeworkSaving = true; homeworkError = null; createdHomeworkId = null;
    try {
      const created = await api.post('/teach/homework', {
        item_type: homeworkType, title: homeworkTitle, body: homeworkBody,
        audience_type: assignment.target_type,
        class_section_id: assignment.target_type === 'class_section' ? targetId : null,
        subject_group_id: assignment.target_type === 'subject_group' ? targetId : null,
        due_at: homeworkDueAt ? new Date(homeworkDueAt).toISOString() : null,
        resource_links: homeworkLinksPayload()
      }, { ...schoolOptions(assignment.school.id), signal: controller.signal });
      createdHomeworkId = created.id;
      for (const file of files) {
        const formData = new FormData(); formData.append('file', file);
        await api.upload(`/teach/homework/${created.id}/attachments`, formData, { ...schoolOptions(assignment.school.id), signal: controller.signal });
      }
      resetHomeworkForm(); setHomeworkNotice($_('teach.homework.created')); homeworkModalOpen = false; await loadHomeworkItems();
    } catch (err: any) {
      if (createdHomeworkId) homeworkError = err?.name === 'AbortError' ? $_('teach.homework.cancelledAfterCreate') : $_('teach.homework.attachmentFailed');
      else homeworkError = err?.name === 'AbortError' ? $_('teach.homework.cancelled') : err?.message || $_('teach.homework.saveError');
    } finally { homeworkSaving = false; homeworkAbortController = null; }
  }

  function formatEventDate(item: CalendarItem) {
    const options: Intl.DateTimeFormatOptions = item.all_day ? { dateStyle: 'medium' } : { dateStyle: 'medium', timeStyle: 'short' };
    let label = new Intl.DateTimeFormat(undefined, options).format(new Date(item.starts_at));
    if (item.ends_at && !item.all_day) label += ` – ${new Intl.DateTimeFormat(undefined, { timeStyle: 'short' }).format(new Date(item.ends_at))}`;
    return label;
  }
  async function loadCalendarItems() {
    if (!detail) return;
    try {
      calendarItems = (await api.get(`/teach/calendar${homeworkQuery()}`, schoolOptions(detail.assignment.school.id)))?.items || [];
      calendarError = null;
    } catch (err: any) {
      calendarError = err?.message || $_('calendar.loadError');
    }
  }
  async function openCalendarModal() {
    calendarError = null; calendarNotice = null; editingEvent = null; calendarMode = 'list'; calendarModalOpen = true;
    await loadCalendarItems();
  }
  function closeCalendarModal() {
    if (calendarSaving) return;
    calendarModalOpen = false; editingEvent = null;
  }
  function openEventCreate() {
    eventTitle = ''; eventBody = ''; eventStartsAt = ''; eventEndsAt = ''; eventAllDay = true;
    editingEvent = null; calendarError = null; calendarMode = 'create';
  }
  function openEventEdit(item: CalendarItem) {
    editingEvent = item; eventTitle = item.title; eventBody = item.body || '';
    eventStartsAt = item.all_day ? toDateInput(item.starts_at) : toDatetimeLocal(item.starts_at); eventEndsAt = item.all_day ? '' : toDatetimeLocal(item.ends_at); eventAllDay = item.all_day;
    calendarError = null; calendarMode = 'edit';
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
    const assignment = detail?.assignment;
    if (!assignment || calendarSaving || !eventStartsAt) return;
    calendarSaving = true; calendarError = null;
    try {
      if (editingEvent) {
        await api.patch(`/school/calendar/${editingEvent.event_id}`, eventPayload(), schoolOptions(assignment.school.id));
        calendarNotice = $_('calendar.updated');
      } else {
        const targetId = assignment.target_type === 'subject_group' ? assignment.subject_group?.id : assignment.class_section?.id;
        if (!targetId) return;
        await api.post('/school/calendar', {
          ...eventPayload(),
          audience_type: assignment.target_type,
          class_section_id: assignment.target_type === 'class_section' ? targetId : null,
          subject_group_id: assignment.target_type === 'subject_group' ? targetId : null
        }, schoolOptions(assignment.school.id));
        calendarNotice = $_('calendar.created');
      }
      editingEvent = null; calendarMode = 'list'; await loadCalendarItems();
    } catch (err: any) {
      calendarError = err?.message || $_('calendar.saveError');
    } finally { calendarSaving = false; }
  }
  async function archiveEvent(item: CalendarItem) {
    if (!detail || calendarSaving || item.kind !== 'event') return;
    calendarSaving = true; calendarError = null;
    try {
      await api.delete(`/school/calendar/${item.event_id}`, schoolOptions(detail.assignment.school.id));
      calendarNotice = $_('calendar.archived');
      await loadCalendarItems();
    } catch (err: any) {
      calendarError = err?.message || $_('calendar.archiveError');
    } finally { calendarSaving = false; }
  }

  onMount(async () => {
    void detectNativeAndroid().catch(() => { isNativeAndroid = false; });
    try {
      detail = await api.get(`/teach/assignments/${$page.params.id}`);
      await Promise.all([loadHomeworkItems(), loadQuickActions()]);
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

      <div class="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <button type="button" class="flex min-h-20 min-w-0 items-center gap-3 rounded-2xl border border-violet-100 bg-white p-4 text-left shadow-sm hover:border-violet-300" onclick={openPointsModal}>
          <span class="shrink-0 rounded-xl bg-violet-100 p-2 text-violet-700"><Star size={21} aria-hidden="true" /></span>
          <span class="min-w-0 flex-1"><strong class="block break-words text-sm leading-tight text-slate-900">{$_('teach.classDetail.actions.points')}</strong><small class="block break-words text-xs font-semibold text-violet-600">{$_('teach.points.open')}</small></span>
        </button>
        <button type="button" class="flex min-h-20 min-w-0 items-center gap-3 rounded-2xl border border-sky-100 bg-white p-4 text-left shadow-sm hover:border-sky-300" onclick={openUpdatesModal}>
          <span class="shrink-0 rounded-xl bg-sky-100 p-2 text-sky-700"><Camera size={21} aria-hidden="true" /></span>
          <span class="min-w-0 flex-1"><strong class="block break-words text-sm leading-tight text-slate-900">{$_('teach.classDetail.actions.updates')}</strong><small class="block break-words text-xs font-semibold text-sky-600">{$_('teach.points.open')}</small></span>
        </button>
        <button type="button" class="flex min-h-20 min-w-0 items-center gap-3 rounded-2xl border border-amber-100 bg-white p-4 text-left shadow-sm hover:border-amber-300" onclick={openHomeworkModal}>
          <span class="shrink-0 rounded-xl bg-amber-100 p-2 text-amber-700"><BookOpen size={21} aria-hidden="true" /></span>
          <span class="min-w-0 flex-1"><strong class="block break-words text-sm leading-tight text-slate-900">{$_('teach.classDetail.actions.homework')}</strong><small class="block break-words text-xs font-semibold text-amber-700">{$_('teach.points.open')}</small></span>
        </button>
        <button type="button" class="flex min-h-20 min-w-0 items-center gap-3 rounded-2xl border border-indigo-100 bg-white p-4 text-left shadow-sm hover:border-indigo-300" onclick={openCalendarModal}>
          <span class="shrink-0 rounded-xl bg-indigo-100 p-2 text-indigo-700"><CalendarDays size={21} aria-hidden="true" /></span>
          <span class="min-w-0 flex-1"><strong class="block break-words text-sm leading-tight text-slate-900">{$_('calendar.title')}</strong><small class="block break-words text-xs font-semibold text-indigo-600">{$_('teach.points.open')}</small></span>
        </button>
        <button type="button" class="flex min-h-20 min-w-0 items-center gap-3 rounded-2xl border border-emerald-100 bg-white p-4 text-left shadow-sm hover:border-emerald-200" onclick={openAnnouncementModal}>
          <span class="shrink-0 rounded-xl bg-emerald-100 p-2 text-emerald-700"><Megaphone size={21} aria-hidden="true" /></span>
          <span class="min-w-0 flex-1"><strong class="block break-words text-sm leading-tight text-slate-900">{$_('teach.classDetail.actions.announcements')}</strong><small class="block break-words text-xs font-semibold text-emerald-600">{$_('teach.points.open')}</small></span>
        </button>
      </div>

      {#if announcementPublished}
        <div class="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm font-semibold text-emerald-700">{$_('teach.announcements.created')}</div>
      {/if}
      {#if homeworkNotice}<div class="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm font-semibold text-amber-800">{homeworkNotice}</div>{/if}
      {#if updatesNotice && !updatesModalOpen}<div class="mt-4 rounded-lg border border-sky-200 bg-sky-50 p-3 text-sm font-semibold text-sky-800">{updatesNotice}</div>{/if}
      {#if pointsSuccess}<div class="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm font-semibold text-emerald-700">{pointsSuccess}</div>{/if}
      {#if quickAwardNotice}<div class="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm font-semibold text-emerald-700" role="status">{quickAwardNotice}</div>{/if}

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
            <button type="button" class="group min-w-0 overflow-hidden rounded-2xl border border-slate-200 bg-white p-3 text-center shadow-sm transition hover:-translate-y-0.5 hover:border-violet-300 hover:shadow-md focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-violet-300/70 sm:p-4" aria-label={$_('teach.quickAward.openForStudent', { values: { student: student.display_name } })} onclick={(event) => openQuickAward(student, event.currentTarget)}>
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
            </button>
          {/each}
        </div>
      {/if}
    {/if}
  </div>
</section>

{#if quickAwardStudent && detail}
  <div class="fixed inset-0 z-[60] flex items-end justify-center bg-slate-950/45 p-2 backdrop-blur-[2px] sm:items-center sm:p-5" role="presentation" onclick={(event) => { if (event.target === event.currentTarget) closeQuickAward(); }}>
    <div bind:this={quickAwardDialog} tabindex="-1" class="max-h-[calc(100vh-1rem)] w-full max-w-3xl overflow-y-auto rounded-2xl bg-white p-2 shadow-2xl outline-none sm:max-h-[94vh] sm:rounded-3xl sm:p-7" role="dialog" aria-modal="true" aria-labelledby="quick-award-title" onkeydown={quickAwardKeydown}>
      <div class="flex items-start justify-between gap-2 sm:gap-4">
        <div class="flex min-w-0 items-center gap-2 sm:gap-3">
          <div class="flex h-11 w-11 shrink-0 items-center justify-center overflow-hidden rounded-xl bg-gradient-to-br from-violet-100 to-sky-100 text-sm font-black text-hero ring-2 ring-violet-50 sm:h-14 sm:w-14 sm:rounded-2xl sm:text-lg sm:ring-4">
            {#if quickAwardStudent.avatar_url_256 && !failedImages[quickAwardStudent.id]}
              <img src={quickAwardStudent.avatar_url_256} alt="" class="h-full w-full object-contain p-1" />
            {:else}{initialsFromStudentName(quickAwardStudent)}{/if}
          </div>
          <div class="min-w-0"><p class="text-[10px] font-black uppercase tracking-[0.08em] text-violet-600 sm:text-xs sm:tracking-[0.16em]">{$_('teach.quickAward.title')}</p><h2 id="quick-award-title" class="truncate text-lg font-black text-slate-900 sm:text-2xl">{quickAwardStudent.display_name}</h2><p class="mt-0.5 truncate text-xs font-semibold text-slate-500 sm:mt-1 sm:text-sm">{$_('teach.quickAward.context')}: {classTitle()} · {quickAwardStudent.points_total > 0 ? '+' : ''}{quickAwardStudent.points_total} {$_('teach.points.pts')}</p></div>
        </div>
        <button type="button" class="rounded-xl border border-slate-200 px-3 py-2 text-sm font-black text-slate-600 transition hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-violet-200 disabled:opacity-50" disabled={quickAwardSaving} onclick={closeQuickAward}>{$_('teach.points.close')}</button>
      </div>

      <div class="sr-only" aria-live="polite">{quickAwardError || quickAwardNotice || ''}</div>
      {#if quickAwardError}<div class="mt-5 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-bold text-red-800" role="alert">{quickAwardError}</div>{/if}

      {#if quickActionsLoading}
        <div class="mt-6 rounded-2xl bg-slate-50 p-8 text-center text-sm font-bold text-slate-500">{$_('common.loading')}</div>
      {:else if quickActionsError && !quickActions}
        <div class="mt-6 rounded-2xl border border-red-200 bg-red-50 p-5 text-center"><p class="text-sm font-bold text-red-800">{quickActionsError}</p><button type="button" class="mt-3 rounded-xl bg-white px-4 py-2 text-sm font-black text-violet-700 shadow-sm ring-1 ring-violet-100" onclick={loadQuickActions}>{$_('teach.quickAward.retry')}</button></div>
      {:else if quickActions}
        {#if quickAwardMode === 'quick' && quickActions.quick_actions.positive.length === 0 && quickActions.quick_actions.needs_work.length === 0}
          <p class="mt-6 rounded-2xl border border-violet-100 bg-violet-50 px-4 py-3 text-sm font-bold text-violet-800">{$_('teach.quickAward.noQuickActions')}</p>
        {/if}
        <div class="mt-3 grid grid-cols-2 gap-1 sm:mt-6 sm:gap-4">
          {#each ['positive', 'needs_work'] as type}
            {@const isPositive = type === 'positive'}
            {@const otherMode = isPositive ? 'other_positive' : 'other_needs_work'}
            {@const showingOther = quickAwardMode === otherMode}
            {@const actions = showingOther ? quickActions.other_actions[type as 'positive' | 'needs_work'] : quickActions.quick_actions[type as 'positive' | 'needs_work']}
            <section class={`flex min-w-0 flex-col rounded-2xl border p-1.5 sm:p-5 ${isPositive ? 'border-emerald-200 bg-emerald-50/70' : 'border-orange-200 bg-orange-50/70'}`}>
              <div class="flex items-start justify-between gap-1 sm:items-center sm:gap-3"><h3 class={`text-[10px] font-black uppercase leading-tight tracking-[0.04em] sm:text-sm sm:tracking-[0.13em] ${isPositive ? 'text-emerald-800' : 'text-orange-800'}`}><span class="sm:hidden">{isPositive ? $_('teach.points.positive') : $_('teach.points.needsWork')}</span><span class="hidden sm:inline">{isPositive ? $_('teach.quickAward.positive') : $_('teach.quickAward.needsWork')}</span></h3>{#if showingOther}<button type="button" class={`text-xs font-black leading-tight underline underline-offset-4 sm:text-sm ${isPositive ? 'text-emerald-800' : 'text-orange-800'}`} disabled={quickAwardSaving} onclick={() => quickAwardMode = 'quick'}>{$_('teach.quickAward.back')}</button>{/if}</div>
              <div class="mt-1.5 flex flex-1 flex-col gap-1 sm:mt-3 sm:gap-2">
                {#if actions.length}
                  {#each actions as action}
                    <button type="button" class={`grid min-h-11 w-full grid-cols-[minmax(0,1fr)_auto] items-center gap-1 rounded-xl border bg-white px-1.5 py-2 text-left shadow-sm transition focus-visible:outline-none focus-visible:ring-4 disabled:cursor-wait disabled:opacity-60 sm:min-h-14 sm:gap-3 sm:px-4 sm:py-3 ${isPositive ? 'border-emerald-200 text-emerald-950 hover:border-emerald-400 hover:shadow-md focus-visible:ring-emerald-200' : 'border-orange-200 text-orange-950 hover:border-orange-400 hover:shadow-md focus-visible:ring-orange-200'}`} disabled={quickAwardSaving} title={action.label} aria-label={actionLabel(action, quickAwardStudent)} onclick={() => submitQuickAward(action)}><span class="min-w-0 break-normal text-[13px] font-bold leading-[1.15] sm:truncate sm:whitespace-nowrap sm:text-base sm:font-black">{quickAwardSaving ? $_('teach.quickAward.saving') : action.label}</span><span class={`shrink-0 rounded-md px-1.5 py-0.5 text-[11px] font-black sm:rounded-lg sm:px-2 sm:py-1 sm:text-sm ${isPositive ? 'bg-emerald-100 text-emerald-800' : 'bg-orange-100 text-orange-800'}`}>{action.points_value > 0 ? '+' : ''}{action.points_value}</span></button>
                  {/each}
                {:else if showingOther}
                  <p class="rounded-xl bg-white/70 px-3 py-4 text-sm font-semibold text-slate-500">{$_('teach.quickAward.noOther')}</p>
                {/if}
                {#if !showingOther && quickActions.other_actions[type as 'positive' | 'needs_work'].length}
                  <button type="button" class={`mt-auto min-h-11 rounded-xl border border-dashed bg-white/70 px-2 py-2 text-xs font-black leading-tight transition hover:bg-white focus-visible:outline-none focus-visible:ring-4 disabled:opacity-60 sm:min-h-12 sm:px-4 sm:py-3 sm:text-sm ${isPositive ? 'border-emerald-300 text-emerald-800 focus-visible:ring-emerald-200' : 'border-orange-300 text-orange-800 focus-visible:ring-orange-200'}`} disabled={quickAwardSaving} onclick={() => quickAwardMode = otherMode}>{isPositive ? $_('teach.quickAward.otherPositive') : $_('teach.quickAward.otherNeedsWork')}</button>
                {/if}
              </div>
            </section>
          {/each}
        </div>
        {#if quickActions.quick_actions.positive.length === 0 && quickActions.quick_actions.needs_work.length === 0 && quickActions.other_actions.positive.length === 0 && quickActions.other_actions.needs_work.length === 0}
          <p class="mt-4 text-center text-sm font-semibold text-slate-500">{$_('teach.quickAward.noBehaviours')}</p>
        {/if}
      {/if}
    </div>
  </div>
{/if}

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

{#if homeworkModalOpen && detail}
  <div class="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/50 sm:items-center sm:p-4" role="dialog" aria-modal="true" aria-labelledby="homework-title">
    <div class="max-h-[94vh] w-full max-w-2xl overflow-y-auto overflow-x-hidden rounded-t-2xl bg-white p-5 shadow-xl sm:rounded-2xl sm:p-6">
      <div class="flex items-start justify-between gap-3"><h2 id="homework-title" class="text-2xl font-black text-slate-900">{$_('teach.homework.title')}</h2><button type="button" class="btn-secondary rounded-lg px-3 py-2" onclick={closeHomeworkModal}>{$_('teach.homework.close')}</button></div>
      {#if homeworkError}<div class="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-700">{homeworkError}</div>{/if}
      {#if homeworkMode === 'list' && homeworkNotice}<div class="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm font-semibold text-amber-800">{homeworkNotice}</div>{/if}
      <div class="mt-5 grid grid-cols-2 gap-2 rounded-xl bg-slate-100 p-1"><button type="button" class={`rounded-lg px-3 py-2 text-sm font-black ${homeworkMode === 'create' ? 'bg-white text-amber-800 shadow-sm' : 'text-slate-600'}`} onclick={() => { homeworkMode = 'create'; viewingHomework = null; homeworkEditing = null; }}>{$_('teach.homework.createTab')}</button><button type="button" class={`rounded-lg px-3 py-2 text-sm font-black ${homeworkMode === 'list' ? 'bg-white text-amber-800 shadow-sm' : 'text-slate-600'}`} onclick={() => { homeworkMode = 'list'; viewingHomework = null; homeworkEditing = null; loadHomeworkItems(); }}>{$_('teach.homework.previousTab')}</button></div>
      {#if homeworkMode === 'list' && homeworkEditing}
        <form class="mt-5 grid gap-4" onsubmit={(event) => { event.preventDefault(); saveHomeworkEdit(); }}>
          <label class="grid gap-1 text-sm font-bold text-slate-700">{$_('teach.homework.type')}<select class="rounded-lg border border-slate-200 px-3 py-2" bind:value={homeworkType}><option value="homework">{$_('teach.homework.types.homework')}</option><option value="diary">{$_('teach.homework.types.diary')}</option></select></label>
          <label class="grid gap-1 text-sm font-bold text-slate-700">{$_('teach.homework.itemTitle')}<input class="rounded-lg border border-slate-200 px-3 py-2" required maxlength="160" bind:value={homeworkTitle} /></label>
          <label class="grid gap-1 text-sm font-bold text-slate-700">{$_('teach.homework.body')}<textarea class="min-h-32 rounded-lg border border-slate-200 px-3 py-2" required maxlength="10000" bind:value={homeworkBody}></textarea></label>
          <label class="grid gap-1 text-sm font-bold text-slate-700">{$_('teach.homework.due')}<input class="rounded-lg border border-slate-200 px-3 py-2" type="datetime-local" bind:value={homeworkDueAt} /></label>
          <div><div class="flex flex-col items-start gap-2 sm:flex-row sm:items-center sm:justify-between"><span class="break-words text-sm font-bold text-slate-700">{$_('teach.homework.resourceLinks')}</span><button type="button" class="shrink-0 text-sm font-bold text-hero disabled:opacity-50" disabled={homeworkLinks.length >= 5} onclick={addHomeworkLink}>{$_('teach.homework.addLink')}</button></div>{#each homeworkLinks as link, index}<div class="mt-2 grid min-w-0 gap-2 rounded-xl bg-slate-50 p-3 sm:grid-cols-[1fr_2fr_auto]"><input class="min-w-0 rounded-lg border border-slate-200 px-3 py-2 text-sm" maxlength="160" placeholder={$_('teach.homework.linkLabel')} bind:value={link.label} /><input class="min-w-0 rounded-lg border border-slate-200 px-3 py-2 text-sm" type="url" required maxlength="2048" placeholder="https://www.youtube.com/watch?v=…" bind:value={link.url} /><button type="button" class="rounded-lg border border-slate-200 px-3 py-2 text-sm font-bold" onclick={() => removeHomeworkLink(index)}>{$_('teach.homework.removeLink')}</button></div>{/each}</div>
          <div class="flex gap-3"><button class="btn-hero rounded-lg px-4 py-2" type="submit" disabled={homeworkSaving}>{homeworkSaving ? $_('teach.homework.saving') : $_('teach.homework.saveChanges')}</button><button class="btn-secondary rounded-lg px-4 py-2" type="button" onclick={cancelEditHomework}>{$_('teach.homework.cancel')}</button></div>
        </form>
      {:else if homeworkMode === 'list' && !viewingHomework}
        {#if homeworkListError}<p class="mt-4 text-sm font-semibold text-red-700">{homeworkListError}</p>{:else if homeworkItems.length === 0}<p class="mt-5 text-sm text-slate-500">{$_('teach.homework.empty')}</p>{:else}<div class="mt-4 max-h-[58vh] divide-y divide-slate-100 overflow-y-auto rounded-xl border border-slate-200">{#each homeworkItems.slice(0, 20) as item}<div class="flex flex-col gap-2 p-4 sm:flex-row sm:items-center sm:justify-between"><button type="button" class="min-w-0 text-left" onclick={() => openHomeworkDetail(item)}><p class="truncate font-bold text-slate-900">{item.title}</p><p class="mt-1 text-xs text-slate-500">{item.item_type === 'homework' ? $_('teach.homework.types.homework') : $_('teach.homework.types.diary')}{item.due_at ? ` · ${new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(item.due_at))}` : ''} · {$_('teach.homework.attachmentCount', { values: { count: item.attachment_count } })} · {$_('teach.homework.resourceCount', { values: { count: item.resource_links?.length || 0 } })}{item.status === 'archived' ? ` · ${$_('teach.homework.archived')}` : ''}</p></button><div class="flex shrink-0 gap-2"><button type="button" class="btn-secondary rounded-lg px-3 py-2 text-sm" onclick={() => openHomeworkDetail(item)}>{$_('teach.homework.view')}</button>{#if item.status === 'active'}<button type="button" class="rounded-lg border border-sky-200 px-3 py-2 text-sm font-bold text-sky-800" onclick={() => startEditHomework(item)}>{$_('teach.homework.edit')}</button><button type="button" class="rounded-lg border border-amber-200 px-3 py-2 text-sm font-bold text-amber-800" onclick={() => archiveHomework(item)}>{$_('teach.homework.archive')}</button>{/if}</div></div>{/each}</div>{/if}
      {:else if homeworkMode === 'list' && viewingHomework}
        <div class="mt-5"><button type="button" class="text-sm font-bold text-hero" onclick={() => viewingHomework = null}>{$_('teach.homework.back')}</button><h3 class="mt-3 break-words text-2xl font-black text-slate-900">{viewingHomework.title}</h3><p class="mt-1 text-xs font-bold uppercase text-amber-700">{viewingHomework.item_type === 'homework' ? $_('teach.homework.types.homework') : $_('teach.homework.types.diary')}</p>{#if viewingHomework.due_at}<p class="mt-4 rounded-xl bg-amber-50 p-3 text-sm font-bold text-amber-800">{$_('teach.homework.due')}: {new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(viewingHomework.due_at))}</p>{/if}<div class="mt-5 whitespace-pre-wrap break-words text-slate-700">{viewingHomework.body}</div>{#if viewingHomework.resource_links?.length}<div class="mt-6"><h4 class="text-sm font-black uppercase text-slate-500">{$_('teach.homework.resourceLinks')}</h4><div class="mt-2 grid gap-2">{#each viewingHomework.resource_links as link}<a class="break-all rounded-xl border border-sky-100 bg-sky-50 p-3 text-sm font-bold text-sky-800" href={link.url} target="_blank" rel="noopener noreferrer">{link.label || link.url}</a>{/each}</div></div>{/if}<div class="mt-6 flex justify-end gap-3">{#if viewingHomework.status === 'active'}<button type="button" class="rounded-lg border border-sky-200 px-4 py-2 font-bold text-sky-800" onclick={() => startEditHomework(viewingHomework!)}>{$_('teach.homework.edit')}</button><button type="button" class="rounded-lg border border-amber-200 px-4 py-2 font-bold text-amber-800" onclick={() => archiveHomework(viewingHomework!)}>{$_('teach.homework.archive')}</button>{/if}</div></div>
      {:else}
      <form class="mt-5 grid gap-4" onsubmit={(event) => { event.preventDefault(); publishHomework(); }}>
        <p class="rounded-xl bg-amber-50 px-4 py-3 text-sm font-semibold text-slate-700">{$_('teach.homework.audience')}: <strong>{classTitle()}</strong></p>
        <label class="grid gap-1 text-sm font-bold text-slate-700">{$_('teach.homework.type')}<select class="rounded-lg border border-slate-200 px-3 py-2" bind:value={homeworkType}><option value="homework">{$_('teach.homework.types.homework')}</option><option value="diary">{$_('teach.homework.types.diary')}</option></select></label>
        <label class="grid gap-1 text-sm font-bold text-slate-700">{$_('teach.homework.itemTitle')}<input class="rounded-lg border border-slate-200 px-3 py-2" required maxlength="160" bind:value={homeworkTitle} /></label>
        <label class="grid gap-1 text-sm font-bold text-slate-700">{$_('teach.homework.body')}<textarea class="min-h-32 rounded-lg border border-slate-200 px-3 py-2" required maxlength="10000" bind:value={homeworkBody}></textarea></label>
        <label class="grid gap-1 text-sm font-bold text-slate-700">{$_('teach.homework.due')}<input class="rounded-lg border border-slate-200 px-3 py-2" type="datetime-local" bind:value={homeworkDueAt} /></label>
        <div><div class="flex flex-col items-start gap-2 sm:flex-row sm:items-center sm:justify-between"><span class="break-words text-sm font-bold text-slate-700">{$_('teach.homework.resourceLinks')}</span><button type="button" class="shrink-0 text-sm font-bold text-hero disabled:opacity-50" disabled={homeworkLinks.length >= 5} onclick={addHomeworkLink}>{$_('teach.homework.addLink')}</button></div>{#each homeworkLinks as link, index}<div class="mt-2 grid min-w-0 gap-2 rounded-xl bg-slate-50 p-3 sm:grid-cols-[1fr_2fr_auto]"><input class="min-w-0 rounded-lg border border-slate-200 px-3 py-2 text-sm" maxlength="160" placeholder={$_('teach.homework.linkLabel')} bind:value={link.label} /><input class="min-w-0 rounded-lg border border-slate-200 px-3 py-2 text-sm" type="url" required maxlength="2048" placeholder="https://www.youtube.com/watch?v=…" bind:value={link.url} /><button type="button" class="rounded-lg border border-slate-200 px-3 py-2 text-sm font-bold" onclick={() => removeHomeworkLink(index)}>{$_('teach.homework.removeLink')}</button></div>{/each}</div>
        <label class="grid gap-1 text-sm font-bold text-slate-700">{$_('teach.homework.attachments')}<input class="rounded-lg border border-slate-200 px-3 py-2 text-sm" type="file" multiple accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt,.csv,.jpg,.jpeg,.png,.webp" onchange={handleHomeworkFiles} /></label>
        <p class="text-xs text-slate-500">{$_('teach.homework.attachmentRules')}</p>
        <div class="flex gap-3"><button class="btn-hero rounded-lg px-4 py-2" type="submit" disabled={homeworkSaving || !!homeworkError || createdHomeworkId !== null}>{homeworkSaving ? $_('teach.homework.saving') : $_('teach.homework.create')}</button><button class="btn-secondary rounded-lg px-4 py-2" type="button" onclick={closeHomeworkModal}>{homeworkSaving ? $_('teach.homework.cancelUpload') : $_('teach.homework.cancel')}</button></div>
      </form>
      {/if}
    </div>
  </div>
{/if}

{#if updatesModalOpen && detail}
  <div class="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/50 sm:items-center sm:p-4" role="dialog" aria-modal="true" aria-labelledby="updates-title">
    <div class="max-h-[94vh] w-full max-w-2xl overflow-y-auto overflow-x-hidden rounded-t-2xl bg-white p-5 shadow-xl sm:rounded-2xl sm:p-6">
      <div class="flex items-start justify-between gap-3"><h2 id="updates-title" class="text-2xl font-black text-slate-900">{$_('teach.updates.title')}</h2><button type="button" class="btn-secondary rounded-lg px-3 py-2" onclick={closeUpdatesModal}>{$_('teach.updates.close')}</button></div>
      {#if updatesError}<div class="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-700">{updatesError}</div>{/if}
      {#if updatesMode === 'list' && updatesNotice}<div class="mt-4 rounded-lg border border-sky-200 bg-sky-50 p-3 text-sm font-semibold text-sky-800">{updatesNotice}</div>{/if}
      <div class="mt-5 grid grid-cols-2 gap-2 rounded-xl bg-slate-100 p-1"><button type="button" class={`rounded-lg px-3 py-2 text-sm font-black ${updatesMode === 'create' ? 'bg-white text-sky-800 shadow-sm' : 'text-slate-600'}`} onclick={() => { updatesMode = 'create'; viewingUpdate = null; updateEditing = null; }}>{$_('teach.updates.createTab')}</button><button type="button" class={`rounded-lg px-3 py-2 text-sm font-black ${updatesMode === 'list' ? 'bg-white text-sky-800 shadow-sm' : 'text-slate-600'}`} onclick={() => { updatesMode = 'list'; viewingUpdate = null; updateEditing = null; loadUpdateItems(); }}>{$_('teach.updates.previousTab')}</button></div>
      {#if updatesMode === 'list' && updateEditing}
        <form class="mt-5 grid gap-4" onsubmit={(event) => { event.preventDefault(); saveUpdateEdit(); }}>
          <label class="grid gap-1 text-sm font-bold text-slate-700">{$_('teach.updates.body')}<textarea class="min-h-32 rounded-lg border border-slate-200 px-3 py-2" required maxlength="10000" bind:value={updateBody}></textarea></label>
          <div class="flex gap-3"><button class="btn-hero rounded-lg px-4 py-2" type="submit" disabled={updatesSaving}>{updatesSaving ? $_('teach.updates.saving') : $_('teach.updates.saveChanges')}</button><button class="btn-secondary rounded-lg px-4 py-2" type="button" onclick={cancelEditUpdate}>{$_('teach.updates.cancel')}</button></div>
        </form>
      {:else if updatesMode === 'list' && !viewingUpdate}
        {#if updatesListError}<p class="mt-4 text-sm font-semibold text-red-700">{updatesListError}</p>{:else if updateItems.length === 0}<p class="mt-5 text-sm text-slate-500">{$_('teach.updates.empty')}</p>{:else}<div class="mt-4 max-h-[58vh] divide-y divide-slate-100 overflow-y-auto rounded-xl border border-slate-200">{#each updateItems.slice(0, 20) as item}<div class="flex flex-col gap-2 p-4 sm:flex-row sm:items-center sm:justify-between"><button type="button" class="min-w-0 text-left" onclick={() => openUpdateDetail(item)}><p class="line-clamp-2 break-words font-bold text-slate-900">{item.body}</p><p class="mt-1 text-xs text-slate-500">{item.created_at ? new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(item.created_at)) : ''} · {$_('teach.updates.photoCount', { values: { count: item.photo_count } })}{item.status === 'archived' ? ` · ${$_('teach.updates.archived')}` : ''}</p></button><div class="flex shrink-0 gap-2"><button type="button" class="btn-secondary rounded-lg px-3 py-2 text-sm" onclick={() => openUpdateDetail(item)}>{$_('teach.updates.view')}</button>{#if item.status === 'active'}<button type="button" class="rounded-lg border border-sky-200 px-3 py-2 text-sm font-bold text-sky-800" onclick={() => startEditUpdate(item)}>{$_('teach.updates.edit')}</button><button type="button" class="rounded-lg border border-amber-200 px-3 py-2 text-sm font-bold text-amber-800" onclick={() => archiveUpdate(item)}>{$_('teach.updates.archive')}</button>{/if}</div></div>{/each}</div>{/if}
      {:else if updatesMode === 'list' && viewingUpdate}
        <div class="mt-5">
          <button type="button" class="text-sm font-bold text-hero" onclick={() => viewingUpdate = null}>{$_('teach.updates.back')}</button>
          <p class="mt-3 text-xs text-slate-500">{viewingUpdate.created_at ? new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(viewingUpdate.created_at)) : ''}</p>
          <div class="mt-3 whitespace-pre-wrap break-words text-slate-700">{viewingUpdate.body}</div>
          {#if viewingUpdate.photos?.length}
            <div class="mt-5 grid grid-cols-2 gap-2 sm:grid-cols-3">
              {#each viewingUpdate.photos as photo (photo.id)}
                {@const photoState = updatePhotoLoadStates[updatePhotoKey(viewingUpdate, photo)]}
                {@const photoUrl = updatePhotoUrl(viewingUpdate, photo)}
                <button type="button" class="relative aspect-square overflow-hidden rounded-xl border border-slate-200 bg-slate-100" onclick={() => openUpdatePhoto(viewingUpdate!, photo)}>
                  {#if photoState === 'failed'}
                    <p class="absolute inset-0 flex items-center justify-center p-2 text-center text-xs font-semibold text-slate-500">{$_('teach.updates.photoLoadError')}</p>
                  {:else if photoState !== 'loaded'}
                    <p class="absolute inset-0 flex items-center justify-center p-2 text-center text-xs font-semibold text-slate-500">{$_('teach.updates.photoLoading')}</p>
                  {/if}
                  {#if photoUrl}<img src={photoUrl} alt={photo.original_filename} loading="lazy" class={`h-full w-full object-cover transition-opacity ${photoState === 'loaded' ? 'opacity-100' : 'opacity-0'}`} onload={() => updatePhotoLoaded(viewingUpdate!, photo)} onerror={() => updatePhotoFailed(viewingUpdate!, photo)} />{/if}
                </button>
              {/each}
            </div>
          {:else}
            <p class="mt-5 text-sm text-slate-500">{$_('teach.updates.noPhotos')}</p>
          {/if}
          <div class="mt-6 flex justify-end gap-3">{#if viewingUpdate.status === 'active'}<button type="button" class="rounded-lg border border-sky-200 px-4 py-2 font-bold text-sky-800" onclick={() => startEditUpdate(viewingUpdate!)}>{$_('teach.updates.edit')}</button><button type="button" class="rounded-lg border border-amber-200 px-4 py-2 font-bold text-amber-800" onclick={() => archiveUpdate(viewingUpdate!)}>{$_('teach.updates.archive')}</button>{/if}</div>
        </div>
      {:else}
      <form class="mt-5 grid gap-4" onsubmit={(event) => { event.preventDefault(); publishUpdate(); }}>
        <p class="rounded-xl bg-sky-50 px-4 py-3 text-sm font-semibold text-slate-700">{$_('teach.updates.audience')}: <strong>{classTitle()}</strong></p>
        <label class="grid gap-1 text-sm font-bold text-slate-700">{$_('teach.updates.body')}<textarea class="min-h-32 rounded-lg border border-slate-200 px-3 py-2" required maxlength="10000" bind:value={updateBody}></textarea></label>
        <div class="grid gap-2">
          <span class="text-sm font-bold text-slate-700">{$_('teach.updates.photos')}</span>
          <div class="flex flex-wrap gap-2">
            {#if isNativeAndroid}
              <button type="button" class="btn-secondary rounded-lg px-4 py-2 text-sm disabled:opacity-50" disabled={updatePhotoPicking} onclick={() => pickNativeUpdatePhoto('photos')}>{$_('teach.updates.uploadPhotos')}</button>
              <button type="button" class="btn-secondary rounded-lg px-4 py-2 text-sm disabled:opacity-50" disabled={updatePhotoPicking} onclick={() => pickNativeUpdatePhoto('camera')}>{$_('teach.updates.takePhoto')}</button>
            {:else}
              <label class="btn-secondary cursor-pointer rounded-lg px-4 py-2 text-sm">{$_('teach.updates.uploadPhotos')}<input class="hidden" type="file" multiple accept=".jpg,.jpeg,.png,.webp,.heic,.heif,image/jpeg,image/png,image/webp,image/heic,image/heif" onchange={handleUpdateFiles} /></label>
              <label class="btn-secondary cursor-pointer rounded-lg px-4 py-2 text-sm">{$_('teach.updates.takePhoto')}<input class="hidden" type="file" accept="image/jpeg,image/png,image/webp,image/heic,image/heif" capture="environment" onchange={handleUpdateFiles} /></label>
            {/if}
          </div>
          {#if updatePhotos.length}
            <ul class="grid gap-1">
              {#each updatePhotos as photo, index}
                <li class="flex items-center justify-between gap-2 rounded-lg bg-slate-50 px-3 py-2 text-sm">
                  <span class="min-w-0 truncate font-semibold text-slate-700">{photo.name}</span>
                  <button type="button" class="shrink-0 text-sm font-bold text-slate-500 hover:text-red-600" onclick={() => removeUpdatePhoto(index)}>{$_('teach.updates.removePhoto')}</button>
                </li>
              {/each}
            </ul>
          {/if}
        </div>
        <p class="text-xs text-slate-500">{$_('teach.updates.photoRules')}</p>
        <div class="flex gap-3"><button class="btn-hero rounded-lg px-4 py-2" type="submit" disabled={updatesSaving || createdUpdateId !== null}>{updatesSaving ? $_('teach.updates.saving') : $_('teach.updates.create')}</button><button class="btn-secondary rounded-lg px-4 py-2" type="button" onclick={closeUpdatesModal}>{updatesSaving ? $_('teach.updates.cancelUpload') : $_('teach.updates.cancel')}</button></div>
      </form>
      {/if}
    </div>
  </div>
{/if}

{#if updatePhotoLightbox}
  {@const lightboxSource = updatePhotoObjectUrls[updatePhotoLightbox.key]}
  {@const lightboxState = updatePhotoLoadStates[updatePhotoLightbox.key]}
  <div class="fixed inset-0 z-[60] flex items-center justify-center bg-slate-950/90 p-4" role="dialog" aria-modal="true" aria-label={updatePhotoLightbox.alt}>
    <button type="button" class="absolute end-4 top-4 rounded-lg bg-white/10 px-4 py-2 font-bold text-white" onclick={() => updatePhotoLightbox = null}>{$_('teach.updates.close')}</button>
    {#if lightboxState === 'failed'}
      <p class="rounded-xl bg-white/10 p-4 text-center text-sm font-semibold text-white">{$_('teach.updates.photoLoadError')}</p>
    {:else if !lightboxSource}
      <p class="rounded-xl bg-white/10 p-4 text-center text-sm font-semibold text-white">{$_('teach.updates.photoLoading')}</p>
    {:else}
      <img src={lightboxSource} alt={updatePhotoLightbox.alt} class="max-h-full max-w-full rounded-xl object-contain" />
    {/if}
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

{#if calendarModalOpen && detail}
  <div class="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/50 sm:items-center sm:p-4" role="dialog" aria-modal="true" aria-labelledby="class-calendar-title">
    <div class="max-h-[94vh] w-full max-w-2xl overflow-y-auto overflow-x-hidden rounded-t-2xl bg-white p-5 shadow-xl sm:rounded-2xl sm:p-6">
      <div class="flex items-start justify-between gap-3">
        <div class="min-w-0"><h2 id="class-calendar-title" class="text-2xl font-black text-slate-900">{$_('calendar.classCalendar')}</h2><p class="mt-1 truncate text-sm font-semibold text-slate-500">{classTitle()}</p></div>
        <button type="button" class="btn-secondary shrink-0 rounded-lg px-3 py-2" disabled={calendarSaving} onclick={closeCalendarModal}>{$_('calendar.close')}</button>
      </div>
      {#if calendarError}<div class="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-700">{calendarError}</div>{/if}
      {#if calendarMode === 'list'}
        {#if calendarNotice}<div class="mt-4 rounded-lg border border-indigo-200 bg-indigo-50 p-3 text-sm font-semibold text-indigo-800">{calendarNotice}</div>{/if}
        <button type="button" class="btn-hero mt-4 rounded-lg px-4 py-2" onclick={openEventCreate}>{$_('calendar.create')}</button>
        <p class="mt-4 text-xs font-black uppercase tracking-wide text-slate-500">{$_('calendar.upcoming')}</p>
        <div class="mt-2 max-h-[58vh] divide-y divide-slate-100 overflow-y-auto rounded-xl border border-slate-200">
          {#each calendarItems as item (item.id)}
            <div class="flex flex-col gap-2 p-4 sm:flex-row sm:items-center sm:justify-between">
              <div class="min-w-0">
                <p class="mt-1 break-words font-bold text-slate-900">{item.title}</p>
                <p class="mt-1 text-sm text-slate-500">{formatEventDate(item)}</p>
                {#if item.body}<p class="mt-1 line-clamp-2 break-words text-sm text-slate-600">{item.body}</p>{/if}
              </div>
              {#if item.kind === 'event' && item.can_manage}
                <div class="flex shrink-0 gap-2">
                  <button type="button" class="rounded-lg border border-indigo-200 px-3 py-2 text-sm font-bold text-indigo-800" disabled={calendarSaving} onclick={() => openEventEdit(item)}>{$_('calendar.edit')}</button>
                  <button type="button" class="rounded-lg border border-amber-200 px-3 py-2 text-sm font-bold text-amber-800" disabled={calendarSaving} onclick={() => archiveEvent(item)}>{$_('calendar.archive')}</button>
                </div>
              {/if}
            </div>
          {:else}
            <p class="p-4 text-sm text-slate-500">{$_('calendar.empty')}</p>
          {/each}
        </div>
      {:else}
        <form class="mt-5 grid gap-4" onsubmit={(event) => { event.preventDefault(); saveEvent(); }}>
          <p class="rounded-xl bg-indigo-50 px-4 py-3 text-sm font-semibold text-slate-700">{$_('calendar.audience')}: <strong>{classTitle()}</strong></p>
          <label class="grid gap-1 text-sm font-bold text-slate-700">{$_('calendar.titleField')}<input class="rounded-lg border border-slate-200 px-3 py-2" required maxlength="160" bind:value={eventTitle} /></label>
          <label class="grid gap-1 text-sm font-bold text-slate-700">{$_('calendar.details')}<textarea class="min-h-24 rounded-lg border border-slate-200 px-3 py-2" maxlength="10000" bind:value={eventBody}></textarea></label>
          <label class="flex items-center gap-2 text-sm font-bold text-slate-700"><input type="checkbox" bind:checked={eventAllDay} onchange={changeEventAllDay} />{$_('calendar.allDay')}</label>
          {#if eventAllDay}
            <label class="grid max-w-sm gap-1 text-sm font-bold text-slate-700">{$_('calendar.date')}<input class="rounded-lg border border-slate-200 px-3 py-2" type="date" required bind:value={eventStartsAt} /></label>
          {:else}
            <div class="grid gap-3 sm:grid-cols-2"><label class="grid gap-1 text-sm font-bold text-slate-700">{$_('calendar.starts')}<input class="rounded-lg border border-slate-200 px-3 py-2" type="datetime-local" required bind:value={eventStartsAt} /></label><label class="grid gap-1 text-sm font-bold text-slate-700">{$_('calendar.ends')}<input class="rounded-lg border border-slate-200 px-3 py-2" type="datetime-local" bind:value={eventEndsAt} /></label></div>
          {/if}
          <div class="flex gap-3">
            <button class="btn-hero rounded-lg px-4 py-2" type="submit" disabled={calendarSaving}>{calendarSaving ? $_('calendar.saving') : $_('calendar.save')}</button>
            <button class="btn-secondary rounded-lg px-4 py-2" type="button" disabled={calendarSaving} onclick={() => { calendarMode = 'list'; editingEvent = null; }}>{$_('calendar.cancel')}</button>
          </div>
        </form>
      {/if}
    </div>
  </div>
{/if}
