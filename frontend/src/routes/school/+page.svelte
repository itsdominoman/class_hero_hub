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
  import { CheckCircle2, Circle, Plus } from 'lucide-svelte';

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
  };
  type ChecklistItem = { key: string; label: string; complete: boolean; count: number; required: boolean };

  const tabs = [
    { key: 'checklist', label: 'school.tabs.checklist' },
    { key: 'settings', label: 'school.tabs.settings' },
    { key: 'branches', label: 'school.tabs.branches' },
    { key: 'stages', label: 'school.tabs.stages' },
    { key: 'years', label: 'school.tabs.years' },
    { key: 'levels', label: 'school.tabs.levels' },
    { key: 'sections', label: 'school.tabs.sections' },
    { key: 'subjects', label: 'school.tabs.subjects' },
    { key: 'groups', label: 'school.tabs.groups' }
  ];

  let loading = $state(true);
  let saving = $state(false);
  let editingPath = $state<string | null>(null);
  let editingId = $state<number | null>(null);
  let error = $state<string | null>(null);
  let notice = $state<string | null>(null);
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

  let branchForm = $state(baseForm('MAIN', 'Main Branch'));
  let stageForm = $state(baseForm('PRIMARY', 'Primary'));
  let yearForm = $state(baseForm('2026-27', '2026/27'));
  let levelForm = $state({ ...baseForm('G1', 'Grade 1'), education_stage_id: '' });
  let sectionForm = $state({ ...baseForm('A', ''), branch_campus_id: '', academic_year_id: '', grade_level_id: '' });
  let subjectForm = $state(baseForm('ENG', 'English'));
  let groupForm = $state({ ...baseForm('', ''), academic_year_id: '', class_section_id: '', subject_id: '' });
  let quickLabels = $state('A, B, C');

  function baseForm(code = '', name = '') {
    return { code, name, name_ar: '', sort_order: 0, status: 'active' };
  }

  function schoolOptions(): RequestInit {
    return { headers: { 'X-School-Id': String(schoolId) } };
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

  function yearName(id?: number | string | null) {
    return rowName(years, id);
  }

  function subjectName(id?: number | string | null) {
    return rowName(subjects, id);
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

  async function loadAll() {
    if (!schoolId) return;
    const options = schoolOptions();
    const [settings, checklistData, branchRows, stageRows, yearRows, levelRows, sectionRows, subjectRows, groupRows] = await Promise.all([
      api.get('/school/settings', options),
      api.get('/school/setup-checklist', options),
      api.get('/school/branches', options),
      api.get('/school/education-stages', options),
      api.get('/school/academic-years', options),
      api.get('/school/grade-levels', options),
      api.get('/school/class-sections', options),
      api.get('/school/subjects', options),
      api.get('/school/subject-groups', options)
    ]);
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
    if (path === 'branches') branchForm = baseForm('', '');
    else if (path === 'education-stages') stageForm = baseForm('', '');
    else if (path === 'academic-years') yearForm = baseForm('', '');
    else if (path === 'subjects') subjectForm = baseForm('', '');
    else if (path === 'grade-levels') levelForm = { ...baseForm('', ''), education_stage_id: '' };
    else if (path === 'class-sections') sectionForm = { ...baseForm('', ''), branch_campus_id: '', academic_year_id: '', grade_level_id: '' };
    else if (path === 'subject-groups') groupForm = { ...baseForm('', ''), academic_year_id: '', class_section_id: '', subject_id: '' };
  }

  function cancelEdit() {
    if (editingPath) resetForm(editingPath);
    editingPath = null;
    editingId = null;
    notice = null;
  }

  function selectTab(key: string) {
    cancelEdit();
    activeTab = key;
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
    if (path === 'grade-levels') form.education_stage_id = idStr(row.education_stage_id);
    if (path === 'class-sections') {
      form.branch_campus_id = idStr(row.branch_campus_id);
      form.academic_year_id = idStr(row.academic_year_id);
      form.grade_level_id = idStr(row.grade_level_id);
    }
    if (path === 'subject-groups') {
      form.academic_year_id = idStr(row.academic_year_id);
      form.class_section_id = idStr(row.class_section_id);
      form.subject_id = idStr(row.subject_id);
    }
  }

  // Create when not editing this block, otherwise update the row being edited.
  async function saveVia(path: string, payload: any, reset: () => void) {
    if (!schoolId) return;
    saving = true;
    error = null;
    notice = null;
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
    return saveVia(path, payloadFrom(form), () => resetForm(path));
  }

  async function archiveRow(path: string, row: Row) {
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
    return saveVia('class-sections', sectionPayload(), () => resetForm('class-sections'));
  }

  function levelPayload() {
    return {
      ...payloadFrom(levelForm),
      education_stage_id: levelForm.education_stage_id ? Number(levelForm.education_stage_id) : null
    };
  }

  function saveLevel() {
    return saveVia('grade-levels', levelPayload(), () => resetForm('grade-levels'));
  }

  async function createQuickSections() {
    if (!schoolId) return;
    const labels = quickLabels.split(',').map((label) => label.trim()).filter(Boolean);
    if (!labels.length) return;
    saving = true;
    error = null;
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
      class_section_id: Number(groupForm.class_section_id),
      subject_id: Number(groupForm.subject_id)
    };
  }

  function saveGroup() {
    return saveVia('subject-groups', groupPayload(), () => resetForm('subject-groups'));
  }

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
          <CrudBlock title={$_('school.branches.title')} rows={branches} path="branches" bind:form={branchForm} {saving} editing={editingPath === 'branches'} onsubmit={() => saveRow('branches', branchForm)} onedit={(row) => editRow('branches', branchForm, row)} oncancel={cancelEdit} onarchive={archiveRow} />
        {:else if activeTab === 'stages'}
          <CrudBlock title={$_('school.stages.title')} rows={stages} path="education-stages" bind:form={stageForm} {saving} editing={editingPath === 'education-stages'} onsubmit={() => saveRow('education-stages', stageForm)} onedit={(row) => editRow('education-stages', stageForm, row)} oncancel={cancelEdit} onarchive={archiveRow} />
        {:else if activeTab === 'years'}
          <CrudBlock title={$_('school.years.title')} rows={years} path="academic-years" bind:form={yearForm} {saving} editing={editingPath === 'academic-years'} onsubmit={() => saveRow('academic-years', yearForm)} onedit={(row) => editRow('academic-years', yearForm, row)} oncancel={cancelEdit} onarchive={archiveRow} />
        {:else if activeTab === 'levels'}
          <div class="rounded-lg border border-slate-200 bg-white p-5">
            <h2 class="text-lg font-black text-slate-900">{gradeLevelLabel} {$_('school.levels.title')}</h2>
            <div class="mt-4 grid gap-3 md:grid-cols-6">
              <TextInput label={$_('school.code')} bind:value={levelForm.code} />
              <TextInput label={$_('school.nameEn')} bind:value={levelForm.name} />
              <TextInput label={$_('school.nameAr')} bind:value={levelForm.name_ar} />
              <SelectInput label={$_('school.stages.single')} bind:value={levelForm.education_stage_id} rows={stages} optional />
              <NumberInput label={$_('school.sortOrder')} bind:value={levelForm.sort_order} />
              <StatusInput bind:value={levelForm.status} />
            </div>
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
              <SelectInput label={$_('school.branches.single')} bind:value={sectionForm.branch_campus_id} rows={branches} />
              <SelectInput label={$_('school.years.single')} bind:value={sectionForm.academic_year_id} rows={years} />
              <SelectInput label={gradeLevelLabel} bind:value={sectionForm.grade_level_id} rows={levels} />
              <TextInput label={$_('school.sectionLabel')} bind:value={sectionForm.code} />
              <TextInput label={$_('school.nameEn')} bind:value={sectionForm.name} />
              <TextInput label={$_('school.nameAr')} bind:value={sectionForm.name_ar} />
              <NumberInput label={$_('school.sortOrder')} bind:value={sectionForm.sort_order} />
            </div>
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
        {:else if activeTab === 'subjects'}
          <CrudBlock title={$_('school.subjects.title')} rows={subjects} path="subjects" bind:form={subjectForm} {saving} editing={editingPath === 'subjects'} onsubmit={() => saveRow('subjects', subjectForm)} onedit={(row) => editRow('subjects', subjectForm, row)} oncancel={cancelEdit} onarchive={archiveRow} />
        {:else if activeTab === 'groups'}
          <div class="rounded-lg border border-slate-200 bg-white p-5">
            <h2 class="text-lg font-black text-slate-900">{$_('school.groups.title')}</h2>
            <div class="mt-4 grid gap-3 md:grid-cols-7">
              <SelectInput label={$_('school.years.single')} bind:value={groupForm.academic_year_id} rows={years} />
              <SelectInput label={$_('school.sections.single')} bind:value={groupForm.class_section_id} rows={sections} />
              <SelectInput label={$_('school.subjects.single')} bind:value={groupForm.subject_id} rows={subjects} />
              <TextInput label={$_('school.code')} bind:value={groupForm.code} />
              <TextInput label={$_('school.nameEn')} bind:value={groupForm.name} />
              <TextInput label={$_('school.nameAr')} bind:value={groupForm.name_ar} />
              <NumberInput label={$_('school.sortOrder')} bind:value={groupForm.sort_order} />
            </div>
            <div class="mt-4 flex items-center gap-2">
              <button class="btn-hero inline-flex items-center gap-2 rounded-lg" disabled={saving} onclick={saveGroup}>
                {#if editingPath === 'subject-groups'}{$_('school.save')}{:else}<Plus class="h-4 w-4" />{$_('school.add')}{/if}
              </button>
              {#if editingPath === 'subject-groups'}
                <button class="btn-secondary rounded-lg" disabled={saving} onclick={cancelEdit}>{$_('school.cancel')}</button>
              {/if}
            </div>
            <RowsTable rows={groups} extra={(row) => `${yearName(row.academic_year_id)} · ${rowName(sections, row.class_section_id)} · ${subjectName(row.subject_id)}`} onedit={(row) => editRow('subject-groups', groupForm, row)} onarchive={(row) => archiveRow('subject-groups', row)} />
          </div>
        {/if}
      </div>
    </div>
  </section>
{/if}
