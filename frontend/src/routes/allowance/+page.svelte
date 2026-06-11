<script lang="ts">
  import { onMount } from 'svelte';
  import { _, locale } from 'svelte-i18n';
  import { api } from '$lib/api';
  import {
    CURRENCY_EXPONENTS,
    formatAllowanceAmount,
    formatCurrencyLabel,
    searchCurrencies
  } from '$lib/currencies';
  import {
    ArrowLeft,
    BadgeCheck,
    Ban,
    CalendarDays,
    Coins,
    Wallet,
    Save,
    ShieldCheck,
    Sparkles,
    Star
  } from 'lucide-svelte';

  type ChildSummary = {
    child: {
      id: number;
      display_name: string;
      avatar_name: string | null;
    };
    spending_balance?: number;
    savings_balance?: number;
  };

  type AllowanceSettings = {
    id: number | null;
    family_id: number;
    child_id: number;
    is_enabled: boolean;
    currency: string;
    allowance_amount_minor: number;
    currency_exponent: number;
    period: 'weekly' | 'monthly' | string;
    point_goal: number;
    allowance_enabled_at: string | null;
    created_by_parent_id: number | null;
    updated_by_parent_id: number | null;
    created_at: string | null;
    updated_at: string | null;
  };

  type AllowanceSummary = {
    settings: AllowanceSettings;
    period_start: string;
    period_end: string;
    next_reset_at: string;
    allowance_enabled_at: string | null;
    point_value_display: string;
    progress_percent: number;
    maxed_for_period: boolean;
    eligible_points: number;
    raw_eligible_points: number;
    point_goal: number;
    progress_ratio: number;
    earned_amount_minor: number;
    raw_earned_points_period: number;
    earned_points_period: number;
    earned_allowance_minor_period: number;
    spent_points_period: number;
    spent_allowance_minor_period: number;
    pending_points: number;
    pending_allowance_minor: number;
    carried_over_points: number;
    carried_over_allowance_minor: number;
    available_points: number;
    available_allowance_minor: number;
    saved_points: number;
    saved_allowance_minor: number;
    locked_saved_points: number;
    locked_saved_allowance_minor: number;
    max_amount_minor: number;
    currency: string;
    currency_exponent: number;
    display_amount: string;
    display_max_amount: string;
    included_transaction_count: number;
  };

  let children = $state<ChildSummary[]>([]);
  let selectedChildId = $state('');
  let settings = $state<AllowanceSettings | null>(null);
  let preview = $state<AllowanceSummary | null>(null);
  let loading = $state(true);
  let childLoading = $state(false);
  let saving = $state(false);
  let error = $state<string | null>(null);
  let formError = $state<string | null>(null);
  let statusMessage = $state<string | null>(null);
  let needsLogin = $state(false);
  let currencySearch = $state(formatCurrencyLabel('OMR'));
  let showCurrencyOptions = $state(false);
  let form = $state({
    is_enabled: false,
    currency: 'OMR',
    allowance_amount: '0.000',
    period: 'weekly',
    point_goal: 100
  });

  const selectedChild = $derived(children.find((child) => String(child.child.id) === selectedChildId) || null);
  const activeExponent = $derived(CURRENCY_EXPONENTS[form.currency] ?? settings?.currency_exponent ?? 2);
  const previewProgress = $derived(preview ? Math.round(preview.progress_percent) : 0);
  const previewBarWidth = $derived(`${Math.max(0, Math.min(100, previewProgress))}%`);
  const amountMinorForExamples = $derived(parseAmountToMinor(form.allowance_amount, activeExponent));
  const exampleRows = $derived(buildExampleRows());
  const filteredCurrencyOptions = $derived(searchCurrencies(currencySearch));

  const isAuthError = (message: string) =>
    message.toLowerCase().includes('not authenticated') ||
    message.toLowerCase().includes('invalid token') ||
    message.toLowerCase().includes('parent not found');

  function powerOfTen(exponent: number) {
    return 10 ** exponent;
  }

  function minorToInput(minor: number, exponent: number) {
    const scale = powerOfTen(exponent);
    const safeMinor = Math.max(0, Math.trunc(minor || 0));
    const whole = Math.floor(safeMinor / scale);
    const fraction = String(safeMinor % scale).padStart(exponent, '0');
    return exponent > 0 ? `${whole}.${fraction}` : `${whole}`;
  }

  function parseAmountToMinor(value: string, exponent: number) {
    const trimmed = value.trim();
    if (!/^\d+(\.\d*)?$/.test(trimmed)) return null;

    const [wholePart, fractionPart = ''] = trimmed.split('.');
    if (fractionPart.length > exponent) return null;

    const scale = powerOfTen(exponent);
    const whole = Number(wholePart || '0');
    const fraction = Number(fractionPart.padEnd(exponent, '0') || '0');
    const minor = whole * scale + fraction;

    if (!Number.isSafeInteger(minor) || minor < 0) return null;
    return minor;
  }

  function formatMinorAmount(minor: number, currency: string, exponent: number) {
    return formatAllowanceAmount(minor, currency, exponent);
  }

  function formatPointValueDisplay() {
    if (!preview) return '';
    const perPointMinor = Math.floor((preview.settings.allowance_amount_minor || 0) / Math.max(1, preview.settings.point_goal || 1));
    return formatMinorAmount(perPointMinor, preview.currency, preview.currency_exponent);
  }

  function selectCurrency(code: string) {
    form.currency = code;
    currencySearch = formatCurrencyLabel(code);
    showCurrencyOptions = false;
  }

  function handleCurrencySearchInput(event: Event) {
    const value = (event.currentTarget as HTMLInputElement).value;
    currencySearch = value;
    showCurrencyOptions = true;
    const exactCode = value.trim().toUpperCase();
    if (CURRENCY_EXPONENTS[exactCode] !== undefined) {
      form.currency = exactCode;
    }
  }

  function closeCurrencyOptionsSoon() {
    window.setTimeout(() => {
      showCurrencyOptions = false;
      currencySearch = formatCurrencyLabel(form.currency);
    }, 120);
  }

  function formatPeriodDate(value: string) {
    return new Date(`${value}T00:00:00`).toLocaleDateString($locale || 'en', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  }

  function buildExampleRows() {
    const goal = Number(form.point_goal);
    const amountMinor = amountMinorForExamples;
    if (!goal || goal <= 0 || amountMinor === null) return [];

    const points = [goal, Math.round(goal * 0.8), Math.round(goal * 0.5)];
    return points.map((pointValue) => {
      const earnedMinor = Math.floor((amountMinor * Math.min(pointValue, goal)) / goal);
      return {
        points: pointValue,
        amount: formatMinorAmount(earnedMinor, form.currency, activeExponent)
      };
    });
  }

  function applySettingsToForm(nextSettings: AllowanceSettings) {
    settings = nextSettings;
    form = {
      is_enabled: nextSettings.is_enabled,
      currency: nextSettings.currency,
      allowance_amount: minorToInput(nextSettings.allowance_amount_minor, nextSettings.currency_exponent),
      period: nextSettings.period === 'monthly' ? 'monthly' : 'weekly',
      point_goal: nextSettings.point_goal
    };
    currencySearch = formatCurrencyLabel(nextSettings.currency);
  }

  async function loadAllowanceForChild(childId: string) {
    if (!childId) return;

    try {
      childLoading = true;
      formError = null;
      statusMessage = null;
      const [settingsResponse, previewResponse] = await Promise.all([
        api.get(`/allowance/children/${childId}/settings`),
        api.get(`/allowance/children/${childId}/summary`)
      ]);

      applySettingsToForm(settingsResponse);
      preview = previewResponse;
    } catch (e) {
      formError = $_('allowance.errorLoadSettings');
      preview = null;
    } finally {
      childLoading = false;
    }
  }

  async function loadPage() {
    try {
      loading = true;
      error = null;
      needsLogin = false;

      const childResponse = await api.get('/children/');
      children = Array.isArray(childResponse) ? childResponse : [];
      selectedChildId = children.length > 0 ? String(children[0].child.id) : '';

      if (selectedChildId) {
        await loadAllowanceForChild(selectedChildId);
      }
    } catch (e) {
      const message = e instanceof Error ? e['message'] : '';
      if (isAuthError(message)) {
        needsLogin = true;
      } else {
        error = $_('allowance.errorLoadSetup');
      }
    } finally {
      loading = false;
    }
  }

  async function handleChildChange() {
    await loadAllowanceForChild(selectedChildId);
  }

  function validateForm() {
    const exponent = CURRENCY_EXPONENTS[form.currency];
    if (exponent === undefined) return $_('allowance.validationCurrency');
    if (!['weekly', 'monthly'].includes(form.period)) return $_('allowance.validationPeriod');
    if (!Number.isInteger(Number(form.point_goal)) || Number(form.point_goal) <= 0) return $_('allowance.validationPointGoal');
    if (parseAmountToMinor(form.allowance_amount, exponent) === null) {
      return $_('allowance.validationAmount', { values: { exponent, currency: form.currency } });
    }
    return null;
  }

  async function saveSettings(forceEnabled?: boolean) {
    if (!selectedChildId) return;

    const validationMessage = validateForm();
    if (validationMessage) {
      formError = validationMessage;
      statusMessage = null;
      return;
    }

    const exponent = CURRENCY_EXPONENTS[form.currency];
    const allowanceAmountMinor = parseAmountToMinor(form.allowance_amount, exponent);
    if (allowanceAmountMinor === null) return;

    try {
      saving = true;
      formError = null;
      statusMessage = null;
      const nextEnabled = forceEnabled ?? form.is_enabled;
      const response = await api.put(`/allowance/children/${selectedChildId}/settings`, {
        is_enabled: nextEnabled,
        currency: form.currency,
        allowance_amount_minor: allowanceAmountMinor,
        period: form.period,
        point_goal: Number(form.point_goal)
      });

      applySettingsToForm(response);
      await loadAllowanceForChild(selectedChildId);
      statusMessage = nextEnabled ? $_('allowance.saved') : $_('allowance.disabledSaved');
    } catch (e) {
      formError = $_('allowance.errorSaveSettings');
    } finally {
      saving = false;
    }
  }

  async function disableAllowance() {
    form.is_enabled = false;
    await saveSettings(false);
  }

  onMount(loadPage);
</script>

<svelte:head>
  <title>{$_('allowance.title')}</title>
</svelte:head>

<div class="relative max-w-full overflow-hidden bg-hero-pattern">
  <section class="px-3 py-8 sm:px-4 sm:py-10 lg:py-14">
    <div class="mx-auto max-w-7xl">
      <div class="mb-6">
        <a href="/parent" class="inline-flex items-center gap-2 rounded-full border border-hero/15 bg-hero/10 px-4 py-2 text-xs font-black uppercase tracking-[0.16em] text-hero shadow-sm transition hover:border-hero/30 hover:bg-hero/15">
          <ArrowLeft size={14} />
          {$_('allowance.back')}
        </a>
      </div>

      <div class="grid gap-6 lg:grid-cols-[minmax(0,0.92fr)_minmax(0,1.08fr)]">
        <section class="card h-fit overflow-hidden border-slate-200 bg-white p-6 text-slate-950 shadow-xl sm:p-8">
          <div class="space-y-5">
            <div>
              <div class="mb-4 inline-flex items-center gap-2 rounded-full border border-hero/15 bg-hero/10 px-4 py-2 text-xs font-black uppercase tracking-[0.18em] text-hero">
                <Sparkles size={15} />
                {$_('allowance.optional')}
              </div>
              <h1 class="max-w-xl text-4xl font-black leading-[0.95] tracking-tighter sm:text-5xl lg:text-6xl">
                {$_('allowance.heading')}
              </h1>
              <p class="mt-5 max-w-xl text-base font-medium leading-relaxed text-slate-700 sm:text-lg">
                {$_('allowance.intro')}
              </p>
              <p class="mt-4 max-w-xl text-sm font-medium leading-relaxed text-slate-600">
                {$_('allowance.startHelp')}
              </p>
            </div>

            <div class="grid gap-3">
              <div class="flex items-start gap-3 rounded-[1.25rem] border border-slate-200 bg-slate-50 p-4">
                <ShieldCheck class="mt-0.5 shrink-0 text-savings" size={22} />
                <div>
                  <p class="text-sm font-black text-slate-900">{$_('allowance.benefitRewardsTitle')}</p>
                  <p class="mt-1 text-sm font-medium leading-relaxed text-slate-600">{$_('allowance.benefitRewardsText')}</p>
                </div>
              </div>
              <div class="flex items-start gap-3 rounded-[1.25rem] border border-slate-200 bg-slate-50 p-4">
                <CalendarDays class="mt-0.5 shrink-0 text-hero" size={22} />
                <div>
                  <p class="text-sm font-black text-slate-900">{$_('allowance.benefitPeriodTitle')}</p>
                  <p class="mt-1 text-sm font-medium leading-relaxed text-slate-600">{$_('allowance.benefitPeriodText')}</p>
                </div>
              </div>
              <div class="flex items-start gap-3 rounded-[1.25rem] border border-slate-200 bg-slate-50 p-4">
                <Wallet class="mt-0.5 shrink-0 text-reward" size={22} />
                <div>
                  <p class="text-sm font-black text-slate-900">{$_('allowance.benefitParentTitle')}</p>
                  <p class="mt-1 text-sm font-medium leading-relaxed text-slate-600">{$_('allowance.benefitParentText')}</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section class="space-y-5">
          {#if loading}
            <div class="card border-slate-100 bg-white p-6 shadow-xl">
              <div class="flex items-center gap-3">
                <div class="h-11 w-11 animate-spin rounded-full border-4 border-hero border-t-transparent"></div>
                <div>
                  <p class="text-xs font-black uppercase tracking-[0.18em] text-slate-400">{$_('allowance.loadingTitle')}</p>
                  <p class="text-sm font-medium text-slate-600">{$_('allowance.loadingText')}</p>
                </div>
              </div>
            </div>
          {:else if needsLogin}
            <div class="card border-slate-100 bg-white p-6 shadow-xl">
              <h2 class="text-2xl font-black text-slate-950">{$_('allowance.signInTitle')}</h2>
              <p class="mt-2 text-sm font-medium text-slate-600">{$_('allowance.signInText')}</p>
              <a href="/login" class="btn-hero mt-5 inline-flex items-center justify-center rounded-2xl px-5 py-3 text-sm uppercase tracking-[0.14em]">
                {$_('allowance.signInCta')}
              </a>
            </div>
          {:else if error}
            <div class="card border-red-100 bg-red-50 p-6 text-red-700 shadow-xl">
              <p class="font-bold">{error}</p>
            </div>
          {:else if children.length === 0}
            <div class="card border-slate-100 bg-white p-6 shadow-xl">
              <h2 class="text-2xl font-black text-slate-950">{$_('allowance.emptyTitle')}</h2>
              <p class="mt-2 text-sm font-medium leading-relaxed text-slate-600">{$_('allowance.emptyText')}</p>
              <a href="/parent" class="btn-secondary mt-5 inline-flex items-center justify-center rounded-2xl px-5 py-3 text-sm uppercase tracking-[0.14em]">
                {$_('allowance.emptyCta')}
              </a>
            </div>
          {:else}
            <div class="card border-slate-100 bg-white p-5 shadow-xl sm:p-6">
              <p class="text-xs font-black uppercase tracking-[0.18em] text-slate-400">{$_('allowance.stepChooseChild')}</p>
              <p class="mt-2 text-sm font-medium leading-relaxed text-slate-600">{$_('allowance.selectChildHelp')}</p>
              <label for="child-select" class="sr-only">{$_('allowance.child')}</label>
              <select
                id="child-select"
                bind:value={selectedChildId}
                onchange={handleChildChange}
                class="mt-4 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 text-base font-black text-slate-900 outline-none transition focus:border-hero focus:ring-4 focus:ring-hero/10"
              >
                {#each children as child}
                  <option value={String(child.child.id)}>{child.child.display_name}</option>
                {/each}
              </select>
            </div>

            {#if childLoading}
              <div class="card border-slate-100 bg-white p-6 shadow-xl">
                <p class="text-xs font-black uppercase tracking-[0.18em] text-slate-400">{$_('allowance.loadingChildSettings')}</p>
                <p class="mt-2 text-sm font-medium leading-relaxed text-slate-600">{$_('allowance.loadingDetails', { values: { name: selectedChild?.child.display_name || $_('allowance.thisChild') } })}</p>
              </div>
            {:else}
              <div class="card border-slate-100 bg-white p-5 shadow-xl sm:p-6">
                <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <p class="text-xs font-black uppercase tracking-[0.18em] text-slate-400">{$_('allowance.onOff')}</p>
                    <h2 class="mt-2 text-2xl font-black text-slate-950">
                      {$_('allowance.status', { values: { status: form.is_enabled ? $_('allowance.enabled') : $_('allowance.disabled') } })}
                    </h2>
                    <p class="mt-2 text-sm font-medium leading-relaxed text-slate-600">
                      {$_('allowance.reducesAvailableNote')}
                    </p>
                  </div>
                  <div class={`inline-flex w-fit items-center gap-2 rounded-full px-4 py-2 text-xs font-black uppercase tracking-[0.16em] ${form.is_enabled ? 'bg-savings/10 text-savings' : 'bg-slate-100 text-slate-500'}`}>
                    {#if form.is_enabled}
                      <BadgeCheck size={15} />
                      {$_('allowance.enabled')}
                    {:else}
                      <Ban size={15} />
                      {$_('allowance.disabled')}
                    {/if}
                  </div>
                </div>
              </div>

              <div class="card border-slate-100 bg-white p-5 shadow-xl sm:p-6">
                <div class="flex items-start justify-between gap-4">
                  <div>
                    <p class="text-xs font-black uppercase tracking-[0.18em] text-slate-400">{$_('allowance.stepAmountCurrencyGoal')}</p>
                    <h2 class="mt-2 text-2xl font-black text-slate-950">{$_('allowance.setLinked')}</h2>
                    <p class="mt-2 text-sm font-medium leading-relaxed text-slate-600">{$_('allowance.setHelp')}</p>
                  </div>
                </div>

                <div class="mt-5 grid gap-5 sm:grid-cols-2">
                  <label class="flex items-start gap-3 rounded-[1.5rem] border border-slate-200 bg-slate-50 p-4">
                    <input
                      type="checkbox"
                      bind:checked={form.is_enabled}
                      class="mt-1 h-5 w-5 rounded border-slate-300 text-hero focus:ring-hero"
                    />
                    <span>
                      <span class="block text-sm font-black text-slate-900">{$_('allowance.enableLinked')}</span>
                      <span class="mt-1 block text-sm font-medium leading-relaxed text-slate-600">{$_('allowance.optionalPerChildNote')}</span>
                      <span class="mt-2 block text-sm font-bold leading-relaxed text-amber-700">{$_('allowance.enableWarning')}</span>
                    </span>
                  </label>

                  <label class="relative">
                    <span class="text-xs font-black uppercase tracking-[0.18em] text-slate-400">{$_('allowance.currency')}</span>
                      <input
                        value={currencySearch}
                        oninput={handleCurrencySearchInput}
                        onfocus={() => (showCurrencyOptions = true)}
                        onblur={closeCurrencyOptionsSoon}
                        role="combobox"
                        aria-expanded={showCurrencyOptions}
                        aria-controls="currency-options"
                        autocomplete="off"
                        placeholder={$_('allowance.currencySearchPlaceholder')}
                        class="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 text-base font-black text-slate-900 outline-none transition focus:border-hero focus:ring-4 focus:ring-hero/10"
                      />
                      {#if showCurrencyOptions}
                        <div
                          id="currency-options"
                          class="absolute z-20 mt-2 max-h-72 w-full overflow-y-auto rounded-2xl border border-slate-200 bg-white p-2 shadow-xl"
                        >
                          {#if filteredCurrencyOptions.length > 0}
                            {#each filteredCurrencyOptions as currency}
                              <button
                                type="button"
                                class={`flex w-full items-start justify-between gap-3 rounded-xl px-3 py-2 text-left transition hover:bg-hero/10 ${currency.code === form.currency ? 'bg-hero/10 text-hero' : 'text-slate-800'}`}
                                onmousedown={(event) => event.preventDefault()}
                                onclick={() => selectCurrency(currency.code)}
                              >
                                <span class="min-w-0">
                                  <span class="block text-sm font-black">{currency.code} — {currency.symbol} {currency.name}</span>
                                  <span class="block text-xs font-bold text-slate-500">
                                    {currency.exponent} {currency.exponent === 1 ? $_('allowance.decimalSingular') : $_('allowance.decimalPlural')}
                                  </span>
                                </span>
                              </button>
                            {/each}
                          {:else}
                            <p class="px-3 py-2 text-sm font-bold text-slate-500">{$_('allowance.currencySearchEmpty')}</p>
                          {/if}
                        </div>
                      {/if}
                  </label>

                  <label>
                    <span class="text-xs font-black uppercase tracking-[0.18em] text-slate-400">{$_('allowance.amount')}</span>
                    <input
                      bind:value={form.allowance_amount}
                      inputmode="decimal"
                      placeholder={activeExponent === 3 ? '10.000' : activeExponent === 0 ? '10' : '10.00'}
                      class="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 text-base font-black text-slate-900 outline-none transition focus:border-hero focus:ring-4 focus:ring-hero/10"
                    />
                    <p class="mt-2 text-xs font-medium leading-relaxed text-slate-500">{$_('allowance.currencyMinorUnitsNote')}</p>
                  </label>

                  <label>
                    <span class="text-xs font-black uppercase tracking-[0.18em] text-slate-400">{$_('allowance.period')}</span>
                    <select
                      bind:value={form.period}
                      class="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 text-base font-black text-slate-900 outline-none transition focus:border-hero focus:ring-4 focus:ring-hero/10"
                    >
                      <option value="weekly">{$_('allowance.weekly')}</option>
                      <option value="monthly">{$_('allowance.monthly')}</option>
                    </select>
                  </label>

                  <label class="sm:col-span-2">
                    <span class="text-xs font-black uppercase tracking-[0.18em] text-slate-400">{$_('allowance.pointGoalLabel')}</span>
                    <input
                      type="number"
                      min="1"
                      step="1"
                      bind:value={form.point_goal}
                      class="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 text-base font-black text-slate-900 outline-none transition focus:border-hero focus:ring-4 focus:ring-hero/10"
                    />
                  </label>
                </div>

                {#if formError}
                  <div class="mt-5 rounded-2xl border border-red-100 bg-red-50 p-4 text-sm font-bold text-red-700" aria-live="polite">
                    {formError}
                  </div>
                {/if}

                {#if statusMessage}
                  <div class="mt-5 rounded-2xl border border-savings/20 bg-savings/10 p-4 text-sm font-bold text-savings" aria-live="polite">
                    {statusMessage}
                  </div>
                {/if}

                <div class="mt-6 flex flex-col gap-3 sm:flex-row">
                  <button
                    type="button"
                    onclick={() => saveSettings()}
                    disabled={saving}
                    class="btn-hero inline-flex flex-1 items-center justify-center gap-2 rounded-2xl px-5 py-4 text-xs font-black uppercase tracking-[0.16em] disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <Save size={16} />
                    {saving ? $_('common.saving') : $_('allowance.saveSettings')}
                  </button>
                  <button
                    type="button"
                    onclick={disableAllowance}
                    disabled={saving || !form.is_enabled}
                    class="btn-secondary inline-flex flex-1 items-center justify-center gap-2 rounded-2xl px-5 py-4 text-xs font-black uppercase tracking-[0.16em] disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {$_('allowance.disabled')}
                  </button>
                </div>
              </div>

              <div class="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,0.78fr)]">
                <div class="card border-slate-100 bg-white p-5 shadow-xl sm:p-6">
                  <div class="flex items-start justify-between gap-4">
                    <div>
                      <p class="text-xs font-black uppercase tracking-[0.18em] text-slate-400">{$_('allowance.stepCurrentSummary')}</p>
                      <h2 class="mt-2 text-2xl font-black text-slate-950">{$_('allowance.availableBalanceHeading')}</h2>
                    </div>
                    <div class="rounded-2xl bg-hero/10 p-3 text-hero">
                      <Coins size={22} />
                    </div>
                  </div>

                  {#if preview}
                    <div class="mt-5 rounded-[1.5rem] border border-slate-100 bg-slate-50 p-4">
                      <p class="text-xs font-black uppercase tracking-[0.16em] text-slate-400">{$_('allowance.currentPeriodLabel')}</p>
                      <p class="mt-2 text-lg font-black text-slate-950">
                        {formatPeriodDate(preview.period_start)} {$_('allowance.periodRangeSeparator')} {formatPeriodDate(preview.period_end)}
                      </p>
                    </div>

                    <div class="mt-4 rounded-[1.5rem] border border-slate-100 bg-slate-50 p-4">
                      <p class="text-xs font-black uppercase tracking-[0.16em] text-slate-400">{$_('allowance.pointValueLabel')}</p>
                      <p class="mt-2 text-lg font-black text-slate-950">{$_('allowance.onePointEquals', { values: { value: formatPointValueDisplay() } })}</p>
                    </div>

                      {#if preview.allowance_enabled_at}
                        <p class="mt-4 text-sm font-medium leading-relaxed text-slate-600">
                          {$_('allowance.enabledHistoryNote', { values: { date: new Date(preview.allowance_enabled_at).toLocaleString($locale || 'en', {
                            month: 'short',
                            day: 'numeric',
                            hour: 'numeric',
                            minute: '2-digit'
                          }) } })}
                        </p>
                      {/if}

                    <div class="mt-5 grid gap-3 sm:grid-cols-2">
                      <div class="rounded-[1.5rem] bg-slate-50 p-4">
                        <p class="text-xs font-black uppercase tracking-[0.16em] text-slate-400">{$_('allowance.earnedThisPeriod')}</p>
                        <p class="mt-2 text-3xl font-black text-slate-950">{formatMinorAmount(preview.earned_allowance_minor_period, preview.currency, preview.currency_exponent)}</p>
                        <p class="mt-1 text-sm font-medium text-slate-500">{preview.earned_points_period} {$_('allowance.pointsUnit')}</p>
                      </div>
                      <div class="rounded-[1.5rem] bg-slate-50 p-4">
                        <p class="text-xs font-black uppercase tracking-[0.16em] text-slate-400">{$_('allowance.availableToSpend')}</p>
                        <p class="mt-2 text-3xl font-black text-slate-950">{formatMinorAmount(preview.available_allowance_minor, preview.currency, preview.currency_exponent)}</p>
                        <p class="mt-1 text-sm font-medium text-slate-500">{preview.available_points} {$_('allowance.pointsUnit')}</p>
                      </div>
                      <div class="rounded-[1.5rem] bg-slate-50 p-4">
                        <p class="text-xs font-black uppercase tracking-[0.16em] text-slate-400">{$_('allowance.spentThisPeriod')}</p>
                        <p class="mt-2 text-3xl font-black text-slate-950">{formatMinorAmount(preview.spent_allowance_minor_period, preview.currency, preview.currency_exponent)}</p>
                        <p class="mt-1 text-sm font-medium text-slate-500">{preview.spent_points_period} {$_('allowance.pointsUnit')}</p>
                      </div>
                      <div class="rounded-[1.5rem] bg-slate-50 p-4">
                        <p class="text-xs font-black uppercase tracking-[0.16em] text-slate-400">{$_('allowance.carriedOverLabel')}</p>
                        <p class="mt-2 text-3xl font-black text-slate-950">{formatMinorAmount(preview.carried_over_allowance_minor, preview.currency, preview.currency_exponent)}</p>
                        <p class="mt-1 text-sm font-medium text-slate-500">{preview.carried_over_points} {$_('allowance.pointsUnit')}</p>
                      </div>
                    </div>

                    <div class="mt-5 grid gap-3 sm:grid-cols-2">
                      <div class="rounded-[1.5rem] bg-slate-50 p-4">
                        <p class="text-xs font-black uppercase tracking-[0.16em] text-slate-400">{$_('allowance.pointsOnHoldLabel')}</p>
                        <p class="mt-2 text-3xl font-black text-slate-950">{formatMinorAmount(preview.pending_allowance_minor, preview.currency, preview.currency_exponent)}</p>
                        <p class="mt-1 text-sm font-medium text-slate-500">{preview.pending_points} {$_('allowance.pointsUnit')}</p>
                      </div>
                      <div class="rounded-[1.5rem] bg-slate-50 p-4">
                        <p class="text-xs font-black uppercase tracking-[0.16em] text-slate-400">{$_('allowance.savedLabel')}</p>
                        <p class="mt-2 text-3xl font-black text-slate-950">{formatMinorAmount(preview.saved_allowance_minor, preview.currency, preview.currency_exponent)}</p>
                        <p class="mt-1 text-sm font-medium text-slate-500">{preview.saved_points} {$_('allowance.pointsUnit')}</p>
                      </div>
                    </div>

                    <div class="mt-5">
                      <div class="mb-2 flex items-center justify-between text-xs font-black uppercase tracking-[0.16em] text-slate-400">
                        <span>{$_('allowance.progressToGoal')}</span>
                        <span>{previewProgress}%</span>
                      </div>
                      <div class="h-4 overflow-hidden rounded-full bg-slate-100">
                        <div class="h-full rounded-full bg-gradient-to-r from-hero to-savings shadow-lg shadow-hero/20" style={`width: ${previewBarWidth}`}></div>
                      </div>
                      <p class="mt-3 text-sm font-medium leading-relaxed text-slate-600">{$_('allowance.summaryHelp')}</p>
                    </div>
                  {:else}
                    <p class="mt-5 text-sm font-medium leading-relaxed text-slate-600">{$_('allowance.previewPlaceholder')}</p>
                  {/if}
                </div>

                <div class="card border-slate-100 bg-white p-5 shadow-xl sm:p-6">
                  <div class="flex items-start gap-3">
                    <div class="rounded-2xl bg-savings/10 p-3 text-savings">
                      <Star size={22} fill="currentColor" />
                    </div>
                    <div>
                      <p class="text-xs font-black uppercase tracking-[0.18em] text-slate-400">{$_('allowance.quickExamplesHeading')}</p>
                      <h2 class="mt-2 text-2xl font-black text-slate-950">{$_('allowance.pointsToAllowanceHeading')}</h2>
                    </div>
                  </div>

                  <div class="mt-5 space-y-3">
                    {#if exampleRows.length > 0}
                      {#each exampleRows as row}
                        <div class="flex items-center justify-between gap-4 rounded-[1.25rem] border border-slate-100 bg-slate-50 p-4">
                          <span class="text-sm font-black text-slate-950">{row.points} {$_('allowance.pointsUnit')}</span>
                          <span class="text-sm font-black text-savings">{row.amount}</span>
                        </div>
                      {/each}
                    {:else}
                      <p class="text-sm font-medium leading-relaxed text-slate-600">{$_('allowance.examplesHelp')}</p>
                    {/if}
                  </div>

                  <div class="mt-5 rounded-[1.5rem] border border-amber-100 bg-amber-50 p-4 text-sm font-medium leading-relaxed text-amber-900">
                    {$_('allowance.linkedNote')}
                  </div>
                </div>
              </div>
            {/if}
          {/if}
        </section>
      </div>
    </div>
  </section>
</div>
