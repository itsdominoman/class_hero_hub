<script lang="ts">
  import { onMount } from "svelte";
  import { _, locale } from 'svelte-i18n';
  import { page } from "$app/state";
  import { api } from "$lib/api";
  import { formatAllowanceAmount } from "$lib/currencies";
  import {
    ArrowRight,
    BadgeCheck,
    Clock3,
    Check,
    Gift,
    History,
    PiggyBank,
    Repeat2,
    Sparkles,
    Star,
    Trophy,
    X,
  } from "lucide-svelte";

  type PetStage = "egg" | "hatchling" | "cub" | "hero" | "beast";

  type ChildSummary = {
    child: {
      id: number;
      display_name: string;
      avatar_name: string | null;
    };
    spending_balance: number;
    savings_balance: number;
    locked_savings: number;
    available_savings: number;
    available_spending: number;
    pending_redemptions: number;
    pet_progress: {
      current_stage: PetStage;
      lifetime_points: number;
    };
    savings_unlock_schedule: SavingsUnlockScheduleItem[];
  };

  type SavingsUnlockScheduleItem = {
    unlock_date: string;
    points: number;
    principal_points: number;
    bonus_points: number;
  };

  type LedgerTransaction = {
    jar: string;
    transaction_type: string;
    points: number;
    description: string;
    created_at: string;
    locked_until: string | null;
  };

  type RedemptionRequest = {
    id: number;
    child_id: number;
    points: number;
    title: string;
    description: string;
    status: "pending" | "approved" | "rejected";
    parent_note: string | null;
    created_at: string;
    reviewed_at: string | null;
  };

  type Reward = {
    id: number;
    title: string;
    description: string | null;
    icon: string | null;
    points: number;
    is_active: boolean;
  };

  type AllowanceSummary = {
    settings: {
      is_enabled: boolean;
      currency: string;
      currency_exponent: number;
      period: "weekly" | "monthly" | string;
      point_goal: number;
      allowance_amount_minor: number;
      allowance_enabled_at: string | null;
    };
    allowance_enabled_at: string | null;
    point_value_display: string;
    period_start: string;
    period_end: string;
    next_reset_at: string;
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
    progress_percent: number;
    maxed_for_period: boolean;
    currency: string;
    currency_exponent: number;
  };

  type ErrorKind =
    | "not-linked"
    | "link-expired"
    | "wrong-child"
    | "not-found"
    | "server-error";

  type DayCalendarOccurrence = {
    entry: {
      id: number;
      title: string;
      description: string | null;
      entry_type: "task" | "event" | string;
      is_rewardable: boolean;
      points_value: number | null;
      recurrence_type: "none" | "daily" | "weekly" | string;
      recurrence_days: string | null;
      start_time: string | null;
    };
    occurrence_date: string;
    completion: {
      id: number;
      status: "pending" | "approved" | "rejected" | string;
      points_awarded: number | null;
    } | null;
  };

  type SchoolItem = {
    id: number;
    family_id: number;
    child_id: number;
    weekday: number;
    class_name: string;
    needed_item: string | null;
    sort_order: number;
    is_active: boolean;
    created_by_parent_id: number;
    created_at: string;
    updated_at: string | null;
  };

  let childId = $derived(page.params.id);
  let childIdNumber = $derived(Number(childId));

  let summary = $state(null as ChildSummary | null);
  let ledger = $state([] as LedgerTransaction[]);
  let redemptions = $state([] as RedemptionRequest[]);
  let rewards = $state([] as Reward[]);
  let allowanceSummary = $state<AllowanceSummary | null>(null);
  let accessMode = $state<"parent" | "child">("parent");
  let loading = $state(true);
  let error = $state(null as string | null);
  let errorKind = $state(null as ErrorKind | null);
  let linkedChildName = $state("");
  let submitting = $state(false);
  let submittingRewardId = $state<number | null>(null);
  let dayLoading = $state(false);
  let dayError = $state<string | null>(null);
  let dayItems = $state<DayCalendarOccurrence[]>([]);
  let schoolTodayItems = $state<SchoolItem[]>([]);
  let schoolTomorrowItems = $state<SchoolItem[]>([]);
  let schoolTodayError = $state<string | null>(null);
  let schoolTomorrowError = $state<string | null>(null);
  let daySubmittingId = $state<number | null>(null);
  let statusMessage = $state("");
  let statusTone = $state<"success" | "error" | "info">("success");
  let customRewardTitle = $state("");
  let customRewardPoints = $state(1);
  let showUnlockSchedule = $state(false);
  let showSavingsBankModal = $state(false);
  let savingsBankPoints = $state(1);

  const SAVINGS_LOCK_DAYS = 30;

  const PET_STAGES: Record<PetStage, { label: string; image: string }> = {
    egg: { label: "child.petStageEgg", image: "/pets/dragon-1/egg.png" },
    hatchling: {
      label: "child.petStageHatchling",
      image: "/pets/dragon-1/hatchling.png",
    },
    cub: {
      label: "child.petStageCub",
      image: "/pets/dragon-1/young-dragon.png",
    },
    hero: {
      label: "child.petStageHero",
      image: "/pets/dragon-1/hero-dragon.png",
    },
    beast: {
      label: "child.petStageBeast",
      image: "/pets/dragon-1/legendary-dragon.png",
    },
  };

  const ACTIVITY_LABELS: Record<string, string> = {
    award: "child.activityEarned",
    penalty: "child.activityLost",
    adjustment: "child.activityAdjusted",
    savings_deposit: "child.activitySaved",
    savings_withdrawal: "child.activityUnsaved",
    savings_maturity: "child.activityUnlocked",
    savings_bonus: "child.activitySavingsBonus",
    redemption_hold: "child.activityRewardRequested",
    redemption_rejected: "child.activityRequestReturned",
    redemption_approved: "child.activityRewardApproved",
  };

  const ACTIVITY_TONES: Record<string, string> = {
    award: "gain",
    penalty: "loss",
    adjustment: "adjustment",
    savings_deposit: "savings",
    savings_withdrawal: "savings",
    savings_maturity: "savings",
    savings_bonus: "gain",
    redemption_hold: "hold",
    redemption_rejected: "release",
    redemption_approved: "approved",
  };

  const rewardOptions = $derived(
    rewards
      .filter((reward) => reward.is_active && reward.points > 0)
      .sort((a, b) => a.points - b.points),
  );

  const pendingRequests = $derived(
    redemptions
      .filter(
        (request) =>
          request.child_id === childIdNumber && request.status === "pending",
      )
      .sort(
        (a, b) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
      ),
  );

  const recentActivity = $derived(ledger.slice(0, 8));

  const savingsUnlockSchedule = $derived(
    summary?.savings_unlock_schedule ?? [],
  );

  const nextSavingsUnlock = $derived(
    savingsUnlockSchedule.length > 0 ? savingsUnlockSchedule[0] : null,
  );

  const avatarLabel = $derived(summary?.child.avatar_name?.trim() || "");
  const stageImage = $derived(
    summary
      ? PET_STAGES[summary.pet_progress.current_stage].image
      : PET_STAGES.egg.image,
  );
  const stageInfo = $derived(
    summary ? PET_STAGES[summary.pet_progress.current_stage] : PET_STAGES.egg,
  );
  const allowanceActive = $derived(
    allowanceSummary?.settings?.is_enabled ? allowanceSummary : null,
  );
  const progressToNextStage = $derived(
    summary
      ? (() => {
          const thresholds: Record<PetStage, number> = {
            egg: 0,
            hatchling: 50,
            cub: 150,
            hero: 300,
            beast: 600,
          };
          const order: PetStage[] = [
            "egg",
            "hatchling",
            "cub",
            "hero",
            "beast",
          ];
          const index = order.indexOf(summary.pet_progress.current_stage);
          const nextStage = index < order.length - 1 ? order[index + 1] : null;
          if (!nextStage) return 100;
          return Math.min(
            100,
            Math.round(
              (summary.pet_progress.lifetime_points / thresholds[nextStage]) *
                100,
            ),
          );
        })()
      : 0,
  );

  function setStatus(
    message: string,
    tone: "success" | "error" | "info" = "success",
  ) {
    statusMessage = message;
    statusTone = tone;
  }

  function formatPoints(points: number) {
    return `${points > 0 ? "+" : ""}${points}`;
  }

  function formatDate(value: string) {
    return new Date(value).toLocaleDateString($locale || "en", {
      month: "short",
      day: "numeric",
    });
  }

  function formatUnlockDate(value: string) {
    const [year, month, day] = value.split("-").map(Number);
    const date = new Date(year, month - 1, day);
    return date.toLocaleDateString($locale || "en", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  }

  function unlockDayLabel(value: string) {
    const [year, month, day] = value.split("-").map(Number);
    const unlockDate = new Date(year, month - 1, day);
    unlockDate.setHours(0, 0, 0, 0);

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const tomorrow = new Date(today);
    tomorrow.setDate(today.getDate() + 1);

    if (unlockDate.getTime() === today.getTime()) return $_('common.today');
    if (unlockDate.getTime() === tomorrow.getTime()) return $_('common.tomorrow');
    return $_('child.unlockOn', { values: { date: formatUnlockDate(value) } });
  }

  function unlockScheduleDateLabel(value: string) {
    return unlockDayLabel(value);
  }

  function calculateSavingsBonus(points: number) {
    if (points <= 0) return 0;
    const rawBonusUnits = points * 1000;
    const wholePoints = Math.floor(rawBonusUnits / 10000);
    const remainder = rawBonusUnits % 10000;
    return wholePoints + (remainder >= 6000 ? 1 : 0);
  }

  function getBankUnlockDateValue(reference = new Date()) {
    const unlockDate = new Date(reference);
    unlockDate.setDate(unlockDate.getDate() + SAVINGS_LOCK_DAYS);
    return getLocalDateValue(unlockDate);
  }

  function savingsBankAmount() {
    return Math.max(0, Math.trunc(Number(savingsBankPoints) || 0));
  }

  function savingsBankBonus() {
    return calculateSavingsBonus(savingsBankAmount());
  }

  function savingsBankTotal() {
    return savingsBankAmount() + savingsBankBonus();
  }

  function savingsBankUnlockLabel() {
    return unlockDayLabel(getBankUnlockDateValue());
  }

  function openSavingsBankModal() {
    if (!summary || summary.available_spending <= 0) return;
    savingsBankPoints = Math.min(
      Math.max(1, summary.available_spending),
      summary.available_spending,
    );
    showSavingsBankModal = true;
  }

  function closeSavingsBankModal() {
    showSavingsBankModal = false;
  }

  function nextUnlockText() {
    if (!summary || summary.savings_balance <= 0)
      return $_('child.noSavedPoints');
    if (!nextSavingsUnlock) return $_('child.noSavedPointsLocked');
    return $_('child.nextUnlock', {
      values: {
        points: nextSavingsUnlock.points,
        date: unlockDayLabel(nextSavingsUnlock.unlock_date),
      },
    });
  }

  function formatDateTime(value: string) {
    return new Date(value).toLocaleString($locale || "en", {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  function formatMinorAmount(
    minor: number,
    currency: string,
    exponent: number,
  ) {
    return formatAllowanceAmount(minor, currency, exponent);
  }

  function getLocalDateValue(reference = new Date()) {
    const year = reference.getFullYear();
    const month = `${reference.getMonth() + 1}`.padStart(2, "0");
    const day = `${reference.getDate()}`.padStart(2, "0");
    return `${year}-${month}-${day}`;
  }

  function formatCalendarTime(value: string | null) {
    if (!value) return $_('calendar.allDay');
    const [hours, minutes] = value.slice(0, 5).split(":").map(Number);
    const date = new Date();
    date.setHours(hours, minutes, 0, 0);
    return date.toLocaleTimeString($locale || "en", {
      hour: "numeric",
      minute: "2-digit",
    });
  }

  function recurrenceLabel(item: DayCalendarOccurrence) {
    if (item.entry.recurrence_type === "daily")
      return $_('calendar.repeatsDaily');
    if (item.entry.recurrence_type === "weekly")
      return $_('calendar.repeatsWeekly');
    return $_('calendar.oneTime');
  }

  function statusLabel(status: string) {
    if (status === "pending") return $_('calendar.pendingApproval');
    if (status === "approved") return $_('calendar.completed');
    if (status === "rejected") return $_('calendar.rejected');
    return status;
  }

  function statusClass(status: string) {
    if (status === "pending")
      return "bg-amber-100 text-amber-700 border-amber-200";
    if (status === "approved")
      return "bg-savings/10 text-savings border-savings/20";
    if (status === "rejected")
      return "bg-rose-100 text-rose-700 border-rose-200";
    return "bg-slate-100 text-slate-500 border-slate-200";
  }

  function typeClass(type: string) {
    return type === "event"
      ? "bg-sky-100 text-sky-700 border-sky-200"
      : "bg-emerald-100 text-emerald-700 border-emerald-200";
  }

  function recurrenceClass(item: DayCalendarOccurrence) {
    if (item.entry.recurrence_type === "weekly")
      return "bg-indigo-100 text-indigo-700 border-indigo-200";
    if (item.entry.recurrence_type === "daily")
      return "bg-slate-100 text-slate-600 border-slate-200";
    return "bg-slate-100 text-slate-500 border-slate-200";
  }

  function cleanCalendarDescription(item: DayCalendarOccurrence) {
    return item.entry.description || "";
  }

  function schoolNeedLabel(item: SchoolItem) {
    const listedItem = item.needed_item?.trim();
    if (listedItem) return listedItem;
    if (/p\.?\s*e\.?/i.test(item.class_name))
      return $_('child.gymClothesFallback');
    return $_('child.classBookFallback', {
      values: { className: item.class_name },
    });
  }

  function getJarLabel(jar: string) {
    const normalized = jar.trim().toLowerCase();
    if (normalized === "spending") return $_('child.spendingJar');
    if (normalized === "savings") return $_('child.savingsJar');
    return `${jar} ${$_('child.jarSuffix')}`;
  }

  function schoolItemsToday() {
    return schoolTodayItems;
  }

  function schoolItemsTomorrow() {
    return schoolTomorrowItems;
  }

  function tasksToday() {
    return dayItems.filter((item) => item.entry.entry_type === "task");
  }

  function eventsToday() {
    return dayItems.filter((item) => item.entry.entry_type === "event");
  }

  async function loadMyDay() {
    const today = getLocalDateValue();
    const query = `from_date=${today}&to_date=${today}`;
    dayLoading = true;
    dayError = null;
    schoolTodayError = null;
    schoolTomorrowError = null;
    const [calendarResult, schoolTodayResult, schoolTomorrowResult] =
      await Promise.allSettled([
        accessMode === "child"
          ? api.get(`/child/calendar?${query}`)
          : api.get(`/calendar?child_id=${childIdNumber}&${query}`),
        accessMode === "child"
          ? api.get("/child/school-items/today?offset=0")
          : api.get(`/school-items/today?child_id=${childIdNumber}&offset=0`),
        accessMode === "child"
          ? api.get("/child/school-items/today?offset=1")
          : api.get(`/school-items/today?child_id=${childIdNumber}&offset=1`),
      ]);

    if (calendarResult.status === "fulfilled") {
      dayItems = Array.isArray(calendarResult.value)
        ? calendarResult.value
        : [];
    } else {
      dayItems = [];
      dayError =
        calendarResult.reason instanceof Error
          ? calendarResult.reason.message
          : $_('child.unableToLoadTodaySchedule');
    }

    if (schoolTodayResult.status === "fulfilled") {
      schoolTodayItems = Array.isArray(schoolTodayResult.value)
        ? schoolTodayResult.value
        : [];
    } else {
      schoolTodayItems = [];
      schoolTodayError =
        schoolTodayResult.reason instanceof Error
          ? schoolTodayResult.reason.message
          : $_('calendar.unableToLoadSchoolItems');
    }

    if (schoolTomorrowResult.status === "fulfilled") {
      schoolTomorrowItems = Array.isArray(schoolTomorrowResult.value)
        ? schoolTomorrowResult.value
        : [];
    } else {
      schoolTomorrowItems = [];
      schoolTomorrowError =
        schoolTomorrowResult.reason instanceof Error
          ? schoolTomorrowResult.reason.message
          : $_('calendar.unableToLoadSchoolItems');
    }

    dayLoading = false;
  }

  async function refreshMyDay() {
    await loadMyDay();
  }

  async function completeTodayItem(item: DayCalendarOccurrence) {
    if (item.entry.entry_type !== "task") return;

    try {
      daySubmittingId = item.entry.id;
      const today = getLocalDateValue();
      await api.post(
        `/child/calendar/${item.entry.id}/complete?occurrence_date=${today}`,
        {},
      );
      await refreshMyDay();
    } catch (e) {
      dayError = $_('child.unableToMarkTaskDone');
    } finally {
      daySubmittingId = null;
    }
  }

  function getActivityTone(tx: LedgerTransaction) {
    if (tx.transaction_type === "award") return "gain";
    if (tx.transaction_type === "penalty") return "loss";
    if (tx.transaction_type === "adjustment")
      return tx.points >= 0 ? "gain" : "loss";
    return ACTIVITY_TONES[tx.transaction_type] ?? "neutral";
  }

  function getActivityLabel(tx: LedgerTransaction) {
    if (tx.transaction_type === "adjustment") {
      return tx.points >= 0
        ? $_('child.activityAdjustedUp')
        : $_('child.activityAdjustedDown');
    }
    return $_(ACTIVITY_LABELS[tx.transaction_type] ?? 'child.activityFallback');
  }

  function getActivityBadgeClass(tx: LedgerTransaction) {
    const tone = getActivityTone(tx);
    if (tone === "gain") return "bg-savings/10 text-savings border-savings/20";
    if (tone === "loss") return "bg-penalty/10 text-penalty border-penalty/20";
    if (tone === "savings") return "bg-hero/10 text-hero border-hero/20";
    if (tone === "hold") return "bg-reward/10 text-reward border-reward/20";
    if (tone === "release")
      return "bg-slate-100 text-slate-500 border-slate-200";
    if (tone === "approved") return "bg-slate-900 text-white border-slate-900";
    return "bg-slate-100 text-slate-500 border-slate-200";
  }

  function rewardShortfall(points: number) {
    if (!summary) return 0;
    return Math.max(0, points - summary.available_spending);
  }

  function rewardValueMinor(points: number) {
    if (!allowanceActive) return null;
    return Math.floor(
      (Math.max(0, points) * allowanceActive.settings.allowance_amount_minor) /
        allowanceActive.settings.point_goal,
    );
  }

  const isAuthError = (message: string) =>
    message.toLowerCase().includes("not authenticated") ||
    message.toLowerCase().includes("invalid token") ||
    message.toLowerCase().includes("child session") ||
    message.toLowerCase().includes("invalid child session") ||
    message.toLowerCase().includes("child session missing");

  const isExpiredChildLinkError = (message: string) =>
    message.toLowerCase().includes("child session expired") ||
    message.toLowerCase().includes("invalid child session");

  const isNotFoundError = (message: string) =>
    message.toLowerCase().includes("not found");

  function displayErrorMessage() {
    if (error?.toLowerCase().includes("child session missing")) {
      return $_('child.sessionMissing');
    }

    if (errorKind === "server-error") {
      return $_('child.failedLoad');
    }

    return error || $_('child.failedLoad');
  }

  async function loadData() {
    try {
      loading = true;
      error = null;
      errorKind = null;
      linkedChildName = "";

      try {
        const childSummary = await api.get("/child/me");
        accessMode = "child";

        if (Number(childId) !== childSummary.child.id) {
          linkedChildName = childSummary.child.display_name;
          errorKind = "wrong-child";
          error = $_('child.wrongChild', {
            values: { name: childSummary.child.display_name },
          });
          summary = null;
          ledger = [];
          redemptions = [];
          rewards = [];
          allowanceSummary = null;
          return;
        }

        const [activity, childRedemptions, childRewards] = await Promise.all([
          api.get("/child/ledger?period=month"),
          api.get("/child/redemptions"),
          api.get("/child/rewards"),
        ]);
        const childAllowance = await api
          .get("/child/allowance")
          .catch(() => null);

        summary = childSummary;
        ledger = activity;
        redemptions = childRedemptions;
        rewards = childRewards;
        allowanceSummary = childAllowance;
        await loadMyDay();
      } catch (childError) {
        if (
          !(childError instanceof Error) ||
          !isAuthError(childError.message)
        ) {
          throw childError;
        }

        accessMode = "parent";
        const childAuthMessage = childError.message;
        try {
          const [childSummary, activity, allRedemptions, allRewards] =
            await Promise.all([
              api.get(`/children/${childId}`),
              api.get(`/children/${childId}/ledger?period=month`),
              api.get("/redemptions"),
              api.get("/rewards"),
            ]);
          const parentAllowance = await api
            .get(`/allowance/children/${childId}/summary`)
            .catch(() => null);

          summary = childSummary;
          ledger = activity;
          redemptions = allRedemptions;
          rewards = allRewards;
          allowanceSummary = parentAllowance;
          await loadMyDay();
        } catch (parentError) {
          const message = parentError instanceof Error
            ? parentError.message
            : $_('child.failedLoad');
          if (isAuthError(message)) {
            if (isExpiredChildLinkError(childAuthMessage)) {
              errorKind = "link-expired";
              error = $_('child.linkExpired');
            } else {
              errorKind = "not-linked";
              error = $_('child.deviceNotLinked');
            }
          } else if (isNotFoundError(message)) {
            errorKind = "not-found";
            error = $_('child.notFound');
          } else {
            errorKind = "server-error";
            error = $_('child.failedLoad');
          }
          summary = null;
          ledger = [];
          redemptions = [];
          rewards = [];
          allowanceSummary = null;
        }
      }
    } catch (e) {
      errorKind = "server-error";
      error = $_('child.failedLoad');
      summary = null;
      ledger = [];
      redemptions = [];
      rewards = [];
      allowanceSummary = null;
    } finally {
      loading = false;
    }
  }

  async function requestReward(
    title: string,
    points: number,
    description: string,
  ) {
    if (!summary || points < 1) return;
    if (points > summary.available_spending) {
      setStatus($_('child.rewardRequestTooExpensive'), "error");
      return;
    }

    try {
      submitting = true;
      const requestPath =
        accessMode === "child"
          ? "/child/redemptions"
          : `/children/${childId}/redemptions`;
      await api.post(requestPath, {
        title,
        points,
        description,
      });
      customRewardTitle = "";
      customRewardPoints = 1;
      setStatus($_('child.rewardRequestSent'), "success");
      await loadData();
    } catch (e) {
      setStatus(
        $_('child.rewardRequestFailed'),
        "error",
      );
    } finally {
      submitting = false;
    }
  }

  async function requestPresetReward(reward: Reward) {
    if (!summary) return;
    try {
      submittingRewardId = reward.id;
      await requestReward(
        reward.title,
        reward.points,
        reward.description?.trim() || $_('child.requestedFromDashboard'),
      );
    } finally {
      submittingRewardId = null;
    }
  }

  async function submitCustomRequest(e: SubmitEvent) {
    e.preventDefault();
    await requestReward(
      customRewardTitle.trim(),
      customRewardPoints,
      $_('child.requestedFromDashboard'),
    );
  }

  async function submitSavingsBank(e: SubmitEvent) {
    e.preventDefault();
    if (!summary) return;

    const points = Math.min(savingsBankAmount(), summary.available_spending);
    if (points < 1) {
      setStatus($_('child.bankMinimumOnePoint'), "error");
      return;
    }

    try {
      submitting = true;
      const requestPath =
        accessMode === "child"
          ? "/child/savings/deposit"
          : `/children/${childId}/savings/deposit`;
      await api.post(requestPath, {
        points,
        description: $_('child.bankingDescription'),
      });
      showSavingsBankModal = false;
      savingsBankPoints = Math.min(points, summary.available_spending);
      setStatus($_('child.bankSuccess', {
        values: {
          points,
          total: points + calculateSavingsBonus(points),
        },
      }), "success");
      await loadData();
    } catch (e) {
      setStatus(
        $_('child.bankFailed'),
        "error",
      );
    } finally {
      submitting = false;
    }
  }

  onMount(loadData);
</script>

<div
  class="min-h-dvh max-w-full bg-[#fffaf4] pb-[calc(4rem+var(--safe-bottom))] overflow-x-hidden"
>
  {#if loading}
    <div class="flex justify-center py-40">
      <div class="flex flex-col items-center gap-4">
        <div
          class="animate-spin w-14 h-14 border-4 border-hero border-t-transparent rounded-full"
        ></div>
        <p class="text-xs font-black uppercase tracking-[0.3em] text-slate-400">
          {$_('child.loading')}
        </p>
      </div>
    </div>
  {:else if error}
    <div class="max-w-xl mx-auto px-4 py-24">
      <div
        class="card bg-white p-8 md:p-10 text-center border border-red-100 shadow-xl"
      >
        <div
          class="w-16 h-16 rounded-2xl bg-red-100 text-red-600 flex items-center justify-center mx-auto mb-6"
        >
          <History size={30} />
        </div>
        <h1 class="text-2xl md:text-3xl font-black text-slate-900 mb-2">
          {errorKind === "not-linked"
            ? $_('child.deviceNotLinked')
            : errorKind === "link-expired"
              ? $_('child.linkExpired')
              : errorKind === "wrong-child"
                ? $_('child.wrongChild', { values: { name: linkedChildName || $_('common.unknownChild') } })
                : errorKind === "not-found"
                  ? $_('child.notFound')
                  : $_('child.unavailable')}
        </h1>
        <p class="text-slate-600 mb-6 break-words">{displayErrorMessage()}</p>
        {#if errorKind === "wrong-child"}
          <a
            href="/parent"
            class="btn-secondary inline-flex w-full items-center justify-center px-6 py-4 rounded-2xl mb-3"
          >
            {$_('child.backParent')}
          </a>
        {/if}
        <button
          type="button"
          class="btn-hero px-6 py-4 rounded-2xl"
          onclick={loadData}>{$_('common.tryAgain')}</button
        >
      </div>
    </div>
  {:else if summary}
    <section
      class="border-b border-[#f0e4d7] bg-[linear-gradient(180deg,#fffaf4_0%,#ffffff_100%)]"
    >
      <div class="max-w-7xl mx-auto px-3 sm:px-4 py-8 md:py-12">
        <div
          class="grid gap-8 lg:grid-cols-[minmax(0,1.3fr)_minmax(320px,0.7fr)] items-center"
        >
          <div class="space-y-6">
            {#if accessMode === "parent"}
              <a
                href="/parent"
                class="inline-flex items-center gap-2 rounded-full border border-hero/15 bg-hero/10 px-4 py-2 text-[10px] font-black uppercase tracking-[0.14em] text-hero transition hover:border-hero/30 hover:bg-hero/15 sm:tracking-[0.18em]"
              >
                <ArrowRight class="rotate-180" size={14} />
                {$_('child.backParent')}
              </a>
            {/if}
            <div
              class="inline-flex max-w-full items-center gap-2 px-4 py-2 rounded-full bg-hero/10 text-hero border border-hero/20 text-xs font-black uppercase tracking-[0.14em] sm:tracking-[0.22em]"
            >
              <Sparkles size={14} />
              {$_('child.kidDashboard')}
            </div>

            <div class="flex flex-col sm:flex-row sm:items-center gap-5">
              <div
                class="w-24 h-24 md:w-28 md:h-28 rounded-[2rem] bg-white border-4 border-white shadow-[0_16px_40px_-18px_rgba(0,0,0,0.35)] flex items-center justify-center text-slate-900 overflow-hidden"
              >
                <div
                  class="w-full h-full bg-gradient-to-br from-[#ffe7cb] via-[#fff] to-[#dff7ee] flex flex-col items-center justify-center text-slate-900 p-4"
                >
                  <img
                    src={stageImage}
                    alt={$_(stageInfo.label)}
                    class="w-full h-full object-contain"
                  />
                </div>
              </div>

              <div class="min-w-0">
                <h1
                  class="text-3xl sm:text-4xl md:text-6xl font-black text-slate-950 tracking-tight break-words"
                >
                  {summary.child.display_name}
                </h1>
                <p class="text-slate-600 font-medium mt-2 max-w-2xl">
                  {$_('child.heroIntro')}
                </p>
                <div class="mt-4 flex flex-wrap gap-3">
                  <span
                    class="inline-flex max-w-full items-center gap-2 px-3 py-2 rounded-full bg-slate-900 text-white text-xs font-black uppercase tracking-[0.14em] sm:tracking-[0.2em]"
                  >
                    <BadgeCheck size={14} />
                    <span class="min-w-0 break-words"
                      >{$_('child.stage', { values: { label: $_(stageInfo.label) } })}</span
                    >
                  </span>
                  <span
                    class="inline-flex max-w-full items-center gap-2 px-3 py-2 rounded-full bg-white text-slate-700 border border-slate-200 text-xs font-black uppercase tracking-[0.14em] sm:tracking-[0.2em]"
                  >
                    {accessMode === "child"
                      ? $_('child.childSession')
                      : $_('child.parentPreview')}
                  </span>
                  {#if avatarLabel}
                    <span
                      class="inline-flex max-w-full items-center gap-2 px-3 py-2 rounded-full bg-white text-slate-700 border border-slate-200 text-xs font-black uppercase tracking-[0.14em] sm:tracking-[0.2em]"
                    >
                      <span class="min-w-0 break-words"
                        >{$_('child.avatar', { values: { label: avatarLabel } })}</span
                      >
                    </span>
                  {/if}
                </div>
              </div>
            </div>

            {#if statusMessage}
              <div
                class={`rounded-2xl px-4 py-3 text-sm font-bold border ${statusTone === "success" ? "bg-savings/10 text-savings border-savings/20" : statusTone === "error" ? "bg-red-50 text-red-700 border-red-100" : "bg-slate-100 text-slate-700 border-slate-200"}`}
              >
                {statusMessage}
              </div>
            {/if}
          </div>

          <div
            class="card bg-white p-6 md:p-8 shadow-xl border border-slate-100"
          >
            <div class="flex items-center justify-between mb-5">
              <div>
                <p
                  class="text-[10px] font-black uppercase tracking-[0.25em] text-slate-400"
                >
                  {$_('child.availablePoints')}
                </p>
                <p class="text-4xl md:text-5xl font-black text-slate-950 mt-1">
                  {summary.spending_balance}
                </p>
                {#if allowanceActive}
                  <p class="mt-2 text-sm font-bold text-slate-600">
                    {$_('child.worth', { values: { value: formatMinorAmount(
                      allowanceActive.available_allowance_minor,
                      allowanceActive.currency,
                      allowanceActive.currency_exponent,
                    ) } })}
                  </p>
                {/if}
              </div>
              <div
                class="w-14 h-14 rounded-2xl bg-hero/10 text-hero flex items-center justify-center"
              >
                <Star size={28} fill="currentColor" />
              </div>
            </div>

            <div class="space-y-4">
              <div>
                <div
                  class="flex items-center justify-between text-xs font-black uppercase tracking-[0.22em] text-slate-400 mb-2"
                >
                  <span>{$_('child.nextDragon')}</span>
                  <span>{$_('child.earned', { values: { points: summary.pet_progress.lifetime_points } })}</span>
                </div>
                <div class="h-4 rounded-full bg-slate-100 overflow-hidden">
                  <div
                    class="h-full rounded-full bg-gradient-to-r from-hero to-[#ff8d59]"
                    style={`width: ${progressToNextStage}%`}
                  ></div>
                </div>
              </div>

              <div class="grid grid-cols-2 gap-3">
                <div
                  class="rounded-2xl bg-[#fff8e9] border border-[#f4e3b2] p-4"
                >
                  <p
                    class="text-[10px] font-black uppercase tracking-[0.22em] text-[#b98612]"
                  >
                    {$_('child.savedPoints')}
                  </p>
                  <p class="text-2xl font-black text-slate-950 mt-1">
                    {summary.savings_balance}
                  </p>
                  {#if allowanceActive}
                    <p class="mt-1 text-xs font-bold text-slate-500">
                      {formatMinorAmount(
                        allowanceActive.saved_allowance_minor,
                        allowanceActive.currency,
                        allowanceActive.currency_exponent,
                      )}
                    </p>
                  {/if}
                </div>
                <div
                  class="rounded-2xl bg-[#f0fbf7] border border-[#cdeee2] p-4"
                >
                  <p
                    class="text-[10px] font-black uppercase tracking-[0.22em] text-savings"
                  >
                    {$_('child.availableToSpend')}
                  </p>
                  <p class="text-2xl font-black text-slate-950 mt-1">
                    {summary.available_spending}
                  </p>
                  {#if allowanceActive}
                    <p class="mt-1 text-xs font-bold text-slate-500">
                      {formatMinorAmount(
                        allowanceActive.available_allowance_minor,
                        allowanceActive.currency,
                        allowanceActive.currency_exponent,
                      )}
                    </p>
                  {/if}
                </div>
              </div>

              <div class="grid grid-cols-2 gap-3">
                <div
                  class="rounded-2xl bg-slate-50 border border-slate-200 p-4"
                >
                  <p
                    class="text-[10px] font-black uppercase tracking-[0.22em] text-slate-400"
                  >
                    {$_('child.lockedSaved')}
                  </p>
                  <p class="text-xl font-black text-slate-950 mt-1">
                    {summary.locked_savings}
                  </p>
                  {#if allowanceActive}
                    <p class="mt-1 text-xs font-bold text-slate-500">
                      {formatMinorAmount(
                        allowanceActive.locked_saved_allowance_minor,
                        allowanceActive.currency,
                        allowanceActive.currency_exponent,
                      )}
                    </p>
                  {/if}
                </div>
                <div
                  class="rounded-2xl bg-[#fff1f1] border border-[#f0c6c6] p-4"
                >
                  <p
                    class="text-[10px] font-black uppercase tracking-[0.22em] text-penalty"
                  >
                    {$_('child.pointsOnHold')}
                  </p>
                  <p class="text-xl font-black text-slate-950 mt-1">
                    {summary.pending_redemptions}
                  </p>
                  {#if allowanceActive}
                    <p class="mt-1 text-xs font-bold text-slate-500">
                      {formatMinorAmount(
                        allowanceActive.pending_allowance_minor,
                        allowanceActive.currency,
                        allowanceActive.currency_exponent,
                      )}
                    </p>
                  {/if}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <main class="max-w-7xl mx-auto px-3 sm:px-4 pt-8 md:pt-10">
      <div class="grid gap-8 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]">
        <div class="order-2 space-y-8 lg:order-1">
          <section
            class="card bg-white p-6 md:p-8 border border-slate-100 shadow-xl"
          >
            <div
              class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between sm:gap-4 mb-6"
            >
              <div class="min-w-0">
                <p
                  class="text-[10px] font-black uppercase tracking-[0.25em] text-slate-400 mb-2"
                >
                  {$_('child.rewardsEyebrow')}
                </p>
                <h2 class="text-2xl md:text-3xl font-black text-slate-950">
                  {$_('child.chooseReward')}
                </h2>
              </div>
              <div
                class="inline-flex w-fit items-center gap-2 px-3 py-2 rounded-full bg-slate-100 text-slate-700 text-xs font-black uppercase tracking-[0.14em] sm:tracking-[0.22em]"
              >
                <Gift size={14} />
                {$_('child.availableRewards', { values: { count: rewardOptions.length } })}
              </div>
            </div>

            {#if rewardOptions.length > 0}
              <div class="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-4">
                {#each rewardOptions as reward}
                  {@const affordable =
                    reward.points <= summary.available_spending}
                  <div
                    data-qa="child-reward-card"
                    class={`rounded-[1.75rem] border p-4 md:p-5 flex flex-col gap-4 min-w-0 ${affordable ? "border-slate-200 bg-[#fffefb]" : "border-slate-200 bg-slate-50 opacity-80"}`}
                  >
                    <div class="flex flex-col gap-3">
                      <div class="min-w-0">
                        <h3
                          data-qa="child-reward-title"
                          class="text-lg font-black text-slate-950 break-words"
                        >
                          {reward.title}
                        </h3>
                      </div>
                      <div
                        data-qa="child-reward-value"
                        class={`inline-flex w-fit max-w-full rounded-2xl px-3 py-2 text-xs font-black uppercase tracking-[0.12em] sm:tracking-[0.15em] border leading-snug whitespace-normal break-words ${affordable ? "bg-savings/10 text-savings border-savings/20" : "bg-slate-100 text-slate-400 border-slate-200"}`}
                      >
                        {#if allowanceActive}
                          {reward.points} {$_('common.points')} / {formatMinorAmount(
                            rewardValueMinor(reward.points) || 0,
                            allowanceActive.currency,
                            allowanceActive.currency_exponent,
                          )}
                        {:else}
                          {reward.points} {$_('common.points')}
                        {/if}
                      </div>
                      <p
                        class="text-sm text-slate-600 break-words line-clamp-2"
                      >
                        {reward.description ||
                          $_('child.rewardFallback')}
                      </p>
                    </div>

                    <div class="flex flex-col gap-2">
                      <span
                        class="inline-flex w-fit max-w-full items-center rounded-full px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.12em] sm:tracking-[0.16em] leading-none bg-slate-100 text-slate-500"
                      >
                        {affordable
                          ? $_('child.affordable')
                          : $_('child.needMore', { values: { points: rewardShortfall(reward.points) } })}
                      </span>
                      <button
                        type="button"
                        disabled={!affordable ||
                          submittingRewardId === reward.id}
                        onclick={() => requestPresetReward(reward)}
                        class="inline-flex w-full max-w-full justify-center items-center gap-2 rounded-2xl px-3 py-3 text-[10px] sm:text-xs font-black uppercase tracking-[0.14em] sm:tracking-[0.18em] bg-hero text-white shadow-lg shadow-hero/20 disabled:opacity-50 disabled:shadow-none shrink-0"
                      >
                        {submittingRewardId === reward.id
                          ? $_('common.sending')
                          : $_('common.request')}
                        <ArrowRight size={12} />
                      </button>
                    </div>
                  </div>
                {/each}
              </div>
            {:else}
              <div
                class="rounded-[1.75rem] border border-dashed border-slate-200 bg-slate-50 p-6 text-center"
              >
                <p
                  class="text-sm font-black uppercase tracking-[0.22em] text-slate-400"
                >
                  {$_('child.noRewards')}
                </p>
                <p class="text-sm text-slate-500 mt-2">
                  {$_('child.askBelow')}
                </p>
              </div>
            {/if}
          </section>

          <section
            class="card bg-white p-6 md:p-8 border border-slate-100 shadow-xl"
          >
            <div
              class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between sm:gap-4 mb-6"
            >
              <div class="min-w-0">
                <p
                  class="text-[10px] font-black uppercase tracking-[0.25em] text-slate-400 mb-2"
                >
                  {$_('child.customRequest')}
                </p>
                <h2 class="text-2xl md:text-3xl font-black text-slate-950">
                  {$_('child.askSpend')}
                </h2>
                {#if allowanceActive}
                  <p
                    data-qa="child-custom-request-conversion"
                    class="mt-2 text-[10px] font-black uppercase tracking-widest text-slate-500 bg-slate-50 w-fit px-3 py-1.5 rounded-full border border-slate-200/60 shadow-sm"
                  >
                    {$_('child.onePointValue', { values: { value: formatMinorAmount(
                      Math.floor(
                        allowanceActive.settings.allowance_amount_minor /
                          allowanceActive.settings.point_goal,
                      ),
                      allowanceActive.currency,
                      allowanceActive.currency_exponent,
                    ) } })}
                  </p>
                {/if}
              </div>
              <div
                class="w-12 h-12 rounded-2xl bg-reward/10 text-reward flex items-center justify-center shrink-0"
              >
                <Trophy size={22} />
              </div>
            </div>

            <form
              data-qa="child-custom-request-form"
              class="grid grid-cols-1 md:grid-cols-[1fr_140px_auto] gap-4 md:items-start"
              onsubmit={submitCustomRequest}
            >
              <label class="block space-y-2 min-w-0">
                <span
                  class="block text-[10px] font-black uppercase tracking-[0.22em] text-slate-400 ml-1"
                  >{$_('child.requestName')}</span
                >
                <input
                  type="text"
                  bind:value={customRewardTitle}
                  placeholder={$_('child.requestPlaceholder')}
                  class="h-14 w-full rounded-2xl border-2 border-slate-200 bg-slate-50 px-4 text-slate-900 font-bold focus:outline-none focus:border-hero/30 transition-all"
                />
              </label>

              <label class="block space-y-2 min-w-0">
                <span
                  class="block text-[10px] font-black uppercase tracking-[0.22em] text-slate-400 ml-1"
                  >{$_('common.points')}</span
                >
                <div class="relative">
                  <input
                    type="number"
                    min="1"
                    max={Math.max(1, summary.available_spending)}
                    bind:value={customRewardPoints}
                    class="h-14 w-full rounded-2xl border-2 border-slate-200 bg-slate-50 pl-4 pr-12 text-slate-900 font-bold focus:outline-none focus:border-hero/30 transition-all"
                  />
                  <span
                    class="absolute right-4 top-1/2 -translate-y-1/2 text-[10px] font-black uppercase text-slate-300"
                    >{$_('common.pts')}</span
                  >
                </div>
              </label>

              <div class="space-y-2">
                <span
                  class="hidden md:block text-[10px] font-black uppercase tracking-[0.22em] text-transparent select-none"
                  aria-hidden="true"
                >Action</span>
                <button
                  type="submit"
                  disabled={submitting ||
                    !customRewardTitle.trim() ||
                    customRewardPoints < 1 ||
                    customRewardPoints > summary.available_spending}
                  class="btn-hero h-14 px-8 w-full md:w-auto rounded-2xl flex items-center justify-center gap-2 text-sm uppercase tracking-widest shadow-xl shadow-hero/20 disabled:opacity-50 whitespace-nowrap"
                >
                  {submitting ? $_('common.sending') : $_('common.request')}
                  <ArrowRight size={18} />
                </button>
              </div>
            </form>

            {#if allowanceActive}
              <div
                class="mt-4 flex flex-col sm:flex-row items-center justify-center md:justify-start gap-2"
              >
                <p
                  data-qa="child-custom-request-value"
                  class="text-[10px] font-black uppercase tracking-wider text-slate-500 bg-slate-100/50 px-3 py-1.5 rounded-full border border-slate-200/40"
                >
                  {$_('child.calculatedValue', { values: { value: formatMinorAmount(
                    rewardValueMinor(customRewardPoints) || 0,
                    allowanceActive.currency,
                    allowanceActive.currency_exponent,
                  ) } })}
                </p>
              </div>
            {/if}
          </section>

          <section
            class="card bg-white p-6 md:p-8 border border-slate-100 shadow-xl"
          >
            <div
              class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between sm:gap-4 mb-6"
            >
              <div class="min-w-0">
                <p
                  class="text-[10px] font-black uppercase tracking-[0.25em] text-slate-400 mb-2"
                >
                  {$_('child.recentActivity')}
                </p>
                <h2 class="text-2xl md:text-3xl font-black text-slate-950">
                  {$_('child.pointsLog')}
                </h2>
              </div>
              <div
                class="inline-flex w-fit items-center gap-2 px-3 py-2 rounded-full bg-slate-100 text-slate-700 text-xs font-black uppercase tracking-[0.14em] sm:tracking-[0.22em]"
              >
                <Clock3 size={14} />
                {$_('child.latestEntries')}
              </div>
            </div>

            {#if recentActivity.length > 0}
              <div class="space-y-3">
                {#each recentActivity as tx}
                  <div
                    class="rounded-[1.5rem] border p-4 md:p-5 flex flex-col sm:flex-row sm:items-start gap-4 min-w-0 bg-[#fffefb]"
                  >
                    <div
                      class={`shrink-0 w-14 h-14 rounded-2xl border flex flex-col items-center justify-center text-xs font-black uppercase tracking-[0.15em] ${getActivityBadgeClass(tx)}`}
                    >
                      <span class="text-base leading-none"
                        >{formatPoints(tx.points)}</span
                      >
                      <span>{$_('common.pts')}</span>
                    </div>
                    <div class="min-w-0 flex-1">
                      <div class="flex flex-wrap items-center gap-2 mb-2">
                        <span
                          class="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.22em] text-slate-500"
                        >
                          {getActivityLabel(tx)}
                        </span>
                        <span
                          class="text-[10px] font-black uppercase tracking-[0.2em] text-slate-300"
                          >{formatDate(tx.created_at)}</span
                        >
                      </div>
                      <p class="font-black text-slate-950 break-words">
                        {tx.description}
                      </p>
                      <p
                        class="text-xs text-slate-500 mt-1 uppercase tracking-[0.18em]"
                      >
                        {getJarLabel(tx.jar)}
                      </p>
                    </div>
                  </div>
                {/each}
              </div>
            {:else}
              <div
                class="rounded-[1.5rem] border border-dashed border-slate-200 bg-slate-50 p-8 text-center"
              >
                <p
                  class="text-sm font-black uppercase tracking-[0.22em] text-slate-400"
                >
                  {$_('child.noActivity')}
                </p>
                <p class="text-sm text-slate-500 mt-2">
                  {$_('child.noActivityHelp')}
                </p>
              </div>
            {/if}
          </section>
        </div>

        <aside class="order-1 space-y-8 lg:order-2">
          <section
            class="card bg-white p-6 md:p-8 border border-slate-100 shadow-xl"
          >
            <div
              class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between mb-6"
            >
              <div>
                <p
                  class="text-[10px] font-black uppercase tracking-[0.25em] text-slate-400 mb-2"
                >
                  {$_('child.myDay')}
                </p>
                <h2 class="text-2xl font-black text-slate-950">
                  {$_('child.todaySchedule')}
                </h2>
                <p class="mt-1 text-sm text-slate-500">
                  {getLocalDateValue()
                    ? new Date().toLocaleDateString($locale || "en", {
                        weekday: "long",
                        month: "short",
                        day: "numeric",
                      })
                    : ""}
                </p>
              </div>
              <div
                class="w-12 h-12 rounded-2xl bg-hero/10 text-hero flex items-center justify-center"
              >
                <Sparkles size={22} />
              </div>
            </div>

            {#if dayLoading}
              <div
                class="rounded-[1.5rem] border border-dashed border-slate-200 bg-slate-50 p-6 text-center"
              >
                <p
                  class="text-sm font-black uppercase tracking-[0.22em] text-slate-400"
                >
                  {$_('child.loadingTodaySchedule')}
                </p>
              </div>
            {:else if dayError}
              <div class="space-y-5">
                <div
                  class="rounded-[1.5rem] border border-red-100 bg-red-50 p-5 text-red-700 font-bold break-words"
                >
                  {dayError}
                </div>

                <div
                  class="rounded-[1.75rem] border border-slate-100 bg-white p-4 shadow-sm"
                >
                  <div class="mb-4 flex items-center justify-between gap-3">
                    <div>
                      <p
                        class="text-[10px] font-black uppercase tracking-[0.22em] text-slate-400"
                      >
                        {$_('child.schoolBag')}
                      </p>
                      <h3 class="mt-1 text-lg font-black text-slate-950">
                        {$_('child.packTomorrow')}
                      </h3>
                    </div>
                    <span
                      class="rounded-full bg-amber-100 px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.16em] text-amber-700"
                    >
                      {schoolItemsTomorrow().length}
                    </span>
                  </div>
                  <p
                    class="mb-4 rounded-2xl bg-slate-50 px-3 py-2 text-xs font-black uppercase tracking-[0.18em] text-slate-500"
                  >
                    {$_('child.checkStationery')}
                  </p>

                  {#if schoolTomorrowError}
                    <div
                      class="rounded-2xl border border-rose-100 bg-rose-50 p-4 text-sm font-bold text-rose-700 break-words"
                    >
                      {schoolTomorrowError}
                    </div>
                  {:else if schoolItemsTomorrow().length > 0}
                    <div class="space-y-2">
                      {#each schoolItemsTomorrow() as item}
                        <div
                          class="flex items-start gap-3 rounded-2xl border border-amber-100 bg-amber-50/80 px-3 py-3"
                        >
                          <span
                            class="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-amber-100 text-amber-700"
                          >
                            <Check size={13} />
                          </span>
                          <div class="min-w-0">
                            <p class="font-black text-slate-950 break-words">
                              {schoolNeedLabel(item)}
                            </p>
                            <p
                              class="mt-1 text-xs font-bold uppercase tracking-[0.16em] text-slate-400 break-words"
                            >
                              {item.class_name}
                            </p>
                          </div>
                        </div>
                      {/each}
                    </div>
                  {:else}
                    <div
                      class="rounded-2xl border border-dashed border-amber-100 bg-amber-50/40 p-4 text-center"
                    >
                        <p class="text-sm font-bold text-slate-500">
                          {$_('child.nothingTomorrow')}
                        </p>
                    </div>
                  {/if}

                  <div class="mt-5 border-t border-slate-100 pt-4">
                    <div class="mb-3 flex items-center justify-between gap-3">
                      <div>
                        <p
                          class="text-[10px] font-black uppercase tracking-[0.2em] text-sky-600"
                        >
                          {$_('child.neededToday')}
                        </p>
                        <h4 class="mt-1 text-base font-black text-slate-950">
                          {$_('child.neededNow')}
                        </h4>
                      </div>
                      <span
                        class="rounded-full bg-sky-100 px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.16em] text-sky-700"
                      >
                        {schoolItemsToday().length}
                      </span>
                    </div>

                    {#if schoolTodayError}
                      <div
                        class="rounded-2xl border border-rose-100 bg-white p-4 text-sm font-bold text-rose-700 break-words"
                      >
                        {schoolTodayError}
                      </div>
                    {:else if schoolItemsToday().length > 0}
                      <div class="space-y-2">
                        {#each schoolItemsToday() as item}
                          <div
                            class="flex items-start gap-3 rounded-2xl border border-sky-100 bg-sky-50/60 px-3 py-3"
                          >
                            <span
                              class="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-sky-100 text-sky-700"
                            >
                              <Check size={13} />
                            </span>
                            <div class="min-w-0">
                              <p class="font-black text-slate-950 break-words">
                                {schoolNeedLabel(item)}
                              </p>
                              <p
                                class="mt-1 text-xs font-bold uppercase tracking-[0.16em] text-slate-400 break-words"
                              >
                                {item.class_name}
                              </p>
                            </div>
                          </div>
                        {/each}
                      </div>
                    {:else}
                      <div
                        class="rounded-2xl border border-dashed border-sky-100 bg-sky-50/30 p-4 text-center"
                      >
                        <p class="text-sm font-bold text-slate-500">
                          {$_('child.nothingToday')}
                        </p>
                      </div>
                    {/if}
                  </div>
                </div>
              </div>
            {:else}
              <div class="space-y-5">
                <div
                  class="rounded-[1.75rem] border border-slate-100 bg-white p-4 shadow-sm"
                >
                  <div class="mb-4 flex items-center justify-between gap-3">
                    <div>
                      <p
                        class="text-[10px] font-black uppercase tracking-[0.22em] text-slate-400"
                      >
                        {$_('child.schoolBag')}
                      </p>
                      <h3 class="mt-1 text-lg font-black text-slate-950">
                        {$_('child.packTomorrow')}
                      </h3>
                    </div>
                    <span
                      class="rounded-full bg-amber-100 px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.16em] text-amber-700"
                    >
                      {schoolItemsTomorrow().length}
                    </span>
                  </div>
                  <p
                    class="mb-4 rounded-2xl bg-slate-50 px-3 py-2 text-xs font-black uppercase tracking-[0.18em] text-slate-500"
                  >
                    {$_('child.checkStationery')}
                  </p>

                  {#if schoolTomorrowError}
                    <div
                      class="rounded-2xl border border-rose-100 bg-rose-50 p-4 text-sm font-bold text-rose-700 break-words"
                    >
                      {schoolTomorrowError}
                    </div>
                  {:else if schoolItemsTomorrow().length > 0}
                    <div class="space-y-2">
                      {#each schoolItemsTomorrow() as item}
                        <div
                          class="flex items-start gap-3 rounded-2xl border border-amber-100 bg-amber-50/80 px-3 py-3"
                        >
                          <span
                            class="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-amber-100 text-amber-700"
                          >
                            <Check size={13} />
                          </span>
                          <div class="min-w-0">
                            <p class="font-black text-slate-950 break-words">
                              {schoolNeedLabel(item)}
                            </p>
                            <p
                              class="mt-1 text-xs font-bold uppercase tracking-[0.16em] text-slate-400 break-words"
                            >
                              {item.class_name}
                            </p>
                          </div>
                        </div>
                      {/each}
                    </div>
                  {:else}
                    <div
                      class="rounded-2xl border border-dashed border-amber-100 bg-amber-50/40 p-4 text-center"
                    >
                        <p class="text-sm font-bold text-slate-500">
                          {$_('child.nothingTomorrow')}
                        </p>
                    </div>
                  {/if}

                  <div class="mt-5 border-t border-slate-100 pt-4">
                    <div class="mb-3 flex items-center justify-between gap-3">
                      <div>
                        <p
                          class="text-[10px] font-black uppercase tracking-[0.2em] text-sky-600"
                        >
                          {$_('child.neededToday')}
                        </p>
                        <h4 class="mt-1 text-base font-black text-slate-950">
                          {$_('child.neededNow')}
                        </h4>
                      </div>
                      <span
                        class="rounded-full bg-sky-100 px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.16em] text-sky-700"
                      >
                        {schoolItemsToday().length}
                      </span>
                    </div>

                    {#if schoolTodayError}
                      <div
                        class="rounded-2xl border border-rose-100 bg-white p-4 text-sm font-bold text-rose-700 break-words"
                      >
                        {schoolTodayError}
                      </div>
                    {:else if schoolItemsToday().length > 0}
                      <div class="space-y-2">
                        {#each schoolItemsToday() as item}
                          <div
                            class="flex items-start gap-3 rounded-2xl border border-sky-100 bg-sky-50/60 px-3 py-3"
                          >
                            <span
                              class="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-sky-100 text-sky-700"
                            >
                              <Check size={13} />
                            </span>
                            <div class="min-w-0">
                              <p class="font-black text-slate-950 break-words">
                                {schoolNeedLabel(item)}
                              </p>
                              <p
                                class="mt-1 text-xs font-bold uppercase tracking-[0.16em] text-slate-400 break-words"
                              >
                                {item.class_name}
                              </p>
                            </div>
                          </div>
                        {/each}
                      </div>
                    {:else}
                      <div
                        class="rounded-2xl border border-dashed border-sky-100 bg-sky-50/30 p-4 text-center"
                      >
                        <p class="text-sm font-bold text-slate-500">
                          {$_('child.nothingToday')}
                        </p>
                      </div>
                    {/if}
                  </div>
                </div>

                <div>
                  <div class="mb-3 flex items-center justify-between gap-3">
                    <h3 class="text-lg font-black text-slate-950">
                      {$_('child.tasksToday')}
                    </h3>
                    <span
                      class="rounded-full bg-slate-100 px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.16em] text-slate-500"
                      >{tasksToday().length}</span
                    >
                  </div>
                  {#if tasksToday().length > 0}
                    <div class="space-y-3">
                      {#each tasksToday() as item}
                        <article
                          class="min-w-0 rounded-[1.5rem] border border-slate-100 bg-[#fffefb] p-4 shadow-sm"
                        >
                          <div
                            class="flex min-w-0 flex-col gap-4 sm:flex-row sm:items-start sm:justify-between"
                          >
                            <div class="min-w-0 flex-1">
                              <div
                                class="mb-3 flex flex-wrap items-center gap-2"
                              >
                                <span
                                class={`inline-flex items-center rounded-full border px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.14em] sm:tracking-[0.18em] ${typeClass(item.entry.entry_type)}`}
                              >
                                  {$_('child.task')}
                                </span>
                                {#if item.entry.is_rewardable && item.entry.points_value}
                                  <span
                                    class="inline-flex items-center rounded-full border border-amber-200 bg-amber-100 px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.14em] text-amber-700 sm:tracking-[0.18em]"
                                  >
                                    {item.entry.points_value} {$_('common.points')}
                                  </span>
                                {/if}
                                {#if item.completion}
                                  <span
                                    class={`inline-flex items-center rounded-full border px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.14em] sm:tracking-[0.18em] ${statusClass(item.completion.status)}`}
                                  >
                                    {statusLabel(item.completion.status)}
                                  </span>
                                {/if}
                              </div>

                              <h4
                                class="text-lg font-black text-slate-950 break-words"
                              >
                                {item.entry.title}
                              </h4>
                              {#if cleanCalendarDescription(item)}
                                <p
                                  class="mt-2 text-sm text-slate-600 break-words leading-6"
                                >
                                  {cleanCalendarDescription(item)}
                                </p>
                              {/if}

                              <div
                                class="mt-3 flex flex-wrap items-center gap-2 text-[11px] font-black uppercase tracking-[0.16em] text-slate-500"
                              >
                                <span
                                  class="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-1"
                                >
                                  <Clock3 size={12} />
                                  {formatCalendarTime(item.entry.start_time)}
                                </span>
                                <span
                                  class={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 ${recurrenceClass(item)}`}
                                >
                                  <Repeat2 size={12} />
                                  {recurrenceLabel(item)}
                                </span>
                              </div>
                            </div>

                            {#if accessMode === "child" && !item.completion}
                              <button
                                type="button"
                                class="inline-flex w-full shrink-0 items-center justify-center gap-2 rounded-2xl bg-slate-900 px-4 py-3 text-xs font-black uppercase tracking-[0.14em] text-white shadow-sm disabled:opacity-60 sm:w-auto sm:tracking-[0.18em]"
                                disabled={daySubmittingId === item.entry.id}
                                onclick={() => completeTodayItem(item)}
                              >
                                <Check size={16} />
                                {daySubmittingId === item.entry.id
                                  ? $_('common.saving')
                                  : $_('child.markDone')}
                              </button>
                            {/if}
                          </div>
                        </article>
                      {/each}
                    </div>
                  {:else}
                    <div
                      class="rounded-[1.5rem] border border-dashed border-slate-200 bg-slate-50 p-5 text-center"
                    >
                      <p
                        class="text-sm font-black uppercase tracking-[0.18em] text-slate-400"
                      >
                        {$_('child.noTasks')}
                      </p>
                    </div>
                  {/if}
                </div>

                <div>
                  <div class="mb-3 flex items-center justify-between gap-3">
                    <h3 class="text-lg font-black text-slate-950">
                      {$_('child.eventsToday')}
                    </h3>
                    <span
                      class="rounded-full bg-slate-100 px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.16em] text-slate-500"
                      >{eventsToday().length}</span
                    >
                  </div>
                  {#if eventsToday().length > 0}
                    <div class="space-y-3">
                      {#each eventsToday() as item}
                        <article
                          class="min-w-0 rounded-[1.5rem] border border-slate-100 bg-white p-4 shadow-sm"
                        >
                          <div class="mb-3 flex flex-wrap items-center gap-2">
                            <span
                            class={`inline-flex items-center rounded-full border px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.14em] sm:tracking-[0.18em] ${typeClass(item.entry.entry_type)}`}
                          >
                              {$_('child.event')}
                            </span>
                            <span
                              class={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.14em] sm:tracking-[0.18em] ${recurrenceClass(item)}`}
                            >
                              <Repeat2 size={12} />
                              {recurrenceLabel(item)}
                            </span>
                          </div>
                          <h4
                            class="text-lg font-black text-slate-950 break-words"
                          >
                            {item.entry.title}
                          </h4>
                          {#if cleanCalendarDescription(item)}
                            <p
                              class="mt-2 text-sm text-slate-600 break-words leading-6"
                            >
                              {cleanCalendarDescription(item)}
                            </p>
                          {/if}
                          <div
                            class="mt-3 flex flex-wrap items-center gap-2 text-[11px] font-black uppercase tracking-[0.16em] text-slate-500"
                          >
                            <span
                              class="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-1"
                            >
                              <Clock3 size={12} />
                              {formatCalendarTime(item.entry.start_time)}
                            </span>
                          </div>
                        </article>
                      {/each}
                    </div>
                  {:else}
                    <div
                      class="rounded-[1.5rem] border border-dashed border-slate-200 bg-slate-50 p-5 text-center"
                    >
                      <p
                        class="text-sm font-black uppercase tracking-[0.18em] text-slate-400"
                      >
                        {$_('child.noEvents')}
                      </p>
                    </div>
                  {/if}
                </div>
              </div>
            {/if}
          </section>

          <section
            class="card bg-white p-6 md:p-8 border border-slate-100 shadow-xl"
          >
            <div
              class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between sm:gap-4 mb-6"
            >
              <div class="min-w-0">
                <p
                  class="text-[10px] font-black uppercase tracking-[0.25em] text-slate-400 mb-2"
                >
                  {$_('child.pendingRequests')}
                </p>
                <h2 class="text-2xl font-black text-slate-950">
                  {$_('child.waitingRequests')}
                </h2>
              </div>
              <div
                class="w-12 h-12 rounded-2xl bg-hero/10 text-hero flex items-center justify-center"
              >
                <BadgeCheck size={22} />
              </div>
            </div>

            {#if pendingRequests.length > 0}
              <div class="space-y-3">
                {#each pendingRequests as request}
                  <div
                    class="rounded-[1.5rem] border border-hero/20 bg-hero/5 p-4"
                  >
                    <div
                      class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between"
                    >
                      <div class="min-w-0 flex-1">
                        <h3 class="font-black text-slate-950 break-words">
                          {request.title}
                        </h3>
                        <p class="text-sm text-slate-600 mt-1 break-words">
                          {request.description || $_('child.waitingApproval')}
                        </p>
                      </div>
                      <span
                        class="shrink-0 rounded-2xl bg-white px-3 py-2 text-xs font-black uppercase tracking-[0.12em] sm:tracking-[0.2em] text-hero border border-hero/20 max-w-full sm:max-w-[45%] whitespace-normal sm:whitespace-nowrap"
                      >
                        {#if allowanceActive}
                          {request.points} {$_('common.points')} / {formatMinorAmount(
                            rewardValueMinor(request.points) || 0,
                            allowanceActive.currency,
                            allowanceActive.currency_exponent,
                          )}
                        {:else}
                          {request.points} {$_('common.points')}
                        {/if}
                      </span>
                    </div>
                    <p
                      class="text-[10px] font-black uppercase tracking-[0.22em] text-slate-400 mt-3 break-words"
                    >
                      {$_('child.requested', { values: { date: formatDateTime(request.created_at) } })}
                    </p>
                  </div>
                {/each}
              </div>
            {:else}
              <div
                class="rounded-[1.5rem] border border-dashed border-slate-200 bg-slate-50 p-6 text-center"
              >
                <p
                  class="text-sm font-black uppercase tracking-[0.22em] text-slate-400"
                >
                  {$_('child.nothingWaiting')}
                </p>
                <p class="text-sm text-slate-500 mt-2">
                  {$_('child.requestsShowHere')}
                </p>
              </div>
            {/if}
          </section>

          <section
            class="card bg-gradient-to-br from-[#f3efff] via-[#eef2ff] to-[#f8f8ff] text-slate-900 p-6 md:p-8 shadow-2xl relative overflow-hidden border border-slate-200"
          >
            <div
              class="absolute inset-0 bg-gradient-to-br from-hero/20 via-transparent to-transparent"
            ></div>
            <div class="relative z-10">
              <div class="flex items-center gap-3 mb-5 min-w-0">
                <div
                  class="w-12 h-12 rounded-2xl bg-white/80 border border-slate-200 flex items-center justify-center text-slate-700"
                >
                  <PiggyBank size={22} />
                </div>
              <div class="min-w-0">
                <p
                  class="text-[10px] font-black uppercase tracking-[0.25em] text-slate-600"
                >
                    {$_('child.bank')}
                  </p>
                  <h2 class="text-2xl font-black text-slate-950">
                    {$_('child.savingsSnapshot')}
                  </h2>
                </div>
              </div>
              <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div
                  class="rounded-2xl bg-white/80 border border-slate-200 p-4"
                >
                  <p
                    class="text-[10px] font-black uppercase tracking-[0.2em] text-slate-600"
                  >
                    {$_('common.saved')}
                  </p>
                  <p class="text-3xl font-black mt-1 text-slate-950">
                    {summary.savings_balance}
                  </p>
                  {#if allowanceActive}
                    <p class="mt-1 text-sm font-bold text-slate-600">
                      {formatMinorAmount(
                        allowanceActive.saved_allowance_minor,
                        allowanceActive.currency,
                        allowanceActive.currency_exponent,
                      )}
                    </p>
                  {/if}
                </div>
                <div
                  class="rounded-2xl bg-white/80 border border-slate-200 p-4"
                >
                  <p
                    class="text-[10px] font-black uppercase tracking-[0.2em] text-slate-600"
                  >
                    {$_('common.available')}
                  </p>
                  <p class="text-3xl font-black mt-1 text-slate-950">
                    {summary.available_savings}
                  </p>
                  {#if allowanceActive}
                    <p class="mt-1 text-sm font-bold text-slate-600">
                      {formatMinorAmount(
                        allowanceActive.available_allowance_minor,
                        allowanceActive.currency,
                        allowanceActive.currency_exponent,
                      )}
                    </p>
                  {/if}
                </div>
                <div
                  class="rounded-2xl bg-white/80 border border-slate-200 p-4"
                >
                  <p
                    class="text-[10px] font-black uppercase tracking-[0.2em] text-slate-600"
                  >
                    {$_('common.locked')}
                  </p>
                  <p class="text-3xl font-black mt-1 text-slate-950">
                    {summary.locked_savings}
                  </p>
                  {#if allowanceActive}
                    <p class="mt-1 text-sm font-bold text-slate-600">
                      {formatMinorAmount(
                        allowanceActive.locked_saved_allowance_minor,
                        allowanceActive.currency,
                        allowanceActive.currency_exponent,
                      )}
                    </p>
                  {/if}
                </div>
              </div>
              <div
                class="mt-5 rounded-2xl border border-slate-200 bg-white/70 p-4"
              >
                <div
                  class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"
                >
                  <p
                    data-qa="child-savings-next-unlock"
                    class="text-sm font-black text-slate-800"
                  >
                    {nextUnlockText()}
                  </p>
                  {#if savingsUnlockSchedule.length > 0}
                    <button
                      type="button"
                      class="inline-flex w-full items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-[10px] font-black uppercase tracking-[0.16em] text-slate-700 sm:w-auto"
                      aria-expanded={showUnlockSchedule}
                      onclick={() => (showUnlockSchedule = !showUnlockSchedule)}
                    >
                      <Clock3 size={14} />
                      {showUnlockSchedule
                        ? $_('child.hideUnlock')
                        : $_('child.viewUnlock')}
                    </button>
                  {/if}
                </div>

                {#if showUnlockSchedule && savingsUnlockSchedule.length > 0}
                  <div
                    data-qa="child-savings-unlock-schedule"
                    class="mt-4 space-y-2"
                  >
                    {#each savingsUnlockSchedule as unlock}
                      <div
                        class="flex items-center justify-between gap-3 rounded-xl bg-slate-50 px-3 py-2 text-sm font-bold text-slate-700"
                      >
                        <span>{unlockScheduleDateLabel(unlock.unlock_date)}</span>
                        <span class="text-right">
                          {unlock.points} {$_('common.pts')}
                          {#if unlock.bonus_points > 0}
                            <span class="block text-[10px] font-black uppercase tracking-[0.14em] text-savings">
                              {$_('child.includesBonus', {
                                values: { points: unlock.bonus_points },
                              })}
                            </span>
                          {/if}
                        </span>
                      </div>
                    {/each}
                  </div>
                {/if}

                <div class="mt-4 flex flex-col gap-2">
                  <button
                    type="button"
                    class="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-savings px-4 py-3 text-xs font-black uppercase tracking-[0.16em] text-white shadow-lg shadow-savings/20 transition hover:bg-[#008c81] disabled:cursor-not-allowed disabled:opacity-50"
                    disabled={!summary || summary.available_spending <= 0}
                    onclick={openSavingsBankModal}
                  >
                    <PiggyBank size={14} />
                    {$_('child.bankPoints')}
                  </button>
                  <p
                    class="text-[10px] font-black uppercase tracking-[0.14em] text-slate-500"
                  >
                    {$_('child.bankedLocked')}
                  </p>
                </div>
              </div>
            </div>
          </section>
        </aside>
      </div>
    </main>
    {#if showSavingsBankModal}
      <!-- Show the savings bonus, next unlock date, grouped unlock schedule, and dedicated banking modal. -->
      <div
        class="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/70 px-3 py-3 backdrop-blur-sm sm:items-center sm:px-4"
      >
        <button
          type="button"
          class="absolute inset-0 cursor-default"
          aria-label={$_('common.close')}
          onclick={closeSavingsBankModal}
        ></button>
        <div
          class="relative z-10 flex w-full max-w-lg flex-col overflow-hidden rounded-[2rem] bg-white shadow-2xl"
        >
          <div
            class="flex items-start justify-between gap-4 border-b border-slate-100 px-5 py-5 sm:px-6"
          >
            <div class="min-w-0">
              <p
                class="text-[10px] font-black uppercase tracking-[0.22em] text-slate-400"
              >
                {$_('child.bank')}
              </p>
              <h3 class="mt-1 text-2xl font-black text-slate-950">
                {$_('child.bankPoints')}
              </h3>
              <p class="mt-2 text-sm font-medium text-slate-600 break-words">
                {summary.child.display_name}
              </p>
            </div>
            <button
              type="button"
              class="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-slate-50 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
              aria-label={$_('common.close')}
              onclick={closeSavingsBankModal}
            >
              <X size={18} />
            </button>
          </div>

          <form class="flex flex-1 flex-col" onsubmit={submitSavingsBank}>
            <div class="space-y-4 px-5 py-5 sm:px-6">
              <div class="rounded-[1.5rem] border border-savings/10 bg-savings/5 p-4">
                <p
                  class="text-[10px] font-black uppercase tracking-[0.18em] text-savings-dark"
                >
                  {$_('child.bankedLockedLong')}
                </p>
              </div>

              <label class="block">
                <span
                  class="mb-2 block text-[10px] font-black uppercase tracking-[0.2em] text-slate-400"
                >
                  {$_('child.pointsToBank')}
                </span>
                <input
                  type="number"
                  min="1"
                  max={summary.available_spending}
                  bind:value={savingsBankPoints}
                  class="w-full rounded-2xl border-2 border-slate-200 bg-slate-50 px-4 py-4 text-2xl font-black text-slate-900 focus:border-savings/30 focus:outline-none"
                />
              </label>

              <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div class="rounded-2xl border border-slate-100 bg-slate-50 p-4">
                  <p
                    class="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400"
                  >
                    {$_('child.savingsBonus')}
                  </p>
                  <p class="mt-1 text-2xl font-black text-slate-950">
                    +{savingsBankBonus()} {$_('common.pts')}
                  </p>
                </div>
                <div class="rounded-2xl border border-slate-100 bg-slate-50 p-4">
                  <p
                    class="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400"
                  >
                    {$_('child.unlocksAs')}
                  </p>
                  <p class="mt-1 text-2xl font-black text-slate-950">
                    {savingsBankTotal()} {$_('common.pts')}
                  </p>
                  <p class="mt-1 text-xs font-bold text-slate-500">
                    {$_('child.unlocksAt', { values: { date: savingsBankUnlockLabel() } })}
                  </p>
                </div>
              </div>
            </div>

            <div
              class="border-t border-slate-100 bg-white px-5 py-5 sm:px-6"
            >
              <div class="flex flex-col gap-3 sm:flex-row">
              <button
                type="button"
                class="inline-flex w-full items-center justify-center rounded-2xl border border-slate-200 bg-white px-4 py-4 text-xs font-black uppercase tracking-[0.16em] text-slate-700 transition hover:border-slate-300"
                onclick={closeSavingsBankModal}
              >
                  {$_('common.cancel')}
              </button>
                <button
                  type="submit"
                  disabled={
                    submitting ||
                    savingsBankAmount() < 1 ||
                    savingsBankAmount() > summary.available_spending
                  }
                  class="inline-flex w-full items-center justify-center rounded-2xl bg-savings px-4 py-4 text-xs font-black uppercase tracking-[0.16em] text-white shadow-lg shadow-savings/20 transition hover:bg-[#008c81] disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {submitting ? $_('child.banking') : $_('child.bankPoints')}
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>
    {/if}
  {:else}
    <div class="flex justify-center py-32">
      <p class="text-slate-400 font-black uppercase tracking-[0.28em]">
        {$_('child.childNotFound')}
      </p>
    </div>
  {/if}
</div>

<style>
  :global(.card) {
    border-radius: 2rem;
    box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.08);
  }

  .text-hero {
    color: #7c3aed;
  }

  .text-savings {
    color: #10b981;
  }

  .text-reward {
    color: #f59e0b;
  }

  .text-penalty {
    color: #f43f5e;
  }

  .bg-hero {
    background: #7c3aed;
  }

  .bg-penalty {
    background: #f43f5e;
  }

  .bg-savings {
    background: #10b981;
  }

  .bg-reward {
    background: #f59e0b;
  }

  .shadow-hero\/20 {
    box-shadow: 0 10px 20px -5px rgba(124, 58, 237, 0.2);
  }

  .line-clamp-2 {
    display: -webkit-box;
    line-clamp: 2;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
</style>
