<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { api } from '$lib/api';
  import CrudBlock from '$lib/components/school/CrudBlock.svelte';
  import NumberInput from '$lib/components/school/NumberInput.svelte';
  import RowsTable from '$lib/components/school/RowsTable.svelte';
  import SelectInput from '$lib/components/school/SelectInput.svelte';
  import StatusInput from '$lib/components/school/StatusInput.svelte';
  import TextInput from '$lib/components/school/TextInput.svelte';
  import { CheckCircle2, Circle, Pencil, Plus, Trash2 } from 'lucide-svelte';

  type Membership = { school_id: number; school_name: string; role: string };
  type Row = {
    id: number;
    code: string;
    name: string;
    name_ar?: string | null;
    sort_order: number;
    status: string;
    education_stage_id?: number | null;
    branch_campus_id?: number | null;
    academic_year_id?: number | null;
    grade_level_id?: number | null;
    class_section_id?: number | null;
    subject_id?: number | null;
    enrolment_policy?: 'explicit_only' | 'default_for_section' | 'default_for_grade';
    is_current?: boolean;
    start_date?: string | null;
    end_date?: string | null;
  };
  type ChecklistItem = { key: string; label: string; complete: boolean; count: number; required: boolean };
  type Teacher = {
    membership_id: number;
    assignment_count: number;
    user: { id: number; email: string; name?: string | null };
  };
  type StaffInvite = {
    id: number;
    email: string;
    status: string;
    send_status?: string;
    created_at?: string;
  };
  type StaffAssignment = {
    id: number;
    role: string;
    class_section_id?: number | null;
    subject_group_id?: number | null;
    valid_from: string;
    valid_to?: string | null;
    is_open: boolean;
    class_section?: Row | null;
    subject_group?: Row | null;
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
    current_subject_groups?: (Row & { source?: 'default' | 'explicit'; enrolment_id?: number | null; enrolled_from?: string })[];
  };
  type StudentForm = {
    external_ref: string;
    first_name: string;
    last_name: string;
    preferred_name: string;
    name_ar: string;
    date_of_birth: string;
    gender: string;
    status: string;
  };
  type ImportRow = {
    id: number;
    row_number: number;
    student_id?: string | null;
    first_name?: string | null;
    last_name?: string | null;
    grade?: string | null;
    section?: string | null;
    branch?: string | null;
    guardian1_name?: string | null;
    guardian1_email?: string | null;
    guardian1_relationship?: string | null;
    guardian2_name?: string | null;
    guardian2_email?: string | null;
    guardian2_relationship?: string | null;
    action: 'create' | 'update' | 'move' | 'restore' | 'skip' | 'error';
    errors: string[];
    warnings: string[];
    applied_entity_id?: number | null;
  };
  type StudentImport = {
    id: number;
    filename?: string | null;
    status: 'staged' | 'committed' | 'discarded';
    summary: Record<string, number>;
    rows: ImportRow[];
  };
  type TeacherImportRow = {
    id: number;
    row_number: number;
    email?: string | null;
    first_name?: string | null;
    last_name?: string | null;
    name_ar?: string | null;
    action: 'create' | 'update' | 'skip' | 'error';
    errors: string[];
    warnings: string[];
    applied_entity_id?: number | null;
  };
  type TeacherImport = {
    id: number;
    filename?: string | null;
    status: 'staged' | 'committed' | 'discarded';
    summary: Record<string, number>;
    rows: TeacherImportRow[];
  };
  type Enrolment = {
    id: number;
    student_id: number;
    class_section_id?: number | null;
    subject_group_id?: number | null;
    kind?: 'member' | 'excluded';
    valid_from: string;
    valid_to?: string | null;
    is_open: boolean;
    class_section?: Row | null;
    subject_group?: Row | null;
  };
  type TeacherRef = {
    assignment_id: number;
    membership_id: number;
    valid_from: string;
    user: { id: number; email: string; name?: string | null };
  };
  type ClassRosterSetup = {
    class_section: Row;
    branch?: Row | null;
    academic_year?: Row | null;
    grade_level?: Row | null;
    students: (Student & { enrolment_id?: number; enrolled_from?: string })[];
    homeroom_teacher?: TeacherRef | null;
    subject_groups: {
      subject_group: Row;
      subject?: Row | null;
      teacher?: TeacherRef | null;
    }[];
  };
  type SubjectGroupRoster = {
    class_section?: Row | null;
    subject_group?: Row | null;
    enrolment_policy?: 'explicit_only' | 'default_for_section' | 'default_for_grade';
    students: (Student & { enrolment_id?: number | null; enrolled_from?: string; source?: 'default' | 'explicit' })[];
    excluded_students: (Student & { enrolment_id: number; enrolled_from?: string; source?: 'excluded' })[];
  };
  type BulkSubjectGroupResult = {
    created: number;
    restored: number;
    skipped: number;
    failed: number;
    results: {
      class_section_id: number;
      status: string;
      reason?: string | null;
      class_section?: Row;
      subject_group?: Row;
    }[];
  };
  type DefaultSubjectTemplate = {
    id: number;
    school_id: number;
    education_stage_id?: number | null;
    grade_level_id?: number | null;
    subject_id: number;
    status: string;
    sort_order: number;
    subject?: Row | null;
    education_stage?: Row | null;
    grade_level?: Row | null;
  };
  type TemplatePlanRow = {
    class_section_id: number;
    class_section?: Row | null;
    subject_id: number;
    subject?: Row | null;
    code?: string | null;
    name?: string | null;
    status: string;
    reason?: string | null;
    subject_group?: Row | null;
  };
  type TemplatePreviewResult = {
    would_create: number;
    would_restore: number;
    skipped_existing: number;
    failed: number;
    results: TemplatePlanRow[];
  };
  type TemplateApplyResult = {
    created: number;
    restored: number;
    skipped: number;
    failed: number;
    results: TemplatePlanRow[];
  };

  const tabs = [
    { key: 'checklist', label: 'school.tabs.checklist' },
    { key: 'settings', label: 'school.tabs.settings' },
    { key: 'branches', label: 'school.tabs.branches' },
    { key: 'stages', label: 'school.tabs.stages' },
    { key: 'years', label: 'school.tabs.years' },
    { key: 'levels', label: 'school.tabs.levels' },
    { key: 'sections', label: 'school.tabs.sections' },
    { key: 'rosters', label: 'school.tabs.rosters' },
    { key: 'teachers', label: 'school.tabs.teachers' },
    { key: 'students', label: 'school.tabs.students' },
    { key: 'subjects', label: 'school.tabs.subjects' },
    { key: 'defaults', label: 'school.tabs.defaults' },
    { key: 'groups', label: 'school.tabs.groups' }
  ];

  let loading = $state(true);
  let saving = $state(false);
  let editingPath = $state<string | null>(null);
  let editingId = $state<number | null>(null);
  let error = $state<string | null>(null);
  let notice = $state<string | null>(null);
  let formErrors = $state<Record<string, string>>({});
  let allowed = $state(false);
  let schoolId = $state<number | null>(null);
  let schoolName = $state('');
  let activeTab = $state('checklist');
  let checklist = $state<ChecklistItem[]>([]);
  let setupComplete = $state(false);
  let gradeLevelLabel = $state('Grade');
  let labelChoice = $state('Grade');
  let customLabel = $state('');

  let branches = $state<Row[]>([]);
  let stages = $state<Row[]>([]);
  let years = $state<Row[]>([]);
  let levels = $state<Row[]>([]);
  let sections = $state<Row[]>([]);
  let subjects = $state<Row[]>([]);
  let groups = $state<Row[]>([]);
  let students = $state<Student[]>([]);
  let studentsLoaded = $state(false);
  let teachers = $state<Teacher[]>([]);
  let pendingTeacherInvites = $state<StaffInvite[]>([]);
  let teacherAssignments = $state<Record<number, StaffAssignment[]>>({});
  let teacherInviteEmail = $state('');
  let homeroomSelections = $state<Record<number, string>>({});
  let groupSelections = $state<Record<number, string>>({});
  let selectedStudentId = $state<number | null>(null);
  let studentSearch = $state('');
  let studentSectionFilter = $state('');
  let studentEnrolments = $state<Enrolment[]>([]);
  let loadingEnrolments = $state(false);
  let classEnrolmentSectionId = $state('');
  let subjectEnrolmentGroupId = $state('');
  let moveSectionId = $state('');
  let rosterSectionId = $state('');
  let classRoster = $state<ClassRosterSetup | null>(null);
  let rosterLoading = $state(false);
  let groupRosterId = $state('');
  let groupRosterStudentId = $state('');
  let groupRoster = $state<SubjectGroupRoster | null>(null);
  let groupRosterLoading = $state(false);

  let importFile = $state<File | null>(null);
  let importUploading = $state(false);
  let importCommitting = $state(false);
  let studentImport = $state<StudentImport | null>(null);

  let teacherImportFile = $state<File | null>(null);
  let teacherImportUploading = $state(false);
  let teacherImportCommitting = $state(false);
  let teacherImport = $state<TeacherImport | null>(null);

  let branchForm = $state(baseForm('MAIN', 'Main Branch'));
  let stageForm = $state(baseForm('PRIMARY', 'Primary'));
  let yearForm = $state({ ...baseForm('2026-27', '2026/27'), is_current: false, start_date: '', end_date: '' });
  let levelForm = $state({ ...baseForm('G1', 'Grade 1'), education_stage_id: '' });
  let sectionForm = $state({ ...baseForm('A', ''), branch_campus_id: '', academic_year_id: '', grade_level_id: '' });
  let subjectForm = $state(baseForm('ENG', 'English'));
  let groupForm = $state({ ...baseForm('', ''), academic_year_id: '', class_section_id: '', grade_level_id: '', subject_id: '', enrolment_policy: 'default_for_section' });
  let studentForm = $state({ external_ref: '', first_name: '', last_name: '', preferred_name: '', name_ar: '', date_of_birth: '', gender: '', status: 'active' });
  let groupContextMode = $state<'section' | 'grade'>('section');
  let lastAutoGroupCode = $state('');
  let lastAutoGroupName = $state('');
  let bulkGroupForm = $state({ academic_year_id: '', grade_level_id: '', subject_id: '', enrolment_policy: 'default_for_section', class_section_ids: [] as string[] });
  let bulkGroupResult = $state<BulkSubjectGroupResult | null>(null);
  let lastBulkSectionKey = $state('');
  let quickLabels = $state('A, B, C');

  let templates = $state<DefaultSubjectTemplate[]>([]);
  let templateForm = $state({ scope: 'stage' as 'stage' | 'grade', education_stage_id: '', grade_level_id: '', subject_id: '', sort_order: 0, status: 'active' });
  let templateApplyForm = $state({ academic_year_id: '', branch_campus_id: '', education_stage_id: '', grade_level_id: '' });
  let templatePreviewResult = $state<TemplatePreviewResult | null>(null);
  let templateApplyResult = $state<TemplateApplyResult | null>(null);
  let templatePreviewLoading = $state(false);
  let templateApplyLoading = $state(false);

  function baseForm(code = '', name = '') {
    return { code, name, name_ar: '', sort_order: 0, status: 'active' };
  }

  function schoolOptions(): RequestInit {
    return { headers: { 'X-School-Id': String(schoolId) } };
  }

  function errorKey(scope: string, field: string) {
    return `${scope}.${field}`;
  }

  function setValidationErrors(scope: string, errors: Record<string, string>) {
    formErrors = Object.fromEntries(Object.entries(errors).map(([field, message]) => [errorKey(scope, field), message]));
    error = Object.values(errors)[0] || $_('school.validation.fixErrors');
  }

  function fieldError(scope: string, field: string) {
    return formErrors[errorKey(scope, field)] || '';
  }

  function clearValidation() {
    formErrors = {};
  }

  function validateRequiredText(scope: string, form: { code?: string; name?: string }) {
    const errors: Record<string, string> = {};
    if (!form.code?.trim()) errors.code = $_('school.validation.codeRequired');
    if (!form.name?.trim()) errors.name = $_('school.validation.nameRequired');
    if (Object.keys(errors).length) {
      setValidationErrors(scope, errors);
      return false;
    }
    clearValidation();
    return true;
  }

  function rowName(rows: Row[], id?: number | string | null) {
    const numericId = Number(id);
    return rows.find((row) => row.id === numericId)?.name || '-';
  }

  function levelName(id?: number | string | null) {
    return rowName(levels, id);
  }

  function branchName(id?: number | string | null) {
    return rowName(branches, id);
  }

  function stageName(id?: number | string | null) {
    return rowName(stages, id);
  }

  function yearName(id?: number | string | null) {
    return rowName(years, id);
  }

  function subjectName(id?: number | string | null) {
    return rowName(subjects, id);
  }

  function findRow(rows: Row[], id?: number | string | null) {
    const numericId = Number(id);
    return rows.find((row) => row.id === numericId);
  }

  function currentYearId() {
    return years.find((year) => year.is_current && year.status !== 'archived')?.id;
  }

  function defaultYearValue() {
    return idStr(currentYearId() ?? years[0]?.id);
  }

  function nextSort<T extends { sort_order: number }>(rows: T[], filter: (row: T) => boolean = () => true) {
    const values = rows.filter(filter).map((row) => Number(row.sort_order || 0));
    return values.length ? Math.max(...values) + 10 : 10;
  }

  function applyNewSortDefaults() {
    if (editingPath) return;
    branchForm.sort_order = nextSort(branches);
    stageForm.sort_order = nextSort(stages);
    yearForm.sort_order = nextSort(years);
    levelForm.sort_order = nextSort(levels);
    subjectForm.sort_order = nextSort(subjects);
    sectionForm.sort_order = nextSort(
      sections,
      (row) =>
        row.branch_campus_id === Number(sectionForm.branch_campus_id) &&
        row.academic_year_id === Number(sectionForm.academic_year_id) &&
        row.grade_level_id === Number(sectionForm.grade_level_id)
    );
    groupForm.sort_order =
      groupContextMode === 'section'
        ? nextSort(groups, (row) => row.class_section_id === Number(groupForm.class_section_id))
        : nextSort(groups, (row) => row.grade_level_id === Number(groupForm.grade_level_id));
  }

  async function loadMe() {
    const me = await api.get('/me/v2');
    const memberships = (me?.memberships || []) as Membership[];
    const adminMembership = memberships.find((membership) => membership.role === 'school_admin');
    if (!adminMembership) {
      allowed = false;
      return;
    }
    schoolId = adminMembership.school_id;
    schoolName = adminMembership.school_name;
    allowed = true;
  }

  function studentsPath() {
    const studentQuery = new URLSearchParams();
    if (studentSearch.trim()) studentQuery.set('search', studentSearch.trim());
    if (studentSectionFilter) studentQuery.set('class_section_id', studentSectionFilter);
    return `/school/students${studentQuery.toString() ? `?${studentQuery.toString()}` : ''}`;
  }

  async function ensureStudentsLoaded() {
    if (!schoolId || studentsLoaded) return;
    studentsLoaded = true;
    students = await api.get(studentsPath(), schoolOptions());
  }

  async function loadAll() {
    if (!schoolId) return;
    const options = schoolOptions();
    const [settings, checklistData, branchRows, stageRows, yearRows, levelRows, sectionRows, subjectRows, groupRows, teacherData, templateRows] = await Promise.all([
      api.get('/school/settings', options),
      api.get('/school/setup-checklist', options),
      api.get('/school/branches', options),
      api.get('/school/education-stages', options),
      api.get('/school/academic-years', options),
      api.get('/school/grade-levels', options),
      api.get('/school/class-sections', options),
      api.get('/school/subjects', options),
      api.get('/school/subject-groups', options),
      api.get('/school/teachers', options),
      api.get('/school/default-subject-templates', options)
    ]);
    // Students is the heaviest dataset (subject-group roster derivation over every
    // student). Skip it on initial/background loads and only fetch it once the
    // Students tab (or the subject-group roster "add student" picker) needs it;
    // loadAll() keeps it in sync afterwards so mutations elsewhere still refresh it.
    if (studentsLoaded) students = await api.get(studentsPath(), options);
    gradeLevelLabel = settings.grade_level_label || 'Grade';
    labelChoice = ['Grade', 'Year', 'Form', 'Level'].includes(gradeLevelLabel) ? gradeLevelLabel : 'custom';
    customLabel = labelChoice === 'custom' ? gradeLevelLabel : '';
    checklist = checklistData.items || [];
    setupComplete = Boolean(checklistData.complete);
    branches = branchRows;
    stages = stageRows;
    years = yearRows;
    levels = levelRows;
    sections = sectionRows;
    subjects = subjectRows;
    groups = groupRows;
    templates = templateRows;
    teachers = teacherData.teachers || [];
    pendingTeacherInvites = teacherData.pending_invites || [];
    // SelectInput's value prop has a fallback, so binding an undefined record
    // entry throws props_invalid_value and kills the Teachers panel render.
    for (const teacher of teachers) {
      homeroomSelections[teacher.membership_id] ??= '';
      groupSelections[teacher.membership_id] ??= '';
    }
    const assignmentsByTeacher = await api.get('/school/teachers/assignments', options);
    teacherAssignments = Object.fromEntries(
      teachers.map((teacher) => [teacher.membership_id, assignmentsByTeacher?.[teacher.membership_id] || []])
    );
    const defaultYear = defaultYearValue();
    if (!sectionForm.academic_year_id) sectionForm.academic_year_id = defaultYear;
    if (!groupForm.academic_year_id) groupForm.academic_year_id = defaultYear;
    if (!bulkGroupForm.academic_year_id) bulkGroupForm.academic_year_id = defaultYear;
    if (!templateApplyForm.academic_year_id) templateApplyForm.academic_year_id = defaultYear;
    if (rosterSectionId && !sections.some((section) => section.id === Number(rosterSectionId))) {
      rosterSectionId = '';
      classRoster = null;
    }
    if (groupRosterId && !groups.some((group) => group.id === Number(groupRosterId))) {
      groupRosterId = '';
      groupRoster = null;
    }
    if (selectedStudentId && !students.some((student) => student.id === selectedStudentId)) {
      selectedStudentId = null;
      studentEnrolments = [];
    }
    if (selectedStudentId) await loadStudentEnrolments(selectedStudentId);
    if (classRoster && rosterSectionId) await loadClassRoster(false);
    if (groupRoster && groupRosterId) await loadGroupRoster(false);
    applyNewSortDefaults();
  }

  async function refresh() {
    error = null;
    try {
      await loadAll();
    } catch (err: any) {
      error = err?.message || $_('school.loadError');
    }
  }

  async function init() {
    loading = true;
    error = null;
    try {
      await loadMe();
      if (allowed) await loadAll();
    } catch (err: any) {
      if (err?.status === 401) {
        window.location.href = `/login?returnTo=${encodeURIComponent('/school')}`;
        return;
      }
      error = err?.message || $_('school.loadError');
    } finally {
      loading = false;
    }
  }

  function payloadFrom(form: any) {
    return {
      ...form,
      name_ar: form.name_ar || null,
      sort_order: Number(form.sort_order || 0)
    };
  }

  function idStr(value?: number | string | null) {
    return value != null && value !== '' ? String(value) : '';
  }

  function resetForm(path: string) {
    if (path === 'branches') branchForm = { ...baseForm('', ''), sort_order: nextSort(branches) };
    else if (path === 'education-stages') stageForm = { ...baseForm('', ''), sort_order: nextSort(stages) };
    else if (path === 'academic-years') yearForm = { ...baseForm('', ''), sort_order: nextSort(years), is_current: false, start_date: '', end_date: '' };
    else if (path === 'subjects') subjectForm = { ...baseForm('', ''), sort_order: nextSort(subjects) };
    else if (path === 'grade-levels') levelForm = { ...baseForm('', ''), sort_order: nextSort(levels), education_stage_id: '' };
    else if (path === 'class-sections') sectionForm = { ...baseForm('', ''), sort_order: nextSort(sections), branch_campus_id: '', academic_year_id: defaultYearValue(), grade_level_id: '' };
    else if (path === 'subject-groups') {
      groupForm = { ...baseForm('', ''), sort_order: nextSort(groups), academic_year_id: defaultYearValue(), class_section_id: '', grade_level_id: '', subject_id: '', enrolment_policy: 'default_for_section' };
      groupContextMode = 'section';
      lastAutoGroupCode = '';
      lastAutoGroupName = '';
    } else if (path === 'students') {
      studentForm = { external_ref: '', first_name: '', last_name: '', preferred_name: '', name_ar: '', date_of_birth: '', gender: '', status: 'active' };
    } else if (path === 'default-subject-templates') {
      resetTemplateForm();
    }
  }

  function resetTemplateForm() {
    templateForm = { scope: templateForm.scope, education_stage_id: '', grade_level_id: '', subject_id: '', sort_order: nextSort(templates), status: 'active' };
  }

  function setTemplateScope(scope: 'stage' | 'grade') {
    templateForm.scope = scope;
    if (scope === 'stage') templateForm.grade_level_id = '';
    else templateForm.education_stage_id = '';
  }

  function templatePayload() {
    return {
      education_stage_id: templateForm.scope === 'stage' ? Number(templateForm.education_stage_id) || null : null,
      grade_level_id: templateForm.scope === 'grade' ? Number(templateForm.grade_level_id) || null : null,
      subject_id: Number(templateForm.subject_id),
      sort_order: Number(templateForm.sort_order || 0),
      status: templateForm.status
    };
  }

  async function saveTemplate() {
    const errors: Record<string, string> = {};
    if (templateForm.scope === 'stage' && !templateForm.education_stage_id) errors.education_stage_id = $_('school.validation.stageRequired');
    if (templateForm.scope === 'grade' && !templateForm.grade_level_id) errors.grade_level_id = $_('school.validation.gradeRequired');
    if (!templateForm.subject_id) errors.subject_id = $_('school.validation.subjectRequired');
    if (Object.keys(errors).length) {
      setValidationErrors('default-subject-templates', errors);
      return;
    }
    return saveVia('default-subject-templates', templatePayload(), () => resetTemplateForm());
  }

  function editTemplate(row: DefaultSubjectTemplate) {
    editingPath = 'default-subject-templates';
    editingId = row.id;
    templateForm = {
      scope: row.education_stage_id ? 'stage' : 'grade',
      education_stage_id: idStr(row.education_stage_id),
      grade_level_id: idStr(row.grade_level_id),
      subject_id: idStr(row.subject_id),
      sort_order: row.sort_order,
      status: row.status
    };
  }

  function templateApplyPayload() {
    return {
      academic_year_id: Number(templateApplyForm.academic_year_id),
      branch_campus_id: templateApplyForm.branch_campus_id ? Number(templateApplyForm.branch_campus_id) : null,
      education_stage_id: templateApplyForm.education_stage_id ? Number(templateApplyForm.education_stage_id) : null,
      grade_level_id: templateApplyForm.grade_level_id ? Number(templateApplyForm.grade_level_id) : null
    };
  }

  async function previewTemplateApplication() {
    if (!schoolId) return;
    if (!templateApplyForm.academic_year_id) {
      setValidationErrors('template-apply', { academic_year_id: $_('school.validation.yearRequired') });
      return;
    }
    clearValidation();
    error = null;
    notice = null;
    templateApplyResult = null;
    templatePreviewLoading = true;
    try {
      templatePreviewResult = await api.post('/school/default-subject-templates/preview', templateApplyPayload(), schoolOptions());
    } catch (err: any) {
      error = err?.message || $_('school.saveError');
    } finally {
      templatePreviewLoading = false;
    }
  }

  async function applyTemplateApplication() {
    if (!schoolId) return;
    if (!templateApplyForm.academic_year_id) {
      setValidationErrors('template-apply', { academic_year_id: $_('school.validation.yearRequired') });
      return;
    }
    clearValidation();
    error = null;
    notice = null;
    templateApplyLoading = true;
    try {
      templateApplyResult = await api.post('/school/default-subject-templates/apply', templateApplyPayload(), schoolOptions());
      templatePreviewResult = null;
      notice = $_('school.defaults.applyComplete');
      await refresh();
    } catch (err: any) {
      error = err?.message || $_('school.saveError');
    } finally {
      templateApplyLoading = false;
    }
  }

  function cancelEdit() {
    if (editingPath) resetForm(editingPath);
    editingPath = null;
    editingId = null;
    notice = null;
    clearValidation();
  }

  function selectTab(key: string) {
    editingPath = null;
    editingId = null;
    notice = null;
    clearValidation();
    activeTab = key;
    if (key === 'students') ensureStudentsLoaded();
  }

  // Load a row's current values into its form and switch that block into edit mode.
  function editRow(path: string, form: any, row: Row) {
    editingPath = path;
    editingId = row.id;
    form.code = row.code;
    form.name = row.name;
    form.name_ar = row.name_ar ?? '';
    form.sort_order = row.sort_order;
    form.status = row.status;
    if (path === 'academic-years') {
      form.is_current = Boolean(row.is_current);
      form.start_date = row.start_date ?? '';
      form.end_date = row.end_date ?? '';
    }
    if (path === 'grade-levels') form.education_stage_id = idStr(row.education_stage_id);
    if (path === 'class-sections') {
      form.branch_campus_id = idStr(row.branch_campus_id);
      form.academic_year_id = idStr(row.academic_year_id);
      form.grade_level_id = idStr(row.grade_level_id);
    }
    if (path === 'subject-groups') {
      form.academic_year_id = idStr(row.academic_year_id);
      form.class_section_id = idStr(row.class_section_id);
      form.grade_level_id = idStr(row.grade_level_id);
      form.subject_id = idStr(row.subject_id);
      form.enrolment_policy = row.enrolment_policy || 'explicit_only';
      groupContextMode = row.class_section_id ? 'section' : 'grade';
      lastAutoGroupCode = '';
      lastAutoGroupName = '';
    }
    if (path === 'students') {
      studentForm.external_ref = (row as any).external_ref ?? '';
      studentForm.first_name = (row as any).first_name ?? '';
      studentForm.last_name = (row as any).last_name ?? '';
      studentForm.preferred_name = (row as any).preferred_name ?? '';
      studentForm.name_ar = row.name_ar ?? '';
      studentForm.date_of_birth = (row as any).date_of_birth ?? '';
      studentForm.gender = (row as any).gender ?? '';
      studentForm.status = row.status;
    }
  }

  function groupAutoDefaults() {
    if (!groupForm.academic_year_id || !groupForm.subject_id) return null;
    const subject = findRow(subjects, groupForm.subject_id);
    if (!subject) return null;
    const context = groupContextMode === 'section' ? findRow(sections, groupForm.class_section_id) : findRow(levels, groupForm.grade_level_id);
    if (!context) return null;
    const grade = groupContextMode === 'section' ? findRow(levels, context.grade_level_id) : context;
    const contextCode = groupContextMode === 'section' ? `${compactCode(grade?.code)}${compactCode(context.code)}` : compactCode(context.code);
    return {
      code: `${contextCode}-${compactCode(subject.code)}`,
      name: `${context.name} ${subject.name}`.trim()
    };
  }

  function compactCode(value?: string | null) {
    return String(value || '').toUpperCase().replace(/[^A-Z0-9]/g, '');
  }

  function applyGroupAutoDefaults() {
    if (editingPath === 'subject-groups') return;
    const defaults = groupAutoDefaults();
    if (!defaults) {
      if (lastAutoGroupCode && groupForm.code === lastAutoGroupCode) groupForm.code = '';
      if (lastAutoGroupName && groupForm.name === lastAutoGroupName) groupForm.name = '';
      lastAutoGroupCode = '';
      lastAutoGroupName = '';
      return;
    }

    if (!groupForm.code.trim() || groupForm.code === lastAutoGroupCode) {
      groupForm.code = defaults.code;
      lastAutoGroupCode = defaults.code;
    }
    if (!groupForm.name.trim() || groupForm.name === lastAutoGroupName) {
      groupForm.name = defaults.name;
      lastAutoGroupName = defaults.name;
    }
  }

  function setGroupContextMode(mode: 'section' | 'grade') {
    groupContextMode = mode;
    if (mode === 'section') {
      groupForm.grade_level_id = '';
      if (!editingPath) groupForm.enrolment_policy = 'default_for_section';
    } else {
      groupForm.class_section_id = '';
      if (groupForm.enrolment_policy === 'default_for_section') groupForm.enrolment_policy = 'explicit_only';
    }
    applyGroupAutoDefaults();
  }

  function eligibleBulkSections() {
    return sections.filter(
      (section) =>
        section.status === 'active' &&
        section.academic_year_id === Number(bulkGroupForm.academic_year_id) &&
        section.grade_level_id === Number(bulkGroupForm.grade_level_id)
    );
  }

  function toggleBulkSection(sectionId: number, checked: boolean) {
    const id = String(sectionId);
    if (checked && !bulkGroupForm.class_section_ids.includes(id)) {
      bulkGroupForm.class_section_ids = [...bulkGroupForm.class_section_ids, id];
    }
    if (!checked) {
      bulkGroupForm.class_section_ids = bulkGroupForm.class_section_ids.filter((current) => current !== id);
    }
  }

  function selectAllBulkSections() {
    bulkGroupForm.class_section_ids = eligibleBulkSections().map((section) => String(section.id));
  }

  // Create when not editing this block, otherwise update the row being edited.
  async function saveVia(path: string, payload: any, reset: () => void) {
    if (!schoolId) return;
    saving = true;
    error = null;
    notice = null;
    clearValidation();
    try {
      if (editingPath === path && editingId != null) {
        await api.put(`/school/${path}/${editingId}`, payload, schoolOptions());
      } else {
        const created = await api.post(`/school/${path}`, payload, schoolOptions());
        if (created?.restored) notice = $_('school.restored');
      }
      reset();
      editingPath = null;
      editingId = null;
      await refresh();
    } catch (err: any) {
      error = err?.message || $_('school.saveError');
    } finally {
      saving = false;
    }
  }

  function saveRow(path: string, form: any) {
    if (!validateRequiredText(path, form)) return;
    return saveVia(path, payloadFrom(form), () => resetForm(path));
  }

  function yearPayload() {
    return {
      ...payloadFrom(yearForm),
      is_current: Boolean(yearForm.is_current),
      start_date: yearForm.start_date || null,
      end_date: yearForm.end_date || null
    };
  }

  function saveYear() {
    if (!validateRequiredText('academic-years', yearForm)) return;
    return saveVia('academic-years', yearPayload(), () => resetForm('academic-years'));
  }

  async function archiveRow(path: string, row: { id: number }) {
    if (!schoolId) return;
    if (editingPath === path && editingId === row.id) cancelEdit();
    saving = true;
    error = null;
    notice = null;
    try {
      await api.delete(`/school/${path}/${row.id}`, schoolOptions());
      await refresh();
    } catch (err: any) {
      error = err?.message || $_('school.saveError');
    } finally {
      saving = false;
    }
  }

  function studentPayload() {
    return {
      external_ref: studentForm.external_ref || null,
      first_name: studentForm.first_name,
      last_name: studentForm.last_name,
      preferred_name: studentForm.preferred_name || null,
      name_ar: studentForm.name_ar || null,
      date_of_birth: studentForm.date_of_birth || null,
      gender: studentForm.gender || null,
      status: studentForm.status
    };
  }

  function editStudent(student: Student) {
    editingPath = 'students';
    editingId = student.id;
    selectedStudentId = student.id;
    studentForm = {
      external_ref: student.external_ref ?? '',
      first_name: student.first_name,
      last_name: student.last_name,
      preferred_name: student.preferred_name ?? '',
      name_ar: student.name_ar ?? '',
      date_of_birth: student.date_of_birth ?? '',
      gender: student.gender ?? '',
      status: student.status
    };
    loadStudentEnrolments(student.id);
  }

  async function saveStudent() {
    const errors: Record<string, string> = {};
    if (!studentForm.first_name.trim()) errors.first_name = $_('school.validation.firstNameRequired');
    if (!studentForm.last_name.trim()) errors.last_name = $_('school.validation.lastNameRequired');
    if (!studentForm.gender.trim()) studentForm.gender = '';
    if (Object.keys(errors).length) {
      setValidationErrors('students', errors);
      return;
    }
    if (!schoolId) return;
    saving = true;
    error = null;
    notice = null;
    clearValidation();
    try {
      const saved = editingPath === 'students' && editingId
        ? await api.put(`/school/students/${editingId}`, studentPayload(), schoolOptions())
        : await api.post('/school/students', studentPayload(), schoolOptions());
      notice = saved?.restored ? $_('school.restored') : editingPath === 'students' && editingId ? $_('school.students.updated') : $_('school.students.created');
      selectedStudentId = saved.id;
      upsertStudentRow(saved);
      resetForm('students');
      editingPath = null;
      editingId = null;
      await loadStudentEnrolments(saved.id);
      await refresh();
    } catch (err: any) {
      error = err?.message || $_('school.students.saveError');
    } finally {
      saving = false;
    }
  }

  async function archiveStudent(student: Student) {
    if (!schoolId || !confirm($_('school.students.archiveConfirm'))) return;
    saving = true;
    error = null;
    try {
      await api.delete(`/school/students/${student.id}`, schoolOptions());
      if (selectedStudentId === student.id) {
        selectedStudentId = null;
        studentEnrolments = [];
      }
      removeStudentRow(student.id);
      notice = $_('school.students.archived');
      await refresh();
    } catch (err: any) {
      error = err?.message || $_('school.students.saveError');
    } finally {
      saving = false;
    }
  }

  async function removeStudentMistake(student: Student) {
    if (!schoolId || !confirm($_('school.students.removeMistakeConfirm'))) return;
    saving = true;
    error = null;
    notice = null;
    try {
      await api.delete(`/school/students/${student.id}/remove-mistake`, schoolOptions());
      if (selectedStudentId === student.id) {
        selectedStudentId = null;
        studentEnrolments = [];
      }
      removeStudentRow(student.id);
      notice = $_('school.students.removedMistake');
      await refresh();
    } catch (err: any) {
      error = err?.message || $_('school.students.removeMistakeError');
    } finally {
      saving = false;
    }
  }

  async function downloadImportTemplate() {
    if (!schoolId) return;
    error = null;
    try {
      const blob = await api.download('/school/students/import-template', schoolOptions());
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'student_import_template.csv';
      link.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      error = err?.message || $_('school.imports.templateError');
    }
  }

  function handleImportFileChange(event: Event) {
    const target = event.target as HTMLInputElement;
    importFile = target.files?.[0] || null;
  }

  async function uploadImportFile() {
    if (!schoolId || !importFile) return;
    importUploading = true;
    error = null;
    notice = null;
    try {
      const formData = new FormData();
      formData.append('file', importFile);
      studentImport = await api.upload('/school/students/imports', formData, schoolOptions());
    } catch (err: any) {
      error = err?.message || $_('school.imports.uploadError');
    } finally {
      importUploading = false;
    }
  }

  async function commitImport() {
    if (!schoolId || !studentImport) return;
    importCommitting = true;
    error = null;
    notice = null;
    try {
      studentImport = await api.post(`/school/students/imports/${studentImport.id}/commit`, {}, schoolOptions());
      notice = $_('school.imports.committed');
      await ensureStudentsLoaded();
      await refresh();
    } catch (err: any) {
      error = err?.message || $_('school.imports.commitError');
    } finally {
      importCommitting = false;
    }
  }

  async function discardImport() {
    if (!schoolId || !studentImport) return;
    try {
      await api.post(`/school/students/imports/${studentImport.id}/discard`, {}, schoolOptions());
    } catch (err: any) {
      error = err?.message || $_('school.imports.discardError');
      return;
    }
    studentImport = null;
    importFile = null;
  }

  function importRowRowClass(row: ImportRow) {
    if (row.action === 'error') return 'bg-red-50';
    if (row.action === 'skip') return 'bg-white';
    return 'bg-emerald-50';
  }

  function importActionLabel(action: ImportRow['action']) {
    return $_(`school.imports.actionLabel.${action}`);
  }

  const IMPORT_SUMMARY_BADGE_STYLES: Record<string, string> = {
    create: 'bg-emerald-100 text-emerald-800',
    update: 'bg-sky-100 text-sky-800',
    move: 'bg-amber-100 text-amber-800',
    restore: 'bg-indigo-100 text-indigo-800',
    skip: 'bg-slate-200 text-slate-700',
    error: 'bg-red-100 text-red-800'
  };

  function importSummaryBadges() {
    if (!studentImport) return [];
    return Object.entries(IMPORT_SUMMARY_BADGE_STYLES).map(([key, classes]) => ({
      classes,
      label: $_(`school.imports.summary.${key}`),
      count: studentImport?.summary[key] || 0
    }));
  }

  function importRowGuardianSummaries(row: ImportRow): string[] {
    const summaries: string[] = [];
    for (const slot of [1, 2] as const) {
      const name = row[`guardian${slot}_name`];
      const email = row[`guardian${slot}_email`];
      const relationship = row[`guardian${slot}_relationship`];
      if (!name && !email && !relationship) continue;
      const parts = [name || $_('school.imports.guardianNoName'), email, relationship].filter(Boolean);
      summaries.push(`${$_('school.imports.guardianSlot')} ${slot}: ${parts.join(' · ')}`);
    }
    return summaries;
  }

  async function downloadTeacherImportTemplate() {
    if (!schoolId) return;
    error = null;
    try {
      const blob = await api.download('/school/teachers/import-template', schoolOptions());
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'teacher_import_template.csv';
      link.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      error = err?.message || $_('school.teacherImports.templateError');
    }
  }

  function handleTeacherImportFileChange(event: Event) {
    const target = event.target as HTMLInputElement;
    teacherImportFile = target.files?.[0] || null;
  }

  async function uploadTeacherImportFile() {
    if (!schoolId || !teacherImportFile) return;
    teacherImportUploading = true;
    error = null;
    notice = null;
    try {
      const formData = new FormData();
      formData.append('file', teacherImportFile);
      teacherImport = await api.upload('/school/teachers/imports', formData, schoolOptions());
    } catch (err: any) {
      error = err?.message || $_('school.teacherImports.uploadError');
    } finally {
      teacherImportUploading = false;
    }
  }

  async function commitTeacherImport() {
    if (!schoolId || !teacherImport) return;
    teacherImportCommitting = true;
    error = null;
    notice = null;
    try {
      teacherImport = await api.post(`/school/teachers/imports/${teacherImport.id}/commit`, {}, schoolOptions());
      notice = $_('school.teacherImports.committed');
      await refresh();
    } catch (err: any) {
      error = err?.message || $_('school.teacherImports.commitError');
    } finally {
      teacherImportCommitting = false;
    }
  }

  async function discardTeacherImport() {
    if (!schoolId || !teacherImport) return;
    try {
      await api.post(`/school/teachers/imports/${teacherImport.id}/discard`, {}, schoolOptions());
    } catch (err: any) {
      error = err?.message || $_('school.teacherImports.discardError');
      return;
    }
    teacherImport = null;
    teacherImportFile = null;
  }

  function teacherImportRowRowClass(row: TeacherImportRow) {
    if (row.action === 'error') return 'bg-red-50';
    if (row.action === 'skip') return 'bg-white';
    return 'bg-emerald-50';
  }

  function teacherImportActionLabel(action: TeacherImportRow['action']) {
    return $_(`school.teacherImports.actionLabel.${action}`);
  }

  const TEACHER_IMPORT_SUMMARY_BADGE_STYLES: Record<string, string> = {
    create: 'bg-emerald-100 text-emerald-800',
    update: 'bg-sky-100 text-sky-800',
    skip: 'bg-slate-200 text-slate-700',
    error: 'bg-red-100 text-red-800'
  };

  function teacherImportSummaryBadges() {
    if (!teacherImport) return [];
    return Object.entries(TEACHER_IMPORT_SUMMARY_BADGE_STYLES).map(([key, classes]) => ({
      classes,
      label: $_(`school.teacherImports.summary.${key}`),
      count: teacherImport?.summary[key] || 0
    }));
  }

  async function loadStudentEnrolments(studentId: number) {
    if (!schoolId) return;
    loadingEnrolments = true;
    try {
      studentEnrolments = await api.get(`/school/students/${studentId}/enrolments`, schoolOptions());
    } catch (err: any) {
      error = err?.message || $_('school.students.enrolmentError');
    } finally {
      loadingEnrolments = false;
    }
  }

  async function loadClassRoster(showValidation = true) {
    if (!schoolId) return;
    if (!rosterSectionId) {
      if (showValidation) setValidationErrors('class-roster', { class_section_id: $_('school.validation.sectionRequired') });
      return;
    }
    rosterLoading = true;
    error = null;
    clearValidation();
    try {
      classRoster = await api.get(`/school/class-sections/${rosterSectionId}/roster`, schoolOptions());
    } catch (err: any) {
      error = err?.message || $_('school.rosters.loadError');
    } finally {
      rosterLoading = false;
    }
  }

  async function loadGroupRoster(showValidation = true) {
    if (!schoolId) return;
    if (!groupRosterId) {
      if (showValidation) setValidationErrors('group-roster', { subject_group_id: $_('school.validation.subjectGroupRequired') });
      return;
    }
    groupRosterLoading = true;
    error = null;
    clearValidation();
    try {
      await ensureStudentsLoaded();
      groupRoster = await api.get(`/school/subject-groups/${groupRosterId}/students`, schoolOptions());
    } catch (err: any) {
      error = err?.message || $_('school.groups.rosterLoadError');
    } finally {
      groupRosterLoading = false;
    }
  }

  async function addGroupRosterStudent() {
    if (!groupRosterId || !groupRosterStudentId) {
      setValidationErrors('group-roster-add', { student_id: $_('school.validation.studentRequired') });
      return;
    }
    saving = true;
    error = null;
    clearValidation();
    try {
      await api.post(`/school/students/${groupRosterStudentId}/enrolments`, { subject_group_id: Number(groupRosterId) }, schoolOptions());
      groupRosterStudentId = '';
      notice = $_('school.students.enrolled');
      await loadGroupRoster(false);
      await refresh();
    } catch (err: any) {
      error = err?.message || $_('school.students.enrolmentError');
    } finally {
      saving = false;
    }
  }

  async function removeGroupRosterStudent(student: SubjectGroupRoster['students'][number]) {
    if (!groupRosterId) return;
    saving = true;
    error = null;
    try {
      if (student.source === 'default') {
        await api.post(`/school/students/${student.id}/enrolments`, { subject_group_id: Number(groupRosterId), kind: 'excluded' }, schoolOptions());
      } else if (student.enrolment_id) {
        await api.delete(`/school/enrolments/${student.enrolment_id}`, schoolOptions());
      }
      notice = $_('school.groups.rosterUpdated');
      await loadGroupRoster(false);
      await refresh();
    } catch (err: any) {
      error = err?.message || $_('school.students.enrolmentError');
    } finally {
      saving = false;
    }
  }

  async function includeGroupRosterStudent(student: SubjectGroupRoster['excluded_students'][number]) {
    saving = true;
    error = null;
    try {
      await api.delete(`/school/enrolments/${student.enrolment_id}`, schoolOptions());
      notice = $_('school.groups.rosterUpdated');
      await loadGroupRoster(false);
      await refresh();
    } catch (err: any) {
      error = err?.message || $_('school.students.enrolmentError');
    } finally {
      saving = false;
    }
  }

  async function openStudentFromRoster(student: Student) {
    studentSearch = '';
    studentSectionFilter = '';
    await ensureStudentsLoaded();
    upsertStudentRow(student);
    activeTab = 'students';
    await selectStudent(student);
    await refresh();
  }

  async function selectStudent(student: Student) {
    selectedStudentId = student.id;
    await loadStudentEnrolments(student.id);
  }

  function selectStudentForAction(student: Student) {
    selectedStudentId = student.id;
    moveSectionId = '';
    classEnrolmentSectionId = '';
    subjectEnrolmentGroupId = '';
    void loadStudentEnrolments(student.id);
    queueMicrotask(() => document.getElementById('student-detail-panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
  }

  async function addClassEnrolment() {
    if (!selectedStudentId || !classEnrolmentSectionId) {
      setValidationErrors('student-class-enrolment', { class_section_id: $_('school.validation.sectionRequired') });
      return;
    }
    saving = true;
    error = null;
    clearValidation();
    try {
      await api.post(`/school/students/${selectedStudentId}/enrolments`, { class_section_id: Number(classEnrolmentSectionId) }, schoolOptions());
      classEnrolmentSectionId = '';
      notice = $_('school.students.enrolled');
      await loadStudentEnrolments(selectedStudentId);
      await refresh();
    } catch (err: any) {
      error = err?.message || $_('school.students.enrolmentError');
    } finally {
      saving = false;
    }
  }

  async function addSubjectEnrolment() {
    if (!selectedStudentId || !subjectEnrolmentGroupId) {
      setValidationErrors('student-subject-enrolment', { subject_group_id: $_('school.validation.subjectGroupRequired') });
      return;
    }
    saving = true;
    error = null;
    clearValidation();
    try {
      await api.post(`/school/students/${selectedStudentId}/enrolments`, { subject_group_id: Number(subjectEnrolmentGroupId) }, schoolOptions());
      subjectEnrolmentGroupId = '';
      notice = $_('school.students.enrolled');
      await loadStudentEnrolments(selectedStudentId);
      await refresh();
    } catch (err: any) {
      error = err?.message || $_('school.students.enrolmentError');
    } finally {
      saving = false;
    }
  }

  async function moveStudentSection() {
    if (!selectedStudentId || !moveSectionId) {
      setValidationErrors('student-move', { class_section_id: $_('school.validation.sectionRequired') });
      return;
    }
    if (!confirm($_('school.students.moveConfirm'))) return;
    saving = true;
    error = null;
    clearValidation();
    try {
      await api.post(`/school/students/${selectedStudentId}/move-section`, { class_section_id: Number(moveSectionId) }, schoolOptions());
      moveSectionId = '';
      notice = $_('school.students.moved');
      await loadStudentEnrolments(selectedStudentId);
      await refresh();
    } catch (err: any) {
      error = err?.message || $_('school.students.enrolmentError');
    } finally {
      saving = false;
    }
  }

  async function closeEnrolment(enrolmentId: number) {
    if (!schoolId) return;
    saving = true;
    error = null;
    try {
      await api.delete(`/school/enrolments/${enrolmentId}`, schoolOptions());
      notice = $_('school.students.closedEnrolment');
      if (selectedStudentId) await loadStudentEnrolments(selectedStudentId);
      await refresh();
    } catch (err: any) {
      error = err?.message || $_('school.students.enrolmentError');
    } finally {
      saving = false;
    }
  }

  async function saveSettings() {
    if (!schoolId) return;
    const label = labelChoice === 'custom' ? customLabel : labelChoice;
    saving = true;
    error = null;
    try {
      await api.put('/school/settings', { grade_level_label: label || 'Grade' }, schoolOptions());
      await refresh();
    } catch (err: any) {
      error = err?.message || $_('school.saveError');
    } finally {
      saving = false;
    }
  }

  function sectionPayload() {
    return {
      ...payloadFrom(sectionForm),
      branch_campus_id: Number(sectionForm.branch_campus_id),
      academic_year_id: Number(sectionForm.academic_year_id),
      grade_level_id: Number(sectionForm.grade_level_id)
    };
  }

  function saveSection() {
    const errors: Record<string, string> = {};
    if (!sectionForm.branch_campus_id) errors.branch_campus_id = $_('school.validation.branchRequired');
    if (!sectionForm.academic_year_id) errors.academic_year_id = $_('school.validation.yearRequired');
    if (!sectionForm.grade_level_id) errors.grade_level_id = $_('school.validation.gradeRequired');
    if (!sectionForm.code?.trim()) errors.code = $_('school.validation.codeRequired');
    if (!sectionForm.name?.trim()) errors.name = $_('school.validation.nameRequired');
    if (Object.keys(errors).length) {
      setValidationErrors('class-sections', errors);
      return;
    }
    clearValidation();
    return saveVia('class-sections', sectionPayload(), () => resetForm('class-sections'));
  }

  function levelPayload() {
    return {
      ...payloadFrom(levelForm),
      education_stage_id: levelForm.education_stage_id ? Number(levelForm.education_stage_id) : null
    };
  }

  function saveLevel() {
    if (!validateRequiredText('grade-levels', levelForm)) return;
    return saveVia('grade-levels', levelPayload(), () => resetForm('grade-levels'));
  }

  async function createQuickSections() {
    if (!schoolId) return;
    const labels = quickLabels.split(',').map((label) => label.trim()).filter(Boolean);
    if (!labels.length) return;
    saving = true;
    error = null;
    clearValidation();
    try {
      for (const label of labels) {
        const level = levelName(sectionForm.grade_level_id);
        await api.post('/school/class-sections', {
          ...sectionPayload(),
          code: label,
          name: `${level} ${label}`.trim()
        }, schoolOptions());
      }
      await refresh();
    } catch (err: any) {
      error = err?.message || $_('school.saveError');
    } finally {
      saving = false;
    }
  }

  function groupPayload() {
    return {
      ...payloadFrom(groupForm),
      academic_year_id: Number(groupForm.academic_year_id),
      class_section_id: groupContextMode === 'section' && groupForm.class_section_id ? Number(groupForm.class_section_id) : null,
      grade_level_id: groupContextMode === 'grade' && groupForm.grade_level_id ? Number(groupForm.grade_level_id) : null,
      subject_id: Number(groupForm.subject_id),
      enrolment_policy: groupForm.enrolment_policy
    };
  }

  function saveGroup() {
    const errors: Record<string, string> = {};
    if (!groupForm.academic_year_id) errors.academic_year_id = $_('school.validation.yearRequired');
    if (groupContextMode === 'section' && !groupForm.class_section_id) errors.class_section_id = $_('school.validation.sectionRequired');
    if (groupContextMode === 'grade' && !groupForm.grade_level_id) errors.grade_level_id = $_('school.validation.gradeRequired');
    if (!groupForm.subject_id) errors.subject_id = $_('school.validation.subjectRequired');
    if (groupForm.enrolment_policy === 'default_for_section' && groupContextMode !== 'section') errors.enrolment_policy = $_('school.groups.defaultForSection');
    if (groupForm.enrolment_policy === 'default_for_grade' && groupContextMode !== 'grade') errors.enrolment_policy = $_('school.groups.defaultForGrade');
    if (!groupForm.code?.trim()) errors.code = $_('school.validation.codeRequired');
    if (!groupForm.name?.trim()) errors.name = $_('school.validation.nameRequired');
    if (Object.keys(errors).length) {
      setValidationErrors('subject-groups', errors);
      return;
    }
    clearValidation();
    return saveVia('subject-groups', groupPayload(), () => resetForm('subject-groups'));
  }

  async function bulkCreateSubjectGroups() {
    if (!schoolId) return;
    const errors: Record<string, string> = {};
    if (!bulkGroupForm.academic_year_id) errors.academic_year_id = $_('school.validation.yearRequired');
    if (!bulkGroupForm.grade_level_id) errors.grade_level_id = $_('school.validation.gradeRequired');
    if (!bulkGroupForm.subject_id) errors.subject_id = $_('school.validation.subjectRequired');
    if (!bulkGroupForm.class_section_ids.length) errors.class_section_ids = $_('school.validation.sectionsRequired');
    if (Object.keys(errors).length) {
      setValidationErrors('bulk-subject-groups', errors);
      return;
    }
    saving = true;
    error = null;
    notice = null;
    bulkGroupResult = null;
    clearValidation();
    try {
      bulkGroupResult = await api.post('/school/subject-groups/bulk-section', {
        academic_year_id: Number(bulkGroupForm.academic_year_id),
        grade_level_id: Number(bulkGroupForm.grade_level_id),
        subject_id: Number(bulkGroupForm.subject_id),
        enrolment_policy: bulkGroupForm.enrolment_policy,
        class_section_ids: bulkGroupForm.class_section_ids.map(Number)
      }, schoolOptions());
      notice = $_('school.groups.bulkComplete');
      await refresh();
    } catch (err: any) {
      error = err?.message || $_('school.saveError');
    } finally {
      saving = false;
    }
  }

  async function inviteTeacher() {
    if (!schoolId) return;
    if (!teacherInviteEmail.trim()) {
      setValidationErrors('teachers', { email: $_('school.validation.teacherEmailRequired') });
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(teacherInviteEmail.trim())) {
      setValidationErrors('teachers', { email: $_('school.validation.teacherEmailInvalid') });
      return;
    }
    saving = true;
    error = null;
    notice = null;
    clearValidation();
    try {
      const invite = await api.post('/school/teachers/invites', { email: teacherInviteEmail }, schoolOptions());
      teacherInviteEmail = '';
      if (invite?.warning) notice = invite.warning;
      await refresh();
    } catch (err: any) {
      error = err?.message || $_('school.teachers.inviteError');
    } finally {
      saving = false;
    }
  }

  async function revokeTeacherInvite(inviteId: number) {
    if (!schoolId) return;
    saving = true;
    error = null;
    try {
      await api.delete(`/school/teachers/invites/${inviteId}`, schoolOptions());
      await refresh();
    } catch (err: any) {
      error = err?.message || $_('school.teachers.revokeError');
    } finally {
      saving = false;
    }
  }

  async function assignHomeroom(teacher: Teacher) {
    const sectionId = Number(homeroomSelections[teacher.membership_id]);
    if (!schoolId) return;
    if (!sectionId) {
      setValidationErrors(`homeroom-${teacher.membership_id}`, { class_section_id: $_('school.validation.sectionRequired') });
      return;
    }
    saving = true;
    error = null;
    clearValidation();
    try {
      await api.post(`/school/teachers/${teacher.membership_id}/assignments`, { role: 'homeroom', class_section_id: sectionId }, schoolOptions());
      homeroomSelections[teacher.membership_id] = '';
      await refresh();
    } catch (err: any) {
      error = err?.message || $_('school.teachers.assignmentError');
    } finally {
      saving = false;
    }
  }

  async function assignSubject(teacher: Teacher) {
    const groupId = Number(groupSelections[teacher.membership_id]);
    if (!schoolId) return;
    if (!groupId) {
      setValidationErrors(`subject-${teacher.membership_id}`, { subject_group_id: $_('school.validation.subjectGroupRequired') });
      return;
    }
    saving = true;
    error = null;
    clearValidation();
    try {
      await api.post(`/school/teachers/${teacher.membership_id}/assignments`, { role: 'subject', subject_group_id: groupId }, schoolOptions());
      groupSelections[teacher.membership_id] = '';
      await refresh();
    } catch (err: any) {
      error = err?.message || $_('school.teachers.assignmentError');
    } finally {
      saving = false;
    }
  }

  async function closeAssignment(assignmentId: number) {
    if (!schoolId) return;
    saving = true;
    error = null;
    try {
      await api.delete(`/school/assignments/${assignmentId}`, schoolOptions());
      await refresh();
    } catch (err: any) {
      error = err?.message || $_('school.teachers.assignmentError');
    } finally {
      saving = false;
    }
  }

  async function deactivateTeacher(teacher: Teacher) {
    if (!schoolId || !confirm($_('school.teachers.deactivateConfirm'))) return;
    saving = true;
    error = null;
    try {
      await api.post(`/school/teachers/${teacher.membership_id}/deactivate`, {}, schoolOptions());
      await refresh();
    } catch (err: any) {
      error = err?.message || $_('school.teachers.deactivateError');
    } finally {
      saving = false;
    }
  }

  function assignmentName(assignment: StaffAssignment) {
    if (assignment.role === 'homeroom') return assignment.class_section?.name || rowName(sections, assignment.class_section_id);
    return assignment.subject_group?.name || rowName(groups, assignment.subject_group_id);
  }

  function selectedStudent() {
    return students.find((student) => student.id === selectedStudentId) || null;
  }

  function studentFilterActive() {
    return Boolean(studentSearch.trim() || studentSectionFilter);
  }

  function studentListEmptyKey() {
    if (students.length > 0) return '';
    return studentFilterActive() ? 'school.students.emptyFiltered' : 'school.students.empty';
  }

  function enrolmentName(enrolment: Enrolment) {
    return enrolment.class_section?.name || enrolment.subject_group?.name || rowName(sections, enrolment.class_section_id) || rowName(groups, enrolment.subject_group_id);
  }

  function enrolmentType(enrolment: Enrolment) {
    const type = enrolment.class_section_id ? $_('school.students.classSection') : $_('school.students.subjectGroup');
    return enrolment.kind === 'excluded' ? `${type} · ${$_('school.groups.excluded')}` : type;
  }

  function policyOptions() {
    return [
      { id: 'explicit_only', name: $_('school.groups.manualList') },
      { id: 'default_for_section', name: $_('school.groups.allOfSection') },
      { id: 'default_for_grade', name: $_('school.groups.allOfGrade') }
    ];
  }

  function groupPolicyLabel(group?: Row | null) {
    if (!group) return '';
    if (group.enrolment_policy === 'default_for_section') return $_('school.groups.allOfNamedSection', { values: { section: rowName(sections, group.class_section_id) } });
    if (group.enrolment_policy === 'default_for_grade') return $_('school.groups.allOfNamedGrade', { values: { grade: levelName(group.grade_level_id) } });
    return $_('school.groups.manualList');
  }

  function sourceLabel(source?: string) {
    if (source === 'default') return $_('school.groups.sourceDefault');
    if (source === 'excluded') return $_('school.groups.excluded');
    return $_('school.groups.sourceExplicit');
  }

  function groupRosterTitle() {
    return groupRoster?.subject_group?.name || rowName(groups, groupRosterId);
  }

  function genderOptions() {
    return [
      { value: '', label: $_('school.select') },
      { value: 'male', label: $_('school.students.genderMale') },
      { value: 'female', label: $_('school.students.genderFemale') },
      { value: 'other', label: $_('school.students.genderOther') },
      { value: 'unspecified', label: $_('school.students.genderUnspecified') }
    ];
  }

  function studentCurrentClass(student: Student) {
    return student.current_class_section?.name || $_('school.students.notEnrolled');
  }

  function studentActionLabel(student: Student) {
    return student.current_class_section ? $_('school.students.moveClass') : $_('school.students.enrol');
  }

  function teacherName(ref?: TeacherRef | null) {
    if (!ref) return $_('school.rosters.notAssigned');
    return ref.user.name ? `${ref.user.name} (${ref.user.email})` : ref.user.email;
  }

  function classRosterTitle() {
    return classRoster?.class_section?.name || rowName(sections, rosterSectionId);
  }

  function upsertStudentRow(row: Student) {
    students = [row, ...students.filter((student) => student.id !== row.id)];
  }

  function removeStudentRow(studentId: number) {
    students = students.filter((student) => student.id !== studentId);
  }

  $effect(() => {
    groupForm.academic_year_id;
    groupForm.class_section_id;
    groupForm.grade_level_id;
    groupForm.subject_id;
    groupContextMode;
    sections.length;
    levels.length;
    subjects.length;
    applyGroupAutoDefaults();
    applyNewSortDefaults();
  });

  $effect(() => {
    const key = `${bulkGroupForm.academic_year_id}:${bulkGroupForm.grade_level_id}:${sections.length}`;
    if (key !== lastBulkSectionKey) {
      lastBulkSectionKey = key;
      selectAllBulkSections();
    }
  });

  onMount(init);
</script>

<svelte:head>
  <title>{$_('school.title')}</title>
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
      <h1 class="text-2xl font-black text-slate-900">{$_('school.accessDeniedTitle')}</h1>
      <p class="mt-3 text-slate-600">{error || $_('school.accessDenied')}</p>
    </div>
  </section>
{:else}
  <section class="mx-auto max-w-7xl px-4 py-8">
    <div class="flex flex-col gap-4 border-b border-slate-200 pb-5 md:flex-row md:items-end md:justify-between">
      <div>
        <p class="eyebrow">{schoolName}</p>
        <h1 class="mt-2 text-3xl font-black text-slate-900">{$_('school.heading')}</h1>
        <p class="mt-2 max-w-2xl text-slate-600">{$_('school.intro')}</p>
      </div>
      <div class="rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700">
        {setupComplete ? $_('school.setupComplete') : $_('school.setupInProgress')}
      </div>
    </div>

    {#if error}
      <div class="mt-5 rounded-lg border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">{error}</div>
    {/if}

    {#if notice}
      <div class="mt-5 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm font-semibold text-emerald-700">{notice}</div>
    {/if}

    <div class="mt-6 grid gap-6 lg:grid-cols-[220px_minmax(0,1fr)]">
      <nav class="flex gap-2 overflow-x-auto lg:block lg:overflow-visible">
        {#each tabs as tab}
          <button
            type="button"
            class={`whitespace-nowrap rounded-lg px-3 py-2 text-left text-sm font-semibold transition lg:mb-1 lg:block lg:w-full ${activeTab === tab.key ? 'bg-slate-900 text-white' : 'bg-white text-slate-600 hover:bg-slate-100'}`}
            onclick={() => selectTab(tab.key)}
          >
            {$_(tab.label)}
          </button>
        {/each}
      </nav>

      <div class="min-w-0">
        {#if activeTab === 'checklist'}
          <div class="grid gap-3 sm:grid-cols-2">
            {#each checklist as item}
              <div class="rounded-lg border border-slate-200 bg-white p-4">
                <div class="flex items-start gap-3">
                  {#if item.complete}
                    <CheckCircle2 class="mt-0.5 h-5 w-5 text-emerald-600" />
                  {:else}
                    <Circle class="mt-0.5 h-5 w-5 text-slate-300" />
                  {/if}
                  <div>
                    <h2 class="font-bold text-slate-900">{item.label}</h2>
                    <p class="mt-1 text-sm text-slate-500">{item.count} {$_('school.records')}</p>
                    {#if !item.required}
                      <p class="mt-1 text-xs font-semibold uppercase tracking-wide text-slate-400">{$_('school.optional')}</p>
                    {/if}
                  </div>
                </div>
              </div>
            {/each}
          </div>
        {:else if activeTab === 'settings'}
          <div class="rounded-lg border border-slate-200 bg-white p-5">
            <h2 class="text-lg font-black text-slate-900">{$_('school.settings.levelLabel')}</h2>
            <div class="mt-4 grid gap-3 sm:grid-cols-5">
              {#each ['Grade', 'Year', 'Form', 'Level'] as option}
                <label class="flex items-center gap-2 rounded-lg border border-slate-200 p-3 text-sm font-semibold">
                  <input type="radio" bind:group={labelChoice} value={option} />
                  {option}
                </label>
              {/each}
              <label class="flex items-center gap-2 rounded-lg border border-slate-200 p-3 text-sm font-semibold">
                <input type="radio" bind:group={labelChoice} value="custom" />
                {$_('school.custom')}
              </label>
            </div>
            {#if labelChoice === 'custom'}
              <input class="mt-4 w-full rounded-lg border border-slate-200 px-3 py-2" bind:value={customLabel} placeholder={$_('school.settings.customLabel')} />
            {/if}
            <button class="btn-hero mt-5 rounded-lg px-5 py-2" disabled={saving} onclick={saveSettings}>{$_('school.save')}</button>
          </div>
        {:else if activeTab === 'branches'}
          <CrudBlock title={$_('school.branches.title')} rows={branches} path="branches" bind:form={branchForm} {saving} editing={editingPath === 'branches'} errors={{ code: fieldError('branches', 'code'), name: fieldError('branches', 'name') }} onsubmit={() => saveRow('branches', branchForm)} onedit={(row) => editRow('branches', branchForm, row)} oncancel={cancelEdit} onarchive={archiveRow} />
        {:else if activeTab === 'stages'}
          <CrudBlock title={$_('school.stages.title')} rows={stages} path="education-stages" bind:form={stageForm} {saving} editing={editingPath === 'education-stages'} errors={{ code: fieldError('education-stages', 'code'), name: fieldError('education-stages', 'name') }} onsubmit={() => saveRow('education-stages', stageForm)} onedit={(row) => editRow('education-stages', stageForm, row)} oncancel={cancelEdit} onarchive={archiveRow} />
        {:else if activeTab === 'years'}
          <div class="rounded-lg border border-slate-200 bg-white p-5">
            <h2 class="text-lg font-black text-slate-900">{$_('school.years.title')}</h2>
            <div class="mt-4 grid gap-3 md:grid-cols-7">
              <TextInput label={$_('school.code')} bind:value={yearForm.code} error={fieldError('academic-years', 'code')} />
              <TextInput label={$_('school.nameEn')} bind:value={yearForm.name} error={fieldError('academic-years', 'name')} />
              <TextInput label={$_('school.nameAr')} bind:value={yearForm.name_ar} />
              <label class="block text-sm font-semibold text-slate-700">
                {$_('school.years.startDate')}
                <input type="date" class="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 font-normal" bind:value={yearForm.start_date} />
              </label>
              <label class="block text-sm font-semibold text-slate-700">
                {$_('school.years.endDate')}
                <input type="date" class="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 font-normal" bind:value={yearForm.end_date} />
              </label>
              <StatusInput bind:value={yearForm.status} />
              <label class="flex items-end gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700">
                <input type="checkbox" bind:checked={yearForm.is_current} />
                {$_('school.years.current')}
              </label>
            </div>
            <details class="mt-3 rounded-lg border border-slate-100 bg-slate-50 px-3 py-2">
              <summary class="cursor-pointer text-xs font-bold uppercase tracking-wide text-slate-500">{$_('school.advanced')}</summary>
              <div class="mt-3 max-w-xs">
                <NumberInput label={$_('school.sortOrderOptional')} bind:value={yearForm.sort_order} />
              </div>
            </details>
            <div class="mt-4 flex items-center gap-2">
              <button class="btn-hero inline-flex items-center gap-2 rounded-lg" disabled={saving} onclick={saveYear}>
                {#if editingPath === 'academic-years'}{$_('school.save')}{:else}<Plus class="h-4 w-4" />{$_('school.add')}{/if}
              </button>
              {#if editingPath === 'academic-years'}
                <button class="btn-secondary rounded-lg" disabled={saving} onclick={cancelEdit}>{$_('school.cancel')}</button>
              {/if}
            </div>
            <RowsTable rows={years} extra={(row) => `${row.is_current ? $_('school.years.current') : ''}${row.start_date || row.end_date ? ` · ${row.start_date || '-'} - ${row.end_date || '-'}` : ''}`} onedit={(row) => editRow('academic-years', yearForm, row)} onarchive={(row) => archiveRow('academic-years', row)} />
          </div>
        {:else if activeTab === 'levels'}
          <div class="rounded-lg border border-slate-200 bg-white p-5">
            <h2 class="text-lg font-black text-slate-900">{gradeLevelLabel} {$_('school.levels.title')}</h2>
            <div class="mt-4 grid gap-3 md:grid-cols-5">
              <TextInput label={$_('school.code')} bind:value={levelForm.code} error={fieldError('grade-levels', 'code')} />
              <TextInput label={$_('school.nameEn')} bind:value={levelForm.name} error={fieldError('grade-levels', 'name')} />
              <TextInput label={$_('school.nameAr')} bind:value={levelForm.name_ar} />
              <SelectInput label={$_('school.stages.single')} bind:value={levelForm.education_stage_id} rows={stages} optional />
              <StatusInput bind:value={levelForm.status} />
            </div>
            <details class="mt-3 rounded-lg border border-slate-100 bg-slate-50 px-3 py-2">
              <summary class="cursor-pointer text-xs font-bold uppercase tracking-wide text-slate-500">{$_('school.advanced')}</summary>
              <div class="mt-3 max-w-xs">
                <NumberInput label={$_('school.sortOrderOptional')} bind:value={levelForm.sort_order} />
              </div>
            </details>
            <div class="mt-4 flex items-center gap-2">
              <button class="btn-hero inline-flex items-center gap-2 rounded-lg" disabled={saving} onclick={saveLevel}>
                {#if editingPath === 'grade-levels'}{$_('school.save')}{:else}<Plus class="h-4 w-4" />{$_('school.add')}{/if}
              </button>
              {#if editingPath === 'grade-levels'}
                <button class="btn-secondary rounded-lg" disabled={saving} onclick={cancelEdit}>{$_('school.cancel')}</button>
              {/if}
            </div>
            <RowsTable rows={levels} extra={(row) => rowName(stages, row.education_stage_id)} onedit={(row) => editRow('grade-levels', levelForm, row)} onarchive={(row) => archiveRow('grade-levels', row)} />
          </div>
        {:else if activeTab === 'sections'}
          <div class="rounded-lg border border-slate-200 bg-white p-5">
            <h2 class="text-lg font-black text-slate-900">{$_('school.sections.title')}</h2>
            <div class="mt-4 grid gap-3 md:grid-cols-7">
              <SelectInput label={$_('school.branches.single')} bind:value={sectionForm.branch_campus_id} rows={branches} error={fieldError('class-sections', 'branch_campus_id')} />
              <SelectInput label={$_('school.years.single')} bind:value={sectionForm.academic_year_id} rows={years} error={fieldError('class-sections', 'academic_year_id')} />
              <SelectInput label={gradeLevelLabel} bind:value={sectionForm.grade_level_id} rows={levels} error={fieldError('class-sections', 'grade_level_id')} />
              <TextInput label={$_('school.sectionLabel')} bind:value={sectionForm.code} error={fieldError('class-sections', 'code')} />
              <TextInput label={$_('school.nameEn')} bind:value={sectionForm.name} error={fieldError('class-sections', 'name')} />
              <TextInput label={$_('school.nameAr')} bind:value={sectionForm.name_ar} />
              <StatusInput bind:value={sectionForm.status} />
            </div>
            <details class="mt-3 rounded-lg border border-slate-100 bg-slate-50 px-3 py-2">
              <summary class="cursor-pointer text-xs font-bold uppercase tracking-wide text-slate-500">{$_('school.advanced')}</summary>
              <div class="mt-3 max-w-xs">
                <NumberInput label={$_('school.sortOrderOptional')} bind:value={sectionForm.sort_order} />
              </div>
            </details>
            <div class="mt-4 flex flex-col gap-3 sm:flex-row">
              <button class="btn-hero inline-flex items-center gap-2 rounded-lg" disabled={saving} onclick={saveSection}>
                {#if editingPath === 'class-sections'}{$_('school.save')}{:else}<Plus class="h-4 w-4" />{$_('school.add')}{/if}
              </button>
              {#if editingPath === 'class-sections'}
                <button class="btn-secondary rounded-lg" disabled={saving} onclick={cancelEdit}>{$_('school.cancel')}</button>
              {:else}
                <div class="flex min-w-0 flex-1 gap-2">
                  <input class="min-w-0 flex-1 rounded-lg border border-slate-200 px-3 py-2" bind:value={quickLabels} aria-label={$_('school.quickLabels')} />
                  <button class="btn-secondary rounded-lg" disabled={saving} onclick={createQuickSections}>{$_('school.quickCreate')}</button>
                </div>
              {/if}
            </div>
            <RowsTable rows={sections} extra={(row) => `${branchName(row.branch_campus_id)} · ${yearName(row.academic_year_id)} · ${levelName(row.grade_level_id)}`} onedit={(row) => editRow('class-sections', sectionForm, row)} onarchive={(row) => archiveRow('class-sections', row)} />
          </div>
        {:else if activeTab === 'rosters'}
          <div class="space-y-5">
            <div class="rounded-lg border border-slate-200 bg-white p-5">
              <h2 class="text-lg font-black text-slate-900">{$_('school.rosters.title')}</h2>
              <p class="mt-2 max-w-3xl text-sm text-slate-600">{$_('school.rosters.help')}</p>
              <div class="mt-4 grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto]">
                <SelectInput label={$_('school.sections.single')} bind:value={rosterSectionId} rows={sections} optional error={fieldError('class-roster', 'class_section_id')} />
                <button type="button" class="btn-hero self-end rounded-lg px-4 py-2" disabled={saving || rosterLoading} onclick={() => loadClassRoster()}>
                  {$_('school.rosters.view')}
                </button>
              </div>
            </div>

            {#if rosterLoading}
              <div class="rounded-lg border border-slate-200 bg-white p-5 text-sm font-semibold text-slate-500">{$_('common.loading')}</div>
            {:else if classRoster}
              <div class="rounded-lg border border-slate-200 bg-white p-5">
                <div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <h3 class="text-xl font-black text-slate-900">{classRosterTitle()}</h3>
                    <p class="mt-2 text-sm text-slate-600">
                      {$_('school.branches.single')}: {classRoster.branch?.name || '-'} ·
                      {$_('school.years.single')}: {classRoster.academic_year?.name || '-'} ·
                      {gradeLevelLabel}: {classRoster.grade_level?.name || '-'}
                    </p>
                  </div>
                  <div class="rounded-lg border border-slate-100 bg-slate-50 px-3 py-2 text-sm">
                    <p class="font-bold text-slate-700">{$_('school.rosters.homeroomTeacher')}</p>
                    <p class="mt-1 text-slate-600">{teacherName(classRoster.homeroom_teacher)}</p>
                  </div>
                </div>

                <div class="mt-5 grid gap-5 lg:grid-cols-2">
                  <div>
                    <h4 class="font-black text-slate-900">{$_('school.rosters.currentStudents')}</h4>
                    {#if classRoster.students.length === 0}
                      <p class="mt-2 text-sm text-slate-500">{$_('school.rosters.emptyStudents')}</p>
                    {:else}
                      <div class="mt-3 divide-y divide-slate-100 rounded-lg border border-slate-100">
                        {#each classRoster.students as student}
                          <div class="flex flex-col gap-2 p-3 sm:flex-row sm:items-center sm:justify-between">
                            <div>
                              <p class="font-semibold text-slate-900">{student.display_name}</p>
                              <p class="mt-1 text-sm text-slate-500">{student.external_ref || $_('school.students.noExternalRef')}</p>
                            </div>
                            <button type="button" class="btn-secondary rounded-lg px-3 py-2 text-sm" onclick={() => openStudentFromRoster(student)}>{$_('school.rosters.openStudent')}</button>
                          </div>
                        {/each}
                      </div>
                    {/if}
                  </div>

                  <div>
                    <h4 class="font-black text-slate-900">{$_('school.rosters.subjectGroups')}</h4>
                    {#if classRoster.subject_groups.length === 0}
                      <p class="mt-2 text-sm text-slate-500">{$_('school.rosters.emptySubjectGroups')}</p>
                    {:else}
                      <div class="mt-3 divide-y divide-slate-100 rounded-lg border border-slate-100">
                        {#each classRoster.subject_groups as item}
                          <div class="p-3">
                            <p class="font-semibold text-slate-900">{item.subject?.name || item.subject_group.name}</p>
                            <p class="mt-1 text-sm text-slate-500">{item.subject_group.name}</p>
                            <p class="mt-1 text-sm text-slate-600">{$_('school.rosters.teacher')}: {teacherName(item.teacher)}</p>
                          </div>
                        {/each}
                      </div>
                    {/if}
                  </div>
                </div>
              </div>
            {/if}
          </div>
        {:else if activeTab === 'teachers'}
          <div class="space-y-5">
            <div class="rounded-lg border border-slate-200 bg-white p-5">
              <h2 class="text-lg font-black text-slate-900">{$_('school.teachers.inviteTitle')}</h2>
              <form class="mt-4 flex flex-col gap-3 sm:flex-row" onsubmit={(event) => { event.preventDefault(); inviteTeacher(); }}>
                <div class="min-w-0 flex-1">
                  <input required type="email" bind:value={teacherInviteEmail} placeholder={$_('school.teachers.email')} class={`w-full rounded-lg border px-3 py-3 font-medium ${fieldError('teachers', 'email') ? 'border-red-400 bg-red-50' : 'border-slate-300'}`} aria-invalid={fieldError('teachers', 'email') ? 'true' : 'false'} />
                  {#if fieldError('teachers', 'email')}
                    <p class="mt-1 text-xs font-semibold text-red-600">{fieldError('teachers', 'email')}</p>
                  {/if}
                </div>
              <button type="submit" class="btn-hero rounded-lg px-5 py-3" disabled={saving}>{$_('school.teachers.sendInvite')}</button>
              </form>
            </div>

            <div class="rounded-lg border border-slate-200 bg-white p-5">
              <h3 class="text-base font-black text-slate-900">{$_('school.teacherImports.title')}</h3>
              <p class="mt-1 text-sm text-slate-500">{$_('school.teacherImports.help')}</p>
              <div class="mt-4 flex flex-wrap items-center gap-2">
                <button type="button" class="btn-secondary rounded-lg px-4 py-2" onclick={downloadTeacherImportTemplate}>{$_('school.teacherImports.downloadTemplate')}</button>
                <input
                  type="file"
                  accept=".csv,text/csv"
                  class="rounded-lg border border-slate-200 px-3 py-2 text-sm"
                  onchange={handleTeacherImportFileChange}
                />
                <button type="button" class="btn-hero rounded-lg px-4 py-2" disabled={!teacherImportFile || teacherImportUploading} onclick={uploadTeacherImportFile}>
                  {teacherImportUploading ? $_('school.teacherImports.uploading') : $_('school.teacherImports.upload')}
                </button>
              </div>

              {#if teacherImport}
                <div class="mt-5">
                  <div class="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p class="font-bold text-slate-900">{teacherImport.filename || $_('school.teacherImports.title')}</p>
                      <p class="mt-1 text-sm text-slate-600">
                        {$_('school.teacherImports.status')}: {$_(`school.teacherImports.statusValue.${teacherImport.status}`)}
                      </p>
                    </div>
                    <div class="flex flex-wrap gap-2 text-sm">
                      {#each teacherImportSummaryBadges() as badge}
                        <span class={`rounded-full px-3 py-1 font-semibold ${badge.classes}`}>{badge.label}: {badge.count}</span>
                      {/each}
                    </div>
                  </div>

                  {#if teacherImport.status === 'staged'}
                    <div class="mt-3 flex gap-2">
                      <button type="button" class="btn-hero rounded-lg px-4 py-2" disabled={teacherImportCommitting} onclick={commitTeacherImport}>
                        {teacherImportCommitting ? $_('school.teacherImports.committing') : $_('school.teacherImports.commit')}
                      </button>
                      <button type="button" class="btn-secondary rounded-lg px-4 py-2" disabled={teacherImportCommitting} onclick={discardTeacherImport}>{$_('school.teacherImports.discard')}</button>
                    </div>
                  {/if}

                  <p class="mt-4 text-xs text-slate-500">{$_('school.teacherImports.note')}</p>
                  <div class="mt-2 overflow-x-auto rounded-lg border border-slate-100">
                    <table class="w-full min-w-[700px] text-left text-sm">
                      <thead class="bg-slate-50 text-xs font-bold uppercase text-slate-500">
                        <tr>
                          <th class="px-3 py-2">{$_('school.teacherImports.row')}</th>
                          <th class="px-3 py-2">{$_('school.teacherImports.email')}</th>
                          <th class="px-3 py-2">{$_('school.teacherImports.name')}</th>
                          <th class="px-3 py-2">{$_('school.teacherImports.action')}</th>
                          <th class="px-3 py-2">{$_('school.teacherImports.notes')}</th>
                        </tr>
                      </thead>
                      <tbody class="divide-y divide-slate-100">
                        {#each teacherImport.rows as row}
                          <tr class={teacherImportRowRowClass(row)}>
                            <td class="px-3 py-2">{row.row_number}</td>
                            <td class="px-3 py-2 break-all">{row.email || '—'}</td>
                            <td class="px-3 py-2">{[row.first_name, row.last_name].filter(Boolean).join(' ') || '—'}</td>
                            <td class="px-3 py-2 font-semibold">{teacherImportActionLabel(row.action)}</td>
                            <td class="px-3 py-2 text-xs">
                              {#each row.errors as message}
                                <p class="text-red-700">{message}</p>
                              {/each}
                              {#each row.warnings as message}
                                <p class="text-amber-700">{message}</p>
                              {/each}
                            </td>
                          </tr>
                        {/each}
                      </tbody>
                    </table>
                  </div>
                </div>
              {/if}
            </div>

            <div class="rounded-lg border border-slate-200 bg-white p-5">
              <h2 class="text-lg font-black text-slate-900">{$_('school.teachers.pending')}</h2>
              {#if pendingTeacherInvites.length === 0}
                <p class="mt-3 text-sm text-slate-500">{$_('school.teachers.noPending')}</p>
              {:else}
                <div class="mt-4 divide-y divide-slate-100">
                  {#each pendingTeacherInvites as invite}
                    <div class="flex flex-col gap-3 py-3 sm:flex-row sm:items-center sm:justify-between">
                      <div>
                        <p class="break-all font-bold text-slate-900">{invite.email}</p>
                        <p class="mt-1 text-sm text-slate-500">{$_(`platform.inviteStatuses.${invite.status}`)} · {invite.send_status || '-'}</p>
                      </div>
                      <div class="flex gap-2">
                        <button type="button" class="btn-secondary rounded-lg px-3 py-2 text-sm" disabled={saving} onclick={() => { teacherInviteEmail = invite.email; inviteTeacher(); }}>{$_('platform.resend')}</button>
                        <button type="button" class="btn-secondary rounded-lg px-3 py-2 text-sm" disabled={saving} onclick={() => revokeTeacherInvite(invite.id)}>{$_('platform.revoke')}</button>
                      </div>
                    </div>
                  {/each}
                </div>
              {/if}
            </div>

            <div class="rounded-lg border border-slate-200 bg-white p-5">
              <h2 class="text-lg font-black text-slate-900">{$_('school.teachers.active')}</h2>
              {#if teachers.length === 0}
                <p class="mt-3 text-sm text-slate-500">{$_('school.teachers.empty')}</p>
              {:else}
                <div class="mt-4 space-y-4">
                  {#each teachers as teacher}
                    <div class="rounded-lg border border-slate-200 p-4">
                      <div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                        <div>
                          <h3 class="font-black text-slate-900">{teacher.user.name || teacher.user.email}</h3>
                          <p class="mt-1 break-all text-sm text-slate-500">{teacher.user.email}</p>
                          <p class="mt-1 text-xs font-semibold uppercase tracking-wide text-slate-400">{teacher.assignment_count} {$_('school.teachers.assignments')}</p>
                        </div>
                        <button type="button" class="btn-secondary rounded-lg px-3 py-2 text-sm" disabled={saving} onclick={() => deactivateTeacher(teacher)}>{$_('school.teachers.deactivate')}</button>
                      </div>

                      <div class="mt-4 grid gap-3 lg:grid-cols-2">
                        <div class="rounded-lg border border-slate-100 p-3">
                          <p class="text-sm font-bold text-slate-800">{$_('school.teachers.assignHomeroom')}</p>
                          <div class="mt-3 flex gap-2">
                            <div class="min-w-0 flex-1">
                              <SelectInput label={$_('school.sections.single')} bind:value={homeroomSelections[teacher.membership_id]} rows={sections} optional error={fieldError(`homeroom-${teacher.membership_id}`, 'class_section_id')} />
                            </div>
                            <button type="button" class="btn-hero self-end rounded-lg px-4 py-2" disabled={saving} onclick={() => assignHomeroom(teacher)}>{$_('school.teachers.assign')}</button>
                          </div>
                        </div>
                        <div class="rounded-lg border border-slate-100 p-3">
                          <p class="text-sm font-bold text-slate-800">{$_('school.teachers.assignSubject')}</p>
                          <div class="mt-3 flex gap-2">
                            <div class="min-w-0 flex-1">
                              <SelectInput label={$_('school.groups.title')} bind:value={groupSelections[teacher.membership_id]} rows={groups} optional error={fieldError(`subject-${teacher.membership_id}`, 'subject_group_id')} />
                            </div>
                            <button type="button" class="btn-hero self-end rounded-lg px-4 py-2" disabled={saving} onclick={() => assignSubject(teacher)}>{$_('school.teachers.assign')}</button>
                          </div>
                        </div>
                      </div>

                      <div class="mt-4">
                        <p class="text-sm font-bold text-slate-800">{$_('school.teachers.currentAssignments')}</p>
                        {#if !(teacherAssignments[teacher.membership_id] || []).some((assignment) => assignment.is_open)}
                          <p class="mt-2 text-sm text-slate-500">{$_('school.teachers.noAssignments')}</p>
                        {:else}
                          <div class="mt-2 divide-y divide-slate-100 rounded-lg border border-slate-100">
                            {#each (teacherAssignments[teacher.membership_id] || []).filter((assignment) => assignment.is_open) as assignment}
                              <div class="flex flex-col gap-2 p-3 sm:flex-row sm:items-center sm:justify-between">
                                <div>
                                  <p class="font-semibold text-slate-900">{assignmentName(assignment)}</p>
                                  <p class="mt-1 text-sm text-slate-500">{$_(`school.teachers.roles.${assignment.role}`)} · {assignment.valid_from}</p>
                                </div>
                                <button type="button" class="btn-secondary rounded-lg px-3 py-2 text-sm" disabled={saving} onclick={() => closeAssignment(assignment.id)}>{$_('school.teachers.closeAssignment')}</button>
                              </div>
                            {/each}
                          </div>
                        {/if}
                      </div>
                    </div>
                  {/each}
                </div>
              {/if}
            </div>
          </div>
        {:else if activeTab === 'students'}
          <div class="space-y-5">
            <div class="rounded-lg border border-slate-200 bg-white p-5">
              <h2 class="text-lg font-black text-slate-900">{$_('school.students.title')}</h2>
              <div class="mt-4 grid gap-3 md:grid-cols-4">
                <TextInput label={$_('school.students.externalRef')} bind:value={studentForm.external_ref} />
                <TextInput label={$_('school.students.firstName')} bind:value={studentForm.first_name} error={fieldError('students', 'first_name')} />
                <TextInput label={$_('school.students.lastName')} bind:value={studentForm.last_name} error={fieldError('students', 'last_name')} />
                <TextInput label={$_('school.students.preferredName')} bind:value={studentForm.preferred_name} />
                <TextInput label={$_('school.nameAr')} bind:value={studentForm.name_ar} />
                <label class="block text-sm font-semibold text-slate-700">
                  {$_('school.students.dateOfBirth')}
                  <input type="date" class="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 font-normal" bind:value={studentForm.date_of_birth} />
                </label>
                <label class="block text-sm font-semibold text-slate-700">
                  {$_('school.students.gender')}
                  <select class="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 font-normal" bind:value={studentForm.gender}>
                    {#each genderOptions() as option}
                      <option value={option.value}>{option.label}</option>
                    {/each}
                  </select>
                </label>
                <StatusInput bind:value={studentForm.status} />
              </div>
              <div class="mt-4 flex items-center gap-2">
                <button type="button" class="btn-hero inline-flex items-center gap-2 rounded-lg" disabled={saving} onclick={saveStudent}>
                  {#if editingPath === 'students'}{$_('school.save')}{:else}<Plus class="h-4 w-4" />{$_('school.add')}{/if}
                </button>
                {#if editingPath === 'students'}
                  <button type="button" class="btn-secondary rounded-lg" disabled={saving} onclick={cancelEdit}>{$_('school.cancel')}</button>
                {/if}
              </div>
            </div>

            <div class="rounded-lg border border-slate-200 bg-white p-5">
              <h3 class="text-base font-black text-slate-900">{$_('school.imports.title')}</h3>
              <p class="mt-1 text-sm text-slate-500">{$_('school.imports.help')}</p>
              <div class="mt-4 flex flex-wrap items-center gap-2">
                <button type="button" class="btn-secondary rounded-lg px-4 py-2" onclick={downloadImportTemplate}>{$_('school.imports.downloadTemplate')}</button>
                <input
                  type="file"
                  accept=".csv,text/csv"
                  class="rounded-lg border border-slate-200 px-3 py-2 text-sm"
                  onchange={handleImportFileChange}
                />
                <button type="button" class="btn-hero rounded-lg px-4 py-2" disabled={!importFile || importUploading} onclick={uploadImportFile}>
                  {importUploading ? $_('school.imports.uploading') : $_('school.imports.upload')}
                </button>
              </div>

              {#if studentImport}
                <div class="mt-5">
                  <div class="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p class="font-bold text-slate-900">{studentImport.filename || $_('school.imports.title')}</p>
                      <p class="mt-1 text-sm text-slate-600">
                        {$_('school.imports.status')}: {$_(`school.imports.statusValue.${studentImport.status}`)}
                      </p>
                    </div>
                    <div class="flex flex-wrap gap-2 text-sm">
                      {#each importSummaryBadges() as badge}
                        <span class={`rounded-full px-3 py-1 font-semibold ${badge.classes}`}>{badge.label}: {badge.count}</span>
                      {/each}
                    </div>
                  </div>

                  {#if studentImport.status === 'staged'}
                    <div class="mt-3 flex gap-2">
                      <button type="button" class="btn-hero rounded-lg px-4 py-2" disabled={importCommitting} onclick={commitImport}>
                        {importCommitting ? $_('school.imports.committing') : $_('school.imports.commit')}
                      </button>
                      <button type="button" class="btn-secondary rounded-lg px-4 py-2" disabled={importCommitting} onclick={discardImport}>{$_('school.imports.discard')}</button>
                    </div>
                  {/if}

                  <p class="mt-4 text-xs text-slate-500">{$_('school.imports.guardianNote')}</p>
                  <div class="mt-2 overflow-x-auto rounded-lg border border-slate-100">
                    <table class="w-full min-w-[900px] text-left text-sm">
                      <thead class="bg-slate-50 text-xs font-bold uppercase text-slate-500">
                        <tr>
                          <th class="px-3 py-2">{$_('school.imports.row')}</th>
                          <th class="px-3 py-2">{$_('school.students.externalRef')}</th>
                          <th class="px-3 py-2">{$_('school.students.title')}</th>
                          <th class="px-3 py-2">{$_('school.imports.grade')}</th>
                          <th class="px-3 py-2">{$_('school.imports.section')}</th>
                          <th class="px-3 py-2">{$_('school.imports.guardians')}</th>
                          <th class="px-3 py-2">{$_('school.imports.action')}</th>
                          <th class="px-3 py-2">{$_('school.imports.notes')}</th>
                        </tr>
                      </thead>
                      <tbody class="divide-y divide-slate-100">
                        {#each studentImport.rows as row}
                          <tr class={importRowRowClass(row)}>
                            <td class="px-3 py-2">{row.row_number}</td>
                            <td class="px-3 py-2">{row.student_id || '—'}</td>
                            <td class="px-3 py-2">{[row.first_name, row.last_name].filter(Boolean).join(' ') || '—'}</td>
                            <td class="px-3 py-2">{row.grade || '—'}</td>
                            <td class="px-3 py-2">{row.section || '—'}</td>
                            <td class="px-3 py-2 text-xs">
                              {#each importRowGuardianSummaries(row) as summary}
                                <p>{summary}</p>
                              {:else}
                                —
                              {/each}
                            </td>
                            <td class="px-3 py-2 font-semibold">{importActionLabel(row.action)}</td>
                            <td class="px-3 py-2 text-xs">
                              {#each row.errors as message}
                                <p class="text-red-700">{message}</p>
                              {/each}
                              {#each row.warnings as message}
                                <p class="text-amber-700">{message}</p>
                              {/each}
                            </td>
                          </tr>
                        {/each}
                      </tbody>
                    </table>
                  </div>
                </div>
              {/if}
            </div>

            <div class="rounded-lg border border-slate-200 bg-white p-5">
              <div class="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
                <div>
                  <h3 class="text-base font-black text-slate-900">{$_('school.students.listTitle')}</h3>
                  <p class="mt-1 text-sm text-slate-500">{$_('school.students.hiddenArchived')}</p>
                </div>
                <div class="grid gap-2 sm:grid-cols-[minmax(0,1fr)_220px_auto] lg:w-[720px]">
                  <input class="rounded-lg border border-slate-200 px-3 py-2" bind:value={studentSearch} placeholder={$_('school.students.search')} />
                  <SelectInput label={$_('school.sections.single')} bind:value={studentSectionFilter} rows={sections} optional />
                  <button type="button" class="btn-secondary rounded-lg px-4 py-2 self-end" disabled={saving} onclick={refresh}>{$_('school.students.applyFilters')}</button>
                </div>
              </div>

              {#if studentListEmptyKey()}
                <p class="mt-4 text-sm text-slate-500">{$_(studentListEmptyKey())}</p>
              {:else}
                <div class="mt-4 divide-y divide-slate-100 rounded-lg border border-slate-100">
                  {#each students as student}
                    <div class={`p-4 ${selectedStudentId === student.id ? 'bg-slate-50' : 'bg-white'}`}>
                      <div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                        <button type="button" class="text-left" onclick={() => selectStudent(student)}>
                          <h4 class="font-black text-slate-900">{student.display_name}</h4>
                          <p class="mt-1 text-sm text-slate-500">
                            {student.external_ref || $_('school.students.noExternalRef')}
                            {#if student.name_ar} · {student.name_ar}{/if}
                          </p>
                          <p class="mt-1 text-sm text-slate-600">
                            {$_('school.students.currentClass')}: {studentCurrentClass(student)}
                            {#if (student.current_subject_groups || []).length}
                              · {$_('school.students.subjectGroups')}: {(student.current_subject_groups || []).map((group) => group.name).join(', ')}
                            {/if}
                          </p>
                        </button>
                        <div class="flex gap-2">
                          <button type="button" class="btn-secondary rounded-lg px-3 py-2 text-sm" disabled={saving} onclick={() => selectStudentForAction(student)}>{studentActionLabel(student)}</button>
                          <button type="button" class="btn-secondary rounded-lg px-3 py-2 text-sm" disabled={saving} onclick={() => editStudent(student)}>{$_('school.edit')}</button>
                          <button type="button" class="btn-secondary rounded-lg px-3 py-2 text-sm" disabled={saving} onclick={() => removeStudentMistake(student)}>{$_('school.students.removeMistake')}</button>
                          <button type="button" class="btn-secondary rounded-lg px-3 py-2 text-sm" disabled={saving} onclick={() => archiveStudent(student)}>{$_('school.archive')}</button>
                        </div>
                      </div>
                    </div>
                  {/each}
                </div>
              {/if}
            </div>

            {#if selectedStudent()}
              <div id="student-detail-panel" class="rounded-lg border border-slate-200 bg-white p-5">
                <h3 class="text-base font-black text-slate-900">{$_('school.students.enrolmentsFor')} {selectedStudent()?.display_name}</h3>
                <div class="mt-4 grid gap-3 lg:grid-cols-3">
                  <div class="rounded-lg border border-slate-100 p-3">
                    <p class="text-sm font-bold text-slate-800">{$_('school.students.addClassEnrolment')}</p>
                    <div class="mt-3 flex gap-2">
                      <div class="min-w-0 flex-1">
                        <SelectInput label={$_('school.sections.single')} bind:value={classEnrolmentSectionId} rows={sections} optional error={fieldError('student-class-enrolment', 'class_section_id')} />
                      </div>
                      <button type="button" class="btn-hero self-end rounded-lg px-4 py-2" disabled={saving} onclick={addClassEnrolment}>{$_('school.add')}</button>
                    </div>
                  </div>
                  <div class="rounded-lg border border-slate-100 p-3">
                    <p class="text-sm font-bold text-slate-800">{$_('school.students.moveClass')}</p>
                    <p class="mt-1 text-xs text-slate-500">{$_('school.students.moveHelp')}</p>
                    <div class="mt-3 flex gap-2">
                      <div class="min-w-0 flex-1">
                        <SelectInput label={$_('school.sections.single')} bind:value={moveSectionId} rows={sections} optional error={fieldError('student-move', 'class_section_id')} />
                      </div>
                      <button type="button" class="btn-hero self-end rounded-lg px-4 py-2" disabled={saving} onclick={moveStudentSection}>{$_('school.students.move')}</button>
                    </div>
                  </div>
                  <div class="rounded-lg border border-slate-100 p-3">
                    <p class="text-sm font-bold text-slate-800">{$_('school.students.addSubjectEnrolment')}</p>
                    <div class="mt-3 flex gap-2">
                      <div class="min-w-0 flex-1">
                        <SelectInput label={$_('school.groups.title')} bind:value={subjectEnrolmentGroupId} rows={groups} optional error={fieldError('student-subject-enrolment', 'subject_group_id')} />
                      </div>
                      <button type="button" class="btn-hero self-end rounded-lg px-4 py-2" disabled={saving} onclick={addSubjectEnrolment}>{$_('school.add')}</button>
                    </div>
                  </div>
                </div>

                <div class="mt-5">
                  <h4 class="font-bold text-slate-900">{$_('school.students.history')}</h4>
                  {#if loadingEnrolments}
                    <p class="mt-2 text-sm text-slate-500">{$_('common.loading')}</p>
                  {:else if studentEnrolments.length === 0}
                    <p class="mt-2 text-sm text-slate-500">{$_('school.students.noEnrolments')}</p>
                  {:else}
                    <div class="mt-3 divide-y divide-slate-100 rounded-lg border border-slate-100">
                      {#each studentEnrolments as enrolment}
                        <div class="flex flex-col gap-2 p-3 sm:flex-row sm:items-center sm:justify-between">
                          <div>
                            <p class="font-semibold text-slate-900">{enrolmentName(enrolment)}</p>
                            <p class="mt-1 text-sm text-slate-500">
                              {enrolmentType(enrolment)} · {enrolment.valid_from} - {enrolment.valid_to || $_('school.students.open')}
                            </p>
                          </div>
                          {#if enrolment.is_open}
                            <button type="button" class="btn-secondary rounded-lg px-3 py-2 text-sm" disabled={saving} onclick={() => closeEnrolment(enrolment.id)}>{$_('school.students.closeEnrolment')}</button>
                          {/if}
                        </div>
                      {/each}
                    </div>
                  {/if}
                </div>
              </div>
            {/if}
          </div>
        {:else if activeTab === 'subjects'}
          <CrudBlock title={$_('school.subjects.title')} rows={subjects} path="subjects" bind:form={subjectForm} {saving} editing={editingPath === 'subjects'} errors={{ code: fieldError('subjects', 'code'), name: fieldError('subjects', 'name') }} onsubmit={() => saveRow('subjects', subjectForm)} onedit={(row) => editRow('subjects', subjectForm, row)} oncancel={cancelEdit} onarchive={archiveRow} />
        {:else if activeTab === 'groups'}
          <div class="space-y-5">
            <div class="rounded-lg border border-slate-200 bg-white p-5">
              <h2 class="text-lg font-black text-slate-900">{$_('school.groups.title')}</h2>
              <p class="mt-2 max-w-3xl text-sm text-slate-600">{$_('school.groups.help')}</p>
              <p class="mt-2 max-w-3xl text-sm font-semibold text-slate-700">{$_('school.groups.recommendation')}</p>
            </div>

            <div class="rounded-lg border border-slate-200 bg-white p-5">
              <h3 class="text-base font-black text-slate-900">{$_('school.groups.singleCreate')}</h3>
              <div class="mt-4 grid gap-3 md:grid-cols-4">
                <SelectInput label={$_('school.years.single')} bind:value={groupForm.academic_year_id} rows={years} error={fieldError('subject-groups', 'academic_year_id')} />
                <SelectInput label={$_('school.subjects.single')} bind:value={groupForm.subject_id} rows={subjects} error={fieldError('subject-groups', 'subject_id')} />
                <div class="md:col-span-2">
                  <p class="text-sm font-semibold text-slate-700">{$_('school.groups.contextType')}</p>
                  <div class="mt-1 grid gap-2 sm:grid-cols-2">
                    <button type="button" class={`rounded-lg border px-3 py-2 text-left text-sm font-semibold ${groupContextMode === 'section' ? 'border-slate-900 bg-slate-900 text-white' : 'border-slate-200 bg-white text-slate-700'}`} onclick={() => setGroupContextMode('section')}>
                      {$_('school.groups.sectionSpecific')}
                      <span class={`mt-1 block text-xs font-medium ${groupContextMode === 'section' ? 'text-slate-200' : 'text-slate-500'}`}>{$_('school.groups.sectionSpecificHelp')}</span>
                    </button>
                    <button type="button" class={`rounded-lg border px-3 py-2 text-left text-sm font-semibold ${groupContextMode === 'grade' ? 'border-slate-900 bg-slate-900 text-white' : 'border-slate-200 bg-white text-slate-700'}`} onclick={() => setGroupContextMode('grade')}>
                      {$_('school.groups.gradeLevel')}
                      <span class={`mt-1 block text-xs font-medium ${groupContextMode === 'grade' ? 'text-slate-200' : 'text-slate-500'}`}>{$_('school.groups.gradeLevelHelp')}</span>
                    </button>
                  </div>
                </div>
                {#if groupContextMode === 'section'}
                  <SelectInput label={$_('school.sections.single')} bind:value={groupForm.class_section_id} rows={sections} error={fieldError('subject-groups', 'class_section_id')} />
                {:else}
                  <SelectInput label={gradeLevelLabel} bind:value={groupForm.grade_level_id} rows={levels} error={fieldError('subject-groups', 'grade_level_id')} />
                {/if}
                <TextInput label={$_('school.code')} bind:value={groupForm.code} error={fieldError('subject-groups', 'code')} />
                <TextInput label={$_('school.nameEn')} bind:value={groupForm.name} error={fieldError('subject-groups', 'name')} />
                <TextInput label={$_('school.nameAr')} bind:value={groupForm.name_ar} />
                <label class="block text-sm font-semibold text-slate-700">
                  {$_('school.groups.enrolmentPolicy')}
                  <select class={`mt-1 w-full rounded-lg border px-3 py-2 font-normal ${fieldError('subject-groups', 'enrolment_policy') ? 'border-red-400 bg-red-50' : 'border-slate-200'}`} bind:value={groupForm.enrolment_policy}>
                    {#each policyOptions() as option}
                      <option value={option.id}>{option.name}</option>
                    {/each}
                  </select>
                  {#if fieldError('subject-groups', 'enrolment_policy')}
                    <span class="mt-1 block text-xs font-semibold text-red-600">{fieldError('subject-groups', 'enrolment_policy')}</span>
                  {/if}
                </label>
                <StatusInput bind:value={groupForm.status} />
              </div>
              <details class="mt-3 rounded-lg border border-slate-100 bg-slate-50 px-3 py-2">
                <summary class="cursor-pointer text-xs font-bold uppercase tracking-wide text-slate-500">{$_('school.advanced')}</summary>
                <div class="mt-3 max-w-xs">
                  <NumberInput label={$_('school.sortOrderOptional')} bind:value={groupForm.sort_order} />
                </div>
              </details>
              <div class="mt-4 flex items-center gap-2">
                <button class="btn-hero inline-flex items-center gap-2 rounded-lg" disabled={saving} onclick={saveGroup}>
                  {#if editingPath === 'subject-groups'}{$_('school.save')}{:else}<Plus class="h-4 w-4" />{$_('school.add')}{/if}
                </button>
                {#if editingPath === 'subject-groups'}
                  <button class="btn-secondary rounded-lg" disabled={saving} onclick={cancelEdit}>{$_('school.cancel')}</button>
                {/if}
              </div>
            </div>

            <div class="rounded-lg border border-slate-200 bg-white p-5">
              <h3 class="text-base font-black text-slate-900">{$_('school.groups.bulkTitle')}</h3>
              <p class="mt-2 max-w-3xl text-sm text-slate-600">{$_('school.groups.bulkHelp')}</p>
              <div class="mt-4 grid gap-3 md:grid-cols-4">
                <SelectInput label={$_('school.years.single')} bind:value={bulkGroupForm.academic_year_id} rows={years} error={fieldError('bulk-subject-groups', 'academic_year_id')} />
                <SelectInput label={gradeLevelLabel} bind:value={bulkGroupForm.grade_level_id} rows={levels} error={fieldError('bulk-subject-groups', 'grade_level_id')} />
                <SelectInput label={$_('school.subjects.single')} bind:value={bulkGroupForm.subject_id} rows={subjects} error={fieldError('bulk-subject-groups', 'subject_id')} />
                <label class="block text-sm font-semibold text-slate-700">
                  {$_('school.groups.enrolmentPolicy')}
                  <select class="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 font-normal" bind:value={bulkGroupForm.enrolment_policy}>
                    <option value="default_for_section">{$_('school.groups.allOfSection')}</option>
                    <option value="explicit_only">{$_('school.groups.manualList')}</option>
                  </select>
                </label>
              </div>

              <div class={`mt-4 rounded-lg border p-3 ${fieldError('bulk-subject-groups', 'class_section_ids') ? 'border-red-300 bg-red-50' : 'border-slate-100 bg-slate-50'}`}>
                <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <p class="text-sm font-bold text-slate-800">{$_('school.groups.sectionsToCreate')}</p>
                  <button class="btn-secondary rounded-lg px-3 py-2 text-sm" disabled={saving || eligibleBulkSections().length === 0} onclick={selectAllBulkSections}>{$_('school.groups.selectAll')}</button>
                </div>
                {#if fieldError('bulk-subject-groups', 'class_section_ids')}
                  <p class="mt-1 text-xs font-semibold text-red-600">{fieldError('bulk-subject-groups', 'class_section_ids')}</p>
                {/if}
                {#if eligibleBulkSections().length === 0}
                  <p class="mt-3 text-sm text-slate-500">{$_('school.groups.noSectionsForBulk')}</p>
                {:else}
                  <div class="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                    {#each eligibleBulkSections() as section}
                      <label class="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700">
                        <input
                          type="checkbox"
                          checked={bulkGroupForm.class_section_ids.includes(String(section.id))}
                          onchange={(event) => toggleBulkSection(section.id, event.currentTarget.checked)}
                        />
                        {section.name}
                      </label>
                    {/each}
                  </div>
                {/if}
              </div>

              <button class="btn-hero mt-4 inline-flex items-center gap-2 rounded-lg" disabled={saving || eligibleBulkSections().length === 0} onclick={bulkCreateSubjectGroups}>
                <Plus class="h-4 w-4" />{$_('school.groups.createGroups')}
              </button>

              {#if bulkGroupResult}
                <div class="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-4">
                  <p class="font-bold text-slate-900">
                    {$_('school.groups.bulkSummary', {
                      values: {
                        created: bulkGroupResult.created,
                        restored: bulkGroupResult.restored,
                        skipped: bulkGroupResult.skipped,
                        failed: bulkGroupResult.failed
                      }
                    })}
                  </p>
                  {#if bulkGroupResult.results.some((item) => item.status === 'failed' || item.status === 'skipped')}
                    <div class="mt-3 divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
                      {#each bulkGroupResult.results.filter((item) => item.status === 'failed' || item.status === 'skipped') as item}
                        <div class="p-3 text-sm">
                          <p class="font-bold text-slate-900">{item.class_section?.name || rowName(sections, item.class_section_id)} · {item.status}</p>
                          <p class="mt-1 text-slate-600">{item.reason}</p>
                        </div>
                      {/each}
                    </div>
                  {/if}
                </div>
              {/if}
            </div>

            <div class="rounded-lg border border-slate-200 bg-white p-5">
              <h3 class="text-base font-black text-slate-900">{$_('school.groups.existing')}</h3>
              <RowsTable rows={groups} extra={(row) => `${yearName(row.academic_year_id)} · ${row.class_section_id ? rowName(sections, row.class_section_id) : levelName(row.grade_level_id)} · ${subjectName(row.subject_id)} · ${groupPolicyLabel(row)}`} onedit={(row) => editRow('subject-groups', groupForm, row)} onarchive={(row) => archiveRow('subject-groups', row)} />
            </div>

            <div class="rounded-lg border border-slate-200 bg-white p-5">
              <h3 class="text-base font-black text-slate-900">{$_('school.groups.rosterTitle')}</h3>
              <div class="mt-4 grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto]">
                <SelectInput label={$_('school.groups.title')} bind:value={groupRosterId} rows={groups} optional error={fieldError('group-roster', 'subject_group_id')} />
                <button type="button" class="btn-hero self-end rounded-lg px-4 py-2" disabled={saving || groupRosterLoading} onclick={() => loadGroupRoster()}>
                  {$_('school.rosters.view')}
                </button>
              </div>

              {#if groupRosterLoading}
                <p class="mt-4 text-sm text-slate-500">{$_('common.loading')}</p>
              {:else if groupRoster}
                <div class="mt-5">
                  <div class="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <h4 class="font-black text-slate-900">{groupRosterTitle()}</h4>
                      <p class="mt-1 text-sm text-slate-500">{groupPolicyLabel(groupRoster.subject_group)}</p>
                    </div>
                    <div class="flex gap-2">
                      <select class={`min-w-52 rounded-lg border px-3 py-2 text-sm ${fieldError('group-roster-add', 'student_id') ? 'border-red-400 bg-red-50' : 'border-slate-200'}`} bind:value={groupRosterStudentId} aria-label={$_('school.students.title')}>
                        <option value="">{$_('school.select')}</option>
                        {#each students as student}
                          <option value={String(student.id)}>{student.display_name}</option>
                        {/each}
                      </select>
                      <button type="button" class="btn-secondary rounded-lg px-3 py-2 text-sm" disabled={saving} onclick={addGroupRosterStudent}>{$_('school.add')}</button>
                    </div>
                  </div>
                  {#if fieldError('group-roster-add', 'student_id')}
                    <p class="mt-1 text-xs font-semibold text-red-600">{fieldError('group-roster-add', 'student_id')}</p>
                  {/if}

                  <div class="mt-4 divide-y divide-slate-100 rounded-lg border border-slate-100">
                    {#each groupRoster.students as student}
                      <div class="flex flex-col gap-2 p-3 sm:flex-row sm:items-center sm:justify-between">
                        <div>
                          <p class="font-semibold text-slate-900">{student.display_name}</p>
                          <p class="mt-1 text-sm text-slate-500">{sourceLabel(student.source)} · {student.enrolled_from}</p>
                        </div>
                        <button type="button" class="btn-secondary rounded-lg px-3 py-2 text-sm" disabled={saving} onclick={() => removeGroupRosterStudent(student)}>{$_('school.groups.removeFromRoster')}</button>
                      </div>
                    {:else}
                      <p class="p-3 text-sm text-slate-500">{$_('school.groups.emptyRoster')}</p>
                    {/each}
                  </div>

                  {#if groupRoster.excluded_students.length}
                    <div class="mt-5">
                      <h4 class="font-black text-slate-900">{$_('school.groups.excludedStudents')}</h4>
                      <div class="mt-3 divide-y divide-slate-100 rounded-lg border border-slate-100">
                        {#each groupRoster.excluded_students as student}
                          <div class="flex flex-col gap-2 p-3 sm:flex-row sm:items-center sm:justify-between">
                            <p class="font-semibold text-slate-900">{student.display_name}</p>
                            <button type="button" class="btn-secondary rounded-lg px-3 py-2 text-sm" disabled={saving} onclick={() => includeGroupRosterStudent(student)}>{$_('school.groups.reinclude')}</button>
                          </div>
                        {/each}
                      </div>
                    </div>
                  {/if}
                </div>
              {/if}
            </div>
          </div>
        {:else if activeTab === 'defaults'}
          <div class="space-y-5">
            <div class="rounded-lg border border-slate-200 bg-white p-5">
              <h2 class="text-lg font-black text-slate-900">{$_('school.defaults.title')}</h2>
              <p class="mt-2 max-w-3xl text-sm text-slate-600">{$_('school.defaults.help')}</p>
            </div>

            <div class="rounded-lg border border-slate-200 bg-white p-5">
              <h3 class="text-base font-black text-slate-900">{editingPath === 'default-subject-templates' ? $_('school.edit') : $_('school.defaults.addTitle')}</h3>
              <div class="mt-4 grid gap-3 md:grid-cols-4">
                <div class="md:col-span-2">
                  <p class="text-sm font-semibold text-slate-700">{$_('school.defaults.scope')}</p>
                  <div class="mt-1 grid gap-2 sm:grid-cols-2">
                    <button type="button" class={`rounded-lg border px-3 py-2 text-left text-sm font-semibold ${templateForm.scope === 'stage' ? 'border-slate-900 bg-slate-900 text-white' : 'border-slate-200 bg-white text-slate-700'}`} onclick={() => setTemplateScope('stage')}>
                      {$_('school.stages.single')}
                    </button>
                    <button type="button" class={`rounded-lg border px-3 py-2 text-left text-sm font-semibold ${templateForm.scope === 'grade' ? 'border-slate-900 bg-slate-900 text-white' : 'border-slate-200 bg-white text-slate-700'}`} onclick={() => setTemplateScope('grade')}>
                      {gradeLevelLabel}
                    </button>
                  </div>
                </div>
                {#if templateForm.scope === 'stage'}
                  <SelectInput label={$_('school.stages.single')} bind:value={templateForm.education_stage_id} rows={stages} error={fieldError('default-subject-templates', 'education_stage_id')} />
                {:else}
                  <SelectInput label={gradeLevelLabel} bind:value={templateForm.grade_level_id} rows={levels} error={fieldError('default-subject-templates', 'grade_level_id')} />
                {/if}
                <SelectInput label={$_('school.subjects.single')} bind:value={templateForm.subject_id} rows={subjects} error={fieldError('default-subject-templates', 'subject_id')} />
                <StatusInput bind:value={templateForm.status} />
              </div>
              <details class="mt-3 rounded-lg border border-slate-100 bg-slate-50 px-3 py-2">
                <summary class="cursor-pointer text-xs font-bold uppercase tracking-wide text-slate-500">{$_('school.advanced')}</summary>
                <div class="mt-3 max-w-xs">
                  <NumberInput label={$_('school.sortOrderOptional')} bind:value={templateForm.sort_order} />
                </div>
              </details>
              <div class="mt-4 flex items-center gap-2">
                <button class="btn-hero inline-flex items-center gap-2 rounded-lg" disabled={saving} onclick={saveTemplate}>
                  {#if editingPath === 'default-subject-templates'}{$_('school.save')}{:else}<Plus class="h-4 w-4" />{$_('school.add')}{/if}
                </button>
                {#if editingPath === 'default-subject-templates'}
                  <button class="btn-secondary rounded-lg" disabled={saving} onclick={cancelEdit}>{$_('school.cancel')}</button>
                {/if}
              </div>
            </div>

            <div class="rounded-lg border border-slate-200 bg-white p-5">
              <h3 class="text-base font-black text-slate-900">{$_('school.defaults.existing')}</h3>
              <div class="mt-4 overflow-x-auto rounded-lg border border-slate-200">
                <table class="min-w-full divide-y divide-slate-200 text-sm">
                  <thead class="bg-slate-50 text-left text-xs font-bold uppercase tracking-wide text-slate-500">
                    <tr>
                      <th class="px-3 py-2">{$_('school.defaults.scope')}</th>
                      <th class="px-3 py-2">{$_('school.subjects.single')}</th>
                      <th class="px-3 py-2">{$_('school.status')}</th>
                      <th class="px-3 py-2"></th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-slate-100 bg-white">
                    {#each templates as row}
                      <tr>
                        <td class="px-3 py-2 font-semibold text-slate-900">
                          {row.education_stage_id
                            ? `${$_('school.stages.single')}: ${row.education_stage?.name || stageName(row.education_stage_id)}`
                            : `${gradeLevelLabel}: ${row.grade_level?.name || levelName(row.grade_level_id)}`}
                        </td>
                        <td class="px-3 py-2">{row.subject?.name || subjectName(row.subject_id)}</td>
                        <td class="px-3 py-2"><span class={`rounded-full px-2 py-1 text-xs font-bold ${row.status === 'active' ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-600'}`}>{row.status}</span></td>
                        <td class="px-3 py-2 text-right">
                          <div class="inline-flex gap-1">
                            <button class="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 text-slate-500 hover:text-slate-900" aria-label={$_('school.edit')} onclick={() => editTemplate(row)}>
                              <Pencil class="h-4 w-4" />
                            </button>
                            <button class="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 text-slate-500 hover:text-red-600" aria-label={$_('school.archive')} onclick={() => archiveRow('default-subject-templates', row)}>
                              <Trash2 class="h-4 w-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    {:else}
                      <tr><td colspan="4" class="px-3 py-6 text-center text-slate-500">{$_('school.empty')}</td></tr>
                    {/each}
                  </tbody>
                </table>
              </div>
            </div>

            <div class="rounded-lg border border-slate-200 bg-white p-5">
              <h3 class="text-base font-black text-slate-900">{$_('school.defaults.applyTitle')}</h3>
              <p class="mt-2 max-w-3xl text-sm text-slate-600">{$_('school.defaults.applyHelp')}</p>
              <div class="mt-4 grid gap-3 md:grid-cols-4">
                <SelectInput label={$_('school.years.single')} bind:value={templateApplyForm.academic_year_id} rows={years} error={fieldError('template-apply', 'academic_year_id')} />
                <SelectInput label={$_('school.branches.single')} bind:value={templateApplyForm.branch_campus_id} rows={branches} optional />
                <SelectInput label={$_('school.stages.single')} bind:value={templateApplyForm.education_stage_id} rows={stages} optional />
                <SelectInput label={gradeLevelLabel} bind:value={templateApplyForm.grade_level_id} rows={levels} optional />
              </div>
              <div class="mt-4 flex flex-wrap items-center gap-2">
                <button type="button" class="btn-secondary rounded-lg px-4 py-2" disabled={templatePreviewLoading || templateApplyLoading} onclick={previewTemplateApplication}>{$_('school.defaults.preview')}</button>
                <button type="button" class="btn-hero rounded-lg px-4 py-2" disabled={templatePreviewLoading || templateApplyLoading} onclick={applyTemplateApplication}>{$_('school.defaults.apply')}</button>
              </div>

              {#if templatePreviewLoading || templateApplyLoading}
                <p class="mt-4 text-sm text-slate-500">{$_('common.loading')}</p>
              {/if}

              {#if templateApplyResult}
                <div class="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-4">
                  <p class="font-bold text-slate-900">
                    {$_('school.defaults.applySummary', {
                      values: {
                        created: templateApplyResult.created,
                        restored: templateApplyResult.restored,
                        skipped: templateApplyResult.skipped,
                        failed: templateApplyResult.failed
                      }
                    })}
                  </p>
                  {#if templateApplyResult.results.length}
                    <div class="mt-3 max-h-96 divide-y divide-slate-200 overflow-y-auto rounded-lg border border-slate-200 bg-white">
                      {#each templateApplyResult.results as item}
                        <div class="p-3 text-sm">
                          <p class="font-bold text-slate-900">{item.class_section?.name || rowName(sections, item.class_section_id)} · {item.subject?.name || subjectName(item.subject_id)} · {item.status}</p>
                          {#if item.reason}<p class="mt-1 text-slate-600">{item.reason}</p>{/if}
                        </div>
                      {/each}
                    </div>
                  {/if}
                </div>
              {:else if templatePreviewResult}
                <div class="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-4">
                  <p class="font-bold text-slate-900">
                    {$_('school.defaults.previewSummary', {
                      values: {
                        create: templatePreviewResult.would_create,
                        restore: templatePreviewResult.would_restore,
                        skip: templatePreviewResult.skipped_existing,
                        failed: templatePreviewResult.failed
                      }
                    })}
                  </p>
                  {#if templatePreviewResult.results.length}
                    <div class="mt-3 max-h-96 divide-y divide-slate-200 overflow-y-auto rounded-lg border border-slate-200 bg-white">
                      {#each templatePreviewResult.results as item}
                        <div class="p-3 text-sm">
                          <p class="font-bold text-slate-900">{item.class_section?.name || rowName(sections, item.class_section_id)} · {item.subject?.name || subjectName(item.subject_id)} · {item.status}</p>
                          {#if item.reason}<p class="mt-1 text-slate-600">{item.reason}</p>{/if}
                        </div>
                      {/each}
                    </div>
                  {:else}
                    <p class="mt-3 text-sm text-slate-500">{$_('school.defaults.previewEmpty')}</p>
                  {/if}
                </div>
              {/if}
            </div>
          </div>
        {/if}
      </div>
    </div>
  </section>
{/if}
