<script lang="ts">
  import { beforeNavigate } from '$app/navigation';
  import { onDestroy, onMount } from 'svelte';
  import { _, locale } from 'svelte-i18n';
  import { api } from '$lib/api';

  type Membership = { school_id: number; school_name: string; role: string };
  type Year = { id: number; name: string; name_ar?: string | null; status: string; start_date?: string | null };
  type StudentImport = {
    id: number;
    filename?: string | null;
    mode: 'normal' | 'annual';
    academic_year_id?: number | null;
    effective_date?: string | null;
    status: 'staged' | 'committed' | 'discarded' | 'failed';
    summary: Record<string, number>;
    rows?: ImportRow[];
  };
  type ImportRow = { row_number: number; student_id?: string | null; warnings?: string[] };
  type ImportHistoryItem = StudentImport & {
    file_hash?: string | null;
    academic_year?: { id: number; name: string } | null;
    uploaded_by?: { id: number; name?: string | null; email?: string | null } | null;
    committed_by?: { id: number; name?: string | null; email?: string | null } | null;
    created_at?: string | null;
    committed_at?: string | null;
  };
  type ExportHistoryItem = {
    id: number;
    export_type: string;
    import_id?: number | null;
    status: 'downloaded';
    row_count?: number | null;
    created_at?: string | null;
    actor?: { id: number; name?: string | null; email?: string | null } | null;
  };

  const summaryKeys = ['create', 'update', 'move', 'restore', 'reactivate', 'leaver', 'inactive', 'skip', 'conflict', 'error'];
  const reportTypes = ['all', 'conflicts', 'errors', 'committed'] as const;

  let loading = $state(true);
  let allowed = $state(false);
  let schoolId = $state<number | null>(null);
  let schoolName = $state('');
  let years = $state<Year[]>([]);
  let error = $state('');
  let notice = $state('');
  let toast = $state<{ kind: 'error' | 'success'; message: string } | null>(null);
  let toastTimer: ReturnType<typeof setTimeout> | null = null;
  let busy = $state('');

  let importMode = $state<'normal' | 'annual'>('normal');
  let academicYearId = $state('');
  let effectiveDate = $state('');
  let importFile = $state<File | null>(null);
  let stagedImport = $state<StudentImport | null>(null);
  let stagedWarnings = $derived(previewWarnings(stagedImport));

  let imports = $state<ImportHistoryItem[]>([]);
  let importPage = $state(1);
  let importPages = $state(0);
  let importTotal = $state(0);
  let statusFilter = $state('');
  let modeFilter = $state('');
  let dateFrom = $state('');
  let dateTo = $state('');
  let selectedImport = $state<ImportHistoryItem | null>(null);

  let exports = $state<ExportHistoryItem[]>([]);
  let exportPage = $state(1);
  let exportPages = $state(0);
  let exportTotal = $state(0);

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

  function displayWarning(message: string) {
    if (message === 'name_ar contains both Arabic and Latin letters; review that it is the complete Arabic-script student name.') {
      return $_('school.imports.nameArMixedWarning');
    }
    if ($locale !== 'ar') return message;
    const slot = message.match(/(?:guardian|Guardian) ([12])|guardian([12])_/)?.slice(1).find(Boolean) || '';
    if (/name is missing/.test(message)) return $_('school.imports.guardianNameWarning', { values: { slot } });
    if (/relationship must be one of/.test(message)) return $_('school.imports.guardianRelationshipWarning', { values: { slot } });
    if (/saved as a draft contact/.test(message)) return $_('school.imports.guardianDraftWarning', { values: { slot } });
    return $_('school.imports.rowWarning');
  }

  function previewWarnings(item: StudentImport | null) {
    return (item?.rows || [])
      .flatMap((row) => (row.warnings || []).map((message) => ({ row, message })))
      .sort((left, right) => Number(right.message.startsWith('name_ar contains')) - Number(left.message.startsWith('name_ar contains')));
  }

  beforeNavigate(clearToast);
  onDestroy(clearToast);

  function saveDownload(blob: Blob, filename: string) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  }

  function formatDate(value?: string | null) {
    if (!value) return '—';
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString($locale || undefined);
  }

  function actorName(actor?: { name?: string | null; email?: string | null } | null) {
    return actor?.name || actor?.email || '—';
  }

  function rowCount(item: StudentImport) {
    return summaryKeys.reduce((total, key) => total + (item.summary?.[key] || 0), 0);
  }

  function outcomeText(item: StudentImport) {
    return summaryKeys
      .filter((key) => (item.summary?.[key] || 0) > 0)
      .map((key) => `${$_(`school.imports.summary.${key}`)}: ${item.summary[key]}`)
      .join(' · ') || '—';
  }

  async function init() {
    try {
      const me = await api.get('/me/v2');
      const membership = (me?.memberships || []).find((item: Membership) => item.role === 'school_admin');
      if (!membership) return;
      schoolId = membership.school_id;
      schoolName = membership.school_name;
      allowed = true;
      years = await api.get('/school/academic-years', schoolOptions());
      await Promise.all([loadImportHistory(), loadExportHistory()]);
    } catch (err: any) {
      if (err?.status === 401) {
        window.location.href = `/login?returnTo=${encodeURIComponent('/school/students/data')}`;
        return;
      }
      showError(err?.message || $_('school.loadError'));
    } finally {
      loading = false;
    }
  }

  function handleFile(event: Event) {
    importFile = (event.target as HTMLInputElement).files?.[0] || null;
  }

  function handleYear() {
    effectiveDate = years.find((year) => String(year.id) === academicYearId)?.start_date || '';
  }

  async function downloadTemplate() {
    busy = 'template';
    try {
      const blob = await api.download('/school/students/import-template', schoolOptions());
      saveDownload(blob, 'student_import_template.csv');
    } catch (err: any) {
      showError(err?.message || $_('school.imports.templateError'));
    } finally {
      busy = '';
    }
  }

  async function uploadImport() {
    if (!importFile) {
      showError($_('school.studentData.fileRequired'));
      return;
    }
    if (importMode === 'annual' && (!academicYearId || !effectiveDate)) {
      showError($_('school.studentData.annualFieldsRequired'));
      return;
    }
    busy = 'upload';
    try {
      const form = new FormData();
      form.append('file', importFile);
      form.append('mode', importMode);
      if (importMode === 'annual') {
        form.append('academic_year_id', academicYearId);
        form.append('effective_date', effectiveDate);
      }
      stagedImport = await api.upload('/school/students/imports', form, schoolOptions());
      selectedImport = null;
      await loadImportHistory(1);
      showNotice($_('school.studentData.previewReady'));
    } catch (err: any) {
      showError(err?.message || $_('school.imports.uploadError'));
    } finally {
      busy = '';
    }
  }

  async function commitImport() {
    if (!stagedImport) return;
    if (stagedImport.mode === 'annual' && !confirm($_('school.imports.annualCommitConfirm'))) return;
    busy = 'commit';
    try {
      stagedImport = await api.post(`/school/students/imports/${stagedImport.id}/commit`, {}, schoolOptions());
      await loadImportHistory(1);
      showNotice($_('school.imports.committed'));
    } catch (err: any) {
      showError(err?.message || $_('school.imports.commitError'));
    } finally {
      busy = '';
    }
  }

  async function discardImport() {
    if (!stagedImport) return;
    busy = 'discard';
    try {
      await api.post(`/school/students/imports/${stagedImport.id}/discard`, {}, schoolOptions());
      stagedImport = null;
      importFile = null;
      await loadImportHistory(1);
      showNotice($_('school.studentData.discarded'));
    } catch (err: any) {
      showError(err?.message || $_('school.imports.discardError'));
    } finally {
      busy = '';
    }
  }

  async function loadImportHistory(page = 1) {
    if (!schoolId) return;
    const query = new URLSearchParams({ page: String(page), page_size: '10' });
    if (statusFilter) query.set('status', statusFilter);
    if (modeFilter) query.set('mode', modeFilter);
    if (dateFrom) query.set('date_from', dateFrom);
    if (dateTo) query.set('date_to', dateTo);
    const result = await api.get(`/school/students/imports?${query.toString()}`, schoolOptions());
    imports = result.items || [];
    importPage = result.page || page;
    importPages = result.pages || 0;
    importTotal = result.total || 0;
  }

  async function clearFilters() {
    statusFilter = '';
    modeFilter = '';
    dateFrom = '';
    dateTo = '';
    await loadImportHistory(1);
  }

  async function openBatch(item: ImportHistoryItem) {
    try {
      selectedImport = await api.get(`/school/students/imports/${item.id}?page=1&page_size=1`, schoolOptions());
    } catch (err: any) {
      showError(err?.message || $_('school.importHistory.detailError'));
    }
  }

  async function loadExportHistory(page = 1) {
    if (!schoolId) return;
    const result = await api.get(`/school/students/export-history?page=${page}&page_size=10`, schoolOptions());
    exports = result.items || [];
    exportPage = result.page || page;
    exportPages = result.pages || 0;
    exportTotal = result.total || 0;
  }

  async function downloadReport(importId: number, reportType: (typeof reportTypes)[number]) {
    busy = `report-${importId}-${reportType}`;
    try {
      const blob = await api.download(`/school/students/imports/${importId}/reports/${reportType}.csv`, schoolOptions());
      saveDownload(blob, `student-import-${importId}-${reportType}.csv`);
      await loadExportHistory(1);
    } catch (err: any) {
      showError(err?.message || $_('school.importHistory.downloadError'));
    } finally {
      busy = '';
    }
  }

  async function downloadExport(path: string, filename: string) {
    busy = path;
    try {
      const blob = await api.download(path, schoolOptions());
      saveDownload(blob, filename);
      await loadExportHistory(1);
    } catch (err: any) {
      showError(err?.message || $_('school.importHistory.downloadError'));
    } finally {
      busy = '';
    }
  }

  onMount(init);
