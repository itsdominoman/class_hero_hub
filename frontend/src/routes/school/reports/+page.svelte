<script lang="ts">
  import { onMount, tick } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { api } from '$lib/api';

  type Membership = { school_id: number; school_name: string; role: string };
  type Option = { id: number; name: string; status?: string; grade_level_id?: number | null };
  type CategoryOption = { id: number; label: string; type: CategoryType };
  type TeacherOption = { id: number; name: string };
  type StudentOption = { id: number; name: string; classLabel: string };
  type StudentSearchResponse = { id: number; display_name: string; current_class_section?: Option | null };
  type CategoryType = 'positive' | 'needs_work';
  type MatrixDimension = 'student' | 'class_section' | 'grade' | 'subject' | 'subject_group' | 'teacher' | 'duty_context' | 'category' | 'category_type' | 'date_bucket';
  type MatrixOrderBy = 'total_events' | 'positive_count' | 'needs_work_count' | 'signed_points_total';
  type Metrics = {
    total_events: number;
    positive_count: number;
    needs_work_count: number;
    positive_ratio?: number;
    active_students: number;
    active_teachers?: number;
    signed_points_total: number;
  };
  type Row = Metrics & { label: string; dimension_key?: number | string | null; category_type?: CategoryType };
  type StudentRow = Partial<Metrics> & { display_name: string; dimension_key?: number | null; signed_points_change?: number };
  type EventRow = {
    created_at: string;
    student_display_name: string;
    staff_display_name?: string | null;
    category_label: string;
    category_type: CategoryType;
    points_delta: number;
    context_type: string;
    class_section_name?: string | null;
    subject_name?: string | null;
    duty_context?: string | null;
  };
  type MatrixRow = Row & { cells?: Row[] };
  type EffectiveFilters = { date_from: string; date_to: string; category_type?: string | null; duty_context?: string | null; timezone?: string };
  type MatrixTruncation = { row_limit: number; column_limit?: number; rows_truncated: boolean; columns_truncated: boolean; max_cells: number; returned_rows: number; returned_cells: number };
  type FilterKey = 'categoryType' | 'gradeLevelId' | 'classSectionId' | 'subjectId' | 'dutyContext' | 'categoryId' | 'actorUserId' | 'studentId';
  type FilterState = Record<FilterKey, string> & { dateFrom: string; dateTo: string };
  type DrilldownEntry = { key: FilterKey; value: string };
  type ReportSection = 'trend' | 'classes' | 'grades' | 'subjects' | 'duties' | 'categories' | 'students' | 'teachers' | 'events' | 'patterns';

  const duties = ['break', 'lunch', 'playground', 'hallway', 'assembly', 'bus', 'general_duty'];
  const dimensions: MatrixDimension[] = ['student', 'class_section', 'grade', 'subject', 'subject_group', 'teacher', 'duty_context', 'category', 'category_type', 'date_bucket'];
  const matrixFilterKeys: Partial<Record<MatrixDimension, FilterKey>> = {
    student: 'studentId',
    class_section: 'classSectionId',
    grade: 'gradeLevelId',
    subject: 'subjectId',
    teacher: 'actorUserId',
    duty_context: 'dutyContext',
    category: 'categoryId',
    category_type: 'categoryType'
  };

  let schoolId = $state<number | null>(null);
  let allowed = $state(false);
  let loading = $state(true);
  let error = $state('');
  let filterNotice = $state('');
  let filters = $state<FilterState>({
    dateFrom: '', dateTo: '', categoryType: '', gradeLevelId: '', classSectionId: '',
    subjectId: '', dutyContext: '', categoryId: '', actorUserId: '', studentId: ''
  });
  let effectiveFilters = $state<EffectiveFilters | null>(null);

  let grades = $state<Option[]>([]);
  let sections = $state<Option[]>([]);
  let subjects = $state<Option[]>([]);
  let categories = $state<CategoryOption[]>([]);
  let teachers = $state<TeacherOption[]>([]);
  let studentResults = $state<StudentOption[]>([]);
  let studentSearch = $state('');
  let studentSearchOpen = $state(false);
  let selectedStudent = $state<StudentOption | null>(null);

  let overview = $state<{ metrics: Metrics } | null>(null);
  let trends = $state<Row[]>([]);
  let breakdowns = $state<{ classes: Row[]; grades: Row[]; subjects: Row[]; duty_contexts: Row[]; categories: Row[] } | null>(null);
  let support = $state<{ repeated_needs_work: StudentRow[]; top_positive: StudentRow[]; improving: StudentRow[]; worsening: StudentRow[] } | null>(null);
  let usage = $state<Row[]>([]);

  let eventsOpen = $state(false);
  let eventRows = $state<EventRow[]>([]);
  let eventOffset = $state(0);
  let eventTotal = $state(0);
  let eventsLoading = $state(false);
  let drilldownSummary = $state('');
  let drilldownPrevious = $state<Partial<Record<FilterKey, string>> | null>(null);
  let eventsSection = $state<HTMLElement | undefined>();

  let matrixLoading = $state(false);
  let matrixError = $state('');
  let matrixRows = $state<MatrixRow[]>([]);
  let matrixColumns = $state<{ key: number | string | null; label: string }[]>([]);
  let matrixTruncation = $state<MatrixTruncation | null>(null);
  let matrixRowDimension = $state<MatrixDimension>('student');
  let matrixColumnDimension = $state<MatrixDimension | ''>('subject');
  let matrixOrderBy = $state<MatrixOrderBy>('total_events');
  let matrixLimit = $state('25');
  let activeSection = $state<ReportSection | null>(null);

  let hasActivity = $derived(Boolean(overview?.metrics.total_events));
  let visibleCategories = $derived(categories.filter((category) => !filters.categoryType || category.type === filters.categoryType));
  let visibleSections = $derived(sections.filter((section) => !filters.gradeLevelId || String(section.grade_level_id) === filters.gradeLevelId));
  let activeFilterChips = $derived(buildActiveFilterChips());

  function options(): RequestInit {
    return { headers: { 'X-School-Id': String(schoolId) } };
  }

  function query(extra: Record<string, string | number | null | undefined> = {}) {
    const params = new URLSearchParams();
    const values: Record<string, string | number | null | undefined> = {
      date_from: filters.dateFrom,
      date_to: filters.dateTo,
      category_type: filters.categoryType,
      grade_level_id: filters.gradeLevelId,
      class_section_id: filters.classSectionId,
      subject_id: filters.subjectId,
      duty_context: filters.dutyContext,
      category_id: filters.categoryId,
      actor_user_id: filters.actorUserId,
      student_id: filters.studentId,
      ...extra
    };
    Object.entries(values).forEach(([key, value]) => {
      if (value !== '' && value != null) params.set(key, String(value));
    });
    return params.toString() ? `?${params}` : '';
  }

  const number = (value: number | undefined) => new Intl.NumberFormat().format(value || 0);
  const percent = (value: number | undefined) => new Intl.NumberFormat(undefined, { style: 'percent', maximumFractionDigits: 1 }).format(value || 0);
  const dutyLabel = (value: string) => $_(`parent.points.duty.${value}`);
  const categoryTypeLabel = (value: string) => value === 'positive' ? $_('reports.positive') : $_('reports.needsWork');
  const measureLabel = (value: MatrixOrderBy) => $_(`reports.measures.${value}`);
  const measureValue = (row: Row | undefined) => row?.[matrixOrderBy] || 0;
  const matrixCell = (row: MatrixRow, column: { key: number | string | null }) => (row.cells || []).find((item) => item.dimension_key === column.key);

  function matrixValueLabel(dimension: MatrixDimension, value: string) {
    if (dimension === 'category_type') return categoryTypeLabel(value);
    if (dimension === 'duty_context') return value === 'Not duty' ? $_('reports.notDuty') : dutyLabel(value);
    return value;
  }

  function optionName<T extends { id: number }>(rows: T[], id: string, name: (row: T) => string) {
    return rows.find((row) => String(row.id) === id) ? name(rows.find((row) => String(row.id) === id)!) : id;
  }

  function buildActiveFilterChips() {
    const chips: { key: FilterKey; text: string }[] = [];
    if (filters.categoryType) chips.push({ key: 'categoryType', text: `${$_('reports.categoryType')}: ${categoryTypeLabel(filters.categoryType)}` });
    if (filters.gradeLevelId) chips.push({ key: 'gradeLevelId', text: `${$_('reports.grade')}: ${optionName(grades, filters.gradeLevelId, (row) => row.name)}` });
    if (filters.classSectionId) chips.push({ key: 'classSectionId', text: `${$_('reports.classSection')}: ${optionName(sections, filters.classSectionId, (row) => row.name)}` });
    if (filters.subjectId) chips.push({ key: 'subjectId', text: `${$_('reports.subject')}: ${optionName(subjects, filters.subjectId, (row) => row.name)}` });
    if (filters.dutyContext) chips.push({ key: 'dutyContext', text: `${$_('reports.dutyContext')}: ${dutyLabel(filters.dutyContext)}` });
    if (filters.categoryId) chips.push({ key: 'categoryId', text: `${$_('reports.category')}: ${optionName(categories, filters.categoryId, (row) => row.label)}` });
    if (filters.actorUserId) chips.push({ key: 'actorUserId', text: `${$_('reports.teacher')}: ${optionName(teachers, filters.actorUserId, (row) => row.name)}` });
    if (filters.studentId) chips.push({ key: 'studentId', text: `${$_('reports.student')}: ${selectedStudent?.name || optionName(studentResults, filters.studentId, (row) => row.name)}` });
    return chips;
  }

  function reportPeriod() {
    if (!effectiveFilters) return '';
    return $_('reports.showingPeriod', { values: { from: effectiveFilters.date_from, to: effectiveFilters.date_to } });
  }

  function setFilter(key: FilterKey, value: string, { reload = false }: { reload?: boolean } = {}) {
    filterNotice = '';
    if (key === 'categoryType' && filters.categoryId) {
      const selectedCategory = categories.find((category) => String(category.id) === filters.categoryId);
      if (selectedCategory && value && selectedCategory.type !== value) filters.categoryId = '';
    }
    if (key === 'subjectId' && value && filters.dutyContext) {
      filters.dutyContext = '';
      filterNotice = $_('reports.subjectDutyCleared');
    }
    if (key === 'dutyContext' && value && filters.subjectId) {
      filters.subjectId = '';
      filterNotice = $_('reports.subjectDutyCleared');
    }
    filters[key] = value;
    if (reload) void loadReports();
  }

  function clearFilter(key: FilterKey) {
    filters[key] = '';
    if (key === 'classSectionId') studentResults = [];
    if (key === 'studentId') {
      selectedStudent = null;
      studentSearch = '';
      studentResults = [];
      studentSearchOpen = false;
    }
    void loadReports();
  }

  function clearDrilldown({ restore = true, reload = true }: { restore?: boolean; reload?: boolean } = {}) {
    if (restore && drilldownPrevious) {
      Object.entries(drilldownPrevious).forEach(([key, value]) => {
        filters[key as FilterKey] = value || '';
      });
    }
    drilldownSummary = '';
    drilldownPrevious = null;
    eventsOpen = false;
    eventRows = [];
    eventOffset = 0;
    eventTotal = 0;
    if (reload) void loadReports();
  }

  function openSection(section: ReportSection) {
    activeSection = section;
    if (section === 'events') {
      eventsOpen = true;
      void loadEvents(0);
    }
  }

  function closeSection() {
    activeSection = null;
    if (eventsOpen || drilldownSummary) clearDrilldown();
  }

  function reset() {
    filters = { dateFrom: '', dateTo: '', categoryType: '', gradeLevelId: '', classSectionId: '', subjectId: '', dutyContext: '', categoryId: '', actorUserId: '', studentId: '' };
    studentSearch = '';
    studentResults = [];
    studentSearchOpen = false;
    selectedStudent = null;
    filterNotice = '';
    clearDrilldown({ restore: false, reload: false });
    void loadReports();
  }

  async function loadMetadata() {
    const [gradeRows, sectionRows, subjectRows, categoryData, teacherData] = await Promise.all([
      api.get('/school/grade-levels', options()),
      api.get('/school/class-sections', options()),
      api.get('/school/subjects', options()),
      api.get('/school/behaviour/categories', options()),
      api.get('/school/teachers', options())
    ]);
    grades = gradeRows.filter((row: Option) => row.status !== 'archived');
    sections = sectionRows.filter((row: Option) => row.status !== 'archived');
    subjects = subjectRows.filter((row: Option) => row.status !== 'archived');
    categories = categoryData?.categories || [];
    teachers = (teacherData?.teachers || []).map((row: { user: { id: number; name?: string | null } }) => ({
      id: row.user.id,
      name: row.user.name || $_('reports.staffMember')
    }));
  }

  async function loadReports() {
    if (!schoolId) return;
    if (filters.dateFrom && filters.dateTo && filters.dateFrom > filters.dateTo) {
      error = $_('reports.invalidDateRange');
      return;
    }
    if (filters.subjectId && filters.dutyContext) {
      error = $_('reports.subjectDutyIncompatible');
      return;
    }
    loading = true;
    error = '';
    eventOffset = 0;
    try {
      const q = query();
      const [overviewData, trendData, breakdownData, studentData, teacherData] = await Promise.all([
        api.get(`/school/reports/behaviour/overview${q}`, options()),
        api.get(`/school/reports/behaviour/trends${q}`, options()),
        api.get(`/school/reports/behaviour/breakdowns${q}`, options()),
        api.get(`/school/reports/behaviour/students${q}`, options()),
        api.get(`/school/reports/behaviour/teachers${q}`, options())
      ]);
      overview = overviewData;
      effectiveFilters = overviewData?.filters || null;
      trends = (trendData?.series || []).map((row: Row & { date: string }) => ({ ...row, label: row.date }));
      breakdowns = breakdownData;
      support = studentData;
      usage = (teacherData?.teachers || []).map((row: Row & { display_name?: string }) => ({ ...row, label: row.display_name || $_('reports.staffMember') }));
      if (eventsOpen) await loadEvents(0);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : $_('reports.loadError');
      error = message || $_('reports.loadError');
      overview = null;
      trends = [];
      breakdowns = null;
      support = null;
      usage = [];
    } finally {
      loading = false;
    }
  }

  async function loadEvents(offset = eventOffset) {
    if (!schoolId) return;
    eventsLoading = true;
    try {
      const data = await api.get(`/school/reports/behaviour/events${query({ limit: 25, offset })}`, options());
      eventRows = data?.events || [];
      eventTotal = data?.pagination?.total || 0;
      eventOffset = data?.pagination?.offset || 0;
    } catch (err: unknown) {
      error = err instanceof Error ? err.message : $_('reports.loadError');
    } finally {
      eventsLoading = false;
    }
  }

  function studentClassLabel(section: Option | null | undefined) {
    if (!section) return $_('reports.noCurrentClass');
    const gradeName = section.grade_level_id ? grades.find((grade) => grade.id === section.grade_level_id)?.name : '';
    if (!gradeName || section.name.toLocaleLowerCase().includes(gradeName.toLocaleLowerCase())) return section.name;
    return `${gradeName} ${section.name}`;
  }

  async function searchStudents() {
    const searchTerm = studentSearch.trim();
    studentSearchOpen = true;
    selectedStudent = null;
    filters.studentId = '';
    if (!schoolId || searchTerm.length < 2) {
      studentResults = [];
      return;
    }
    try {
      const params = new URLSearchParams({ search: searchTerm });
      if (filters.classSectionId) params.set('class_section_id', filters.classSectionId);
      const data = await api.get(`/school/students?${params}`, options());
      if (studentSearch.trim() !== searchTerm) return;
      studentResults = (data || []).slice(0, 20).map((student: StudentSearchResponse) => ({
        id: student.id,
        name: student.display_name,
        classLabel: studentClassLabel(student.current_class_section)
      }));
    } catch {
      if (studentSearch.trim() === searchTerm) studentResults = [];
    }
  }

  function selectStudent(student: StudentOption) {
    selectedStudent = student;
    studentSearch = student.name;
    studentResults = [];
    studentSearchOpen = false;
    setFilter('studentId', String(student.id));
  }

  async function openDrilldown(entries: DrilldownEntry[], summary: string) {
    if (entries.some((entry) => !entry.value)) return;
    drilldownPrevious = Object.fromEntries(entries.map((entry) => [entry.key, filters[entry.key]]));
    entries.forEach((entry) => setFilter(entry.key, entry.value));
    drilldownSummary = summary;
    eventsOpen = true;
    activeSection = 'events';
    await loadReports();
    await tick();
    eventsSection?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    eventsSection?.focus({ preventScroll: true });
  }

  function matrixEntry(dimension: MatrixDimension, value: number | string | null | undefined): DrilldownEntry | null {
    const key = matrixFilterKeys[dimension];
    if (!key || value == null || value === '') return null;
    return { key, value: String(value) };
  }

  function canDrillMatrix(dimension: MatrixDimension, value: number | string | null | undefined) {
    return Boolean(matrixEntry(dimension, value));
  }

  async function openMatrixDrilldown(row: MatrixRow, cell?: Row) {
    const entries = [matrixEntry(matrixRowDimension, row.dimension_key)];
    if (cell && matrixColumnDimension) entries.push(matrixEntry(matrixColumnDimension, cell.dimension_key));
    if (entries.some((entry) => entry === null)) {
      matrixError = $_('reports.matrixDrilldownUnavailable');
      return;
    }
    const rowLabel = matrixValueLabel(matrixRowDimension, row.label);
    const cellLabel = cell && matrixColumnDimension ? matrixValueLabel(matrixColumnDimension, cell.label) : '';
    await openDrilldown(entries as DrilldownEntry[], cellLabel ? `${rowLabel} · ${cellLabel}` : rowLabel);
  }

  async function loadMatrix() {
    if (!schoolId) return;
    if (filters.subjectId && filters.dutyContext) {
      matrixError = $_('reports.subjectDutyIncompatible');
      return;
    }
    matrixLoading = true;
    matrixError = '';
    try {
      const data = await api.get(`/school/reports/behaviour/matrix${query({ row_dimension: matrixRowDimension, column_dimension: matrixColumnDimension || null, order_by: matrixOrderBy, limit: matrixLimit })}`, options());
      matrixRows = data?.rows || [];
      const columns = new Map<string, { key: number | string | null; label: string }>();
      matrixRows.flatMap((row) => row.cells || []).forEach((cell) => {
        const key = `${String(cell.dimension_key)}:${cell.label}`;
        if (!columns.has(key)) columns.set(key, { key: cell.dimension_key ?? null, label: cell.label });
      });
      matrixColumns = [...columns.values()];
      matrixTruncation = data?.truncation || null;
    } catch (err: unknown) {
      matrixRows = [];
      matrixColumns = [];
      matrixTruncation = null;
      matrixError = err instanceof Error ? err.message : $_('reports.matrixError');
    } finally {
      matrixLoading = false;
    }
  }

  function changeCategoryType(value: string) {
    setFilter('categoryType', value);
    if (filters.categoryId && !visibleCategories.some((category) => String(category.id) === filters.categoryId)) filters.categoryId = '';
  }

  $effect(() => {
    if (filters.classSectionId && !visibleSections.some((section) => String(section.id) === filters.classSectionId)) filters.classSectionId = '';
  });

  async function init() {
    try {
      const me = await api.get('/me/v2');
      const membership = ((me?.memberships || []) as Membership[]).find((item) => item.role === 'school_admin');
      if (!membership) return;
      schoolId = membership.school_id;
      allowed = true;
      await loadMetadata();
      await loadReports();
    } catch (err: unknown) {
      const status = (err as { status?: number })?.status;
      if (status === 401) {
        window.location.href = `/login?returnTo=${encodeURIComponent('/school/reports')}`;
        return;
      }
      error = err instanceof Error ? err.message : $_('reports.loadError');
    } finally {
      loading = false;
    }
  }

  onMount(init);
