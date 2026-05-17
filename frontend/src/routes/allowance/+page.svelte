<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import {
    ArrowLeft,
    BadgeCheck,
    Ban,
    CalendarDays,
    Coins,
    PiggyBank,
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
    created_by_parent_id: number | null;
    updated_by_parent_id: number | null;
    created_at: string | null;
    updated_at: string | null;
  };

  type AllowancePreview = {
    settings: AllowanceSettings;
    period_start: string;
    period_end: string;
    eligible_points: number;
    raw_eligible_points: number;
    point_goal: number;
    progress_ratio: number;
    earned_amount_minor: number;
    max_amount_minor: number;
    currency: string;
    currency_exponent: number;
    display_amount: string;
    display_max_amount: string;
    included_transaction_count: number;
  };

  const CURRENCY_EXPONENTS: Record<string, number> = {
    OMR: 3,
    USD: 2,
    GBP: 2,
    EUR: 2
  };

  const CURRENCIES = Object.keys(CURRENCY_EXPONENTS);

  let children = $state<ChildSummary[]>([]);
  let selectedChildId = $state('');
  let settings = $state<AllowanceSettings | null>(null);
  let preview = $state<AllowancePreview | null>(null);
  let loading = $state(true);
  let childLoading = $state(false);
  let saving = $state(false);
  let error = $state<string | null>(null);
  let formError = $state<string | null>(null);
  let statusMessage = $state<string | null>(null);
  let needsLogin = $state(false);
  let form = $state({
    is_enabled: false,
    currency: 'OMR',
    allowance_amount: '0.000',
    period: 'weekly',
    point_goal: 100
  });

  const selectedChild = $derived(children.find((child) => String(child.child.id) === selectedChildId) || null);
  const activeExponent = $derived(CURRENCY_EXPONENTS[form.currency] ?? settings?.currency_exponent ?? 2);
  const previewProgress = $derived(preview ? Math.round(preview.progress_ratio * 100) : 0);
  const previewBarWidth = $derived(`${Math.max(0, Math.min(100, previewProgress))}%`);
  const amountMinorForExamples = $derived(parseAmountToMinor(form.allowance_amount, activeExponent));
  const exampleRows = $derived(buildExampleRows());

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
    const scale = powerOfTen(exponent);
    const safeMinor = Math.max(0, Math.trunc(minor || 0));
    const whole = Math.floor(safeMinor / scale);
    const fraction = String(safeMinor % scale).padStart(exponent, '0');
    return exponent > 0 ? `${whole}.${fraction} ${currency}` : `${whole} ${currency}`;
  }

  function formatPeriodDate(value: string) {
    return new Date(`${value}T00:00:00`).toLocaleDateString(undefined, {
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
  }

  async function loadAllowanceForChild(childId: string) {
    if (!childId) return;

    try {
      childLoading = true;
      formError = null;
      statusMessage = null;
      const [settingsResponse, previewResponse] = await Promise.all([
        api.get(`/allowance/children/${childId}/settings`),
        api.get(`/allowance/children/${childId}/preview`)
      ]);

      applySettingsToForm(settingsResponse);
      preview = previewResponse;
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Unable to load allowance settings';
      formError = message;
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
      const message = e instanceof Error ? e.message : 'Unable to load allowance setup';
      if (isAuthError(message)) {
        needsLogin = true;
      } else {
        error = message;
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
    if (exponent === undefined) return 'Choose a supported currency.';
    if (!['weekly', 'monthly'].includes(form.period)) return 'Choose weekly or monthly.';
    if (!Number.isInteger(Number(form.point_goal)) || Number(form.point_goal) <= 0) return 'Point goal must be positive.';
    if (parseAmountToMinor(form.allowance_amount, exponent) === null) {
      return `Enter a non-negative amount with up to ${exponent} decimal places for ${form.currency}.`;
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
      statusMessage = nextEnabled ? 'Allowance settings saved.' : 'Allowance disabled for this child.';
    } catch (e) {
      formError = e instanceof Error ? e.message : 'Unable to save allowance settings';
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
  <title>Allowance setup | Family Hero Hub</title>
</svelte:head>

<div class="relative max-w-full overflow-hidden bg-hero-pattern">
  <section class="px-3 py-8 sm:px-4 sm:py-10 lg:py-14">
    <div class="mx-auto max-w-7xl">
      <div class="mb-6">
        <a href="/parent" class="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-xs font-black uppercase tracking-[0.16em] text-slate-500 shadow-sm transition hover:border-hero hover:text-hero">
          <ArrowLeft size={14} />
          Parent dashboard
        </a>
      </div>

      <div class="grid gap-6 lg:grid-cols-[minmax(0,0.92fr)_minmax(0,1.08fr)]">
        <section class="card relative overflow-hidden border-slate-100 bg-slate-950 p-6 text-white shadow-2xl sm:p-8 lg:min-h-[560px]">
          <div class="absolute -right-20 -top-20 h-64 w-64 rounded-full bg-savings/30 blur-3xl"></div>
          <div class="absolute -bottom-24 -left-24 h-72 w-72 rounded-full bg-hero/25 blur-3xl"></div>

          <div class="relative z-10 flex h-full flex-col justify-between gap-10">
            <div>
              <div class="mb-6 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/10 px-4 py-2 text-xs font-black uppercase tracking-[0.18em] text-slate-200">
                <Sparkles size={15} />
                Optional family setup
              </div>
              <h1 class="max-w-xl text-4xl font-black leading-[0.95] tracking-tighter sm:text-5xl lg:text-6xl">
                Allowance setup
              </h1>
              <p class="mt-6 max-w-xl text-base font-medium leading-relaxed text-slate-300 sm:text-lg">
                Connect points to an optional allowance value for each child. Rewards still work separately, and this does not automatically pay money.
              </p>
            </div>

            <div class="grid gap-3 sm:grid-cols-3">
              <div class="rounded-[1.5rem] border border-white/10 bg-white/10 p-4 backdrop-blur">
                <ShieldCheck class="mb-3 text-savings" size={24} />
                <p class="text-xs font-black uppercase tracking-[0.16em] text-slate-400">Separate</p>
                <p class="mt-2 text-sm font-bold leading-snug text-white">Rewards keep their own point costs and approval flow.</p>
              </div>
              <div class="rounded-[1.5rem] border border-white/10 bg-white/10 p-4 backdrop-blur">
                <CalendarDays class="mb-3 text-hero-light" size={24} />
                <p class="text-xs font-black uppercase tracking-[0.16em] text-slate-400">Period based</p>
                <p class="mt-2 text-sm font-bold leading-snug text-white">Preview uses points earned in the current week or month.</p>
              </div>
              <div class="rounded-[1.5rem] border border-white/10 bg-white/10 p-4 backdrop-blur">
                <PiggyBank class="mb-3 text-reward" size={24} />
                <p class="text-xs font-black uppercase tracking-[0.16em] text-slate-400">Estimate</p>
                <p class="mt-2 text-sm font-bold leading-snug text-white">The app shows an allowance estimate; parents stay in control.</p>
              </div>
            </div>
          </div>
        </section>

        <section class="space-y-5">
          {#if loading}
            <div class="card border-slate-100 bg-white p-6 shadow-xl">
              <p class="text-sm font-bold text-slate-500">Loading allowance setup...</p>
            </div>
          {:else if needsLogin}
            <div class="card border-slate-100 bg-white p-6 shadow-xl">
              <h2 class="text-2xl font-black text-slate-950">Parent sign-in needed</h2>
              <p class="mt-2 text-sm font-medium text-slate-600">Sign in as a parent to manage allowance settings.</p>
              <a href="/login" class="btn-hero mt-5 inline-flex items-center justify-center rounded-2xl px-5 py-3 text-sm uppercase tracking-[0.14em]">
                Go to login
              </a>
            </div>
          {:else if error}
            <div class="card border-red-100 bg-red-50 p-6 text-red-700 shadow-xl">
              <p class="font-bold">{error}</p>
            </div>
          {:else if children.length === 0}
            <div class="card border-slate-100 bg-white p-6 shadow-xl">
              <h2 class="text-2xl font-black text-slate-950">No children found</h2>
              <p class="mt-2 text-sm font-medium text-slate-600">Add a child before setting up allowance.</p>
              <a href="/parent" class="btn-secondary mt-5 inline-flex items-center justify-center rounded-2xl px-5 py-3 text-sm uppercase tracking-[0.14em]">
                Back to parent dashboard
              </a>
            </div>
          {:else}
            <div class="card border-slate-100 bg-white p-5 shadow-xl sm:p-6">
              <label for="child-select" class="text-xs font-black uppercase tracking-[0.18em] text-slate-400">Child</label>
              <select
                id="child-select"
                bind:value={selectedChildId}
                onchange={handleChildChange}
                class="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 text-base font-black text-slate-900 outline-none transition focus:border-hero focus:ring-4 focus:ring-hero/10"
              >
                {#each children as child}
                  <option value={String(child.child.id)}>{child.child.display_name}</option>
                {/each}
              </select>
            </div>

            {#if childLoading}
              <div class="card border-slate-100 bg-white p-6 shadow-xl">
                <p class="text-sm font-bold text-slate-500">Loading {selectedChild?.child.display_name || 'child'} settings...</p>
              </div>
            {:else}
              <div class="card border-slate-100 bg-white p-5 shadow-xl sm:p-6">
                <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <p class="text-xs font-black uppercase tracking-[0.18em] text-slate-400">Status</p>
                    <h2 class="mt-2 text-2xl font-black text-slate-950">
                      Allowance is {form.is_enabled ? 'enabled' : 'disabled'} for this child.
                    </h2>
                    <p class="mt-2 text-sm font-medium leading-relaxed text-slate-600">
                      Reward requests, savings transfers, and reward holds do not reduce allowance progress.
                    </p>
                  </div>
                  <div class={`inline-flex w-fit items-center gap-2 rounded-full px-4 py-2 text-xs font-black uppercase tracking-[0.16em] ${form.is_enabled ? 'bg-savings/10 text-savings' : 'bg-slate-100 text-slate-500'}`}>
                    {#if form.is_enabled}
                      <BadgeCheck size={15} />
                      Enabled
                    {:else}
                      <Ban size={15} />
                      Disabled
                    {/if}
                  </div>
                </div>
              </div>

              <div class="card border-slate-100 bg-white p-5 shadow-xl sm:p-6">
                <div class="grid gap-5 sm:grid-cols-2">
                  <label class="flex items-start gap-3 rounded-[1.5rem] border border-slate-200 bg-slate-50 p-4">
                    <input
                      type="checkbox"
                      bind:checked={form.is_enabled}
                      class="mt-1 h-5 w-5 rounded border-slate-300 text-hero focus:ring-hero"
                    />
                    <span>
                      <span class="block text-sm font-black text-slate-900">Enable allowance estimate</span>
                      <span class="mt-1 block text-sm font-medium leading-relaxed text-slate-500">Optional per child. No money is sent by the app.</span>
                    </span>
                  </label>

                  <label>
                    <span class="text-xs font-black uppercase tracking-[0.18em] text-slate-400">Currency</span>
                    <select
                      bind:value={form.currency}
                      class="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 text-base font-black text-slate-900 outline-none transition focus:border-hero focus:ring-4 focus:ring-hero/10"
                    >
                      {#each CURRENCIES as currency}
                        <option value={currency}>{currency}</option>
                      {/each}
                    </select>
                  </label>

                  <label>
                    <span class="text-xs font-black uppercase tracking-[0.18em] text-slate-400">Allowance amount</span>
                    <input
                      bind:value={form.allowance_amount}
                      inputmode="decimal"
                      placeholder={form.currency === 'OMR' ? '10.000' : '10.00'}
                      class="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 text-base font-black text-slate-900 outline-none transition focus:border-hero focus:ring-4 focus:ring-hero/10"
                    />
                    <p class="mt-2 text-xs font-bold text-slate-400">Stored as minor units. Example: 10.000 OMR becomes 10000.</p>
                  </label>

                  <label>
                    <span class="text-xs font-black uppercase tracking-[0.18em] text-slate-400">Allowance period</span>
                    <select
                      bind:value={form.period}
                      class="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 text-base font-black text-slate-900 outline-none transition focus:border-hero focus:ring-4 focus:ring-hero/10"
                    >
                      <option value="weekly">Weekly</option>
                      <option value="monthly">Monthly</option>
                    </select>
                  </label>

                  <label class="sm:col-span-2">
                    <span class="text-xs font-black uppercase tracking-[0.18em] text-slate-400">Point goal</span>
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
                  <div class="mt-5 rounded-2xl border border-red-100 bg-red-50 p-4 text-sm font-bold text-red-700">
                    {formError}
                  </div>
                {/if}

                {#if statusMessage}
                  <div class="mt-5 rounded-2xl border border-savings/20 bg-savings/10 p-4 text-sm font-bold text-savings">
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
                    {saving ? 'Saving...' : 'Save settings'}
                  </button>
                  <button
                    type="button"
                    onclick={disableAllowance}
                    disabled={saving || !form.is_enabled}
                    class="btn-secondary inline-flex flex-1 items-center justify-center gap-2 rounded-2xl px-5 py-4 text-xs font-black uppercase tracking-[0.16em] disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    Disable allowance
                  </button>
                </div>
              </div>

              <div class="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,0.78fr)]">
                <div class="card border-slate-100 bg-white p-5 shadow-xl sm:p-6">
                  <div class="flex items-start justify-between gap-4">
                    <div>
                      <p class="text-xs font-black uppercase tracking-[0.18em] text-slate-400">Preview</p>
                      <h2 class="mt-2 text-2xl font-black text-slate-950">Current period</h2>
                    </div>
                    <div class="rounded-2xl bg-hero/10 p-3 text-hero">
                      <Coins size={22} />
                    </div>
                  </div>

                  {#if preview}
                    <div class="mt-5 rounded-[1.5rem] border border-slate-100 bg-slate-50 p-4">
                      <p class="text-xs font-black uppercase tracking-[0.16em] text-slate-400">Current period</p>
                      <p class="mt-2 text-lg font-black text-slate-950">
                        {formatPeriodDate(preview.period_start)} to {formatPeriodDate(preview.period_end)}
                      </p>
                    </div>

                    <div class="mt-5 grid gap-3 sm:grid-cols-2">
                      <div class="rounded-[1.5rem] bg-slate-50 p-4">
                        <p class="text-xs font-black uppercase tracking-[0.16em] text-slate-400">Eligible points this period</p>
                        <p class="mt-2 text-3xl font-black text-slate-950">{preview.eligible_points}</p>
                      </div>
                      <div class="rounded-[1.5rem] bg-slate-50 p-4">
                        <p class="text-xs font-black uppercase tracking-[0.16em] text-slate-400">Allowance goal</p>
                        <p class="mt-2 text-3xl font-black text-slate-950">{preview.point_goal}</p>
                      </div>
                      <div class="rounded-[1.5rem] bg-slate-50 p-4">
                        <p class="text-xs font-black uppercase tracking-[0.16em] text-slate-400">Estimated allowance earned</p>
                        <p class="mt-2 text-3xl font-black text-slate-950">
                          {formatMinorAmount(preview.earned_amount_minor, preview.currency, preview.currency_exponent)}
                        </p>
                      </div>
                      <div class="rounded-[1.5rem] bg-slate-50 p-4">
                        <p class="text-xs font-black uppercase tracking-[0.16em] text-slate-400">Maximum allowance amount</p>
                        <p class="mt-2 text-3xl font-black text-slate-950">
                          {formatMinorAmount(preview.max_amount_minor, preview.currency, preview.currency_exponent)}
                        </p>
                      </div>
                    </div>

                    <div class="mt-5">
                      <div class="mb-2 flex items-center justify-between text-xs font-black uppercase tracking-[0.16em] text-slate-400">
                        <span>Progress percentage</span>
                        <span>{previewProgress}%</span>
                      </div>
                      <div class="h-4 overflow-hidden rounded-full bg-slate-100">
                        <div class="h-full rounded-full bg-gradient-to-r from-hero to-savings shadow-lg shadow-hero/20" style={`width: ${previewBarWidth}`}></div>
                      </div>
                      <p class="mt-3 text-sm font-medium leading-relaxed text-slate-500">
                        Preview includes awards, calendar task points, adjustments, and penalties. It excludes reward holds, reward approvals or rejections, and savings transfers.
                      </p>
                    </div>
                  {:else}
                    <p class="mt-5 text-sm font-bold text-slate-500">Preview is unavailable until settings load.</p>
                  {/if}
                </div>

                <div class="card border-slate-100 bg-white p-5 shadow-xl sm:p-6">
                  <div class="flex items-start gap-3">
                    <div class="rounded-2xl bg-savings/10 p-3 text-savings">
                      <Star size={22} fill="currentColor" />
                    </div>
                    <div>
                      <p class="text-xs font-black uppercase tracking-[0.18em] text-slate-400">Easy examples</p>
                      <h2 class="mt-2 text-2xl font-black text-slate-950">Points to allowance</h2>
                    </div>
                  </div>

                  <div class="mt-5 space-y-3">
                    {#if exampleRows.length > 0}
                      {#each exampleRows as row}
                        <div class="flex items-center justify-between gap-4 rounded-[1.5rem] border border-slate-100 bg-slate-50 p-4">
                          <span class="text-sm font-black text-slate-950">{row.points} points</span>
                          <span class="text-sm font-black text-savings">{row.amount}</span>
                        </div>
                      {/each}
                    {:else}
                      <p class="text-sm font-bold text-slate-500">Enter an amount and positive point goal to see examples.</p>
                    {/if}
                  </div>

                  <div class="mt-5 rounded-[1.5rem] border border-amber-100 bg-amber-50 p-4 text-sm font-bold leading-relaxed text-amber-800">
                    Allowance is an estimate linked to points. Rewards still work separately, and the app does not automatically pay the child.
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