</script>

<svelte:head>
  <title>{$_('school.studentData.title')}</title>
</svelte:head>

{#if loading}
  <section class="mx-auto max-w-6xl px-4 py-12"><div class="card p-8 text-center">{$_('common.loading')}</div></section>
{:else if !allowed}
  <section class="mx-auto max-w-3xl px-4 py-12"><div class="card p-8 text-center"><h1 class="text-2xl font-black">{$_('school.accessDeniedTitle')}</h1><p class="mt-3 text-slate-600">{error || $_('school.accessDenied')}</p></div></section>
{:else}
  <section class="mx-auto max-w-7xl px-4 py-6 sm:py-8">
    <header class="flex flex-col gap-4 border-b border-slate-200 pb-5 sm:flex-row sm:items-end sm:justify-between">
      <div><a class="text-sm font-bold text-sky-700 hover:underline" href="/school/students"><span class="inline-block rtl:-scale-x-100" aria-hidden="true">←</span> {$_('school.studentAdmin.backToStudents')}</a><p class="eyebrow mt-3">{schoolName}</p><h1 class="mt-2 text-3xl font-black">{$_('school.studentData.title')}</h1><p class="mt-2 max-w-2xl text-slate-600">{$_('school.studentData.intro')}</p></div>
      <a class="btn-secondary rounded-xl px-4 py-3 text-center" href="/school">{$_('school.studentAdmin.backToAdmin')}</a>
    </header>

    {#if error}<div class="mt-5 rounded-xl border border-red-200 bg-red-50 p-4 text-sm font-bold text-red-800" role="alert">{error}</div>{/if}
    {#if notice}<div class="mt-5 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm font-bold text-emerald-800" role="status">{notice}</div>{/if}

    <div class="mt-6 grid gap-6 xl:grid-cols-2">
      <section class="rounded-2xl border border-slate-200 bg-white p-4 sm:p-6">
        <h2 class="text-xl font-black">{$_('school.imports.title')}</h2>
        <p class="mt-1 text-sm text-slate-600">{$_('school.imports.help')}</p>
        <div class="mt-5 grid gap-4 md:grid-cols-2">
          <label class="text-sm font-bold">{$_('school.imports.mode')}<select class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal" bind:value={importMode} disabled={stagedImport?.status === 'staged'}><option value="normal">{$_('school.imports.modeValue.normal')}</option><option value="annual">{$_('school.imports.modeValue.annual')}</option></select></label>
          {#if importMode === 'annual'}
            <label class="text-sm font-bold">{$_('school.imports.destinationYear')} *<select class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal" bind:value={academicYearId} onchange={handleYear} disabled={stagedImport?.status === 'staged'}><option value="">{$_('school.imports.selectYear')}</option>{#each years.filter((year) => year.status !== 'archived') as year}<option value={String(year.id)}>{$locale === 'ar' && year.name_ar ? year.name_ar : year.name}</option>{/each}</select></label>
            <label class="text-sm font-bold">{$_('school.imports.effectiveDate')} *<input type="date" class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal" bind:value={effectiveDate} disabled={stagedImport?.status === 'staged'} /></label>
          {/if}
          <label class="text-sm font-bold md:col-span-2">{$_('school.studentData.csvFile')} *<input type="file" accept=".csv,text/csv" class="mt-1 block w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 font-normal" onchange={handleFile} disabled={stagedImport?.status === 'staged'} /></label>
        </div>
        <p class="mt-3 text-sm text-slate-600">{$_(`school.imports.modeHelp.${importMode}`)}</p>
        <div class="mt-4 flex flex-wrap gap-2"><button type="button" class="btn-secondary rounded-xl px-4 py-2.5" disabled={Boolean(busy)} onclick={downloadTemplate}>{$_('school.imports.downloadTemplate')}</button><button type="button" class="btn-hero rounded-xl px-4 py-2.5" disabled={Boolean(busy) || stagedImport?.status === 'staged'} onclick={uploadImport}>{busy === 'upload' ? $_('school.imports.uploading') : $_('school.imports.upload')}</button></div>

        {#if stagedImport}
          <div class="mt-5 rounded-xl border border-sky-200 bg-sky-50/50 p-4">
            <div class="flex flex-wrap items-start justify-between gap-3"><div><p class="font-black">{stagedImport.filename || `#${stagedImport.id}`}</p><p class="mt-1 text-sm text-slate-600">{$_(`school.imports.modeValue.${stagedImport.mode}`)} · {$_(`school.imports.statusValue.${stagedImport.status}`)}{#if stagedImport.effective_date} · {stagedImport.effective_date}{/if}</p></div><span class="rounded-full bg-white px-3 py-1 text-xs font-black">{rowCount(stagedImport)} {$_('school.studentData.rows')}</span></div>
            <div class="mt-3 flex flex-wrap gap-2">{#each summaryKeys as key}{#if (stagedImport.summary[key] || 0) > 0}<span class="rounded-full bg-white px-2.5 py-1 text-xs font-black">{$_(`school.imports.summary.${key}`)}: {stagedImport.summary[key]}</span>{/if}{/each}</div>
            {#if stagedWarnings.length}
              <div class="mt-4 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-950" role="status">
                <p class="font-black">{$_('school.studentData.previewWarnings')}</p>
                <ul class="mt-2 space-y-1">
                  {#each stagedWarnings.slice(0, 20) as warning}
                    <li>{$_('school.imports.row')} {warning.row.row_number}{#if warning.row.student_id} ({warning.row.student_id}){/if}: {displayWarning(warning.message)}</li>
                  {/each}
                </ul>
                {#if stagedWarnings.length > 20}<p class="mt-2 font-bold">{$_('school.studentData.moreWarnings', { values: { count: stagedWarnings.length - 20 } })}</p>{/if}
              </div>
            {/if}
            <div class="mt-4 flex flex-wrap gap-2">{#each reportTypes as report}<button type="button" class="btn-secondary rounded-lg px-3 py-2 text-sm" disabled={Boolean(busy)} onclick={() => downloadReport(stagedImport!.id, report)}>{$_(`school.importHistory.report.${report}`)}</button>{/each}</div>
            {#if stagedImport.status === 'staged'}<div class="mt-4 flex flex-wrap gap-2"><button type="button" class="btn-hero rounded-xl px-4 py-2.5" disabled={Boolean(busy)} onclick={commitImport}>{busy === 'commit' ? $_('school.imports.committing') : $_('school.imports.commit')}</button><button type="button" class="btn-secondary rounded-xl px-4 py-2.5" disabled={Boolean(busy)} onclick={discardImport}>{$_('school.imports.discard')}</button></div>{/if}
          </div>
        {/if}
      </section>

      <section class="rounded-2xl border border-slate-200 bg-white p-4 sm:p-6">
        <h2 class="text-xl font-black">{$_('school.importHistory.exportsTitle')}</h2>
        <p class="mt-1 text-sm text-slate-600">{$_('school.importHistory.exportsHelp')}</p>
        <div class="mt-5 grid gap-3 sm:grid-cols-2">
          <button type="button" class="btn-secondary rounded-xl px-4 py-3 text-start" disabled={Boolean(busy)} onclick={() => downloadExport('/school/students/exports/active-roster.csv', 'active-student-roster.csv')}>{$_('school.importHistory.exportActive')}</button>
          <button type="button" class="btn-secondary rounded-xl px-4 py-3 text-start" disabled={Boolean(busy)} onclick={() => downloadExport('/school/students/exports/guardian-contacts.csv', 'guardian-contact-roster.csv')}>{$_('school.importHistory.exportGuardians')}</button>
          <button type="button" class="btn-secondary rounded-xl px-4 py-3 text-start" disabled={Boolean(busy)} onclick={() => downloadExport('/school/students/exports/class-enrolments.csv', 'current-class-enrolments.csv')}>{$_('school.importHistory.exportEnrolments')}</button>
          <button type="button" class="btn-secondary rounded-xl px-4 py-3 text-start" disabled={Boolean(busy)} onclick={() => downloadExport('/school/students/exports/annual-update.csv', 'annual-update-student-roster.csv')}>{$_('school.importHistory.exportAnnual')}</button>
        </div>
      </section>
    </div>

    <section class="mt-6 rounded-2xl border border-slate-200 bg-white p-4 sm:p-6">
      <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between"><div><h2 class="text-xl font-black">{$_('school.studentData.importHistory')}</h2><p class="mt-1 text-sm text-slate-600">{$_('school.studentData.importHistoryHelp')}</p></div><span class="text-sm font-bold text-slate-500">{importTotal} {$_('school.importHistory.total')}</span></div>
      <form class="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-6" onsubmit={(event) => { event.preventDefault(); void loadImportHistory(1); }}>
        <label class="text-xs font-bold">{$_('school.imports.status')}<select class="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 font-normal" bind:value={statusFilter}><option value="">{$_('school.importHistory.all')}</option><option value="staged">{$_('school.imports.statusValue.staged')}</option><option value="committed">{$_('school.imports.statusValue.committed')}</option><option value="discarded">{$_('school.imports.statusValue.discarded')}</option><option value="failed">{$_('school.imports.statusValue.failed')}</option></select></label>
        <label class="text-xs font-bold">{$_('school.imports.mode')}<select class="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 font-normal" bind:value={modeFilter}><option value="">{$_('school.importHistory.all')}</option><option value="normal">{$_('school.imports.modeValue.normal')}</option><option value="annual">{$_('school.imports.modeValue.annual')}</option></select></label>
        <label class="text-xs font-bold">{$_('school.importHistory.dateFrom')}<input type="date" class="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 font-normal" bind:value={dateFrom} /></label>
        <label class="text-xs font-bold">{$_('school.importHistory.dateTo')}<input type="date" class="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 font-normal" bind:value={dateTo} /></label>
        <button type="submit" class="btn-hero self-end rounded-lg px-3 py-2">{$_('school.importHistory.applyFilters')}</button><button type="button" class="btn-secondary self-end rounded-lg px-3 py-2" onclick={clearFilters}>{$_('school.importHistory.clearFilters')}</button>
      </form>
      <div class="mt-5 grid gap-3 lg:grid-cols-2">
        {#each imports as item (item.id)}
          <article class="rounded-xl border border-slate-200 p-4"><div class="flex items-start justify-between gap-3"><div><p class="font-black">#{item.id} · {item.filename || '—'}</p><p class="mt-1 text-sm text-slate-600">{$_(`school.imports.modeValue.${item.mode}`)} · {$_(`school.imports.statusValue.${item.status}`)}</p></div><span class="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-black">{rowCount(item)} {$_('school.studentData.rows')}</span></div><dl class="mt-3 grid gap-2 text-sm sm:grid-cols-2"><div><dt class="font-bold text-slate-500">{$_('school.studentData.when')}</dt><dd>{formatDate(item.committed_at || item.created_at)}</dd></div><div><dt class="font-bold text-slate-500">{$_('school.studentData.who')}</dt><dd>{actorName(item.committed_by || item.uploaded_by)}</dd></div></dl><p class="mt-3 text-xs font-semibold text-slate-600">{outcomeText(item)}</p><div class="mt-4 flex flex-wrap gap-2"><button type="button" class="btn-secondary rounded-lg px-3 py-2 text-sm" onclick={() => openBatch(item)}>{$_('school.importHistory.open')}</button>{#each reportTypes as report}<button type="button" class="text-sm font-bold text-sky-700 hover:underline" onclick={() => downloadReport(item.id, report)}>{$_(`school.importHistory.report.${report}`)}</button>{/each}</div></article>
        {:else}
          <p class="rounded-xl bg-slate-50 p-4 text-sm text-slate-600">{$_('school.importHistory.empty')}</p>
        {/each}
      </div>
      {#if importPages > 1}<div class="mt-4 flex items-center justify-between"><button type="button" class="btn-secondary rounded-lg px-3 py-2" disabled={importPage <= 1} onclick={() => loadImportHistory(importPage - 1)}>{$_('school.importHistory.previous')}</button><span class="text-sm font-bold">{importPage} / {importPages}</span><button type="button" class="btn-secondary rounded-lg px-3 py-2" disabled={importPage >= importPages} onclick={() => loadImportHistory(importPage + 1)}>{$_('school.importHistory.next')}</button></div>{/if}
    </section>

    {#if selectedImport}
      <section class="mt-6 rounded-2xl border border-sky-200 bg-sky-50/40 p-4 sm:p-6"><div class="flex items-start justify-between gap-3"><div><h2 class="text-xl font-black">#{selectedImport.id} · {selectedImport.filename || '—'}</h2><p class="mt-1 text-sm text-slate-600">{$_(`school.imports.modeValue.${selectedImport.mode}`)} · {$_(`school.imports.statusValue.${selectedImport.status}`)} · {rowCount(selectedImport)} {$_('school.studentData.rows')}</p></div><button type="button" class="text-sm font-bold text-slate-600" onclick={() => selectedImport = null}>{$_('common.close')}</button></div><p class="mt-4 text-sm font-semibold text-slate-700">{outcomeText(selectedImport)}</p><p class="mt-2 text-sm text-slate-600">{$_('school.studentData.downloadDetailHelp')}</p><div class="mt-4 flex flex-wrap gap-2">{#each reportTypes as report}<button type="button" class="btn-secondary rounded-lg px-3 py-2 text-sm" onclick={() => downloadReport(selectedImport!.id, report)}>{$_(`school.importHistory.report.${report}`)}</button>{/each}</div></section>
    {/if}

    <section class="mt-6 rounded-2xl border border-slate-200 bg-white p-4 sm:p-6">
      <div class="flex items-center justify-between gap-3"><div><h2 class="text-xl font-black">{$_('school.studentData.exportHistory')}</h2><p class="mt-1 text-sm text-slate-600">{$_('school.studentData.exportHistoryHelp')}</p></div><span class="text-sm font-bold text-slate-500">{exportTotal}</span></div>
      <div class="mt-4 grid gap-3 lg:grid-cols-2">{#each exports as item (item.id)}<article class="rounded-xl border border-slate-200 p-4"><div class="flex items-start justify-between gap-3"><p class="font-black">{$_('school.studentData.exportType')}: {item.export_type}</p><span class="rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-black text-emerald-800">{$_('school.studentData.downloaded')}</span></div><dl class="mt-3 grid gap-2 text-sm sm:grid-cols-3"><div><dt class="font-bold text-slate-500">{$_('school.studentData.when')}</dt><dd>{formatDate(item.created_at)}</dd></div><div><dt class="font-bold text-slate-500">{$_('school.studentData.who')}</dt><dd>{actorName(item.actor)}</dd></div><div><dt class="font-bold text-slate-500">{$_('school.studentData.rows')}</dt><dd>{item.row_count ?? '—'}</dd></div></dl></article>{:else}<p class="rounded-xl bg-slate-50 p-4 text-sm text-slate-600">{$_('school.studentData.noExports')}</p>{/each}</div>
      {#if exportPages > 1}<div class="mt-4 flex items-center justify-between"><button type="button" class="btn-secondary rounded-lg px-3 py-2" disabled={exportPage <= 1} onclick={() => loadExportHistory(exportPage - 1)}>{$_('school.importHistory.previous')}</button><span class="text-sm font-bold">{exportPage} / {exportPages}</span><button type="button" class="btn-secondary rounded-lg px-3 py-2" disabled={exportPage >= exportPages} onclick={() => loadExportHistory(exportPage + 1)}>{$_('school.importHistory.next')}</button></div>{/if}
    </section>
  </section>

  {#if toast}<div class={`fixed bottom-4 end-4 z-50 max-w-sm rounded-xl px-4 py-3 text-sm font-bold text-white shadow-xl ${toast.kind === 'error' ? 'bg-red-700' : 'bg-emerald-700'}`} role={toast.kind === 'error' ? 'alert' : 'status'} aria-live={toast.kind === 'error' ? 'assertive' : 'polite'}>{toast.message}</div>{/if}
{/if}