</script>

<svelte:head>
  <title>{$_('reports.title')} | {$_('app.name')}</title>
</svelte:head>

<section class="reports-page mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
  {#if !loading && !allowed}
    <div class="mx-auto max-w-xl rounded-3xl border border-amber-200 bg-amber-50 p-8 text-center">
      <h1 class="text-2xl font-bold">{$_('reports.accessDeniedTitle')}</h1>
      <p class="mt-3 text-slate-600">{$_('reports.accessDenied')}</p>
    </div>
  {:else}
    <header class="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p class="text-sm font-bold uppercase tracking-[.18em] text-hero">{$_('nav.school')}</p>
        <h1 class="mt-1 text-3xl font-bold text-slate-900">{$_('reports.title')}</h1>
        <p class="mt-2 text-slate-600">{$_('reports.subtitle')}</p>
        {#if reportPeriod()}<p class="mt-2 text-sm font-semibold text-slate-700">{reportPeriod()}</p>{/if}
      </div>
      <p class="max-w-xs rounded-2xl bg-slate-100 px-4 py-3 text-xs text-slate-600">{$_('reports.teacherUsageGuardrail')}</p>
    </header>

    <form class="report-card mb-5 rounded-3xl p-5" onsubmit={(event) => { event.preventDefault(); void loadReports(); }}>
      <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2 class="text-lg font-bold text-slate-900">{$_('reports.filters')}</h2>
        <button type="button" onclick={reset} class="text-sm font-semibold text-slate-600 hover:text-hero">{$_('reports.reset')}</button>
      </div>
      <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <label for="date-from">{$_('reports.dateFrom')}<input id="date-from" bind:value={filters.dateFrom} type="date" /></label>
        <label for="date-to">{$_('reports.dateTo')}<input id="date-to" bind:value={filters.dateTo} type="date" /></label>
        <label>{$_('reports.categoryType')}<select value={filters.categoryType} onchange={(event) => changeCategoryType(event.currentTarget.value)}><option value="">{$_('reports.allCategories')}</option><option value="positive">{$_('reports.positive')}</option><option value="needs_work">{$_('reports.needsWork')}</option></select></label>
        <label>{$_('reports.grade')}<select value={filters.gradeLevelId} onchange={(event) => setFilter('gradeLevelId', event.currentTarget.value)}><option value="">{$_('reports.all')}</option>{#each grades as row}<option value={row.id}>{row.name}</option>{/each}</select></label>
        <label>{$_('reports.classSection')}<select value={filters.classSectionId} onchange={(event) => setFilter('classSectionId', event.currentTarget.value)}><option value="">{$_('reports.all')}</option>{#each visibleSections as row}<option value={row.id}>{row.name}</option>{/each}</select>{#if !visibleSections.length}<span class="normal-case text-slate-500">{$_('reports.noRows')}</span>{/if}</label>
        <label>{$_('reports.subject')}<select value={filters.subjectId} onchange={(event) => setFilter('subjectId', event.currentTarget.value)}><option value="">{$_('reports.all')}</option>{#each subjects as row}<option value={row.id}>{row.name}</option>{/each}</select></label>
        <label>{$_('reports.dutyContext')}<select value={filters.dutyContext} onchange={(event) => setFilter('dutyContext', event.currentTarget.value)}><option value="">{$_('reports.all')}</option>{#each duties as duty}<option value={duty}>{dutyLabel(duty)}</option>{/each}</select></label>
        <label>{$_('reports.category')}<select value={filters.categoryId} onchange={(event) => setFilter('categoryId', event.currentTarget.value)}><option value="">{$_('reports.all')}</option>{#each visibleCategories as category}<option value={category.id}>{category.label}</option>{/each}</select></label>
        <label>{$_('reports.teacher')}<select value={filters.actorUserId} onchange={(event) => setFilter('actorUserId', event.currentTarget.value)}><option value="">{$_('reports.all')}</option>{#each teachers as teacher}<option value={teacher.id}>{teacher.name}</option>{/each}</select></label>
        <label class="student-filter">{$_('reports.student')}<div class="student-autocomplete"><input bind:value={studentSearch} oninput={searchStudents} onfocus={() => { if (studentSearch.trim().length >= 2) studentSearchOpen = true; }} onblur={() => window.setTimeout(() => studentSearchOpen = false, 120)} placeholder={$_('reports.studentSearch')} autocomplete="off" aria-expanded={studentSearchOpen} aria-controls="student-suggestions" />{#if selectedStudent}<button type="button" class="clear-student" onclick={() => clearFilter('studentId')}>{$_('reports.clearStudent')}</button>{/if}{#if studentSearchOpen && studentSearch.trim().length >= 2}<div id="student-suggestions" class="student-suggestions" role="listbox">{#if studentResults.length}{#each studentResults as student}<button type="button" role="option" aria-selected={filters.studentId === String(student.id)} class="student-suggestion" onclick={() => selectStudent(student)}><span class="student-name">{student.name}</span><span class="student-class"> — {student.classLabel}</span></button>{/each}{:else}<p class="student-no-results">{$_('reports.noMatchingStudents')}</p>{/if}</div>{/if}</div></label>
      </div>
      <div class="mt-4 flex gap-3"><button class="rounded-xl bg-hero px-5 py-2.5 text-sm font-bold text-white">{$_('reports.apply')}</button></div>
      {#if filterNotice}<p class="mt-3 text-sm text-amber-800">{filterNotice}</p>{/if}
    </form>

    {#if activeFilterChips.length}
      <div class="mb-6 flex flex-wrap items-center gap-2" aria-label={$_('reports.activeFilters')}>
        <span class="text-sm font-semibold text-slate-600">{$_('reports.activeFilters')}:</span>
        {#each activeFilterChips as chip}
          <button class="filter-chip" onclick={() => clearFilter(chip.key)}>{chip.text}<span aria-hidden="true"> ×</span><span class="sr-only">{$_('reports.removeFilter')}</span></button>
        {/each}
        <button class="text-sm font-semibold text-hero hover:underline" onclick={reset}>{$_('reports.clearAllFilters')}</button>
      </div>
    {/if}

    {#if error}<div class="mb-6 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-rose-800" role="alert">{error}</div>{/if}

    {#if loading}
      <div class="rounded-3xl border border-slate-200 bg-white p-10 text-center text-slate-600">{$_('reports.loading')}</div>
    {:else if overview && !hasActivity}
      <div class="rounded-3xl border border-dashed border-slate-300 bg-white p-10 text-center text-slate-600">{$_('reports.empty')}</div>
    {:else if overview && breakdowns}
      <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {@render Metric($_('reports.totalEvents'), number(overview.metrics.total_events))}
        {@render Metric($_('reports.positiveCount'), number(overview.metrics.positive_count), 'positive')}
        {@render Metric($_('reports.needsWorkCount'), number(overview.metrics.needs_work_count), 'needs-work')}
        {@render Metric($_('reports.positiveRatio'), percent(overview.metrics.positive_ratio))}
        {@render Metric($_('reports.activeStudents'), number(overview.metrics.active_students))}
        {@render Metric($_('reports.activeTeachers'), number(overview.metrics.active_teachers))}
        {@render Metric($_('reports.signedPoints'), number(overview.metrics.signed_points_total))}
      </div>

      <section class="mt-7">
        <div class="mb-3 flex flex-wrap items-center justify-between gap-3">
          <h2 class="text-xl font-bold text-slate-900">{$_('reports.overviewOnly')}</h2>
          {#if activeSection}<button onclick={closeSection} class="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-bold text-slate-700 hover:border-hero hover:text-hero">{$_('reports.backToOverview')}</button>{/if}
        </div>
        <div class="launcher-grid">
          {@render Launcher('trend', $_('reports.launcherBehaviourTrend'), $_('reports.launcherBehaviourTrendDescription'))}
          {@render Launcher('classes', $_('reports.launcherClassComparison'), $_('reports.launcherClassComparisonDescription'))}
          {@render Launcher('grades', $_('reports.launcherGradeComparison'), $_('reports.launcherGradeComparisonDescription'))}
          {@render Launcher('subjects', $_('reports.launcherSubjectComparison'), $_('reports.launcherSubjectComparisonDescription'))}
          {@render Launcher('duties', $_('reports.launcherDutyHotspots'), $_('reports.launcherDutyHotspotsDescription'))}
          {@render Launcher('categories', $_('reports.launcherCategoryBreakdown'), $_('reports.launcherCategoryBreakdownDescription'))}
          {@render Launcher('students', $_('reports.launcherStudentSupport'), $_('reports.launcherStudentSupportDescription'))}
          {@render Launcher('teachers', $_('reports.launcherTeacherUsage'), $_('reports.launcherTeacherUsageDescription'))}
          {@render Launcher('events', $_('reports.viewMatchingEvents'), $_('reports.launcherEventsDescription'))}
          {@render Launcher('patterns', $_('reports.deepDive'), $_('reports.launcherPatternsDescription'))}
        </div>
      </section>

      {#if activeSection === 'trend'}<section class="report-card mt-7 card p-5">
        <h2 class="text-xl font-bold">{$_('reports.trends')}</h2>
        <p class="mt-1 text-sm text-slate-600">{$_('reports.trendsIntro')}</p>
        <p class="sort-label">{$_('reports.oldestFirst')}</p>
        {@render SummaryTable($_('reports.trends'), trends, null)}
      </section>{/if}

      {#if activeSection === 'classes'}<div class="mt-7">{@render SummaryTable($_('reports.classComparison'), breakdowns.classes, { key: 'classSectionId', label: $_('reports.classSection') })}</div>{/if}
      {#if activeSection === 'grades'}<div class="mt-7">{@render SummaryTable($_('reports.gradeComparison'), breakdowns.grades, { key: 'gradeLevelId', label: $_('reports.grade') })}</div>{/if}
      {#if activeSection === 'subjects'}<div class="mt-7">{@render SummaryTable($_('reports.subjectComparison'), breakdowns.subjects, { key: 'subjectId', label: $_('reports.subject') })}</div>{/if}
      {#if activeSection === 'duties'}<div class="mt-7">{@render SummaryTable($_('reports.dutyHotspots'), breakdowns.duty_contexts, { key: 'dutyContext', label: $_('reports.dutyContext') }, true)}</div>{/if}
      {#if activeSection === 'categories'}<div class="mt-7">{@render SummaryTable($_('reports.categoryBreakdown'), breakdowns.categories, { key: 'categoryId', label: $_('reports.category') })}</div>{/if}

      {#if activeSection === 'students'}<div class="mt-7">
        <section class="report-card card p-5">
          <h2 class="text-xl font-bold">{$_('reports.studentSupport')}</h2>
          <p class="mt-1 text-sm text-slate-600">{$_('reports.studentSupportIntro')}</p>
          <div class="mt-4 grid gap-4 sm:grid-cols-2">
            {@render StudentTable($_('reports.repeatedNeedsWork'), support?.repeated_needs_work || [], 'needs_work', false)}
            {@render StudentTable($_('reports.topPositive'), support?.top_positive || [], 'positive', false)}
            {@render StudentTable($_('reports.improving'), support?.improving || [], null, true)}
            {@render StudentTable($_('reports.worsening'), support?.worsening || [], null, true)}
          </div>
        </section>
      </div>{/if}
      {#if activeSection === 'teachers'}<div class="mt-7">
        <section class="report-card card p-5">
          <h2 class="text-xl font-bold">{$_('reports.teacherUsage')}</h2>
          <p class="mt-1 text-sm text-slate-600">{$_('reports.teacherUsageGuardrail')}</p>
          {@render SummaryTable($_('reports.teacherUsage'), usage, { key: 'actorUserId', label: $_('reports.teacher') })}
        </section>
      </div>{/if}

      {#if activeSection === 'events'}<section class="report-card mt-7 card p-5" bind:this={eventsSection} tabindex="-1">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 class="text-xl font-bold">{$_('reports.underlyingEvents')}</h2>
            <p class="text-sm text-slate-600">{$_('reports.eventsIntro')}</p>
            <p class="sort-label">{$_('reports.newestFirst')}</p>
          </div>
          <div class="flex gap-2">
            {#if drilldownSummary}<button onclick={() => clearDrilldown()} class="rounded-xl border border-slate-300 px-4 py-2 text-sm font-bold">{$_('reports.clearDrilldown')}</button>{/if}
            <button onclick={closeSection} class="rounded-xl border border-slate-300 px-4 py-2 text-sm font-bold">{$_('reports.closeSection')}</button>
          </div>
        </div>
        {#if drilldownSummary}<p class="mt-3 rounded-xl bg-hero/10 px-3 py-2 text-sm font-semibold text-hero">{$_('reports.showingEventsFor')}: {drilldownSummary}</p>{/if}
        {#if eventsOpen}{@render EventsTable()}{/if}
      </section>{/if}

      {#if activeSection === 'patterns'}<section class="report-card mt-7 card p-5">
        <h2 class="text-xl font-bold">{$_('reports.deepDive')}</h2>
        <p class="text-sm text-slate-600">{$_('reports.deepDiveIntro')}</p>
        <div class="mt-4 flex flex-wrap gap-2">
          {#each [['student', 'subject'], ['teacher', 'subject'], ['subject', 'class_section'], ['class_section', 'category'], ['grade', 'duty_context'], ['student', 'teacher'], ['subject', 'category_type']] as preset}
            <button onclick={() => { matrixRowDimension = preset[0] as MatrixDimension; matrixColumnDimension = preset[1] as MatrixDimension; void loadMatrix(); }} class="rounded-full bg-slate-100 px-3 py-2 text-xs font-semibold text-slate-700">{$_(`reports.dimensions.${preset[0]}`)} × {$_(`reports.dimensions.${preset[1]}`)}</button>
          {/each}
        </div>
        <div class="mt-4 grid gap-3 sm:grid-cols-4">
          <label>{$_('reports.rowDimension')}<select bind:value={matrixRowDimension}>{#each dimensions as dimension}<option value={dimension}>{$_(`reports.dimensions.${dimension}`)}</option>{/each}</select></label>
          <label>{$_('reports.columnDimension')}<select bind:value={matrixColumnDimension}><option value="">{$_('reports.none')}</option>{#each dimensions as dimension}<option value={dimension}>{$_(`reports.dimensions.${dimension}`)}</option>{/each}</select></label>
          <label>{$_('reports.orderBy')}<select bind:value={matrixOrderBy}>{#each ['total_events', 'positive_count', 'needs_work_count', 'signed_points_total'] as measure}<option value={measure}>{measureLabel(measure as MatrixOrderBy)}</option>{/each}</select></label>
          <label>{$_('reports.limit')}<select bind:value={matrixLimit}><option value="10">10</option><option value="25">25</option><option value="50">50</option></select></label>
        </div>
        <button onclick={() => void loadMatrix()} class="mt-4 rounded-xl bg-slate-900 px-5 py-2.5 text-sm font-bold text-white">{$_('reports.runDeepDive')}</button>
        {#if matrixError}<p class="mt-3 text-sm text-rose-700">{matrixError}</p>{/if}
        {#if matrixLoading}<p class="mt-3 text-sm text-slate-500">{$_('reports.loading')}</p>
        {:else if matrixRows.length}
          <p class="sort-label">{$_('reports.sortedBy', { values: { measure: measureLabel(matrixOrderBy) } })}</p>
          {#if matrixTruncation && (matrixTruncation.rows_truncated || matrixTruncation.columns_truncated)}<p class="mt-2 text-sm text-amber-800">{$_('reports.matrixTruncated', { values: { rows: matrixTruncation.returned_rows, cells: matrixTruncation.returned_cells } })}</p>{/if}
          <div class="mt-4 overflow-x-auto"><table><thead><tr><th>{$_('reports.label')}</th>{#each matrixColumns as column}<th>{matrixColumnDimension ? matrixValueLabel(matrixColumnDimension as MatrixDimension, column.label) : column.label}</th>{/each}{#if !matrixColumns.length}<th>{measureLabel(matrixOrderBy)}</th>{/if}</tr></thead><tbody>{#each matrixRows as row}<tr><td>{#if canDrillMatrix(matrixRowDimension, row.dimension_key)}<button onclick={() => void openMatrixDrilldown(row)}>{matrixValueLabel(matrixRowDimension, row.label)} <span aria-hidden="true">→</span></button>{:else}<span>{matrixValueLabel(matrixRowDimension, row.label)}</span>{/if}</td>{#if matrixColumns.length}{#each matrixColumns as column}<td>{#if matrixCell(row, column)}{#if matrixColumnDimension && canDrillMatrix(matrixRowDimension, row.dimension_key) && canDrillMatrix(matrixColumnDimension as MatrixDimension, matrixCell(row, column)?.dimension_key)}<button onclick={() => void openMatrixDrilldown(row, matrixCell(row, column))}>{number(measureValue(matrixCell(row, column)))}</button>{:else}<span title={$_('reports.matrixDrilldownUnavailable')}>{number(measureValue(matrixCell(row, column)))}</span>{/if}<small>{$_('reports.total')}: {number(matrixCell(row, column)?.total_events)}</small>{:else}<span class="text-slate-400">—</span>{/if}</td>{/each}{:else}<td>{#if canDrillMatrix(matrixRowDimension, row.dimension_key)}<button onclick={() => void openMatrixDrilldown(row)}>{number(measureValue(row))}</button>{:else}{number(measureValue(row))}{/if}<small>{$_('reports.total')}: {number(row.total_events)}</small></td>{/if}</tr>{/each}</tbody></table></div>
        {/if}
      </section>{/if}
    {/if}
  {/if}
</section>

{#snippet Metric(label: string, value: string, tone = '')}
  <article class:positive-card={tone === 'positive'} class:needs-work-card={tone === 'needs-work'} class="metric-card rounded-3xl p-5"><p class="text-xs font-bold uppercase text-slate-500">{label}</p><p class="mt-2 text-3xl font-bold text-slate-900">{value}</p></article>
{/snippet}

{#snippet Launcher(section: ReportSection, title: string, description: string)}
  <button type="button" onclick={() => openSection(section)} class:active-launcher={activeSection === section} class="report-launcher text-left">
    <span class="font-bold text-slate-900">{title}</span>
    <span class="mt-1 block text-sm leading-5 text-slate-600">{description}</span>
    <span class="mt-3 block text-sm font-bold text-hero">{activeSection === section ? $_('reports.closeSection') : '→'}</span>
  </button>
{/snippet}

{#snippet SummaryTable(title: string, rows: Row[], drilldown: { key: FilterKey; label: string } | null, duty = false)}
  <section class="report-card overflow-hidden rounded-3xl">
    <div class="border-b px-5 py-4"><h2 class="text-lg font-bold">{title}</h2><p class="sort-label">{$_('reports.sortedByTotal')}</p></div>
    {#if rows.length}
      <div class="overflow-x-auto"><table><thead><tr><th>{$_('reports.label')}</th><th>{$_('reports.positive')}</th><th>{$_('reports.needsWork')}</th><th>{$_('reports.total')}</th></tr></thead><tbody>{#each rows as row}<tr><td>{#if drilldown && row.dimension_key != null}<button class="row-action" onclick={() => void openDrilldown([{ key: drilldown.key, value: String(row.dimension_key) }], `${drilldown.label}: ${duty ? dutyLabel(row.label) : row.label}`)}>{duty ? dutyLabel(row.label) : row.label}<span aria-hidden="true"> →</span><span class="sr-only">{$_('reports.clickToViewEvents')}</span></button>{:else}{row.label}{/if}{#if row.category_type}<span class:positive-badge={row.category_type === 'positive'} class:needs-work-badge={row.category_type === 'needs_work'} class="badge">{categoryTypeLabel(row.category_type)}</span>{/if}</td><td>{number(row.positive_count)}</td><td>{number(row.needs_work_count)}</td><td class="font-semibold">{number(row.total_events)}</td></tr>{/each}</tbody></table></div>
    {:else}<p class="p-5 text-sm text-slate-500">{$_('reports.noRows')}</p>{/if}
  </section>
{/snippet}

{#snippet StudentTable(title: string, rows: StudentRow[], categoryType: CategoryType | null, change: boolean)}
  <div><h3 class="text-sm font-bold">{title}</h3><p class="sort-label">{change ? $_('reports.changeVsPrevious') : categoryType === 'needs_work' ? $_('reports.sortedByNeedsWork') : $_('reports.sortedByPositive')}</p>{#if rows.length}<ul class="mt-2 space-y-1">{#each rows as row}<li><button onclick={() => void openDrilldown([{ key: 'studentId', value: String(row.dimension_key) }, ...(categoryType ? [{ key: 'categoryType' as FilterKey, value: categoryType }] : [])], `${$_('reports.student')}: ${row.display_name}`)} class="w-full rounded-lg bg-slate-50 px-3 py-2 text-left text-sm hover:bg-hero/10"><span class="font-semibold">{row.display_name}</span><span class="float-right text-slate-600">{change ? number(row.signed_points_change) : number(categoryType === 'needs_work' ? row.needs_work_count : row.positive_count)}</span></button></li>{/each}</ul>{:else}<p class="mt-2 text-sm text-slate-500">{$_('reports.noRows')}</p>{/if}</div>
{/snippet}

{#snippet EventsTable()}
  <div class="mt-5 overflow-x-auto">{#if eventsLoading}<p class="py-4 text-sm text-slate-500">{$_('reports.loading')}</p>{:else if !eventRows.length}<p class="rounded-xl bg-slate-50 p-4 text-sm text-slate-600">{$_('reports.noEvents')}</p>{:else}<table><thead><tr><th>{$_('reports.date')}</th><th>{$_('reports.student')}</th><th>{$_('reports.category')}</th><th>{$_('reports.points')}</th><th>{$_('reports.context')}</th><th>{$_('reports.staff')}</th></tr></thead><tbody>{#each eventRows as event}<tr><td>{new Date(event.created_at).toLocaleString()}</td><td>{event.student_display_name}</td><td>{event.category_label}<span class:positive-badge={event.category_type === 'positive'} class:needs-work-badge={event.category_type === 'needs_work'} class="badge">{categoryTypeLabel(event.category_type)}</span></td><td>{number(event.points_delta)}</td><td>{event.class_section_name || event.subject_name || (event.duty_context ? dutyLabel(event.duty_context) : $_(`reports.contextTypes.${event.context_type}`))}</td><td>{event.staff_display_name || $_('reports.staffMember')}</td></tr>{/each}</tbody></table><div class="mt-4 flex items-center justify-between gap-3"><button class="pagination-button" disabled={eventOffset === 0} onclick={() => void loadEvents(Math.max(0, eventOffset - 25))}>{$_('reports.previous')}</button><span class="text-sm text-slate-500">{$_('reports.pagination', { values: { from: eventOffset + 1, to: Math.min(eventOffset + eventRows.length, eventTotal), total: eventTotal } })}</span><button class="pagination-button" disabled={eventOffset + eventRows.length >= eventTotal} onclick={() => void loadEvents(eventOffset + 25)}>{$_('reports.next')}</button></div>{/if}</div>
{/snippet}

<style>
  .reports-page { border-radius: 2rem; background: linear-gradient(180deg, rgba(248, 250, 252, .9), rgba(241, 245, 249, .75)); }
  .report-card { border: 1px solid #cbd5e1; background: rgba(255, 255, 255, .96); box-shadow: 0 12px 28px rgba(15, 23, 42, .07), 0 2px 5px rgba(15, 23, 42, .035); }
  .metric-card { border: 1px solid #cbd5e1; background: linear-gradient(145deg, #ffffff, #f8fafc); box-shadow: 0 10px 22px rgba(15, 23, 42, .075), 0 1px 3px rgba(15, 23, 42, .06); }
  .launcher-grid { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr)); }
  .report-launcher { border: 1px solid #cbd5e1; border-radius: 1.25rem; background: rgba(255,255,255,.96); padding: 1.1rem; box-shadow: 0 5px 15px rgba(15,23,42,.05); transition: border-color .15s, box-shadow .15s, transform .15s; }
  .report-launcher:hover, .report-launcher:focus-visible, .active-launcher { border-color: #0f766e; box-shadow: 0 10px 22px rgba(15,23,42,.1); outline: none; transform: translateY(-1px); }
  label { display: flex; flex-direction: column; gap: .3rem; color: #475569; font-size: .75rem; font-weight: 700; letter-spacing: .04em; text-transform: uppercase; }
  input, select { width: 100%; border: 1px solid #cbd5e1; border-radius: .75rem; padding: .6rem .7rem; background: #fff; color: #1e293b; font-weight: 500; letter-spacing: normal; text-transform: none; }
  table { width: 100%; min-width: 520px; font-size: .875rem; }
  th { padding: .7rem 1rem; background: #f8fafc; color: #64748b; font-size: .7rem; text-align: left; text-transform: uppercase; }
  td { padding: .7rem 1rem; border-top: 1px solid #f1f5f9; vertical-align: middle; }
  td small { display: block; margin-top: .15rem; color: #64748b; font-size: .7rem; }
  .sort-label { margin-top: .35rem; color: #64748b; font-size: .75rem; }
  .filter-chip { border-radius: 9999px; background: #ecfdf5; color: #0f766e; font-size: .75rem; font-weight: 700; padding: .35rem .65rem; }
  .row-action, td button { color: #0f766e; font-weight: 600; text-align: left; }
  .badge { display: inline-flex; margin-left: .45rem; border-radius: 9999px; padding: .12rem .45rem; font-size: .68rem; font-weight: 700; vertical-align: middle; }
  .positive-badge { background: #ecfdf5; color: #047857; }
  .needs-work-badge { background: #fff7ed; color: #c2410c; }
  .positive-card { border-color: rgba(16, 185, 129, .42); background: linear-gradient(145deg, #f0fdf4, #ffffff); }
  .needs-work-card { border-color: rgba(249, 115, 22, .42); background: linear-gradient(145deg, #fff7ed, #ffffff); }
  .pagination-button { border-radius: .5rem; padding: .45rem .7rem; font-size: .875rem; font-weight: 700; color: #334155; }
  .student-filter { position: relative; }
  .student-autocomplete { position: relative; }
  .student-autocomplete input { padding-right: 2.5rem; }
  .clear-student { position: absolute; right: .55rem; top: .55rem; border-radius: .5rem; color: #64748b; font-size: .8rem; font-weight: 800; line-height: 1; text-transform: none; }
  .student-suggestions { position: absolute; z-index: 30; top: calc(100% + .4rem); left: 0; right: 0; overflow: hidden; border: 1px solid #cbd5e1; border-radius: .9rem; background: #fff; box-shadow: 0 14px 28px rgba(15, 23, 42, .14); text-transform: none; }
  .student-suggestion { display: block; width: 100%; padding: .7rem .8rem; border-top: 1px solid #e2e8f0; color: #334155; font-size: .85rem; font-weight: 500; letter-spacing: normal; text-align: left; }
  .student-suggestion:first-child { border-top: 0; }
  .student-suggestion:hover, .student-suggestion:focus-visible { background: #f0fdf4; color: #0f766e; outline: none; }
  .student-name { font-weight: 700; }
  .student-class { color: #64748b; }
  .student-no-results { padding: .7rem .8rem; color: #64748b; font-size: .8rem; font-weight: 500; letter-spacing: normal; text-transform: none; }
  button:disabled { cursor: not-allowed; opacity: .4; }
</style>
