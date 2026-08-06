<script lang="ts">
  import { beforeNavigate } from '$app/navigation';
  import { onDestroy, onMount, tick } from 'svelte';
  import { _, locale } from 'svelte-i18n';
  import { api } from '$lib/api';
  import EntitySearch from '$lib/components/EntitySearch.svelte';

  type Membership = { school_id: number; school_name: string; role: string };
  type Row = {
    id: number;
    code: string;
    name: string;
    name_ar?: string | null;
    status: string;
    branch_campus_id?: number | null;
    academic_year_id?: number | null;
    grade_level_id?: number | null;
  };
  type Student = {
    id: number;
    external_ref?: string | null;
    first_name: string;
    last_name: string;
    preferred_name?: string | null;
    display_name: string;
    name_ar?: string | null;
    date_of_birth?: string | null;
    gender?: string | null;
    status: string;
    current_class_section?: Row | null;
  };
  type StudentPage = {
    items: Student[];
    page: number;
    page_size: number;
    total: number;
    pages: number;
  };
  type Enrolment = {
    id: number;
    class_section_id?: number | null;
    subject_group_id?: number | null;
    valid_from: string;
    valid_to?: string | null;
    is_open: boolean;
    class_section?: Row | null;
    subject_group?: Row | null;
  };
  type GuardianContact = {
    id: number;
    external_ref?: string | null;
    name?: string | null;
    relationship?: string | null;
    email?: string | null;
    phone?: string | null;
    is_primary: boolean;
    is_emergency: boolean;
    is_active: boolean;
    source: 'import' | 'manual';
    access_status: string;
    status: string;
  };
  type GuardianInvite = {
    id: number;
    student_guardian_contact_id?: number | null;
    guardian_name?: string | null;
    relationship?: string | null;
    display_code_last4?: string | null;
    status: string;
    expires_at?: string | null;
    created_at?: string | null;
    code?: string;
    join_url?: string;
  };
  type GuardianLink = {
    id: number;
    user_email?: string | null;
    display_name?: string | null;
    relationship?: string | null;
    status: 'active' | 'revoked';
    created_at?: string | null;
  };
  type Guardians = { contacts: GuardianContact[]; invites: GuardianInvite[]; links: GuardianLink[] };
  type FhhInvite = {
    id: number;
    student_guardian_contact_id?: number | null;
    recipient_email?: string | null;
    display_code_last4?: string | null;
    expires_at?: string | null;
    consumed_at?: string | null;
    revoked_at?: string | null;
    created_at?: string | null;
    send_status?: 'not_requested' | 'pending' | 'sent' | 'failed';
    sent_at?: string | null;
    code?: string;
    related_student_count?: number;
    warning?: string | null;
  };
  type FhhState = {
    invites: FhhInvite[];
    link_status: 'active' | 'revoked' | 'none';
    linked_at?: string | null;
    revoked_at?: string | null;
    link_history_count: number;
    link_history: { status: 'active' | 'revoked'; linked_at?: string | null; revoked_at?: string | null }[];
  };
  type GuardianDraft = {
    key: number;
    external_ref: string;
    name: string;
    relationship: string;
    email: string;
    phone: string;
    is_primary: boolean;
    is_emergency: boolean;
    is_active: boolean;
  };

  const detailTabs = ['details', 'guardians', 'placement', 'access', 'fhh', 'history'] as const;
  type DetailTab = (typeof detailTabs)[number];
  const STUDENT_PAGE_SIZE = 25;

  let loading = $state(true);
  let allowed = $state(false);
  let schoolId = $state<number | null>(null);
  let schoolName = $state('');
  let error = $state('');
  let notice = $state('');
  let toast = $state<{ kind: 'error' | 'success'; message: string } | null>(null);
  let toastTimer: ReturnType<typeof setTimeout> | null = null;
  let saving = $state(false);
  let view = $state<'list' | 'add' | 'detail'>('list');
  let activeDetailTab = $state<DetailTab>('details');

  let branches = $state<Row[]>([]);
  let years = $state<Row[]>([]);
  let levels = $state<Row[]>([]);
  let sections = $state<Row[]>([]);
  let students = $state<Student[]>([]);
  let search = $state('');
  let sectionFilter = $state('');
  let studentPage = $state(1);
  let studentTotal = $state(0);
  let studentPages = $state(0);
  let selectedStudent = $state<Student | null>(null);
  let enrolments = $state<Enrolment[]>([]);
  let guardians = $state<Guardians | null>(null);
  let fhh = $state<FhhState | null>(null);

  let studentForm = $state(emptyStudent());
  let addBranchId = $state('');
  let addLevelId = $state('');
  let addSectionId = $state('');
  let guardianDrafts = $state<GuardianDraft[]>([emptyGuardian(1)]);
  let nextGuardianKey = 2;
  let fieldErrors = $state<Record<string, string>>({});

  let guardianForm = $state(emptyGuardian(0));
  let editingGuardianId = $state<number | null>(null);
  let moveSectionId = $state('');
  let generatedGuardianInvite = $state<GuardianInvite | null>(null);
  let generatedFhhInvite = $state<FhhInvite | null>(null);

  function emptyStudent() {
    return {
      external_ref: '',
      first_name: '',
      last_name: '',
      preferred_name: '',
      name_ar: '',
      date_of_birth: '',
      gender: '',
      status: 'active'
    };
  }

  function emptyGuardian(key: number): GuardianDraft {
    return {
      key,
      external_ref: '',
      name: '',
      relationship: '',
      email: '',
      phone: '',
      is_primary: false,
      is_emergency: false,
      is_active: true
    };
  }

  function schoolOptions(): RequestInit {
    return { headers: { 'X-School-Id': String(schoolId) } };
  }

  function showError(message: string) {
    error = message;
    notice = '';
    showToast('error', message);
  }

  function showNotice(message: string) {
    notice = message;
    error = '';
    showToast('success', message);
  }

  function clearToast() {
    if (toastTimer !== null) clearTimeout(toastTimer);
    toastTimer = null;
    toast = null;
  }

  function showToast(kind: 'error' | 'success', message: string) {
    clearToast();
    toast = { kind, message };
    toastTimer = setTimeout(() => {
      toast = null;
      toastTimer = null;
    }, kind === 'error' ? 6000 : 4000);
  }

  beforeNavigate(clearToast);
  onDestroy(clearToast);

  function rowName(rows: Row[], id?: number | null) {
    const row = rows.find((item) => item.id === id);
    return row ? localizedRowName(row) : '—';
  }

  function localizedRowName(row: Row) {
    return $locale === 'ar' && row.name_ar ? row.name_ar : row.name;
  }

  function relationshipLabel(value?: string | null) {
    if (!value) return '';
    return $locale === 'ar' && ['mother', 'father', 'guardian', 'other'].includes(value)
      ? $_(`school.guardians.relationships.${value}`)
      : value;
  }

  function guardianStatus(value: string) {
    return $locale === 'ar' ? $_(`school.guardians.status.${value}`) : value;
  }

  function studentStatus(value: string) {
    return $locale === 'ar' ? $_(`school.${value}`) : value;
  }

  function sectionContext(section?: Row | null) {
    if (!section) return '—';
    return [rowName(branches, section.branch_campus_id), rowName(levels, section.grade_level_id), localizedRowName(section)]
      .filter(Boolean)
      .join(' · ');
  }

  function currentClass(student: Student) {
    return student.current_class_section ? sectionContext(student.current_class_section) : $_('school.students.notEnrolled');
  }

  function formatDate(value?: string | null) {
    if (!value) return '—';
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString($locale === 'ar' ? 'ar' : undefined);
  }

  function studentPayload() {
    return {
      external_ref: studentForm.external_ref.trim() || null,
      first_name: studentForm.first_name.trim(),
      last_name: studentForm.last_name.trim(),
      preferred_name: studentForm.preferred_name.trim() || null,
      name_ar: studentForm.name_ar.trim() || null,
      date_of_birth: studentForm.date_of_birth || null,
      gender: studentForm.gender || null,
      status: studentForm.status
    };
  }

  function guardianPayload(draft: GuardianDraft) {
    return {
      external_ref: draft.external_ref.trim() || null,
      name: draft.name.trim(),
      relationship: draft.relationship || null,
      email: draft.email.trim() || null,
      phone: draft.phone.trim() || null,
      is_primary: draft.is_primary,
      is_emergency: draft.is_emergency,
      is_active: draft.is_active
    };
  }

  function emailProblem(value: string) {
    const email = value.trim();
    if (!email) return '';
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) return $_('school.studentAdmin.emailInvalid');
    if (/@[^@]+\.test$/i.test(email)) return $_('school.studentAdmin.emailTestInvalid');
    return '';
  }

  async function focusFirstError() {
    await tick();
    const key = Object.keys(fieldErrors)[0];
    const target = key ? document.querySelector<HTMLElement>(`[data-field="${CSS.escape(key)}"]`) : null;
    target?.focus();
    target?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  function parseServerGuardianError(message: string) {
    const match = message.match(/guardian(?:s)?\s+(\d+).*email/i);
    if (match) {
      const index = Number(match[1]) - 1;
      const draft = guardianDrafts[index];
      if (draft) fieldErrors[`guardian-${draft.key}-email`] = message;
    } else if (/email/i.test(message) && editingGuardianId !== null) {
      fieldErrors['guardian-edit-email'] = message;
    }
  }

  function studentListUrl(studentId?: number) {
    const query = new URLSearchParams();
    if (search.trim()) query.set('search', search.trim());
    if (sectionFilter) query.set('class_section_id', sectionFilter);
    if (studentPage > 1) query.set('page', String(studentPage));
    if (studentId) query.set('student', String(studentId));
    return `/school/students${query.size ? `?${query.toString()}` : ''}`;
  }

  function syncStudentUrl(
    studentId?: number,
    historyMode: 'push' | 'replace' | 'none' = 'replace'
  ) {
    if (historyMode === 'none') return;
    const target = studentListUrl(studentId);
    if (target === `${window.location.pathname}${window.location.search}`) return;
    const state = {
      ...(window.history.state || {}),
      chhStudentDetailEntry: historyMode === 'push' && Boolean(studentId)
    };
    window.history[historyMode === 'push' ? 'pushState' : 'replaceState'](state, '', target);
  }

  function firstStudentNumber() {
    return studentTotal ? (studentPage - 1) * STUDENT_PAGE_SIZE + 1 : 0;
  }

  function lastStudentNumber() {
    return Math.min(studentPage * STUDENT_PAGE_SIZE, studentTotal);
  }

  async function loadStudents({
    resetPage = false,
    syncUrl = true,
    historyMode = 'replace'
  }: {
    resetPage?: boolean;
    syncUrl?: boolean;
    historyMode?: 'push' | 'replace';
  } = {}) {
    if (!schoolId) return;
    if (resetPage) studentPage = 1;
    const query = new URLSearchParams();
    if (search.trim()) query.set('search', search.trim());
    if (sectionFilter) query.set('class_section_id', sectionFilter);
    query.set('page', String(studentPage));
    query.set('page_size', String(STUDENT_PAGE_SIZE));
    const result: StudentPage = await api.get(`/school/students?${query.toString()}`, schoolOptions());
    if (result.pages > 0 && studentPage > result.pages) {
      studentPage = result.pages;
      await loadStudents({ syncUrl, historyMode });
      return;
    }
    students = result.items;
    studentPage = result.pages ? result.page : 1;
    studentTotal = result.total;
    studentPages = result.pages;
    if (syncUrl) syncStudentUrl(undefined, historyMode);
  }

  async function applyFilters() {
    await loadStudents({ resetPage: true, historyMode: 'push' });
  }

  async function clearSearch() {
    search = '';
    sectionFilter = '';
    await loadStudents({ resetPage: true, historyMode: 'push' });
  }

  async function changeStudentPage(nextPage: number) {
    if (nextPage < 1 || nextPage > studentPages || nextPage === studentPage) return;
    studentPage = nextPage;
    await loadStudents({ historyMode: 'push' });
    document.getElementById('student-records')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  async function restoreStudentUrl() {
    const requestedUrl = new URL(window.location.href);
    search = requestedUrl.searchParams.get('search') || '';
    sectionFilter = requestedUrl.searchParams.get('class_section_id') || '';
    const requestedPage = Number(requestedUrl.searchParams.get('page'));
    studentPage = Number.isInteger(requestedPage) && requestedPage > 0 ? requestedPage : 1;
    const requestedId = Number(requestedUrl.searchParams.get('student'));
    if (sectionFilter && !sections.some((section) => section.id === Number(sectionFilter) && section.status !== 'archived')) {
      sectionFilter = '';
    }
    await loadStudents({ syncUrl: false });
    if (Number.isInteger(requestedId) && requestedId > 0) {
      try {
        const student = await api.get(`/school/students/${requestedId}`, schoolOptions());
        await openStudent(student, 'none');
        return;
      } catch (err: any) {
        if (err?.status !== 404) throw err;
      }
    }
    view = 'list';
    selectedStudent = null;
    activeDetailTab = 'details';
  }

  async function init() {
    try {
      const me = await api.get('/me/v2');
      const membership = (me?.memberships || []).find((item: Membership) => item.role === 'school_admin');
      if (!membership) return;
      schoolId = membership.school_id;
      schoolName = membership.school_name;
      allowed = true;
      [branches, years, levels, sections] = await Promise.all([
        api.get('/school/branches', schoolOptions()),
        api.get('/school/academic-years', schoolOptions()),
        api.get('/school/grade-levels', schoolOptions()),
        api.get('/school/class-sections', schoolOptions())
      ]);
      await restoreStudentUrl();
      syncStudentUrl(selectedStudent?.id, 'replace');
    } catch (err: any) {
      if (err?.status === 401) {
        window.location.href = `/login?returnTo=${encodeURIComponent('/school/students')}`;
        return;
      }
      showError(err?.message || $_('school.loadError'));
    } finally {
      loading = false;
    }
  }

  function openAdd() {
    view = 'add';
    studentForm = emptyStudent();
    addBranchId = '';
    addLevelId = '';
    addSectionId = '';
    guardianDrafts = [emptyGuardian(1)];
    nextGuardianKey = 2;
    fieldErrors = {};
    error = '';
    notice = '';
  }

  function returnToList() {
    if (view === 'detail' && window.history.state?.chhStudentDetailEntry) {
      window.history.back();
      return;
    }
    view = 'list';
    selectedStudent = null;
    activeDetailTab = 'details';
    syncStudentUrl(undefined, 'replace');
  }

  function addGuardianDraft() {
    guardianDrafts = [...guardianDrafts, emptyGuardian(nextGuardianKey++)];
  }

  function removeGuardianDraft(key: number) {
    guardianDrafts = guardianDrafts.filter((item) => item.key !== key);
  }

  function filteredAddSections() {
    return sections.filter(
      (section) =>
        (!addBranchId || section.branch_campus_id === Number(addBranchId)) &&
        (!addLevelId || section.grade_level_id === Number(addLevelId)) &&
        section.status !== 'archived'
    );
  }

  function validateAdd() {
    const errors: Record<string, string> = {};
    if (!studentForm.external_ref.trim()) errors.student_id = $_('school.studentAdmin.studentIdRequired');
    if (!studentForm.first_name.trim()) errors.first_name = $_('school.validation.firstNameRequired');
    if (!studentForm.last_name.trim()) errors.last_name = $_('school.validation.lastNameRequired');
    if (!addBranchId) errors.branch = $_('school.studentAdmin.branchRequired');
    if (!addLevelId) errors.grade = $_('school.studentAdmin.gradeRequired');
    if (!addSectionId) errors.section = $_('school.validation.sectionRequired');
    guardianDrafts.forEach((draft) => {
      const populated = Boolean(
        draft.name.trim() || draft.external_ref.trim() || draft.relationship || draft.email.trim() || draft.phone.trim()
      );
      if (populated && !draft.name.trim()) errors[`guardian-${draft.key}-name`] = $_('school.studentAdmin.guardianNameRequired');
      const emailError = emailProblem(draft.email);
      if (emailError) errors[`guardian-${draft.key}-email`] = emailError;
    });
    fieldErrors = errors;
    if (Object.keys(errors).length) {
      showError($_('school.studentAdmin.fixErrors'));
      void focusFirstError();
      return false;
    }
    return true;
  }

  async function createCompleteStudent() {
    if (!schoolId || !validateAdd()) return;
    saving = true;
    fieldErrors = {};
    try {
      const populatedGuardians = guardianDrafts.filter((draft) =>
        Boolean(draft.name.trim() || draft.external_ref.trim() || draft.relationship || draft.email.trim() || draft.phone.trim())
      );
      const result = await api.post(
        '/school/students/complete',
        {
          student: studentPayload(),
          class_section_id: Number(addSectionId),
          guardians: populatedGuardians.map(guardianPayload)
        },
        schoolOptions()
      );
      showNotice($_('school.studentAdmin.completeCreated'));
      await loadStudents();
      const student = students.find((item) => item.id === result.student.id) || result.student;
      await openStudent(student);
    } catch (err: any) {
      const message = err?.message || $_('school.students.saveError');
      parseServerGuardianError(message);
      showError(message);
      await focusFirstError();
    } finally {
      saving = false;
    }
  }

  async function openStudent(
    student: Student,
    historyMode: 'push' | 'replace' | 'none' = 'push'
  ) {
    selectedStudent = student;
    studentForm = {
      external_ref: student.external_ref || '',
      first_name: student.first_name,
      last_name: student.last_name,
      preferred_name: student.preferred_name || '',
      name_ar: student.name_ar || '',
      date_of_birth: student.date_of_birth || '',
      gender: student.gender || '',
      status: student.status
    };
    view = 'detail';
    activeDetailTab = 'details';
    fieldErrors = {};
    generatedGuardianInvite = null;
    generatedFhhInvite = null;
    syncStudentUrl(student.id, historyMode);
    await Promise.all([loadEnrolments(), loadGuardians(), loadFhh()]);
  }

  async function reloadSelectedStudent() {
    const id = selectedStudent?.id;
    if (!id) return;
    const refreshed = await api.get(`/school/students/${id}`, schoolOptions());
    selectedStudent = refreshed;
    students = students.map((item) => (item.id === id ? refreshed : item));
  }

  async function loadEnrolments() {
    if (!selectedStudent) return;
    enrolments = await api.get(`/school/students/${selectedStudent.id}/enrolments`, schoolOptions());
  }

  async function loadGuardians() {
    if (!selectedStudent) return;
    guardians = await api.get(`/school/students/${selectedStudent.id}/guardian-invites`, schoolOptions());
  }

  async function loadFhh() {
    if (!selectedStudent) return;
    fhh = await api.get(`/school/students/${selectedStudent.id}/fhh-invites`, schoolOptions());
  }

  async function saveStudentDetails() {
    if (!selectedStudent) return;
    const errors: Record<string, string> = {};
    if (!studentForm.first_name.trim()) errors['detail-first-name'] = $_('school.validation.firstNameRequired');
    if (!studentForm.last_name.trim()) errors['detail-last-name'] = $_('school.validation.lastNameRequired');
    fieldErrors = errors;
    if (Object.keys(errors).length) {
      showError($_('school.studentAdmin.fixErrors'));
      await focusFirstError();
      return;
    }
    saving = true;
    try {
      selectedStudent = await api.put(`/school/students/${selectedStudent.id}`, studentPayload(), schoolOptions());
      await reloadSelectedStudent();
      showNotice($_('school.students.updated'));
    } catch (err: any) {
      showError(err?.message || $_('school.students.saveError'));
    } finally {
      saving = false;
    }
  }

  function editGuardian(contact: GuardianContact) {
    editingGuardianId = contact.id;
    guardianForm = {
      key: 0,
      external_ref: contact.external_ref || '',
      name: contact.name || '',
      relationship: contact.relationship || '',
      email: contact.email || '',
      phone: contact.phone || '',
      is_primary: contact.is_primary,
      is_emergency: contact.is_emergency,
      is_active: contact.is_active
    };
    fieldErrors = {};
  }

  function resetGuardianForm() {
    editingGuardianId = null;
    guardianForm = emptyGuardian(0);
    fieldErrors = {};
  }

  async function saveGuardian() {
    if (!selectedStudent) return;
    const errors: Record<string, string> = {};
    if (!guardianForm.name.trim()) errors['guardian-edit-name'] = $_('school.studentAdmin.guardianNameRequired');
    const emailError = emailProblem(guardianForm.email);
    if (emailError) errors['guardian-edit-email'] = emailError;
    fieldErrors = errors;
    if (Object.keys(errors).length) {
      showError($_('school.studentAdmin.fixErrors'));
      await focusFirstError();
      return;
    }
    saving = true;
    try {
      if (editingGuardianId) {
        await api.put(`/school/guardian-contacts/${editingGuardianId}`, guardianPayload(guardianForm), schoolOptions());
      } else {
        await api.post(
          `/school/students/${selectedStudent.id}/guardian-contacts`,
          guardianPayload(guardianForm),
          schoolOptions()
        );
      }
      showNotice(editingGuardianId ? $_('school.guardians.contactUpdated') : $_('school.guardians.contactCreated'));
      resetGuardianForm();
      await loadGuardians();
    } catch (err: any) {
      const message = err?.message || $_('school.guardians.contactSaveError');
      parseServerGuardianError(message);
      showError(message);
      await focusFirstError();
    } finally {
      saving = false;
    }
  }

  async function toggleGuardian(contact: GuardianContact) {
    if (contact.is_active && !confirm($_('school.guardians.inactivateConfirm'))) return;
    try {
      await api.put(
        `/school/guardian-contacts/${contact.id}`,
        {
          external_ref: contact.external_ref || null,
          name: contact.name || '',
          relationship: contact.relationship || null,
          email: contact.email || null,
          phone: contact.phone || null,
          is_primary: contact.is_primary,
          is_emergency: contact.is_emergency,
          is_active: !contact.is_active
        },
        schoolOptions()
      );
      showNotice(contact.is_active ? $_('school.guardians.contactInactivated') : $_('school.guardians.contactActivated'));
      await loadGuardians();
    } catch (err: any) {
      showError(err?.message || $_('school.guardians.contactSaveError'));
    }
  }

  function activeInvite(contactId: number) {
    return guardians?.invites.find(
      (invite) => invite.student_guardian_contact_id === contactId && invite.status === 'active'
    );
  }

  async function generateGuardianCode(contactId: number) {
    if (!selectedStudent) return;
    try {
      generatedGuardianInvite = await api.post(
        `/school/students/${selectedStudent.id}/guardian-invites`,
        { contact_id: contactId },
        schoolOptions()
      );
      showNotice($_('school.guardians.generated'));
      await loadGuardians();
    } catch (err: any) {
      showError(err?.message || $_('school.guardians.generateError'));
    }
  }

  async function revokeGuardianInvite(id: number) {
    if (!confirm($_('school.guardians.revokeConfirm'))) return;
    try {
      await api.post(`/school/guardian-invites/${id}/revoke`, {}, schoolOptions());
      showNotice($_('school.guardians.revoked'));
      await loadGuardians();
    } catch (err: any) {
      showError(err?.message || $_('school.guardians.revokeError'));
    }
  }

  async function revokeGuardianLink(id: number) {
    if (!confirm($_('school.guardians.revokeLinkConfirm'))) return;
    try {
      await api.post(`/school/guardian-links/${id}/revoke`, {}, schoolOptions());
      showNotice($_('school.guardians.linkRevoked'));
      await loadGuardians();
    } catch (err: any) {
      showError(err?.message || $_('school.guardians.revokeLinkError'));
    }
  }

  async function moveStudent() {
    if (!selectedStudent || !moveSectionId) {
      fieldErrors = { move: $_('school.validation.sectionRequired') };
      await focusFirstError();
      return;
    }
    if (!confirm($_('school.students.moveConfirm'))) return;
    saving = true;
    try {
      await api.post(
        `/school/students/${selectedStudent.id}/move-section`,
        { class_section_id: Number(moveSectionId) },
        schoolOptions()
      );
      moveSectionId = '';
      await Promise.all([loadEnrolments(), reloadSelectedStudent()]);
      showNotice($_('school.students.moved'));
    } catch (err: any) {
      showError(err?.message || $_('school.students.enrolmentError'));
    } finally {
      saving = false;
    }
  }

  function fhhInviteStatus(invite: FhhInvite) {
    if (invite.revoked_at) return 'revoked';
    if (invite.consumed_at) return 'consumed';
    if (invite.expires_at && new Date(invite.expires_at).getTime() <= Date.now()) return 'expired';
    return 'active';
  }

  function currentFhhGuardianInvite(contactId: number) {
    return fhh?.invites.find(
      (invite) =>
        invite.student_guardian_contact_id === contactId &&
        fhhInviteStatus(invite) === 'active'
    );
  }

  async function emailFhhGuardianInvite(contact: GuardianContact) {
    if (!selectedStudent || !contact.email) return;
    saving = true;
    try {
      const result: FhhInvite = await api.post(
        `/school/students/${selectedStudent.id}/fhh-invites/email`,
        { contact_id: contact.id },
        schoolOptions()
      );
      generatedFhhInvite = result;
      await loadFhh();
      if (result.warning || result.send_status === 'failed') {
        showError(result.warning || $_('school.fhhLink.emailInviteFailed'));
      } else if ((result.related_student_count || 1) > 1) {
        showNotice($_('school.fhhLink.emailBundleInviteSent', {
          values: { email: contact.email, count: result.related_student_count }
        }));
      } else {
        showNotice($_('school.fhhLink.emailInviteSent', { values: { email: contact.email } }));
      }
    } catch (err: any) {
      showError(err?.message || $_('school.fhhLink.emailInviteFailed'));
    } finally {
      saving = false;
    }
  }

  async function generateFhhCode() {
    if (!selectedStudent) return;
    try {
      generatedFhhInvite = await api.post(`/school/students/${selectedStudent.id}/fhh-invites`, {}, schoolOptions());
      showNotice($_('school.fhhLink.generated'));
      await loadFhh();
    } catch (err: any) {
      showError(err?.message || $_('school.fhhLink.generateError'));
    }
  }

  async function revokeFhhInvite(id: number) {
    if (!confirm($_('school.fhhLink.revokeConfirm'))) return;
    try {
      await api.post(`/school/fhh-invites/${id}/revoke`, {}, schoolOptions());
      showNotice($_('school.fhhLink.revoked'));
      await loadFhh();
    } catch (err: any) {
      showError(err?.message || $_('school.fhhLink.revokeError'));
    }
  }

  onMount(() => {
    const onPopState = () => {
      if (allowed) void restoreStudentUrl();
    };
    const onNativeBack = (event: Event) => {
      if (event.defaultPrevented || (view !== 'detail' && view !== 'add')) return;
      returnToList();
      event.preventDefault();
      event.stopImmediatePropagation();
    };
    window.addEventListener('popstate', onPopState);
    window.addEventListener('chh:native-back', onNativeBack);
    void init();
    return () => {
      window.removeEventListener('popstate', onPopState);
      window.removeEventListener('chh:native-back', onNativeBack);
    };
  });
</script>

<svelte:head>
  <title>{$_('school.studentAdmin.title')}</title>
</svelte:head>

{#if loading}
  <section class="mx-auto max-w-6xl px-4 py-12"><div class="card p-8 text-center">{$_('common.loading')}</div></section>
{:else if !allowed}
  <section class="mx-auto max-w-3xl px-4 py-12">
    <div class="card p-8 text-center">
      <h1 class="text-2xl font-black">{$_('school.accessDeniedTitle')}</h1>
      <p class="mt-3 text-slate-600">{error || $_('school.accessDenied')}</p>
    </div>
  </section>
{:else}
  <section class="mx-auto max-w-7xl px-4 py-6 sm:py-8">
    <header class="flex flex-col gap-4 border-b border-slate-200 pb-5 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <a class="text-sm font-bold text-sky-700 hover:underline" href="/school"><span class="inline-block rtl:-scale-x-100" aria-hidden="true">←</span> {$_('school.studentAdmin.backToAdmin')}</a>
        <p class="eyebrow mt-3">{schoolName}</p>
        <h1 class="mt-2 text-3xl font-black text-slate-900">{$_('school.studentAdmin.title')}</h1>
        <p class="mt-2 max-w-2xl text-slate-600">{$_('school.studentAdmin.intro')}</p>
      </div>
      <a class="btn-secondary rounded-xl px-4 py-3 text-center" href="/school/students/data">{$_('school.studentData.title')}</a>
    </header>

    {#if error}
      <div class="mt-5 rounded-xl border border-red-200 bg-red-50 p-4 text-sm font-bold text-red-800" role="alert">{error}</div>
    {/if}
    {#if notice}
      <div class="mt-5 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm font-bold text-emerald-800" role="status">{notice}</div>
    {/if}

    {#if view === 'list'}
      <div id="student-records" class="mt-6 scroll-mt-4 rounded-2xl border border-slate-200 bg-white p-4 sm:p-5">
        <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 class="text-xl font-black text-slate-900">{$_('school.students.listTitle')}</h2>
            <p class="mt-1 text-sm text-slate-500">{$_('school.studentAdmin.searchHelp')}</p>
          </div>
          <button type="button" class="btn-hero rounded-xl px-4 py-3" onclick={openAdd}>+ {$_('school.studentAdmin.addStudent')}</button>
        </div>
        <form class="mt-5 grid gap-3 md:grid-cols-[minmax(0,1fr)_minmax(200px,320px)_auto_auto]" onsubmit={(event) => { event.preventDefault(); void applyFilters(); }}>
          <EntitySearch
            id="student-record-search"
            label={$_('school.students.search')}
            placeholder={$_('school.studentAdmin.searchPlaceholder')}
            help={$_('school.studentAdmin.searchPatternHelp')}
            clearLabel={$_('school.studentAdmin.clearStudentSearch')}
            bind:value={search}
            onquery={(query) => { search = query; void applyFilters(); }}
          />
          <label class="text-sm font-bold text-slate-700">
            {$_('school.students.classSection')}
            <select class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal" bind:value={sectionFilter}>
              <option value="">{$_('school.studentAdmin.allClasses')}</option>
              {#each sections.filter((section) => section.status !== 'archived') as section}
                <option value={String(section.id)}>{sectionContext(section)}</option>
              {/each}
            </select>
          </label>
          <button class="btn-hero self-end rounded-xl px-4 py-2.5" type="submit">{$_('school.students.applyFilters')}</button>
          <button class="btn-secondary self-end rounded-xl px-4 py-2.5" type="button" onclick={clearSearch}>{$_('school.studentAdmin.clearSearch')}</button>
        </form>
        <p class="mt-4 text-sm font-semibold text-slate-600" aria-live="polite">
          {$_('school.studentAdmin.resultsSummary', { values: { from: firstStudentNumber(), to: lastStudentNumber(), total: studentTotal } })}
        </p>
        {#if students.length}
          <div class="mt-5 grid gap-3 md:grid-cols-2">
            {#each students as student (student.id)}
              <button type="button" class="rounded-xl border border-slate-200 p-4 text-start transition hover:border-sky-300 hover:bg-sky-50" onclick={() => openStudent(student)}>
                <span class="block font-black text-slate-900">{student.display_name}</span>
                <span class="mt-1 block text-sm text-slate-600">{student.external_ref || $_('school.students.noExternalRef')}</span>
                <span class="mt-2 block text-sm font-semibold text-sky-800">{currentClass(student)}</span>
              </button>
            {/each}
          </div>
        {:else}
          <p class="mt-6 rounded-xl bg-slate-50 p-5 text-sm font-semibold text-slate-600">
            {search.trim() || sectionFilter ? $_('school.students.emptyFiltered') : $_('school.students.empty')}
          </p>
        {/if}
        {#if studentPages > 1}
          <nav class="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 pt-4" aria-label={$_('school.studentAdmin.paginationLabel')}>
            <button type="button" class="btn-secondary rounded-xl px-4 py-2.5" disabled={studentPage <= 1} onclick={() => void changeStudentPage(studentPage - 1)}>
              {$_('school.studentAdmin.previousPage')}
            </button>
            <span class="text-sm font-bold text-slate-700">
              {$_('school.studentAdmin.pageSummary', { values: { page: studentPage, pages: studentPages } })}
            </span>
            <button type="button" class="btn-secondary rounded-xl px-4 py-2.5" disabled={studentPage >= studentPages} onclick={() => void changeStudentPage(studentPage + 1)}>
              {$_('school.studentAdmin.nextPage')}
            </button>
          </nav>
        {/if}
      </div>
    {:else if view === 'add'}
      <div class="mt-6">
        <button type="button" class="text-sm font-bold text-sky-700 hover:underline" onclick={returnToList}><span class="inline-block rtl:-scale-x-100" aria-hidden="true">←</span> {$_('school.studentAdmin.backToStudents')}</button>
        <form class="mt-4 space-y-5" onsubmit={(event) => { event.preventDefault(); void createCompleteStudent(); }}>
          <section class="rounded-2xl border border-slate-200 bg-white p-4 sm:p-6">
            <h2 class="text-xl font-black text-slate-900">{$_('school.studentAdmin.addStudent')}</h2>
            <p class="mt-1 text-sm text-slate-600">{$_('school.studentAdmin.addHelp')}</p>
            <p class="mt-3 text-xs font-bold text-slate-500">{$_('school.studentAdmin.requiredLegend')}</p>
            <div class="mt-5 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              <label class="text-sm font-bold text-slate-700">
                {$_('school.studentAdmin.studentId')} *
                <input data-field="student_id" class:error-input={fieldErrors.student_id} class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal" bind:value={studentForm.external_ref} aria-invalid={Boolean(fieldErrors.student_id)} />
                {#if fieldErrors.student_id}<span class="mt-1 block text-xs text-red-700">{fieldErrors.student_id}</span>{/if}
              </label>
              <label class="text-sm font-bold text-slate-700">
                {$_('school.students.firstName')} *
                <input data-field="first_name" class:error-input={fieldErrors.first_name} class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal" bind:value={studentForm.first_name} />
                {#if fieldErrors.first_name}<span class="mt-1 block text-xs text-red-700">{fieldErrors.first_name}</span>{/if}
              </label>
              <label class="text-sm font-bold text-slate-700">
                {$_('school.students.lastName')} *
                <input data-field="last_name" class:error-input={fieldErrors.last_name} class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal" bind:value={studentForm.last_name} />
                {#if fieldErrors.last_name}<span class="mt-1 block text-xs text-red-700">{fieldErrors.last_name}</span>{/if}
              </label>
              <label class="text-sm font-bold text-slate-700">{$_('school.students.preferredName')}<input class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal" bind:value={studentForm.preferred_name} /></label>
              <label class="text-sm font-bold text-slate-700">{$_('school.nameAr')}<input class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal" bind:value={studentForm.name_ar} /></label>
              <label class="text-sm font-bold text-slate-700">{$_('school.students.dateOfBirth')}<input type="date" class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal" bind:value={studentForm.date_of_birth} /></label>
              <label class="text-sm font-bold text-slate-700">
                {$_('school.students.gender')}
                <select class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal" bind:value={studentForm.gender}>
                  <option value="">{$_('school.select')}</option>
                  <option value="male">{$_('school.students.genderMale')}</option>
                  <option value="female">{$_('school.students.genderFemale')}</option>
                  <option value="other">{$_('school.students.genderOther')}</option>
                  <option value="unspecified">{$_('school.students.genderUnspecified')}</option>
                </select>
              </label>
            </div>
          </section>

          <section class="rounded-2xl border border-slate-200 bg-white p-4 sm:p-6">
            <h2 class="text-lg font-black text-slate-900">{$_('school.studentAdmin.placement')}</h2>
            <div class="mt-4 grid gap-4 md:grid-cols-3">
              <label class="text-sm font-bold text-slate-700">
                {$_('school.studentAdmin.branch')} *
                <select data-field="branch" class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal" bind:value={addBranchId} onchange={() => addSectionId = ''}>
                  <option value="">{$_('school.select')}</option>
                  {#each branches.filter((row) => row.status !== 'archived') as branch}<option value={String(branch.id)}>{branch.name}</option>{/each}
                </select>
                {#if fieldErrors.branch}<span class="mt-1 block text-xs text-red-700">{fieldErrors.branch}</span>{/if}
              </label>
              <label class="text-sm font-bold text-slate-700">
                {$_('school.studentAdmin.grade')} *
                <select data-field="grade" class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal" bind:value={addLevelId} onchange={() => addSectionId = ''}>
                  <option value="">{$_('school.select')}</option>
                  {#each levels.filter((row) => row.status !== 'archived') as level}<option value={String(level.id)}>{level.name}</option>{/each}
                </select>
                {#if fieldErrors.grade}<span class="mt-1 block text-xs text-red-700">{fieldErrors.grade}</span>{/if}
              </label>
              <label class="text-sm font-bold text-slate-700">
                {$_('school.studentAdmin.classSection')} *
                <select data-field="section" class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal" bind:value={addSectionId}>
                  <option value="">{$_('school.select')}</option>
                  {#each filteredAddSections() as section}<option value={String(section.id)}>{section.name}</option>{/each}
                </select>
                {#if fieldErrors.section}<span class="mt-1 block text-xs text-red-700">{fieldErrors.section}</span>{/if}
              </label>
            </div>
          </section>

          <section class="rounded-2xl border border-slate-200 bg-white p-4 sm:p-6">
            <div class="flex items-center justify-between gap-3">
              <div><h2 class="text-lg font-black text-slate-900">{$_('school.guardians.contactsTitle')}</h2><p class="mt-1 text-sm text-slate-600">{$_('school.studentAdmin.guardiansOptional')}</p></div>
              <button class="btn-secondary rounded-xl px-3 py-2 text-sm" type="button" onclick={addGuardianDraft}>+ {$_('school.guardians.addContact')}</button>
            </div>
            <div class="mt-4 space-y-4">
              {#each guardianDrafts as guardian, index (guardian.key)}
                <fieldset class="rounded-xl border border-sky-100 bg-sky-50/40 p-4">
                  <div class="flex items-center justify-between"><legend class="font-black text-slate-900">{$_('school.studentAdmin.guardianNumber', { values: { number: index + 1 } })}</legend>{#if guardianDrafts.length > 1}<button type="button" class="text-sm font-bold text-red-700" onclick={() => removeGuardianDraft(guardian.key)}>{$_('school.studentAdmin.remove')}</button>{/if}</div>
                  <div class="mt-3 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    <label class="text-sm font-bold text-slate-700">{$_('school.guardians.fullName')}<input data-field={`guardian-${guardian.key}-name`} class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal" bind:value={guardian.name} />{#if fieldErrors[`guardian-${guardian.key}-name`]}<span class="mt-1 block text-xs text-red-700">{fieldErrors[`guardian-${guardian.key}-name`]}</span>{/if}</label>
                    <label class="text-sm font-bold text-slate-700">{$_('school.guardians.contactId')}<input class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal" bind:value={guardian.external_ref} /><span class="mt-1 block text-xs font-normal text-slate-500">{$_('school.studentAdmin.guardianIdHelp')}</span></label>
                    <label class="text-sm font-bold text-slate-700">{$_('school.guardians.relationship')}<select class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal" bind:value={guardian.relationship}><option value="">{$_('school.guardians.relationshipNone')}</option><option value="mother">{$_('school.guardians.relationships.mother')}</option><option value="father">{$_('school.guardians.relationships.father')}</option><option value="guardian">{$_('school.guardians.relationships.guardian')}</option><option value="other">{$_('school.guardians.relationships.other')}</option></select></label>
                    <label class="text-sm font-bold text-slate-700">{$_('school.guardians.email')}<input type="email" data-field={`guardian-${guardian.key}-email`} class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal" bind:value={guardian.email} />{#if fieldErrors[`guardian-${guardian.key}-email`]}<span class="mt-1 block text-xs text-red-700">{fieldErrors[`guardian-${guardian.key}-email`]}</span>{/if}</label>
                    <label class="text-sm font-bold text-slate-700">{$_('school.guardians.phone')}<input class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal" bind:value={guardian.phone} /></label>
                    <div class="flex flex-wrap items-center gap-4 pt-6 text-sm font-semibold"><label class="flex gap-2"><input type="checkbox" bind:checked={guardian.is_primary} />{$_('school.guardians.primary')}</label><label class="flex gap-2"><input type="checkbox" bind:checked={guardian.is_emergency} />{$_('school.guardians.emergency')}</label></div>
                  </div>
                </fieldset>
              {/each}
            </div>
          </section>
          <div class="flex flex-wrap justify-end gap-3"><button type="button" class="btn-secondary rounded-xl px-4 py-3" onclick={returnToList}>{$_('common.cancel')}</button><button type="submit" class="btn-hero rounded-xl px-5 py-3" disabled={saving}>{saving ? $_('school.studentAdmin.saving') : $_('school.studentAdmin.createStudent')}</button></div>
        </form>
      </div>
    {:else if selectedStudent}
      <div class="mt-6">
        <button type="button" class="text-sm font-bold text-sky-700 hover:underline" onclick={returnToList}><span class="inline-block rtl:-scale-x-100" aria-hidden="true">←</span> {$_('school.studentAdmin.backToStudents')}</button>
        <div class="mt-4 rounded-2xl border border-slate-200 bg-white p-4 sm:p-6">
          <div class="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between"><div><h2 class="text-2xl font-black text-slate-900">{selectedStudent.display_name}</h2><p class="mt-1 text-sm text-slate-600">{selectedStudent.external_ref || $_('school.students.noExternalRef')} · {currentClass(selectedStudent)}</p></div><span class="w-fit rounded-full bg-slate-100 px-3 py-1 text-xs font-black text-slate-700">{studentStatus(selectedStudent.status)}</span></div>
          <nav class="mt-5 flex gap-2 overflow-x-auto border-b border-slate-200 pb-3" aria-label={$_('school.studentAdmin.detailNavigation')}>
            {#each detailTabs as tab}<button type="button" class:btn-hero={activeDetailTab === tab} class:btn-secondary={activeDetailTab !== tab} class="shrink-0 rounded-lg px-3 py-2 text-sm" onclick={() => activeDetailTab = tab}>{$_(`school.studentAdmin.tabs.${tab}`)}</button>{/each}
          </nav>

          {#if activeDetailTab === 'details'}
            <form class="mt-5" onsubmit={(event) => { event.preventDefault(); void saveStudentDetails(); }}>
              <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                <label class="text-sm font-bold">{$_('school.studentAdmin.studentId')}<input class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal" bind:value={studentForm.external_ref} /></label>
                <label class="text-sm font-bold">{$_('school.students.firstName')} *<input data-field="detail-first-name" class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal" bind:value={studentForm.first_name} />{#if fieldErrors['detail-first-name']}<span class="mt-1 block text-xs text-red-700">{fieldErrors['detail-first-name']}</span>{/if}</label>
                <label class="text-sm font-bold">{$_('school.students.lastName')} *<input data-field="detail-last-name" class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal" bind:value={studentForm.last_name} />{#if fieldErrors['detail-last-name']}<span class="mt-1 block text-xs text-red-700">{fieldErrors['detail-last-name']}</span>{/if}</label>
                <label class="text-sm font-bold">{$_('school.students.preferredName')}<input class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal" bind:value={studentForm.preferred_name} /></label>
                <label class="text-sm font-bold">{$_('school.nameAr')}<input class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal" bind:value={studentForm.name_ar} /></label>
                <label class="text-sm font-bold">{$_('school.students.dateOfBirth')}<input type="date" class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal" bind:value={studentForm.date_of_birth} /></label>
                <label class="text-sm font-bold">{$_('school.students.gender')}<select class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal" bind:value={studentForm.gender}><option value="">{$_('school.select')}</option><option value="male">{$_('school.students.genderMale')}</option><option value="female">{$_('school.students.genderFemale')}</option><option value="other">{$_('school.students.genderOther')}</option><option value="unspecified">{$_('school.students.genderUnspecified')}</option></select></label>
              </div>
              <button class="btn-hero mt-5 rounded-xl px-4 py-3" type="submit" disabled={saving}>{$_('school.save')}</button>
            </form>
          {:else if activeDetailTab === 'guardians'}
            <div class="mt-5">
              <h3 class="font-black text-slate-900">{$_('school.guardians.contactsTitle')}</h3>
              <p class="mt-1 text-sm text-slate-600">{$_('school.guardians.contactsHelp')}</p>
              <form class="mt-4 rounded-xl border border-sky-100 bg-sky-50/40 p-4" onsubmit={(event) => { event.preventDefault(); void saveGuardian(); }}>
                <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  <label class="text-sm font-bold">{$_('school.guardians.fullName')} *<input data-field="guardian-edit-name" class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal" bind:value={guardianForm.name} />{#if fieldErrors['guardian-edit-name']}<span class="mt-1 block text-xs text-red-700">{fieldErrors['guardian-edit-name']}</span>{/if}</label>
                  <label class="text-sm font-bold">{$_('school.guardians.contactId')}<input class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal" bind:value={guardianForm.external_ref} /><span class="mt-1 block text-xs font-normal text-slate-500">{$_('school.studentAdmin.guardianIdHelp')}</span></label>
                  <label class="text-sm font-bold">{$_('school.guardians.relationship')}<select class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal" bind:value={guardianForm.relationship}><option value="">{$_('school.guardians.relationshipNone')}</option><option value="mother">{$_('school.guardians.relationships.mother')}</option><option value="father">{$_('school.guardians.relationships.father')}</option><option value="guardian">{$_('school.guardians.relationships.guardian')}</option><option value="other">{$_('school.guardians.relationships.other')}</option></select></label>
                  <label class="text-sm font-bold">{$_('school.guardians.email')}<input type="email" data-field="guardian-edit-email" class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal" bind:value={guardianForm.email} />{#if fieldErrors['guardian-edit-email']}<span class="mt-1 block text-xs text-red-700">{fieldErrors['guardian-edit-email']}</span>{/if}</label>
                  <label class="text-sm font-bold">{$_('school.guardians.phone')}<input class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal" bind:value={guardianForm.phone} /></label>
                  <div class="flex flex-wrap items-center gap-4 pt-6 text-sm font-semibold"><label class="flex gap-2"><input type="checkbox" bind:checked={guardianForm.is_primary} />{$_('school.guardians.primary')}</label><label class="flex gap-2"><input type="checkbox" bind:checked={guardianForm.is_emergency} />{$_('school.guardians.emergency')}</label><label class="flex gap-2"><input type="checkbox" bind:checked={guardianForm.is_active} />{$_('school.guardians.activeContact')}</label></div>
                </div>
                <div class="mt-4 flex gap-2"><button class="btn-hero rounded-xl px-4 py-2.5" type="submit" disabled={saving}>{editingGuardianId ? $_('school.guardians.updateContact') : $_('school.guardians.addContact')}</button>{#if editingGuardianId}<button type="button" class="btn-secondary rounded-xl px-4 py-2.5" onclick={resetGuardianForm}>{$_('common.cancel')}</button>{/if}</div>
              </form>
              <div class="mt-4 space-y-3">
                {#each guardians?.contacts || [] as contact (contact.id)}
                  <article class={`rounded-xl border p-4 ${contact.is_active ? 'border-slate-200' : 'border-slate-200 bg-slate-50'}`}>
                    <div class="flex flex-col gap-3 sm:flex-row sm:justify-between">
                      <div>
                        <p class="font-black">{contact.name}</p>
                        <p class="mt-1 text-sm text-slate-600">{[relationshipLabel(contact.relationship), contact.email, contact.phone].filter(Boolean).join(' · ') || '—'}</p>
                        <p class="mt-2 text-xs font-bold text-slate-500">{contact.source === 'import' ? $_('school.guardians.imported') : $_('school.guardians.manual')} · {guardianStatus(contact.access_status)}</p>
                        {#if currentFhhGuardianInvite(contact.id)?.send_status === 'sent'}
                          <p class="mt-2 text-xs font-bold text-emerald-700">{$_('school.fhhLink.invitationSent')}</p>
                        {:else if currentFhhGuardianInvite(contact.id)?.send_status === 'failed'}
                          <p class="mt-2 text-xs font-bold text-red-700">{$_('school.fhhLink.invitationFailed')}</p>
                        {/if}
                      </div>
                      <div class="flex flex-wrap gap-2">
                        <button class="btn-secondary rounded-lg px-3 py-2 text-sm" type="button" onclick={() => editGuardian(contact)}>{$_('school.edit')}</button>
                        <button class="btn-secondary rounded-lg px-3 py-2 text-sm" type="button" onclick={() => toggleGuardian(contact)}>{contact.is_active ? $_('school.guardians.inactivate') : $_('school.guardians.activate')}</button>
                        {#if contact.is_active && contact.email}
                          <button class="btn-hero rounded-lg px-3 py-2 text-sm" type="button" disabled={saving} onclick={() => emailFhhGuardianInvite(contact)}>{currentFhhGuardianInvite(contact.id) ? $_('school.fhhLink.resendEmailInvite') : $_('school.fhhLink.emailInvite')}</button>
                        {/if}
                      </div>
                    </div>
                  </article>
                {:else}
                  <p class="rounded-xl bg-slate-50 p-4 text-sm text-slate-600">{$_('school.guardians.noContacts')}</p>
                {/each}
              </div>
            </div>
          {:else if activeDetailTab === 'placement'}
            <div class="mt-5"><h3 class="font-black">{$_('school.studentAdmin.currentPlacement')}</h3><p class="mt-2 text-slate-700">{currentClass(selectedStudent)}</p><div class="mt-5 max-w-xl rounded-xl border border-slate-200 p-4"><label class="text-sm font-bold">{$_('school.students.moveClass')}<select data-field="move" class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal" bind:value={moveSectionId}><option value="">{$_('school.select')}</option>{#each sections.filter((row) => row.status !== 'archived') as section}<option value={String(section.id)}>{sectionContext(section)}</option>{/each}</select>{#if fieldErrors.move}<span class="mt-1 block text-xs text-red-700">{fieldErrors.move}</span>{/if}</label><p class="mt-2 text-xs text-slate-500">{$_('school.students.moveHelp')}</p><button type="button" class="btn-hero mt-4 rounded-xl px-4 py-2.5" disabled={saving} onclick={moveStudent}>{$_('school.students.move')}</button></div></div>
          {:else if activeDetailTab === 'access'}
            <div class="mt-5"><h3 class="font-black">{$_('school.studentAdmin.chhAccounts')}</h3><p class="mt-1 text-sm text-slate-600">{$_('school.studentAdmin.chhAccountsHelp')}</p><div class="mt-4 space-y-3">{#each guardians?.links || [] as link (link.id)}<article class="rounded-xl border border-slate-200 p-4"><div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"><div><p class="font-black">{link.user_email || link.display_name || '—'}</p><p class="mt-1 text-sm text-slate-600">{relationshipLabel(link.relationship) || $_('school.guardians.relationshipNone')} · {guardianStatus(link.status)}</p></div>{#if link.status === 'active'}<button type="button" class="btn-secondary rounded-lg px-3 py-2 text-sm" onclick={() => revokeGuardianLink(link.id)}>{$_('school.guardians.revokeLink')}</button>{/if}</div></article>{:else}<p class="rounded-xl bg-slate-50 p-4 text-sm text-slate-600">{$_('school.studentAdmin.noChhAccounts')}</p>{/each}</div><h4 class="mt-6 font-black">{$_('school.studentAdmin.invitationHistory')}</h4><div class="mt-3 space-y-2">{#each guardians?.invites || [] as invite}<div class="rounded-xl border border-slate-200 p-3 text-sm"><span class="font-bold">{invite.guardian_name || '—'}</span> · {relationshipLabel(invite.relationship) || '—'} · {guardianStatus(invite.status)} · {formatDate(invite.created_at)}{#if invite.status === 'active'}<button type="button" class="ms-3 font-bold text-red-700" onclick={() => revokeGuardianInvite(invite.id)}>{$_('school.guardians.revoke')}</button>{/if}</div>{:else}<p class="text-sm text-slate-500">{$_('school.studentAdmin.noInvitations')}</p>{/each}</div></div>
          {:else if activeDetailTab === 'fhh'}
            <div class="mt-5">
              <h3 class="font-black">{$_('school.fhhLink.title')}</h3>
              <p class="mt-1 text-sm text-slate-600">{$_('school.fhhLink.help')}</p>
              <div class={`mt-4 rounded-xl border p-4 ${fhh?.link_status === 'active' ? 'border-emerald-200 bg-emerald-50' : 'border-slate-200 bg-slate-50'}`}>
                <p class="text-xs font-black uppercase tracking-wide text-slate-500">{$_('school.studentAdmin.currentFhhStatus')}</p>
                <p class="mt-1 text-lg font-black">{$_(`school.guardians.status.${fhh?.link_status || 'none'}`)}</p>
                {#if fhh?.linked_at}<p class="mt-1 text-sm text-slate-600">{formatDate(fhh.linked_at)}</p>{/if}
              </div>
              <button type="button" class="btn-hero mt-4 rounded-xl px-4 py-2.5" onclick={generateFhhCode}>{$_('school.fhhLink.generate')}</button>
              {#if generatedFhhInvite?.code}
                <div class="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 p-4">
                  <p class="font-black">{$_('school.fhhLink.generatedCode')}</p>
                  <p class="mt-2 font-mono text-xl font-black tracking-wider">{generatedFhhInvite.code}</p>
                  <p class="mt-2 text-xs">{$_('school.fhhLink.immediateOnly')}</p>
                </div>
              {/if}
              <details class="mt-5 rounded-xl border border-slate-200 p-4">
                <summary class="cursor-pointer font-black">
                  {$_('school.studentAdmin.viewFhhHistory')} ({(fhh?.link_history?.length || 0) + (fhh?.invites?.length || 0)})
                </summary>
                <div class="mt-3 space-y-2">
                  {#each fhh?.link_history || [] as link}
                    <div class="rounded-lg bg-slate-50 p-3 text-sm">
                      {$_('school.studentAdmin.fhhLinkRecord')} · {$_(`school.guardians.status.${link.status}`)} · {formatDate(link.linked_at)}
                      {#if link.revoked_at} · {formatDate(link.revoked_at)}{/if}
                    </div>
                  {/each}
                  {#each fhh?.invites || [] as invite}
                    <div class="rounded-lg bg-slate-50 p-3 text-sm">
                      {$_('school.studentAdmin.fhhInviteRecord')} · {$_(`school.fhhLink.status.${fhhInviteStatus(invite)}`)} · {formatDate(invite.created_at)}
                      {#if fhhInviteStatus(invite) === 'active'}
                        <button type="button" class="ms-3 font-bold text-red-700" onclick={() => revokeFhhInvite(invite.id)}>{$_('school.fhhLink.revoke')}</button>
                      {/if}
                    </div>
                  {/each}
                  {#if !(fhh?.link_history?.length || fhh?.invites?.length)}
                    <p class="text-sm text-slate-500">{$_('school.fhhLink.empty')}</p>
                  {/if}
                </div>
              </details>
            </div>
          {:else}
            <div class="mt-5"><h3 class="font-black">{$_('school.students.history')}</h3><div class="mt-4 space-y-3">{#each enrolments as enrolment (enrolment.id)}<article class="rounded-xl border border-slate-200 p-4"><p class="font-black">{enrolment.class_section ? localizedRowName(enrolment.class_section) : enrolment.subject_group ? localizedRowName(enrolment.subject_group) : '—'}</p><p class="mt-1 text-sm text-slate-600">{enrolment.valid_from} <span class="inline-block rtl:-scale-x-100" aria-hidden="true">→</span> {enrolment.valid_to || $_('school.students.open')}</p></article>{:else}<p class="rounded-xl bg-slate-50 p-4 text-sm text-slate-600">{$_('school.students.noEnrolments')}</p>{/each}</div></div>
          {/if}
        </div>
      </div>
    {/if}
  </section>

  {#if toast}
    <div class={`fixed bottom-4 end-4 z-50 max-w-sm rounded-xl px-4 py-3 text-sm font-bold text-white shadow-xl ${toast.kind === 'error' ? 'bg-red-700' : 'bg-emerald-700'}`} role={toast.kind === 'error' ? 'alert' : 'status'} aria-live={toast.kind === 'error' ? 'assertive' : 'polite'}>{toast.message}</div>
  {/if}
{/if}

<style>
  .error-input {
    border-color: rgb(248 113 113);
    box-shadow: 0 0 0 1px rgb(248 113 113);
  }
</style>
