<script lang="ts">
  import { onMount, tick } from 'svelte';
  import { _, locale } from 'svelte-i18n';
  import { api } from '$lib/api';

  type Membership = { school_id: number; membership_id: number; school_name: string; role: string };
  type Option = { id: number; name?: string; name_ar?: string | null; label?: string; points_value?: number };
  type RecognitionConfig = {
    id: number;
    recognition_type: 'star_of_week';
    name: string;
    scope: { type: 'branch' | 'grade' | 'class'; id: number; name: string; name_ar?: string | null };
    review_period_days: number;
    category_ids: number[];
    categories: { id: number; label: string; points_value: number }[];
    minimum_positive_points: number;
    shortlist_size: number;
    needs_work_safeguard_enabled: boolean;
    maximum_needs_work_events: number;
    needs_work_category_ids: number[];
    needs_work_categories: { id: number; label: string }[];
    certificate_title: string;
    signatory_text: string;
    active: boolean;
    status: 'active' | 'inactive' | 'archived';
    archived_at?: string | null;
    archive_reason?: string | null;
  };
  type Candidate = {
    id: number;
    student_id: number;
    student_name: string;
    student_name_ar?: string | null;
    branch_name: string;
    grade_name: string;
    class_name: string;
    positive_points_total: number;
    positive_event_count: number;
    category_totals: { id: number; label: string; points: number; events: number }[];
    rank: number;
    is_excluded: boolean;
    exclusion_reason?: string | null;
    safeguard_excluded: boolean;
    safeguard_counted_total: number;
    safeguard_category_totals: { id: number; label: string; events: number }[];
    safeguard_overridden: boolean;
    safeguard_override_reason?: string | null;
    is_eligible: boolean;
  };
  type Review = {
    id: number;
    config_id: number;
    period_start: string;
    period_end: string;
    criteria: any;
    status: 'draft' | 'confirmed' | 'revoked' | 'archived';
    selected_student_id?: number | null;
    selected_candidate?: Candidate | null;
    candidates?: Candidate[];
    citation?: string | null;
    generated_at: string;
    confirmed_at?: string | null;
    revoked_at?: string | null;
    revocation_reason?: string | null;
    archived_at?: string | null;
    archive_reason?: string | null;
    was_existing_draft?: boolean;
    school?: { name: string; name_ar?: string | null; logo_url?: string | null };
  };

  const emptyForm = () => ({
    recognition_type: 'star_of_week' as const,
    name: 'Star of the Week',
    scope_type: 'class' as 'branch' | 'grade' | 'class',
    scope_ref_id: '',
    review_period_days: 7,
    category_ids: [] as number[],
    minimum_positive_points: 1,
    shortlist_size: 3,
    needs_work_safeguard_enabled: false,
    maximum_needs_work_events: 0,
    needs_work_category_ids: [] as number[],
    certificate_title: 'Star of the Week',
    signatory_text: 'Head of School',
    active: true
  });

  let membership = $state<Membership | null>(null);
  let options = $state<{ branches: Option[]; grades: Option[]; classes: Option[]; positive_categories: Option[]; needs_work_categories: Option[] }>({ branches: [], grades: [], classes: [], positive_categories: [], needs_work_categories: [] });
  let configs = $state<RecognitionConfig[]>([]);
  let reviews = $state<Review[]>([]);
  let currentReview = $state<Review | null>(null);
  let form = $state(emptyForm());
  let editingConfigId = $state<number | null>(null);
  let reviewConfigId = $state('');
  let periodEnd = $state(new Date().toISOString().slice(0, 10));
  let selectedStudentId = $state('');
  let citation = $state('');
  let excludingCandidateId = $state<number | null>(null);
  let exclusionReason = $state('');
  let overridingCandidateId = $state<number | null>(null);
  let overrideReason = $state('');
  let revocationReason = $state('');
  let loading = $state(true);
  let saving = $state(false);
  let error = $state('');
  let notice = $state('');
  let openingReviewId = $state<number | null>(null);
  let decisionSection = $state<HTMLElement>();
  let showArchivedConfigs = $state(false);
  let showArchivedReviews = $state(false);
  let discardingReviewId = $state<number | null>(null);
  let discardReason = $state('');
  let archivingConfigId = $state<number | null>(null);
  let configArchiveReason = $state('');

  function schoolOptions() {
    return membership ? { headers: { 'X-School-Id': String(membership.school_id), 'X-Membership-Id': String(membership.membership_id) } } : {};
  }

  function scopeOptions() {
    if (form.scope_type === 'branch') return options.branches;
    if (form.scope_type === 'grade') return options.grades;
    return options.classes;
  }

  function optionName(row: Option) {
    return $locale === 'ar' && row.name_ar ? row.name_ar : row.name || row.label || '';
  }

  function statusLabel(status: Review['status']) {
    return $_(`recognitionPage.status.${status}`);
  }

  function toggleCategory(id: number) {
    form.category_ids = form.category_ids.includes(id)
      ? form.category_ids.filter((value) => value !== id)
      : [...form.category_ids, id];
  }

  function toggleNeedsWorkCategory(id: number) {
    form.needs_work_category_ids = form.needs_work_category_ids.includes(id)
      ? form.needs_work_category_ids.filter((value) => value !== id)
      : [...form.needs_work_category_ids, id];
  }

  function configPayload(confirmSimilar = false) {
    return { ...form, scope_ref_id: Number(form.scope_ref_id), confirm_similar_active_configuration: confirmSimilar };
  }

  function payloadForConfig(config: RecognitionConfig, active = config.active) {
    return {
      recognition_type: config.recognition_type,
      name: config.name,
      scope_type: config.scope.type,
      scope_ref_id: config.scope.id,
      review_period_days: config.review_period_days,
      category_ids: config.category_ids,
      minimum_positive_points: config.minimum_positive_points,
      shortlist_size: config.shortlist_size,
      needs_work_safeguard_enabled: config.needs_work_safeguard_enabled,
      maximum_needs_work_events: config.maximum_needs_work_events,
      needs_work_category_ids: config.needs_work_category_ids,
      certificate_title: config.certificate_title,
      signatory_text: config.signatory_text,
      active,
      confirm_similar_active_configuration: false
    };
  }

  function selectedConfig() {
    return configs.find((row) => row.id === Number(reviewConfigId));
  }

  function activeConfigs() {
    return configs.filter((row) => row.status === 'active' && !row.archived_at);
  }

  function visibleConfigs() {
    return configs.filter((row) => showArchivedConfigs || row.status !== 'archived');
  }

  function visibleReviews() {
    return reviews.filter((row) => showArchivedReviews || row.status !== 'archived');
  }

  function configOptionLabel(config: RecognitionConfig) {
    return `${config.name} · ${config.scope.name} · ${config.minimum_positive_points} ${$_('recognitionPage.positivePoints')} · ${config.shortlist_size}`;
  }

  async function reloadConfigs() {
    const loaded = await api.get('/school/recognition/configs?include_archived=true', schoolOptions());
    configs = loaded.configs;
    if (!activeConfigs().some((row) => String(row.id) === reviewConfigId)) reviewConfigId = String(activeConfigs()[0]?.id || '');
  }

  async function reloadReviews() {
    const loaded = await api.get('/school/recognition/reviews?limit=25&include_archived=true', schoolOptions());
    reviews = loaded.reviews;
  }

  async function load() {
    loading = true;
    error = '';
    try {
      const me = await api.get('/me');
      membership = (me.memberships || []).find((row: Membership) => row.role === 'school_admin') || null;
      if (!membership) throw new Error($_('recognitionPage.adminRequired'));
      const [loadedOptions, loadedConfigs, loadedReviews] = await Promise.all([
        api.get('/school/recognition/options', schoolOptions()),
        api.get('/school/recognition/configs?include_archived=true', schoolOptions()),
        api.get('/school/recognition/reviews?limit=25&include_archived=true', schoolOptions())
      ]);
      options = loadedOptions;
      configs = loadedConfigs.configs;
      reviews = loadedReviews.reviews;
      if (!reviewConfigId && activeConfigs().length) reviewConfigId = String(activeConfigs()[0].id);
    } catch (caught: any) {
      error = caught?.message || $_('recognitionPage.loadError');
    } finally {
      loading = false;
    }
  }

  function resetForm() {
    editingConfigId = null;
    form = emptyForm();
  }

  function editConfig(config: RecognitionConfig) {
    editingConfigId = config.id;
    form = {
      recognition_type: config.recognition_type,
      name: config.name,
      scope_type: config.scope.type,
      scope_ref_id: String(config.scope.id),
      review_period_days: config.review_period_days,
      category_ids: [...config.category_ids],
      minimum_positive_points: config.minimum_positive_points,
      shortlist_size: config.shortlist_size,
      needs_work_safeguard_enabled: config.needs_work_safeguard_enabled,
      maximum_needs_work_events: config.maximum_needs_work_events,
      needs_work_category_ids: [...config.needs_work_category_ids],
      certificate_title: config.certificate_title,
      signatory_text: config.signatory_text,
      active: config.active
    };
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  async function saveConfig(event: SubmitEvent) {
    event.preventDefault();
    error = '';
    notice = '';
    if (!form.scope_ref_id || form.category_ids.length === 0) {
      error = $_('recognitionPage.completeConfig');
      return;
    }
    saving = true;
    try {
      let saved;
      if (editingConfigId) {
        saved = await api.put(`/school/recognition/configs/${editingConfigId}`, configPayload(), schoolOptions());
      } else {
        try {
          saved = await api.post('/school/recognition/configs', configPayload(), schoolOptions());
        } catch (caught: any) {
          const isSimilarWarning = caught?.status === 409 && caught?.message?.includes('similarly named');
          const scopeName = scopeOptions().find((row) => row.id === Number(form.scope_ref_id));
          if (!isSimilarWarning || !window.confirm($_('recognitionPage.similarConfigWarning', { values: { name: form.name, scope: scopeName ? optionName(scopeName) : '' } }))) throw caught;
          saved = await api.post('/school/recognition/configs', configPayload(true), schoolOptions());
        }
      }
      configs = [saved, ...configs.filter((row) => row.id !== saved.id)];
      if (!reviewConfigId && saved.active) reviewConfigId = String(saved.id);
      notice = $_('recognitionPage.configSaved');
      resetForm();
    } catch (caught: any) {
      error = caught?.message || $_('recognitionPage.saveError');
    } finally {
      saving = false;
    }
  }

  async function deactivateConfig(config: RecognitionConfig) {
    if (config.status !== 'active' || !window.confirm($_('recognitionPage.confirmDeactivateConfig', { values: { name: config.name } }))) return;
    saving = true;
    error = '';
    try {
      await api.put(`/school/recognition/configs/${config.id}`, payloadForConfig(config, false), schoolOptions());
      await reloadConfigs();
      notice = $_('recognitionPage.configDeactivated');
    } catch (caught: any) {
      error = caught?.message || $_('recognitionPage.saveError');
    } finally {
      saving = false;
    }
  }

  function beginArchiveConfig(config: RecognitionConfig) {
    archivingConfigId = config.id;
    configArchiveReason = '';
  }

  async function archiveConfig(config: RecognitionConfig) {
    if (configArchiveReason.trim().length < 3 || !window.confirm($_('recognitionPage.confirmArchiveConfig', { values: { name: config.name } }))) return;
    saving = true;
    error = '';
    try {
      await api.post(`/school/recognition/configs/${config.id}/archive`, { reason: configArchiveReason }, schoolOptions());
      await reloadConfigs();
      archivingConfigId = null;
      configArchiveReason = '';
      if (editingConfigId === config.id) resetForm();
      notice = $_('recognitionPage.configArchived');
    } catch (caught: any) {
      error = caught?.message || $_('recognitionPage.saveError');
    } finally {
      saving = false;
    }
  }

  async function generateReview() {
    if (!reviewConfigId || !periodEnd) return;
    saving = true;
    error = '';
    notice = '';
    try {
      const review = await api.post('/school/recognition/reviews', { config_id: Number(reviewConfigId), period_end: periodEnd }, schoolOptions());
      reviews = [review, ...reviews.filter((row) => row.id !== review.id)];
      await openReview(review.id, true);
      notice = review.was_existing_draft ? $_('recognitionPage.existingDraftOpened') : $_('recognitionPage.shortlistReady');
    } catch (caught: any) {
      error = caught?.message || $_('recognitionPage.generateError');
    } finally {
      saving = false;
    }
  }

  async function openReview(reviewId: number, forceReload = false) {
    if (openingReviewId !== null) return;
    if (currentReview?.id === reviewId && !forceReload) {
      await focusDecisionSection();
      return;
    }
    openingReviewId = reviewId;
    saving = true;
    error = '';
    try {
      currentReview = await api.get(`/school/recognition/reviews/${reviewId}`, schoolOptions());
      selectedStudentId = currentReview?.selected_student_id ? String(currentReview.selected_student_id) : '';
      citation = currentReview?.citation || '';
      excludingCandidateId = null;
      exclusionReason = '';
      overridingCandidateId = null;
      overrideReason = '';
      revocationReason = '';
      discardingReviewId = null;
      discardReason = '';
      await focusDecisionSection();
    } catch (caught: any) {
      error = caught?.message || $_('recognitionPage.loadError');
    } finally {
      openingReviewId = null;
      saving = false;
    }
  }

  async function beginDiscardReview(review: Review) {
    if (openingReviewId !== null) return;
    await openReview(review.id);
    if (currentReview?.id !== review.id) return;
    discardingReviewId = review.id;
    discardReason = '';
    await focusDecisionSection();
  }

  async function discardReview() {
    if (!currentReview || currentReview.status !== 'draft' || discardReason.trim().length < 3) return;
    if (!window.confirm($_('recognitionPage.confirmDiscardReview'))) return;
    saving = true;
    error = '';
    try {
      await api.post(`/school/recognition/reviews/${currentReview.id}/archive`, { reason: discardReason }, schoolOptions());
      await reloadReviews();
      currentReview = null;
      discardingReviewId = null;
      discardReason = '';
      notice = $_('recognitionPage.reviewDiscarded');
    } catch (caught: any) {
      error = caught?.message || $_('recognitionPage.saveError');
    } finally {
      saving = false;
    }
  }

  async function focusDecisionSection() {
    await tick();
    decisionSection?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    decisionSection?.focus({ preventScroll: true });
  }

  async function excludeCandidate(candidate: Candidate) {
    if (!currentReview || exclusionReason.trim().length < 3) return;
    saving = true;
    error = '';
    try {
      await api.post(`/school/recognition/reviews/${currentReview.id}/candidates/${candidate.id}/exclude`, { reason: exclusionReason }, schoolOptions());
      await openReview(currentReview.id, true);
      notice = $_('recognitionPage.candidateExcluded');
    } catch (caught: any) {
      error = caught?.message || $_('recognitionPage.saveError');
    } finally {
      saving = false;
    }
  }

  async function overrideSafeguard(candidate: Candidate) {
    if (!currentReview || overrideReason.trim().length < 3) return;
    saving = true;
    error = '';
    try {
      await api.post(`/school/recognition/reviews/${currentReview.id}/candidates/${candidate.id}/override-safeguard`, { reason: overrideReason }, schoolOptions());
      await openReview(currentReview.id, true);
      notice = $_('recognitionPage.overrideRecorded');
    } catch (caught: any) {
      error = caught?.message || $_('recognitionPage.saveError');
    } finally {
      saving = false;
    }
  }

  async function confirmReview() {
    if (!currentReview || !selectedStudentId) return;
    saving = true;
    error = '';
    try {
      await api.post(`/school/recognition/reviews/${currentReview.id}/confirm`, { student_id: Number(selectedStudentId), citation: citation || null }, schoolOptions());
      await openReview(currentReview.id, true);
      await reloadReviews();
      notice = $_('recognitionPage.awardConfirmed');
    } catch (caught: any) {
      error = caught?.message || $_('recognitionPage.confirmError');
    } finally {
      saving = false;
    }
  }

  async function revokeReview() {
    if (!currentReview || revocationReason.trim().length < 3) return;
    saving = true;
    error = '';
    try {
      await api.post(`/school/recognition/reviews/${currentReview.id}/revoke`, { reason: revocationReason }, schoolOptions());
      await openReview(currentReview.id, true);
      await reloadReviews();
      notice = $_('recognitionPage.awardRevoked');
    } catch (caught: any) {
      error = caught?.message || $_('recognitionPage.revokeError');
    } finally {
      saving = false;
    }
  }

  function printCertificate() {
    window.print();
  }

  onMount(load);
</script>

<svelte:head><title>{$_('recognitionPage.pageTitle')}</title></svelte:head>

<section class="recognition-page mx-auto max-w-7xl px-4 py-8">
  <div class="no-print">
    <a href="/school/administration" class="text-sm font-bold text-hero">← {$_('recognitionPage.back')}</a>
    <p class="eyebrow mt-4">{$_('recognitionPage.eyebrow')}</p>
    <h1 class="mt-2 text-3xl font-black text-slate-900">{$_('recognitionPage.title')}</h1>
    <p class="mt-2 max-w-3xl text-slate-600">{$_('recognitionPage.intro')}</p>

    {#if error}<div class="mt-5 rounded-xl border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700" role="alert">{error}</div>{/if}
    {#if notice}<div class="mt-5 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm font-semibold text-emerald-800" role="status">{notice}</div>{/if}

    {#if loading}
      <div class="card mt-6 p-6">{$_('common.loading')}…</div>
    {:else if membership}
      <div class="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(20rem,.7fr)]">
        <form class="card p-6" onsubmit={saveConfig}>
          <h2 class="text-xl font-black text-slate-900">{editingConfigId ? $_('recognitionPage.editConfig') : $_('recognitionPage.newConfig')}</h2>
          <p class="mt-2 text-sm text-slate-600">{$_('recognitionPage.positiveOnlyHelp')}</p>
          <div class="mt-5 grid gap-4 sm:grid-cols-2">
            <label class="text-sm font-bold text-slate-700 sm:col-span-2">{$_('recognitionPage.name')}<input class="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" bind:value={form.name} maxlength="160" required /></label>
            <label class="text-sm font-bold text-slate-700">{$_('recognitionPage.scopeType')}
              <select class="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" bind:value={form.scope_type} onchange={() => (form.scope_ref_id = '')}>
                <option value="branch">{$_('recognitionPage.branch')}</option><option value="grade">{$_('recognitionPage.grade')}</option><option value="class">{$_('recognitionPage.class')}</option>
              </select>
            </label>
            <label class="text-sm font-bold text-slate-700">{$_('recognitionPage.scope')}
              <select class="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" bind:value={form.scope_ref_id} required>
                <option value="">{$_('recognitionPage.choose')}</option>
                {#each scopeOptions() as row}<option value={String(row.id)}>{optionName(row)}</option>{/each}
              </select>
            </label>
            <label class="text-sm font-bold text-slate-700">{$_('recognitionPage.reviewDays')}<input type="number" min="1" max="366" class="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" bind:value={form.review_period_days} /></label>
            <label class="text-sm font-bold text-slate-700">{$_('recognitionPage.minimumPoints')}<input type="number" min="1" class="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" bind:value={form.minimum_positive_points} /></label>
            <label class="text-sm font-bold text-slate-700">{$_('recognitionPage.shortlistSize')}<input type="number" min="1" max="50" class="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" bind:value={form.shortlist_size} /></label>
            <label class="text-sm font-bold text-slate-700">{$_('recognitionPage.certificateTitle')}<input class="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" bind:value={form.certificate_title} maxlength="200" required /></label>
            <label class="text-sm font-bold text-slate-700 sm:col-span-2">{$_('recognitionPage.signatory')}<input class="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" bind:value={form.signatory_text} maxlength="200" required /></label>
          </div>
          <fieldset class="mt-5">
            <legend class="text-sm font-black text-slate-800">{$_('recognitionPage.categories')}</legend>
            <div class="mt-2 grid gap-2 sm:grid-cols-2">
              {#each options.positive_categories as category}
                <label class="flex items-center gap-3 rounded-xl border border-emerald-100 bg-emerald-50 px-3 py-2 text-sm font-semibold text-emerald-900">
                  <input type="checkbox" checked={form.category_ids.includes(category.id)} onchange={() => toggleCategory(category.id)} />
                  <span>{category.label} (+{category.points_value})</span>
                </label>
              {/each}
            </div>
          </fieldset>
          <fieldset class="mt-5 rounded-2xl border border-amber-200 bg-amber-50 p-4">
            <legend class="px-1 text-sm font-black text-amber-950">{$_('recognitionPage.needsWorkSafeguard')}</legend>
            <label class="flex items-center gap-3 text-sm font-bold text-amber-950"><input type="checkbox" bind:checked={form.needs_work_safeguard_enabled} />{$_('recognitionPage.enableSafeguard')}</label>
            <p class="mt-2 text-xs leading-5 text-amber-900">{$_('recognitionPage.safeguardHelp')}</p>
            {#if form.needs_work_safeguard_enabled}
              <label class="mt-4 block text-sm font-bold text-amber-950">{$_('recognitionPage.maximumNeedsWork')}<input type="number" min="0" class="mt-1 w-full rounded-xl border border-amber-200 bg-white px-3 py-2" bind:value={form.maximum_needs_work_events} /></label>
              <p class="mt-4 text-sm font-black text-amber-950">{$_('recognitionPage.safeguardCategories')}</p>
              <p class="mt-1 text-xs leading-5 text-amber-900">{$_('recognitionPage.safeguardCategoriesHelp')}</p>
              <div class="mt-2 grid gap-2 sm:grid-cols-2">
                {#each options.needs_work_categories as category}
                  <label class="flex items-center gap-3 rounded-xl border border-amber-200 bg-white px-3 py-2 text-sm font-semibold text-amber-950">
                    <input type="checkbox" checked={form.needs_work_category_ids.includes(category.id)} onchange={() => toggleNeedsWorkCategory(category.id)} />
                    <span>{category.label}</span>
                  </label>
                {/each}
              </div>
            {/if}
          </fieldset>
          <label class="mt-5 flex items-center gap-3 text-sm font-bold text-slate-700"><input type="checkbox" bind:checked={form.active} />{$_('recognitionPage.active')}</label>
          <div class="mt-6 flex flex-wrap gap-3">
            <button class="btn-hero rounded-xl px-5 py-3" type="submit" disabled={saving}>{$_('recognitionPage.saveConfig')}</button>
            {#if editingConfigId}<button class="btn-secondary rounded-xl px-5 py-3" type="button" onclick={resetForm}>{$_('common.cancel')}</button>{/if}
          </div>
        </form>

        <div class="space-y-6">
          <section class="card p-6">
            <h2 class="text-xl font-black text-slate-900">{$_('recognitionPage.generateTitle')}</h2>
            <p class="mt-2 text-sm text-slate-600">{$_('recognitionPage.generateHelp')}</p>
            <label class="mt-4 block text-sm font-bold text-slate-700">{$_('recognitionPage.configuration')}
              <select class="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" bind:value={reviewConfigId}>
                <option value="">{$_('recognitionPage.choose')}</option>
                {#each activeConfigs() as config}<option value={String(config.id)}>{configOptionLabel(config)}</option>{/each}
              </select>
            </label>
            {#if selectedConfig()}
              {@const config = selectedConfig()!}
              <dl class="mt-4 grid grid-cols-2 gap-3 rounded-xl border border-sky-100 bg-sky-50 p-4 text-sm text-sky-950">
                <div><dt class="font-black">{$_('recognitionPage.scope')}</dt><dd>{config.scope.name}</dd></div>
                <div><dt class="font-black">{$_('recognitionPage.reviewDays')}</dt><dd>{config.review_period_days} {$_('recognitionPage.days')}</dd></div>
                <div><dt class="font-black">{$_('recognitionPage.minimumPoints')}</dt><dd>{config.minimum_positive_points}</dd></div>
                <div><dt class="font-black">{$_('recognitionPage.shortlistSize')}</dt><dd>{config.shortlist_size}</dd></div>
                <div class="col-span-2"><dt class="font-black">{$_('recognitionPage.needsWorkSafeguard')}</dt><dd>{config.needs_work_safeguard_enabled ? $_('recognitionPage.safeguardOn') : $_('recognitionPage.safeguardOff')}</dd></div>
              </dl>
            {/if}
            <label class="mt-4 block text-sm font-bold text-slate-700">{$_('recognitionPage.periodEnd')}<input type="date" class="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" bind:value={periodEnd} /></label>
            <button class="btn-hero mt-5 w-full rounded-xl px-5 py-3" type="button" disabled={saving || !reviewConfigId || !periodEnd} onclick={generateReview}>{$_('recognitionPage.generate')}</button>
            <p class="mt-3 text-xs leading-5 text-slate-500">{$_('recognitionPage.noAutomaticWinner')}</p>
          </section>

          <section class="card p-6">
            <h2 class="text-lg font-black text-slate-900">{$_('recognitionPage.configurations')}</h2>
            <button class="mt-3 text-sm font-bold text-hero underline" type="button" aria-expanded={showArchivedConfigs} onclick={() => (showArchivedConfigs = !showArchivedConfigs)}>{showArchivedConfigs ? $_('recognitionPage.hideArchivedConfigs') : $_('recognitionPage.showArchivedConfigs')}</button>
            {#if visibleConfigs().length === 0}<p class="mt-3 text-sm text-slate-500">{$_('recognitionPage.noConfigs')}</p>{/if}
            <div class="mt-3 space-y-3">
              {#each visibleConfigs() as config}
                <article class={`rounded-xl border p-3 ${config.status === 'active' ? 'border-emerald-200 bg-emerald-50/40' : config.status === 'archived' ? 'border-slate-200 bg-slate-100' : 'border-amber-200 bg-amber-50/40'}`}>
                  <div class="flex flex-wrap items-start justify-between gap-2"><div><h3 class="font-black text-slate-900">{config.name}</h3><p class="mt-1 text-sm text-slate-600">{config.scope.name} · {config.review_period_days} {$_('recognitionPage.days')} · {config.minimum_positive_points} {$_('recognitionPage.positivePoints')} · {config.shortlist_size} {$_('recognitionPage.shortlistPlaces')}</p></div><span class="rounded-full bg-white px-2 py-1 text-xs font-bold text-slate-600">{$_(`recognitionPage.configStatus.${config.status}`)}</span></div>
                  <p class="mt-1 text-xs font-semibold text-slate-600">{config.needs_work_safeguard_enabled ? $_('recognitionPage.safeguardEnabledSummary', { values: { count: config.maximum_needs_work_events } }) : $_('recognitionPage.safeguardOff')}</p>
                  {#if config.status === 'archived'}<p class="mt-2 text-xs text-slate-600">{$_('recognitionPage.archiveReason')}: {config.archive_reason}</p>{/if}
                  {#if config.status !== 'archived'}
                    <div class="mt-3 flex flex-wrap gap-2">
                      <button class="btn-secondary rounded-lg px-3 py-2 text-sm" type="button" onclick={() => editConfig(config)}>{$_('recognitionPage.editAction')}</button>
                      {#if config.status === 'active'}<button class="btn-secondary rounded-lg px-3 py-2 text-sm" type="button" onclick={() => deactivateConfig(config)}>{$_('recognitionPage.deactivateAction')}</button>{/if}
                      <button class="rounded-lg border border-slate-300 px-3 py-2 text-sm font-bold text-slate-700" type="button" onclick={() => beginArchiveConfig(config)}>{$_('recognitionPage.archiveAction')}</button>
                    </div>
                    {#if archivingConfigId === config.id}
                      <div class="mt-3 rounded-xl border border-slate-200 bg-white p-3"><label class="block text-sm font-bold text-slate-700">{$_('recognitionPage.configArchiveReason')}<input class="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" bind:value={configArchiveReason} maxlength="500" /></label><div class="mt-2 flex gap-2"><button class="rounded-lg border border-slate-300 px-3 py-2 text-sm font-bold" type="button" disabled={saving || configArchiveReason.trim().length < 3} onclick={() => archiveConfig(config)}>{$_('recognitionPage.archiveAction')}</button><button class="text-sm font-bold underline" type="button" onclick={() => (archivingConfigId = null)}>{$_('common.cancel')}</button></div></div>
                    {/if}
                  {/if}
                </article>
              {/each}
            </div>
          </section>
        </div>
      </div>

      <section class="card mt-6 p-6">
        <h2 class="text-xl font-black text-slate-900">{$_('recognitionPage.recentReviews')}</h2>
        <button class="mt-3 text-sm font-bold text-hero underline" type="button" aria-expanded={showArchivedReviews} onclick={() => (showArchivedReviews = !showArchivedReviews)}>{showArchivedReviews ? $_('recognitionPage.hideArchivedReviews') : $_('recognitionPage.showArchivedReviews')}</button>
        {#if visibleReviews().length === 0}<p class="mt-3 text-sm text-slate-500">{$_('recognitionPage.noReviews')}</p>{/if}
        <div class="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {#each visibleReviews() as review}
            <article class={`review-card rounded-xl border p-4 ${review.status === 'draft' ? 'review-card-draft' : review.status === 'confirmed' ? 'review-card-confirmed' : review.status === 'archived' ? 'review-card-archived' : 'review-card-revoked'} ${currentReview?.id === review.id ? 'review-card-selected' : ''}`}>
              <h3 class="font-black text-slate-900">{review.criteria?.recognition_name}</h3>
              <p class="mt-1 text-sm text-slate-600">{review.criteria?.scope?.name} · {review.period_start} – {review.period_end}</p>
              <p class="mt-1 text-xs text-slate-500">{$_('recognitionPage.minimumPoints')}: {review.criteria?.minimum_positive_points} · {$_('recognitionPage.shortlistSize')}: {review.criteria?.shortlist_size}</p>
              <span class="mt-2 inline-block rounded-full bg-white px-2 py-1 text-xs font-black text-slate-700">{statusLabel(review.status)}</span>
              {#if review.status === 'archived'}<p class="mt-2 text-xs text-slate-600">{$_('recognitionPage.archiveReason')}: {review.archive_reason}</p>{/if}
              <div class="mt-3 flex flex-wrap gap-2">
                <button type="button" class="review-card-action rounded-lg border border-current px-3 py-2 text-sm font-black" aria-pressed={currentReview?.id === review.id} onclick={() => openReview(review.id)}>{$_('recognitionPage.openReview')} <span aria-hidden="true">→</span></button>
                {#if review.status === 'draft'}<button type="button" class="rounded-lg border border-slate-400 px-3 py-2 text-sm font-bold text-slate-700" onclick={() => beginDiscardReview(review)}>{$_('recognitionPage.discardReview')}</button>{/if}
              </div>
            </article>
          {/each}
        </div>
      </section>

      {#if currentReview}
        <section class="card mt-6 p-6 focus:outline-none focus-visible:ring-4 focus-visible:ring-hero/30" bind:this={decisionSection} tabindex="-1" aria-labelledby="recognition-decision-title">
          <div class="flex flex-wrap items-start justify-between gap-3">
            <div><h2 id="recognition-decision-title" class="text-xl font-black text-slate-900">{currentReview.criteria.recognition_name}</h2><p class="mt-1 text-sm text-slate-600">{currentReview.criteria.scope.name} · {currentReview.period_start} – {currentReview.period_end}</p></div>
            <span class="rounded-full bg-slate-100 px-3 py-1 text-xs font-black text-slate-700">{statusLabel(currentReview.status)}</span>
          </div>
          <div class="mt-4 rounded-xl border border-sky-100 bg-sky-50 p-4 text-sm text-sky-950">
            <p class="font-black">{$_('recognitionPage.criteria')}</p>
            <p class="mt-1">{$_('recognitionPage.criteriaSummary', { values: { points: currentReview.criteria.minimum_positive_points, days: currentReview.criteria.review_period_days, count: currentReview.criteria.shortlist_size } })}</p>
            <p class="mt-1">{$_('recognitionPage.tieHelp')}</p>
            {#if currentReview.criteria.needs_work_safeguard?.enabled}<p class="mt-2 font-semibold">{$_('recognitionPage.safeguardCriteria', { values: { count: currentReview.criteria.needs_work_safeguard.maximum_allowed_events, categories: currentReview.criteria.needs_work_safeguard.categories.length ? currentReview.criteria.needs_work_safeguard.categories.map((row: any) => row.label).join(', ') : $_('recognitionPage.allNeedsWorkCategories') } })}</p>{/if}
          </div>
          {#if (currentReview.candidates || []).length === 0}
            <p class="mt-5 text-sm text-slate-500">{$_('recognitionPage.noEligibleCandidates')}</p>
          {:else}
            <div class="mt-5 space-y-4">
              {#each currentReview.candidates || [] as candidate}
                <article class={`rounded-2xl border p-4 ${candidate.is_eligible ? 'border-emerald-200 bg-white' : 'border-slate-300 bg-slate-50'}`}>
                  <div class="flex flex-wrap items-start justify-between gap-3">
                    <div class="flex gap-3">
                      {#if currentReview.status === 'draft'}<input type="radio" name="recipient" value={String(candidate.student_id)} bind:group={selectedStudentId} disabled={!candidate.is_eligible} aria-label={$_('recognitionPage.selectRecipient')} />{/if}
                      <div><h3 class="font-black text-slate-900">{$locale === 'ar' && candidate.student_name_ar ? candidate.student_name_ar : candidate.student_name}</h3><p class="text-sm text-slate-600">{candidate.grade_name} · {candidate.class_name}</p></div>
                    </div>
                    <div class="text-end"><p class="font-black text-emerald-800">{candidate.positive_points_total} {$_('recognitionPage.positivePoints')}</p><p class="text-xs text-slate-500">{candidate.positive_event_count} {$_('recognitionPage.positiveEvents')} · {$_('recognitionPage.rank')} {candidate.rank}</p></div>
                  </div>
                  <div class="mt-3 flex flex-wrap gap-2">{#each candidate.category_totals as total}<span class="rounded-full bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-800">{total.label}: {total.points} / {total.events}</span>{/each}</div>
                  {#if candidate.safeguard_excluded}
                    <div class={`mt-3 rounded-xl border p-3 text-sm ${candidate.safeguard_overridden ? 'border-sky-200 bg-sky-50 text-sky-950' : 'border-slate-300 bg-white text-slate-700'}`}>
                      <p class="font-black">{candidate.safeguard_overridden ? $_('recognitionPage.eligibilityOverridden') : $_('recognitionPage.notEligible')}</p>
                      <p class="mt-1">{$_('recognitionPage.countedNeedsWork', { values: { count: candidate.safeguard_counted_total } })}</p>
                      <div class="mt-2 flex flex-wrap gap-2">{#each candidate.safeguard_category_totals as total}<span class="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-700">{total.label}: {total.events}</span>{/each}</div>
                      {#if candidate.safeguard_overridden}<p class="mt-2 font-semibold">{$_('recognitionPage.overrideReasonRecorded')}: {candidate.safeguard_override_reason}</p>
                      {:else if currentReview.status === 'draft' && overridingCandidateId === candidate.id}
                        <div class="mt-3 flex flex-col gap-2 sm:flex-row"><input class="flex-1 rounded-xl border border-slate-300 px-3 py-2 text-sm" bind:value={overrideReason} maxlength="500" placeholder={$_('recognitionPage.overrideReason')} /><button class="btn-secondary rounded-xl px-4 py-2" disabled={saving || overrideReason.trim().length < 3} onclick={() => overrideSafeguard(candidate)}>{$_('recognitionPage.recordOverride')}</button></div>
                      {:else if currentReview.status === 'draft'}<button class="mt-3 text-sm font-bold underline" type="button" onclick={() => { overridingCandidateId = candidate.id; overrideReason = ''; }}>{$_('recognitionPage.overrideSafeguard')}</button>{/if}
                    </div>
                  {/if}
                  {#if candidate.is_excluded}<p class="mt-3 text-sm font-semibold text-slate-600">{$_('recognitionPage.excluded')}: {candidate.exclusion_reason}</p>
                  {:else if currentReview.status === 'draft' && excludingCandidateId === candidate.id}
                    <div class="mt-3 flex flex-col gap-2 sm:flex-row"><input class="flex-1 rounded-xl border border-slate-300 px-3 py-2 text-sm" bind:value={exclusionReason} maxlength="500" placeholder={$_('recognitionPage.exclusionReason')} /><button class="btn-secondary rounded-xl px-4 py-2" disabled={saving || exclusionReason.trim().length < 3} onclick={() => excludeCandidate(candidate)}>{$_('recognitionPage.recordExclusion')}</button></div>
                  {:else if currentReview.status === 'draft' && candidate.is_eligible}<button class="mt-3 text-sm font-bold text-slate-600 underline" type="button" onclick={() => { excludingCandidateId = candidate.id; exclusionReason = ''; }}>{$_('recognitionPage.exclude')}</button>{/if}
                </article>
              {/each}
            </div>
          {/if}
          {#if currentReview.status === 'draft'}
            <div class="mt-6 rounded-2xl border border-amber-200 bg-amber-50 p-4">
              <label class="block text-sm font-black text-amber-950">{$_('recognitionPage.citation')}<textarea class="mt-2 min-h-24 w-full rounded-xl border border-amber-200 bg-white px-3 py-2" bind:value={citation} maxlength="500"></textarea></label>
              <button class="btn-hero mt-3 rounded-xl px-5 py-3" type="button" disabled={saving || !selectedStudentId} onclick={confirmReview}>{$_('recognitionPage.confirm')}</button>
              <p class="mt-2 text-xs text-amber-900">{$_('recognitionPage.confirmHelp')}</p>
            </div>
            <div class="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-4">
              {#if discardingReviewId === currentReview.id}
                <label class="block text-sm font-black text-slate-800">{$_('recognitionPage.discardReason')}<textarea class="mt-2 min-h-20 w-full rounded-xl border border-slate-300 bg-white px-3 py-2" bind:value={discardReason} maxlength="500"></textarea></label>
                <div class="mt-3 flex flex-wrap gap-2"><button class="rounded-xl border border-slate-400 px-4 py-2 font-bold text-slate-800" type="button" disabled={saving || discardReason.trim().length < 3} onclick={discardReview}>{$_('recognitionPage.discardReview')}</button><button class="text-sm font-bold underline" type="button" onclick={() => (discardingReviewId = null)}>{$_('common.cancel')}</button></div>
              {:else}
                <button class="rounded-xl border border-slate-400 px-4 py-2 font-bold text-slate-800" type="button" onclick={() => { discardingReviewId = currentReview!.id; discardReason = ''; }}>{$_('recognitionPage.discardReview')}</button>
              {/if}
            </div>
          {:else if currentReview.status === 'confirmed'}
            <div class="mt-6 rounded-2xl border border-red-100 bg-red-50 p-4"><p class="text-sm font-black text-red-900">{$_('recognitionPage.correctAward')}</p><div class="mt-2 flex flex-col gap-2 sm:flex-row"><input class="flex-1 rounded-xl border border-red-200 bg-white px-3 py-2" bind:value={revocationReason} maxlength="500" placeholder={$_('recognitionPage.revocationReason')} /><button class="rounded-xl border border-red-300 px-4 py-2 font-bold text-red-800" disabled={saving || revocationReason.trim().length < 3} onclick={revokeReview}>{$_('recognitionPage.revoke')}</button></div></div>
          {:else if currentReview.status === 'revoked'}<p class="mt-5 text-sm font-semibold text-red-700">{$_('recognitionPage.revokedReason')}: {currentReview.revocation_reason}</p>
          {:else}<p class="mt-5 text-sm font-semibold text-slate-600">{$_('recognitionPage.archiveReason')}: {currentReview.archive_reason}</p>{/if}
        </section>
      {/if}
    {/if}
  </div>

  {#if currentReview?.status === 'confirmed' && currentReview.selected_candidate}
    <section class="certificate mt-8 bg-white p-10 text-center">
      {#if currentReview.school?.logo_url}<img class="mx-auto mb-5 h-24 w-24 object-contain" src={currentReview.school.logo_url} alt="" />{/if}
      <p class="text-lg font-bold text-slate-700">{$locale === 'ar' && currentReview.school?.name_ar ? currentReview.school.name_ar : currentReview.school?.name}</p>
      <p class="mt-8 text-sm font-black uppercase tracking-[.3em] text-amber-700">{$_('recognitionPage.certificateOfRecognition')}</p>
      <h2 class="mt-5 text-4xl font-black text-slate-900">{currentReview.criteria.certificate_title}</h2>
      <p class="mt-8 text-lg text-slate-600">{$_('recognitionPage.presentedTo')}</p>
      <p class="mt-3 text-4xl font-black text-hero">{$locale === 'ar' && currentReview.selected_candidate.student_name_ar ? currentReview.selected_candidate.student_name_ar : currentReview.selected_candidate.student_name}</p>
      <p class="mt-3 text-base text-slate-600">{currentReview.selected_candidate.grade_name} · {currentReview.selected_candidate.class_name}</p>
      {#if currentReview.citation}<p class="mx-auto mt-8 max-w-2xl text-lg italic leading-8 text-slate-700">“{currentReview.citation}”</p>{/if}
      <p class="mt-8 text-sm font-semibold text-slate-600">{$_('recognitionPage.awardPeriod')}: {currentReview.period_start} – {currentReview.period_end}</p>
      <div class="mx-auto mt-12 w-64 border-t border-slate-400 pt-3 text-sm font-bold text-slate-700">{currentReview.criteria.signatory_text}</div>
    </section>
    <div class="no-print mt-4 text-center"><button class="btn-hero rounded-xl px-6 py-3" type="button" onclick={printCertificate}>{$_('recognitionPage.printCertificate')}</button><p class="mt-2 text-xs text-slate-500">{$_('recognitionPage.notPublished')}</p></div>
  {/if}
</section>

<style>
  .review-card { transition: border-color 150ms ease, box-shadow 150ms ease, transform 150ms ease; }
  .review-card:hover { box-shadow: 0 8px 24px rgb(15 23 42 / .1); transform: translateY(-1px); }
  .review-card button { cursor: pointer; }
  .review-card button:hover { background: rgb(255 255 255 / .7); }
  .review-card button:focus-visible { outline: 3px solid rgb(124 58 237 / .35); outline-offset: 3px; }
  .review-card-draft { border-color: #fbbf24; background: #fffbeb; }
  .review-card-confirmed { border-color: #a7f3d0; background: #f0fdf4; }
  .review-card-revoked { border-color: #cbd5e1; background: #f8fafc; }
  .review-card-archived { border-color: #cbd5e1; background: #f1f5f9; opacity: .86; }
  .review-card-selected { border-color: var(--hero-color); box-shadow: 0 0 0 3px rgb(124 58 237 / .18); }
  .review-card-action { color: var(--hero-color); }
  .certificate { border: 12px double #d4a72c; min-height: 720px; display: flex; flex-direction: column; justify-content: center; }
  @media print {
    :global(header), :global(footer), .no-print { display: none !important; }
    :global(body) { background: white !important; }
    .recognition-page { max-width: none; padding: 0; }
    .certificate { margin: 0; min-height: 96vh; break-inside: avoid; box-shadow: none; }
    @page { size: A4 landscape; margin: 12mm; }
  }
</style>
