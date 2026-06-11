<script lang="ts">
  import { onMount } from 'svelte';
  import { _, locale } from 'svelte-i18n';
  import { api } from '$lib/api';
  import {
    ArrowLeft,
    ArrowRight,
    BadgeCheck,
    CalendarDays,
    Check,
    ChevronLeft,
    ChevronRight,
    Clock3,
    PencilLine,
    Plus,
    Repeat2,
    Sparkles,
    Trash2,
    X
  } from 'lucide-svelte';

  type ChildOption = {
    child: {
      id: number;
      display_name: string;
      avatar_name: string | null;
    };
  };

  type CalendarEntry = {
    id: number;
    family_id: number;
    child_id: number;
    created_by_parent_id: number;
    title: string;
    description: string | null;
    entry_type: 'task' | 'event' | string;
    is_rewardable: boolean;
    points_value: number | null;
    recurrence_type: 'none' | 'daily' | 'weekly' | string;
    recurrence_days: string | null;
    start_date: string;
    start_time: string | null;
    duration_minutes: number | null;
    is_active: boolean;
    created_at: string;
  };

  type CalendarCompletion = {
    id: number;
    entry_id: number;
    child_id: number;
    occurrence_date: string;
    status: 'pending' | 'approved' | 'rejected' | string;
    completed_at: string | null;
    reviewed_at: string | null;
    reviewed_by_parent_id: number | null;
    base_points: number | null;
    bonus_multiplier_applied: number;
    points_awarded: number | null;
    transaction_id: number | null;
    streak_source_id: number | null;
  };

  type CalendarOccurrence = {
    entry: CalendarEntry;
    occurrence_date: string;
    completion: CalendarCompletion | null;
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

  type FormState = {
    child_id: string;
    title: string;
    description: string;
    entry_type: 'task' | 'event';
    start_date: string;
    start_time: string;
    duration_minutes: string;
    recurrence_type: 'none' | 'daily' | 'weekly';
    recurrence_days: number[];
    is_rewardable: boolean;
    points_value: string | number;
  };

  type SchoolRow = {
    key: string;
    id: number | null;
    class_name: string;
    needed_item: string;
  };

  const WEEKDAY_OPTIONS = [
    { label: 'calendar.weekdayMondayShort', value: 0 },
    { label: 'calendar.weekdayTuesdayShort', value: 1 },
    { label: 'calendar.weekdayWednesdayShort', value: 2 },
    { label: 'calendar.weekdayThursdayShort', value: 3 },
    { label: 'calendar.weekdayFridayShort', value: 4 },
    { label: 'calendar.weekdaySaturdayShort', value: 5 },
    { label: 'calendar.weekdaySundayShort', value: 6 }
  ];

  const SCHOOL_WEEKDAY_OPTIONS = [
    { label: 'calendar.weekdaySundayShort', name: 'calendar.weekdaySundayShort', value: 6 },
    { label: 'calendar.weekdayMondayShort', name: 'calendar.weekdayMondayShort', value: 0 },
    { label: 'calendar.weekdayTuesdayShort', name: 'calendar.weekdayTuesdayShort', value: 1 },
    { label: 'calendar.weekdayWednesdayShort', name: 'calendar.weekdayWednesdayShort', value: 2 },
    { label: 'calendar.weekdayThursdayShort', name: 'calendar.weekdayThursdayShort', value: 3 },
    { label: 'calendar.weekdayFridayShort', name: 'calendar.weekdayFridayShort', value: 4 },
    { label: 'calendar.weekdaySaturdayShort', name: 'calendar.weekdaySaturdayShort', value: 5 }
  ];

  let children = $state<ChildOption[]>([]);
  let selectedChildId = $state('');
  let selectedDate = $state(dateToInputValue(new Date()));
  let viewMode = $state<'today' | 'week'>('week');
  let calendarItems = $state<CalendarOccurrence[]>([]);
  let loading = $state(true);
  let loadingCalendar = $state(false);
  let error = $state<string | null>(null);
  let calendarNotice = $state<string | null>(null);
  let formError = $state<string | null>(null);
  let modalOpen = $state(false);
  let saving = $state(false);
  let editingEntryId = $state<number | null>(null);
  let form = $state<FormState>(defaultForm());
  let schoolModalOpen = $state(false);
  let schoolSaving = $state(false);
  let schoolError = $state<string | null>(null);
  let schoolChildId = $state('');
  let schoolWeekday = $state(0);
  let schoolRows = $state<SchoolRow[]>([]);
  let schoolExistingRows = $state<SchoolRow[]>([]);
  let schoolLoading = $state(false);
  let nextSchoolRowKey = $state(1);

  function dateToInputValue(value: Date) {
    const year = value.getFullYear();
    const month = `${value.getMonth() + 1}`.padStart(2, '0');
    const day = `${value.getDate()}`.padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  function parseDateInput(value: string) {
    const [year, month, day] = value.split('-').map(Number);
    return new Date(year, month - 1, day);
  }

  function addDays(value: string, days: number) {
    const date = parseDateInput(value);
    date.setDate(date.getDate() + days);
    return dateToInputValue(date);
  }

  function getWeekDates(referenceDate: string) {
    const start = parseDateInput(referenceDate);
    const offset = start.getDay();
    start.setDate(start.getDate() - offset);

    return Array.from({ length: 7 }, (_, index) => {
      const date = new Date(start);
      date.setDate(start.getDate() + index);
      return dateToInputValue(date);
    });
  }

  function formatLongDate(value: string) {
    return parseDateInput(value).toLocaleDateString($locale || 'en', {
      weekday: 'long',
      month: 'short',
      day: 'numeric'
    });
  }

  function formatShortDate(value: string) {
    return parseDateInput(value).toLocaleDateString($locale || 'en', {
      weekday: 'short',
      month: 'short',
      day: 'numeric'
    });
  }

  function formatWeekday(value: string) {
    return parseDateInput(value).toLocaleDateString($locale || 'en', {
      weekday: 'short'
    });
  }

  function formatWeekdayLetter(value: string) {
    const weekday = parseDateInput(value).getDay();
    if (weekday === 0) return $_('calendar.weekdaySundayShort');
    if (weekday === 1) return $_('calendar.weekdayMondayShort');
    if (weekday === 2) return $_('calendar.weekdayTuesdayShort');
    if (weekday === 3) return $_('calendar.weekdayWednesdayShort');
    if (weekday === 4) return $_('calendar.weekdayThursdayShort');
    if (weekday === 5) return $_('calendar.weekdayFridayShort');
    return $_('calendar.weekdaySaturdayShort');
  }

  function isToday(value: string) {
    return value === dateToInputValue(new Date());
  }

  function formatTime(value: string | null) {
    if (!value) return $_('calendar.allDay');
    const trimmed = value.slice(0, 5);
    const [hours, minutes] = trimmed.split(':').map(Number);
    const date = new Date();
    date.setHours(hours, minutes, 0, 0);
    return date.toLocaleTimeString($locale || 'en', {
      hour: 'numeric',
      minute: '2-digit'
    });
  }

  function formatDuration(minutes: number | null) {
    if (!minutes || minutes <= 0) return '';
    const hoursSuffix = $_('calendar.durationHoursShort');
    const minutesSuffix = $_('calendar.durationMinutesShort');
    if (minutes < 60) return `${minutes}${minutesSuffix}`;
    const hours = Math.floor(minutes / 60);
    const remainder = minutes % 60;
    return remainder > 0 ? `${hours}${hoursSuffix} ${remainder}${minutesSuffix}` : `${hours}${hoursSuffix}`;
  }

  function recurrenceLabel(entry: CalendarEntry) {
    if (entry.recurrence_type === 'daily') return $_('calendar.repeatsDaily');
    if (entry.recurrence_type === 'weekly') {
      const days = (entry.recurrence_days || '')
        .split(',')
        .map((value) => Number(value))
        .filter((value) => !Number.isNaN(value));
      if (days.length === 0) return $_('calendar.repeatsWeekly');
      const labels = days.map((day) => weekdayRecurrenceLabel(day)).filter(Boolean);
      return $_('calendar.repeatsWeeklyWithDays', { values: { days: labels.join(' ') } });
    }
    return $_('calendar.oneTime');
  }

  function recurrenceBadgeClass(entry: CalendarEntry) {
    if (entry.recurrence_type === 'weekly') return 'bg-indigo-100 text-indigo-700 border-indigo-200';
    if (entry.recurrence_type === 'daily') return 'bg-sky-100 text-sky-700 border-sky-200';
    return 'bg-slate-100 text-slate-500 border-slate-200';
  }

  function typeBadgeClass(type: string) {
    if (type === 'event') return 'bg-sky-100 text-sky-700 border-sky-200';
    return 'bg-emerald-100 text-emerald-700 border-emerald-200';
  }

  function statusBadgeClass(status: string) {
    if (status === 'approved') return 'bg-slate-900 text-white border-slate-900';
    if (status === 'pending') return 'bg-amber-100 text-amber-700 border-amber-200';
    if (status === 'rejected') return 'bg-rose-100 text-rose-700 border-rose-200';
    return 'bg-slate-100 text-slate-500 border-slate-200';
  }

  function statusLabel(status: string) {
    if (status === 'approved') return $_('calendar.completed');
    if (status === 'pending') return $_('calendar.pendingApproval');
    if (status === 'rejected') return $_('calendar.rejected');
    return status;
  }

  function entryPointsLabel(entry: CalendarEntry) {
    if (!entry.is_rewardable || !entry.points_value) return '';
    return $_('calendar.pointsCount', { values: { count: entry.points_value } });
  }

  function cleanDescription(entry: CalendarEntry) {
    return entry.description || '';
  }

  function getSelectedChildLabel() {
    return children.find((child) => child.child.id.toString() === selectedChildId)?.child.display_name || $_('calendar.chooseChild');
  }

  function weekdayRecurrenceLabel(value: number) {
    if (value === 0) return $_('calendar.weekdayMondayShort');
    if (value === 1) return $_('calendar.weekdayTuesdayShort');
    if (value === 2) return $_('calendar.weekdayWednesdayShort');
    if (value === 3) return $_('calendar.weekdayThursdayShort');
    if (value === 4) return $_('calendar.weekdayFridayShort');
    if (value === 5) return $_('calendar.weekdaySaturdayShort');
    if (value === 6) return $_('calendar.weekdaySundayShort');
    return '';
  }

  function normalizePointsValue(raw: string | number) {
    const text = typeof raw === 'number' ? `${raw}` : raw.trim();
    if (!text) return null;

    const value = Number(text);
    if (!Number.isInteger(value) || value < 1) return null;
    return value;
  }

  function defaultForm(childId = selectedChildId): FormState {
    return {
      child_id: childId || '',
      title: '',
      description: '',
      entry_type: 'task',
      start_date: selectedDate,
      start_time: '',
      duration_minutes: '',
      recurrence_type: 'none',
      recurrence_days: [],
      is_rewardable: false,
      points_value: ''
    };
  }

  function parseRecurrenceDays(value: string | null) {
    if (!value) return [];
    return value
      .split(',')
      .map((item) => Number(item))
      .filter((item) => Number.isInteger(item) && item >= 0 && item <= 6);
  }

  function getErrorStatus(error: unknown) {
    if (!error || typeof error !== 'object') return null;
    const status = (error as { status?: unknown }).status;
    return typeof status === 'number' ? status : null;
  }

  function clearModal() {
    modalOpen = false;
    editingEntryId = null;
    formError = null;
    form = defaultForm();
  }

  function openCreateModal() {
    const childId = selectedChildId || children[0]?.child.id?.toString() || '';
    form = defaultForm(childId);
    form.start_date = selectedDate;
    modalOpen = true;
    editingEntryId = null;
    formError = null;
  }

  function openEditModal(item: CalendarOccurrence) {
    editingEntryId = item.entry.id;
    form = {
      child_id: item.entry.child_id.toString(),
      title: item.entry.title,
      description: cleanDescription(item.entry),
      entry_type: item.entry.entry_type === 'event' ? 'event' : 'task',
      start_date: item.entry.start_date,
      start_time: item.entry.start_time ? item.entry.start_time.slice(0, 5) : '',
      duration_minutes: item.entry.duration_minutes ? item.entry.duration_minutes.toString() : '',
      recurrence_type:
        item.entry.recurrence_type === 'daily' || item.entry.recurrence_type === 'weekly'
          ? item.entry.recurrence_type
          : 'none',
      recurrence_days: parseRecurrenceDays(item.entry.recurrence_days),
      is_rewardable: item.entry.is_rewardable,
      points_value: item.entry.points_value ? item.entry.points_value.toString() : ''
    };
    modalOpen = true;
    formError = null;
  }

  function selectedWeekdayValue() {
    const day = parseDateInput(selectedDate).getDay();
    return day === 0 ? 6 : day - 1;
  }

  function dateForWeekday(weekdayValue: number) {
    const match = getWeekDates(selectedDate).find((weekDate) => {
      const day = parseDateInput(weekDate).getDay();
      return (day === 0 ? 6 : day - 1) === weekdayValue;
    });
    return match || selectedDate;
  }

  function newSchoolRow(seed: Partial<SchoolRow> = {}): SchoolRow {
    const key = `school-row-${nextSchoolRowKey}`;
    nextSchoolRowKey += 1;
    return {
      key,
      id: seed.id ?? null,
      class_name: seed.class_name ?? '',
      needed_item: seed.needed_item ?? ''
    };
  }

  function schoolRowsFromItems(items: SchoolItem[]) {
    return items
      .slice()
      .sort((a, b) => a.sort_order - b.sort_order || a.id - b.id)
      .map((item) => ({
        key: `school-item-${item.id}`,
        id: item.id,
        class_name: item.class_name,
        needed_item: item.needed_item || ''
      }));
  }

  async function fetchSchoolItems(childId: string, weekdayValue: number) {
    if (!childId) return [];
    const query = new URLSearchParams({
      child_id: childId,
      weekday: weekdayValue.toString()
    });
    const response = await api.get(`/school-items?${query.toString()}`);
    return Array.isArray(response) ? response : [];
  }

  function applySchoolRows(items: SchoolItem[]) {
    schoolExistingRows = schoolRowsFromItems(items);
    schoolRows = schoolExistingRows.length > 0
      ? schoolExistingRows.map((row) => ({ ...row }))
      : [newSchoolRow()];
  }

  async function loadSchoolRows() {
    schoolError = null;
    schoolLoading = true;
    try {
      const items = await fetchSchoolItems(schoolChildId, schoolWeekday);
      applySchoolRows(items);
    } catch (e) {
      schoolExistingRows = [];
      schoolRows = [newSchoolRow()];
      schoolError = e instanceof Error ? e.message : $_('calendar.unableToLoadSchoolItems');
    } finally {
      schoolLoading = false;
    }
  }

  async function openSchoolModal() {
    schoolChildId = selectedChildId || children[0]?.child.id?.toString() || '';
    schoolWeekday = selectedWeekdayValue();
    schoolError = null;
    schoolModalOpen = true;
    await loadSchoolRows();
  }

  function closeSchoolModal() {
    schoolModalOpen = false;
    schoolSaving = false;
    schoolError = null;
    schoolLoading = false;
    schoolRows = [];
    schoolExistingRows = [];
  }

  function addSchoolRow() {
    const row = newSchoolRow();
    schoolRows = [...schoolRows, row];
    requestAnimationFrame(() => {
      document.getElementById(`${row.key}-class`)?.focus();
    });
  }

  function removeSchoolRow(key: string) {
    schoolRows = schoolRows.filter((row) => row.key !== key);
    if (schoolRows.length === 0) {
      schoolRows = [newSchoolRow()];
    }
  }

  function updateSchoolRow(key: string, field: 'class_name' | 'needed_item', value: string) {
    schoolRows = schoolRows.map((row) => (row.key === key ? { ...row, [field]: value } : row));
  }

  async function saveSchoolRows(event: SubmitEvent) {
    event.preventDefault();
    schoolError = null;

    if (!schoolChildId) {
      schoolError = $_('calendar.selectChildFirst');
      return;
    }

    const rowsToSave = schoolRows
      .map((row) => ({
        id: row.id,
        class_name: row.class_name.trim(),
        needed_item: row.needed_item.trim()
      }))
      .filter((row) => row.class_name || row.needed_item);

    if (rowsToSave.some((row) => !row.class_name)) {
      schoolError = $_('calendar.rowNeedsClass');
      return;
    }

    try {
      schoolSaving = true;
      const savedItems = await api.put(`/school-items?child_id=${schoolChildId}&weekday=${schoolWeekday}`, rowsToSave);
      applySchoolRows(Array.isArray(savedItems) ? savedItems : []);
      closeSchoolModal();
      calendarNotice = $_('calendar.schoolItemsSaved');
    } catch (e) {
      if (e instanceof Error && getErrorStatus(e) === 401) {
        schoolError = $_('calendar.sessionExpired');
        calendarNotice = $_('calendar.sessionExpired');
      } else {
        schoolError = e instanceof Error ? e.message : $_('calendar.unableToSaveSchoolItems');
      }
    } finally {
      schoolSaving = false;
    }
  }

  async function loadChildren() {
    const response = await api.get('/children/');
    children = Array.isArray(response) ? response : [];

    if (!selectedChildId && children.length > 0) {
      selectedChildId = children[0].child.id.toString();
    }
  }

  async function loadCalendar() {
    if (!selectedChildId) {
      calendarItems = [];
      return;
    }

    const weekDates = getWeekDates(selectedDate);
    const fromDate = weekDates[0];
    const toDate = weekDates[weekDates.length - 1];

    const query = new URLSearchParams({
      child_id: selectedChildId,
      from_date: fromDate,
      to_date: toDate
    });

    loadingCalendar = true;
    try {
      const response = await api.get(`/calendar?${query.toString()}`);
      calendarItems = Array.isArray(response) ? response : [];
    } finally {
      loadingCalendar = false;
    }
  }

  async function loadPage() {
    try {
      loading = true;
      error = null;
      await loadChildren();
      await loadCalendar();
    } catch (e) {
      error = e instanceof Error ? e.message : $_('calendar.unableToLoadCalendar');
    } finally {
      loading = false;
    }
  }

  async function refreshCalendar() {
    if (!selectedChildId) {
      calendarItems = [];
      return;
    }

    try {
      await loadCalendar();
    } catch (e) {
      calendarNotice = e instanceof Error ? e.message : $_('calendar.unableToLoadCalendar');
    }
  }

  async function changeSelectedDate(offset: number) {
    selectedDate = addDays(selectedDate, offset);
    await refreshCalendar();
  }

  async function setToday() {
    selectedDate = dateToInputValue(new Date());
    viewMode = 'today';
    await refreshCalendar();
  }

  async function handleChildChange(event: Event) {
    const target = event.currentTarget as HTMLSelectElement;
    selectedChildId = target.value;
    await refreshCalendar();
  }

  async function handleSchoolChildChange(event: Event) {
    const target = event.currentTarget as HTMLSelectElement;
    schoolChildId = target.value;
    await loadSchoolRows();
  }

  async function handleSchoolWeekdayChange(value: number) {
    schoolWeekday = value;
    await loadSchoolRows();
  }

  async function saveEntry(event: SubmitEvent) {
    event.preventDefault();
    formError = null;

    const title = form.title.trim();
    const description = form.description.trim();
    const childId = Number(form.child_id);
    const duration = form.duration_minutes.trim() ? Number(form.duration_minutes) : null;
    const points = normalizePointsValue(form.points_value);

    if (!selectedChildId && !childId) {
      formError = $_('calendar.selectChildFirst');
      return;
    }

    if (!title) {
      formError = $_('calendar.titleRequired');
      return;
    }

    if (!form.start_date) {
      formError = $_('calendar.startDateRequired');
      return;
    }

    if (duration !== null && (!Number.isInteger(duration) || duration <= 0)) {
      formError = $_('calendar.durationPositive');
      return;
    }

    if (form.entry_type === 'task' && form.is_rewardable && points === null) {
      formError = $_('calendar.validationPointsRequired');
      return;
    }

    if (form.recurrence_type === 'weekly' && form.recurrence_days.length === 0) {
      formError = $_('calendar.validationWeeklyNeedsDay');
      return;
    }

    const payload = {
      title,
      description: description || null,
      entry_type: form.entry_type,
      start_date: form.start_date,
      start_time: form.start_time || null,
      duration_minutes: duration,
      recurrence_type: form.recurrence_type,
      recurrence_days: form.recurrence_type === 'weekly' ? [...form.recurrence_days].sort((a, b) => a - b).join(',') : null,
      is_rewardable: form.entry_type === 'task' ? form.is_rewardable : false,
      points_value: form.entry_type === 'task' && form.is_rewardable ? points : null,
      is_active: true,
      child_id: childId || Number(selectedChildId)
    };

    try {
      saving = true;
      if (editingEntryId) {
        const updatePayload = { ...payload };
        delete (updatePayload as Record<string, unknown>).child_id;
        await api.patch(`/calendar/${editingEntryId}`, updatePayload);
      } else {
        await api.post('/calendar', payload);
      }

      await refreshCalendar();
      clearModal();
    } catch (e) {
      if (e instanceof Error && getErrorStatus(e) === 401) {
        formError = $_('calendar.sessionExpired');
        calendarNotice = $_('calendar.sessionExpired');
      } else {
        formError = e instanceof Error ? e.message : $_('calendar.unableToSave');
      }
    } finally {
      saving = false;
    }
  }

  async function disableEntry(item: CalendarOccurrence) {
    if (!confirm($_('calendar.disableConfirm', { values: { title: item.entry.title } }))) return;

    try {
      await api.delete(`/calendar/${item.entry.id}`);
      if (editingEntryId === item.entry.id) {
        clearModal();
      }
      await refreshCalendar();
    } catch (e) {
      const status = e instanceof Error ? getErrorStatus(e) : null;
      if (status === 401) {
        calendarNotice = $_('calendar.sessionExpired');
      } else if (status === 404) {
        calendarNotice = $_('calendar.itemAlreadyRemoved');
        await refreshCalendar();
      } else {
        calendarNotice = e instanceof Error ? e.message : $_('calendar.unableToDisable');
      }
    }
  }

  async function completeEntry(item: CalendarOccurrence) {
    try {
      await api.post(`/calendar/${item.entry.id}/complete?occurrence_date=${item.occurrence_date}`, {});
      await refreshCalendar();
    } catch (e) {
      const status = e instanceof Error ? getErrorStatus(e) : null;
      if (status === 401) {
        calendarNotice = $_('calendar.sessionExpired');
      } else if (status === 404) {
        calendarNotice = $_('calendar.itemNoLongerAvailable');
        await refreshCalendar();
      } else {
        calendarNotice = e instanceof Error ? e.message : $_('calendar.unableToComplete');
      }
    }
  }

  async function approveCompletion(item: CalendarOccurrence) {
    if (!item.completion) return;
    try {
      await api.post(`/calendar/completions/${item.completion.id}/approve`, {});
      await refreshCalendar();
    } catch (e) {
      const status = e instanceof Error ? getErrorStatus(e) : null;
      if (status === 401) {
        calendarNotice = $_('calendar.sessionExpired');
      } else if (status === 404) {
        calendarNotice = $_('calendar.completionAlreadyHandled');
        await refreshCalendar();
      } else {
        calendarNotice = e instanceof Error ? e.message : $_('calendar.unableToApprove');
      }
    }
  }

  async function rejectCompletion(item: CalendarOccurrence) {
    if (!item.completion) return;
    try {
      await api.post(`/calendar/completions/${item.completion.id}/reject`, {});
      await refreshCalendar();
    } catch (e) {
      const status = e instanceof Error ? getErrorStatus(e) : null;
      if (status === 401) {
        calendarNotice = $_('calendar.sessionExpired');
      } else if (status === 404) {
        calendarNotice = $_('calendar.completionAlreadyHandled');
        await refreshCalendar();
      } else {
        calendarNotice = e instanceof Error ? e.message : $_('calendar.unableToReject');
      }
    }
  }

  function toggleWeekday(day: number) {
    if (form.recurrence_days.includes(day)) {
      form.recurrence_days = form.recurrence_days.filter((value) => value !== day);
      return;
    }

    form.recurrence_days = [...form.recurrence_days, day].sort((a, b) => a - b);
  }

  function toggleRewardable(nextType: string) {
    form.entry_type = nextType === 'event' ? 'event' : 'task';
    if (form.entry_type === 'event') {
      form.is_rewardable = false;
      form.points_value = '';
    }
    formError = null;
  }

  function setRewardable(enabled: boolean) {
    form.is_rewardable = enabled;
    if (!enabled) {
      form.points_value = '';
    }
    formError = null;
  }

  function visibleDates() {
    return viewMode === 'today' ? [selectedDate] : getWeekDates(selectedDate);
  }

  function itemsForDate(date: string) {
    return calendarItems.filter((item) => item.occurrence_date === date);
  }

  function pendingItems() {
    return calendarItems.filter((item) => item.completion?.status === 'pending');
  }

  onMount(() => {
    void loadPage();
  });
</script>

<svelte:head>
  <title>{$_('calendar.eyebrow')}</title>
</svelte:head>

<div class="min-h-dvh max-w-full overflow-x-hidden bg-slate-50 pb-[calc(4rem+var(--safe-bottom))]">
  {#if loading}
    <div class="flex justify-center py-24">
      <div class="flex flex-col items-center gap-4">
        <div class="w-12 h-12 animate-spin rounded-full border-4 border-slate-300 border-t-hero"></div>
        <p class="text-[10px] font-black uppercase tracking-[0.3em] text-slate-400">{$_('calendar.loadingTitle')}</p>
      </div>
    </div>
  {:else if error}
    <div class="mx-auto max-w-xl px-4 py-20">
      <div class="card border border-rose-100 bg-white p-8 text-center shadow-xl">
        <div class="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-rose-100 text-rose-600">
          <CalendarDays size={32} />
        </div>
        <h1 class="text-2xl font-black text-slate-950">{$_('calendar.errorTitle')}</h1>
        <p class="mt-3 break-words text-slate-600">{error}</p>
        <button type="button" class="btn-hero mt-8 w-full rounded-2xl px-6 py-4" onclick={loadPage}>{$_('calendar.tryAgain')}</button>
      </div>
    </div>
  {:else}
    <section class="border-b border-slate-200 bg-white">
      <div class="mx-auto max-w-7xl px-3 py-5 sm:px-4 md:px-6 md:py-8">
        <div class="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div class="min-w-0">
            <div class="mb-3 inline-flex max-w-full items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-2 text-[10px] font-black uppercase tracking-[0.18em] text-slate-500 sm:tracking-[0.24em]">
              <CalendarDays size={14} />
              {$_('calendar.eyebrow')}
            </div>
            <h1 class="break-words text-3xl font-black tracking-tight text-slate-950 md:text-5xl">{$_('calendar.heading')}</h1>
            <p class="mt-3 max-w-2xl text-sm font-medium leading-6 text-slate-500 md:text-base">
              {$_('calendar.intro')}
            </p>
          </div>

          <div class="flex w-full min-w-0 flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center lg:w-auto lg:justify-end">
            <a href="/parent" class="inline-flex w-full min-w-0 items-center justify-center gap-2 rounded-2xl border border-hero/15 bg-hero/10 px-4 py-3 text-xs font-black uppercase tracking-[0.14em] text-hero shadow-sm transition hover:border-hero/30 hover:bg-hero/15 hover:shadow-md sm:w-auto sm:tracking-[0.18em]">
              <ArrowLeft size={16} />
              {$_('calendar.backToParentDashboard')}
            </a>
            <div class="grid w-full grid-cols-2 rounded-2xl border border-slate-200 bg-slate-50 p-1 sm:w-auto">
              <button
                type="button"
                class={`rounded-xl px-4 py-3 text-xs font-black uppercase tracking-[0.14em] transition sm:tracking-[0.18em] ${viewMode === 'today' ? 'bg-slate-900 text-white shadow-sm' : 'text-slate-500 hover:text-slate-900'}`}
                onclick={() => (viewMode = 'today')}
              >
                {$_('calendar.today')}
              </button>
              <button
                type="button"
                class={`rounded-xl px-4 py-3 text-xs font-black uppercase tracking-[0.14em] transition sm:tracking-[0.18em] ${viewMode === 'week' ? 'bg-slate-900 text-white shadow-sm' : 'text-slate-500 hover:text-slate-900'}`}
                onclick={() => (viewMode = 'week')}
              >
                {$_('calendar.week')}
              </button>
            </div>
            <button
              type="button"
              class="inline-flex w-full min-w-0 items-center justify-center gap-2 rounded-2xl bg-slate-900 px-5 py-4 text-xs font-black uppercase tracking-[0.14em] text-white shadow-lg shadow-slate-200 transition hover:-translate-y-0.5 hover:shadow-xl sm:w-auto sm:tracking-[0.2em]"
              onclick={openCreateModal}
            >
              <Plus size={16} />
              {$_('calendar.addScheduleItem')}
            </button>
            <button
              type="button"
              class="inline-flex w-full min-w-0 items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-5 py-4 text-xs font-black uppercase tracking-[0.14em] text-slate-700 shadow-sm transition hover:border-slate-300 hover:shadow-md sm:w-auto sm:tracking-[0.18em]"
              onclick={openSchoolModal}
            >
              <CalendarDays size={16} />
              {$_('calendar.schoolBooksClasses')}
            </button>
          </div>
        </div>

        <div class="mt-6 grid gap-4 lg:grid-cols-[minmax(0,1.25fr)_minmax(0,0.75fr)]">
          <div class="rounded-3xl border border-slate-200 bg-slate-50 p-4 md:p-5">
            <div class="flex flex-col gap-4 md:flex-row md:flex-wrap md:items-end md:justify-between">
              <div class="min-w-0 md:flex-1">
                <p class="text-[10px] font-black uppercase tracking-[0.24em] text-slate-400">{$_('calendar.childLabel')}</p>
                <div class="mt-2 flex min-w-0 flex-col gap-2 sm:flex-row sm:items-center sm:gap-3">
                  <select
                    class="w-full min-w-0 flex-1 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-bold text-slate-900 shadow-sm focus:border-slate-400 focus:outline-none"
                    bind:value={selectedChildId}
                    onchange={handleChildChange}
                    disabled={children.length === 0}
                  >
                    {#if children.length === 0}
                      <option value="">{$_('calendar.noChildrenAvailable')}</option>
                    {:else}
                      {#each children as child}
                        <option value={child.child.id.toString()}>{child.child.display_name}</option>
                      {/each}
                    {/if}
                  </select>
                  <div class="inline-flex max-w-full items-center gap-2 overflow-hidden rounded-full bg-white px-3 py-2 text-[10px] font-black uppercase tracking-[0.14em] text-slate-600 shadow-sm sm:shrink-0 sm:tracking-[0.18em]">
                    <Sparkles size={12} />
                    <span class="min-w-0 truncate">{getSelectedChildLabel()}</span>
                  </div>
                </div>
              </div>

              <div class="min-w-0 md:flex-1">
                <p class="text-[10px] font-black uppercase tracking-[0.24em] text-slate-400">{$_('calendar.selectedDateLabel')}</p>
                <div class="mt-2 grid min-w-0 grid-cols-[48px_minmax(0,1fr)_48px] items-center gap-2">
                  <button type="button" class="inline-flex h-12 w-12 items-center justify-center rounded-2xl border border-slate-200 bg-white text-slate-600 shadow-sm" aria-label={$_('calendar.previousDayAria')} onclick={() => changeSelectedDate(-1)}>
                    <ChevronLeft size={18} />
                  </button>
                  <input
                    type="date"
                    bind:value={selectedDate}
                    onchange={refreshCalendar}
                    class="w-full min-w-0 rounded-2xl border border-slate-200 bg-white px-2 py-3 text-sm font-bold text-slate-900 shadow-sm focus:border-slate-400 focus:outline-none sm:px-4"
                  />
                  <button type="button" class="inline-flex h-12 w-12 items-center justify-center rounded-2xl border border-slate-200 bg-white text-slate-600 shadow-sm" aria-label={$_('calendar.nextDayAria')} onclick={() => changeSelectedDate(1)}>
                    <ChevronRight size={18} />
                  </button>
                </div>
              </div>

              <button
                type="button"
                class="inline-flex w-full min-w-0 items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-xs font-black uppercase tracking-[0.14em] text-slate-700 shadow-sm transition hover:border-slate-300 md:w-auto md:tracking-[0.18em]"
                onclick={setToday}
              >
                <Sparkles size={16} />
                {$_('calendar.jumpToToday')}
              </button>
            </div>
          </div>

          <div class="rounded-3xl border border-slate-200 bg-white p-4 md:p-5">
            <div class="flex items-center justify-between gap-3">
              <div>
                <p class="text-[10px] font-black uppercase tracking-[0.24em] text-slate-400">{$_('calendar.selectedWeekLabel')}</p>
                <p class="mt-2 text-base font-black text-slate-950">{formatShortDate(selectedDate)}</p>
              </div>
              <span class="rounded-full border border-slate-200 bg-slate-50 px-3 py-2 text-[10px] font-black uppercase tracking-[0.18em] text-slate-500">
                {calendarItems.length} {$_('calendar.itemsLabel')}
              </span>
            </div>
            <p class="mt-3 text-sm font-medium text-slate-500">
              {viewMode === 'today' ? $_('calendar.showingSelectedDay') : $_('calendar.showingWeeklyAgenda')}
            </p>
          </div>
        </div>
      </div>
    </section>

    {#if calendarNotice}
      <div class="mx-auto max-w-7xl px-3 pt-4 sm:px-4 md:px-6">
        <div class="flex items-start justify-between gap-3 rounded-3xl border border-slate-200 bg-white px-4 py-3 text-sm font-bold text-slate-700 shadow-sm">
          <p class="min-w-0 break-words">{calendarNotice}</p>
          <button type="button" class="shrink-0 rounded-full bg-slate-100 px-3 py-1 text-[10px] font-black uppercase tracking-[0.16em] text-slate-500" onclick={() => (calendarNotice = null)}>
            {$_('calendar.dismiss')}
          </button>
        </div>
      </div>
    {/if}

    <main class="mx-auto max-w-full px-3 py-6 sm:px-4 md:max-w-7xl md:px-6 md:py-8">
      {#if children.length === 0}
        <div class="rounded-[2rem] border border-dashed border-slate-200 bg-white p-8 text-center shadow-sm md:p-12">
          <div class="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-slate-100 text-slate-400">
            <CalendarDays size={30} />
          </div>
          <h2 class="mt-5 text-2xl font-black text-slate-950">{$_('calendar.noChildrenTitle')}</h2>
          <p class="mx-auto mt-3 max-w-xl text-sm font-medium leading-6 text-slate-500">
            {$_('calendar.noChildrenText')}
          </p>
          <a href="/parent" class="mt-8 inline-flex items-center justify-center gap-2 rounded-2xl bg-hero px-5 py-4 text-xs font-black uppercase tracking-[0.18em] text-white shadow-lg shadow-hero/20">
            {$_('calendar.goToParentDashboard')}
          </a>
        </div>
      {:else}
        <div class="grid min-w-0 gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
          <section class="min-w-0 space-y-6">
            <div class="rounded-[2rem] border border-slate-200 bg-white p-4 shadow-sm md:p-5">
              <div class="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div class="min-w-0">
                  <p class="text-[10px] font-black uppercase tracking-[0.24em] text-slate-400">{$_('calendar.weeklyStripLabel')}</p>
                  <h2 class="mt-1 text-xl font-black text-slate-950">{$_('calendar.moveThroughWeek')}</h2>
                </div>
                <span class="w-fit rounded-full bg-slate-100 px-3 py-2 text-[10px] font-black uppercase tracking-[0.18em] text-slate-500">
                  {$_('calendar.sundayStart')}
                </span>
              </div>

              <div class="grid grid-cols-7 gap-1 sm:gap-2">
                {#each getWeekDates(selectedDate) as weekDate}
                  {@const dayItems = itemsForDate(weekDate)}
                  <button
                    type="button"
                    class={`min-w-0 rounded-2xl border px-1.5 py-2 text-center transition sm:px-3 sm:py-3 ${weekDate === selectedDate ? 'border-slate-900 bg-slate-900 text-white shadow-lg shadow-slate-200' : 'border-slate-200 bg-slate-50 text-slate-700 hover:border-slate-300 hover:bg-white'}`}
                    onclick={async () => {
                      selectedDate = weekDate;
                      await refreshCalendar();
                    }}
                  >
                    <div class="text-[10px] font-black uppercase tracking-normal opacity-70 sm:tracking-[0.16em]">{formatWeekdayLetter(weekDate)}</div>
                    <div class="mt-1 text-lg font-black leading-none sm:mt-2">{parseDateInput(weekDate).getDate()}</div>
                    <div class="mt-2 flex items-center justify-center gap-1 text-[9px] font-black uppercase tracking-normal text-current sm:text-[10px]">
                      <span class={`h-1.5 w-1.5 rounded-full ${dayItems.length > 0 ? 'bg-current' : 'bg-transparent'}`}></span>
                      <span>{dayItems.length}</span>
                      {#if dayItems.some((item) => item.completion?.status === 'pending')}
                        <span class="h-1.5 w-1.5 rounded-full bg-amber-400"></span>
                      {/if}
                    </div>
                    {#if isToday(weekDate)}
                      <div class={`mx-auto mt-1 h-1 w-5 rounded-full ${weekDate === selectedDate ? 'bg-white/60' : 'bg-slate-900/30'}`}></div>
                    {/if}
                  </button>
                {/each}
              </div>
            </div>

            {#if pendingItems().length > 0}
              <section class="rounded-[2rem] border border-amber-200 bg-amber-50/70 p-4 shadow-sm md:p-5">
                <div class="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div class="min-w-0">
                    <p class="text-[10px] font-black uppercase tracking-[0.24em] text-amber-600">{$_('calendar.pendingApprovals')}</p>
                    <h2 class="mt-1 text-xl font-black text-slate-950">{$_('calendar.waitingForReview', { values: { count: pendingItems().length } })}</h2>
                  </div>
                  <div class="rounded-full bg-white px-3 py-2 text-[10px] font-black uppercase tracking-[0.18em] text-amber-700">
                    {$_('calendar.parentReview')}
                  </div>
                </div>

                <div class="space-y-3">
                  {#each pendingItems() as item}
                    <article class="rounded-[1.75rem] border border-amber-200 bg-white p-4 md:p-5 shadow-sm">
                      <div class="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                        <div class="min-w-0 flex-1">
                          <div class="mb-3 flex flex-wrap items-center gap-2">
                            <span class={`inline-flex items-center rounded-full border px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.18em] ${typeBadgeClass(item.entry.entry_type)}`}>
                              {item.entry.entry_type === 'event' ? $_('calendar.eventType') : $_('calendar.taskType')}
                            </span>
                            {#if item.entry.is_rewardable && item.entry.entry_type === 'task'}
                              <span class="inline-flex items-center rounded-full border border-amber-200 bg-amber-100 px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.18em] text-amber-700">
                                {entryPointsLabel(item.entry)}
                              </span>
                            {/if}
                            <span class={`inline-flex items-center rounded-full border px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.18em] ${statusBadgeClass(item.completion?.status || '')}`}>
                              {statusLabel(item.completion?.status || '')}
                            </span>
                          </div>

                          <h3 class="text-lg font-black text-slate-950 break-words">{item.entry.title}</h3>
                          {#if cleanDescription(item.entry)}
                            <p class="mt-2 text-sm font-medium leading-6 text-slate-600 break-words">{cleanDescription(item.entry)}</p>
                          {/if}

                          <div class="mt-3 flex flex-wrap gap-2 text-[11px] font-black uppercase tracking-[0.16em] text-slate-500">
                            <span class="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-1">
                              <Clock3 size={12} />
                              {formatShortDate(item.occurrence_date)}
                            </span>
                            <span class="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-1">
                              <Repeat2 size={12} />
                              {recurrenceLabel(item.entry)}
                            </span>
                            {#if item.entry.start_time || item.entry.duration_minutes}
                              <span class="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-1">
                                {formatTime(item.entry.start_time)}
                                {#if formatDuration(item.entry.duration_minutes)}
                                  <span class="opacity-60">•</span>
                                  {formatDuration(item.entry.duration_minutes)}
                                {/if}
                              </span>
                            {/if}
                          </div>
                        </div>

                        <div class="grid w-full grid-cols-1 gap-2 sm:w-auto sm:grid-cols-2 md:flex md:shrink-0 md:flex-wrap">
                          <button type="button" class="inline-flex items-center justify-center gap-2 rounded-2xl bg-emerald-600 px-4 py-3 text-xs font-black uppercase tracking-[0.14em] text-white shadow-sm sm:tracking-[0.18em]" onclick={() => approveCompletion(item)}>
                            <Check size={16} />
                            {$_('common.approve')}
                          </button>
                          <button type="button" class="inline-flex items-center justify-center gap-2 rounded-2xl border border-rose-200 bg-white px-4 py-3 text-xs font-black uppercase tracking-[0.14em] text-rose-700 shadow-sm sm:tracking-[0.18em]" onclick={() => rejectCompletion(item)}>
                            <X size={16} />
                            {$_('common.reject')}
                          </button>
                        </div>
                      </div>
                    </article>
                  {/each}
                </div>
              </section>
            {/if}

            <section class="rounded-[2rem] border border-slate-200 bg-white p-4 shadow-sm md:p-5">
              <div class="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div class="min-w-0">
                  <p class="text-[10px] font-black uppercase tracking-[0.24em] text-slate-400">{$_('calendar.agenda')}</p>
                  <h2 class="mt-1 text-xl font-black text-slate-950">
                    {viewMode === 'today' ? $_('calendar.today') : $_('calendar.week')}
                  </h2>
                </div>
                <div class="flex w-fit items-center gap-2 rounded-full bg-slate-100 px-3 py-2 text-[10px] font-black uppercase tracking-[0.14em] text-slate-500 sm:tracking-[0.18em]">
                  <BadgeCheck size={14} />
                  {loadingCalendar ? $_('calendar.refreshing') : `${calendarItems.length} ${$_('calendar.occurrencesLabel')}`}
                </div>
              </div>

              <div class="space-y-4">
                {#each visibleDates() as day}
                  {@const dayItems = itemsForDate(day)}
                  <article class="overflow-hidden rounded-[1.75rem] border border-slate-200 bg-slate-50">
                    <div class="flex flex-col gap-3 border-b border-slate-200 bg-white px-4 py-4 sm:flex-row sm:items-center sm:justify-between md:px-5">
                      <div class="min-w-0">
                        <div class="flex flex-wrap items-center gap-2">
                          <h3 class="break-words text-lg font-black text-slate-950">{formatLongDate(day)}</h3>
                          {#if day === selectedDate}
                            <span class="rounded-full bg-slate-900 px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.18em] text-white">{$_('calendar.selected')}</span>
                          {/if}
                        </div>
                        <p class="mt-1 text-sm font-medium text-slate-500">
                          {dayItems.length === 0 ? $_('calendar.nothingScheduled') : $_('calendar.scheduledItems', { values: { count: dayItems.length } })}
                        </p>
                      </div>
                      <button
                        type="button"
                        class="inline-flex w-full items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-xs font-black uppercase tracking-[0.14em] text-slate-700 shadow-sm sm:w-auto sm:tracking-[0.18em]"
                        onclick={() => {
                          selectedDate = day;
                          viewMode = 'today';
                        }}
                      >
                        <Sparkles size={16} />
                        {$_('calendar.focusDay')}
                      </button>
                    </div>

                    <div class="space-y-3 p-4 md:p-5">
                      {#if dayItems.length === 0}
                        <div class="rounded-2xl border border-dashed border-slate-200 bg-white px-4 py-6 text-center">
                          <p class="text-sm font-black uppercase tracking-[0.2em] text-slate-400">{$_('calendar.noItemsYet')}</p>
                          <p class="mt-2 text-sm font-medium text-slate-500">{$_('calendar.addScheduleForDay')}</p>
                        </div>
                      {:else}
                        {#each dayItems as item}
                          <article class="rounded-[1.5rem] border border-slate-200 bg-white p-4 shadow-sm transition hover:shadow-md">
                            <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                              <div class="min-w-0 flex-1">
                                <div class="mb-3 flex flex-wrap items-center gap-2">
                                  <span class={`inline-flex items-center rounded-full border px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.18em] ${typeBadgeClass(item.entry.entry_type)}`}>
                                    {item.entry.entry_type === 'event' ? $_('calendar.eventType') : $_('calendar.taskType')}
                                  </span>
                                  {#if item.entry.is_rewardable && item.entry.entry_type === 'task'}
                                    <span class="inline-flex items-center rounded-full border border-amber-200 bg-amber-100 px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.18em] text-amber-700">
                                      {$_('calendar.rewardTask')}
                                    </span>
                                  {/if}
                                  {#if item.entry.is_rewardable && item.entry.points_value}
                                    <span class="inline-flex items-center rounded-full border border-amber-200 bg-amber-100 px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.18em] text-amber-700">
                                      {$_('calendar.pointsCount', { values: { count: item.entry.points_value } })}
                                    </span>
                                  {/if}
                                  <span class={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.14em] ${recurrenceBadgeClass(item.entry)} sm:tracking-[0.18em]`}>
                                    <Repeat2 size={12} />
                                    {item.entry.recurrence_type === 'none' ? $_('calendar.oneTime') : item.entry.recurrence_type === 'daily' ? $_('calendar.daily') : $_('calendar.weekly')}
                                  </span>
                                  {#if item.completion}
                                    <span class={`inline-flex items-center rounded-full border px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.18em] ${statusBadgeClass(item.completion.status)}`}>
                                      {statusLabel(item.completion.status)}
                                    </span>
                                  {/if}
                                </div>

                                <h4 class="text-xl font-black text-slate-950 break-words">{item.entry.title}</h4>
                                {#if cleanDescription(item.entry)}
                                  <p class="mt-2 max-w-3xl text-sm font-medium leading-6 text-slate-600 break-words">{cleanDescription(item.entry)}</p>
                                {/if}

                                <div class="mt-4 flex flex-wrap gap-2 text-[11px] font-black uppercase tracking-[0.16em] text-slate-500">
                                  <span class="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-1">
                                    <Clock3 size={12} />
                                    {formatTime(item.entry.start_time)}
                                    {#if formatDuration(item.entry.duration_minutes)}
                                      <span class="opacity-60">•</span>
                                      {formatDuration(item.entry.duration_minutes)}
                                    {/if}
                                  </span>
                                  <span class="inline-flex min-w-0 items-center gap-1 rounded-full bg-slate-100 px-2.5 py-1">
                                    <Repeat2 size={12} />
                                    <span class="min-w-0 break-words">{recurrenceLabel(item.entry)}</span>
                                  </span>
                                  <span class="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-1">
                                    <Sparkles size={12} />
                                    {formatShortDate(item.entry.start_date)}
                                  </span>
                                </div>
                              </div>

                              <div class="grid w-full grid-cols-1 gap-2 sm:grid-cols-3 lg:w-auto lg:min-w-[260px] lg:justify-end">
                                {#if !item.completion}
                                  <button type="button" class="inline-flex items-center justify-center gap-2 rounded-2xl bg-slate-900 px-4 py-3 text-xs font-black uppercase tracking-[0.14em] text-white shadow-sm sm:tracking-[0.18em]" onclick={() => completeEntry(item)}>
                                    <Check size={16} />
                                    {$_('calendar.complete')}
                                  </button>
                                {/if}
                                <button type="button" class="inline-flex items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-xs font-black uppercase tracking-[0.14em] text-slate-700 shadow-sm sm:tracking-[0.18em]" onclick={() => openEditModal(item)}>
                                  <PencilLine size={16} />
                                  {$_('calendar.edit')}
                                </button>
                                <button type="button" class="inline-flex items-center justify-center gap-2 rounded-2xl border border-rose-200 bg-white px-4 py-3 text-xs font-black uppercase tracking-[0.14em] text-rose-700 shadow-sm sm:tracking-[0.18em]" onclick={() => disableEntry(item)}>
                                  <Trash2 size={16} />
                                  {$_('calendar.disable')}
                                </button>
                              </div>
                            </div>
                          </article>
                        {/each}
                      {/if}
                    </div>
                  </article>
                {/each}
              </div>
            </section>
          </section>

          <aside class="space-y-6">
            <div class="rounded-[2rem] border border-slate-200 bg-white p-5 shadow-sm">
              <div class="flex items-start justify-between gap-3">
                <div>
                  <p class="text-[10px] font-black uppercase tracking-[0.24em] text-slate-400">{$_('calendar.parentView')}</p>
                  <h2 class="mt-1 text-xl font-black text-slate-950">{$_('calendar.overview')}</h2>
                </div>
                <div class="rounded-2xl bg-slate-900 px-3 py-2 text-[10px] font-black uppercase tracking-[0.18em] text-white">
                  {getSelectedChildLabel()}
                </div>
              </div>
              <div class="mt-4 space-y-3 text-sm text-slate-600">
                <div class="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                  <span class="font-bold text-slate-500">{$_('calendar.visibleOccurrences')}</span>
                  <span class="font-black text-slate-950">{calendarItems.length}</span>
                </div>
                <div class="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                  <span class="font-bold text-slate-500">{$_('calendar.pendingApprovalsCount')}</span>
                  <span class="font-black text-slate-950">{pendingItems().length}</span>
                </div>
                <div class="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                  <span class="font-bold text-slate-500">{$_('calendar.weekMode')}</span>
                  <span class="font-black text-slate-950">{viewMode === 'today' ? $_('calendar.day') : $_('calendar.week')}</span>
                </div>
              </div>
            </div>

          </aside>
        </div>
      {/if}
    </main>
  {/if}
</div>

{#if schoolModalOpen}
  <div class="fixed inset-0 z-[100] flex items-end justify-center bg-slate-900/60 p-0 md:items-center md:p-4">
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="absolute inset-0 backdrop-blur-sm" onclick={closeSchoolModal}></div>

    <div class="relative z-10 flex max-h-[calc(100dvh-var(--safe-top))] w-full flex-col overflow-hidden bg-white shadow-2xl md:max-h-[92dvh] md:max-w-2xl md:rounded-[2rem]">
      <div class="flex items-start justify-between gap-4 border-b border-slate-100 px-4 py-4 md:px-6 md:py-5">
        <div class="min-w-0">
          <p class="text-[10px] font-black uppercase tracking-[0.22em] text-slate-400">{$_('calendar.schoolModalTitle')}</p>
          <h2 class="mt-1 text-2xl font-black text-slate-950">{$_('calendar.schoolModalHeading')}</h2>
          <p class="mt-2 text-sm font-medium leading-6 text-slate-500">
            {$_('calendar.schoolModalIntro')}
          </p>
        </div>
        <button type="button" class="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-slate-100 text-slate-500 transition hover:bg-slate-200" onclick={closeSchoolModal}>
          <X size={18} />
        </button>
      </div>

      <form class="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 py-5 pb-[calc(1.25rem+var(--safe-bottom))] md:px-6 md:pb-5" onsubmit={saveSchoolRows}>
        {#if schoolError}
          <div class="mb-5 rounded-2xl border border-rose-100 bg-rose-50 px-4 py-3 text-sm font-bold text-rose-700">
            {schoolError}
          </div>
        {/if}

        <div class="grid gap-4 sm:grid-cols-2">
          <label class="block min-w-0">
            <span class="mb-2 block text-[10px] font-black uppercase tracking-[0.22em] text-slate-400">{$_('calendar.childLabel')}</span>
            <select
              class="w-full min-w-0 rounded-2xl border-2 border-slate-200 bg-slate-50 px-4 py-4 text-sm font-bold text-slate-900 focus:border-slate-400 focus:outline-none"
              bind:value={schoolChildId}
              onchange={handleSchoolChildChange}
            >
              {#each children as child}
                <option value={child.child.id.toString()}>{child.child.display_name}</option>
              {/each}
            </select>
          </label>

          <div class="min-w-0">
            <span class="mb-2 block text-[10px] font-black uppercase tracking-[0.22em] text-slate-400">{$_('calendar.weekdayLabel')}</span>
            <div class="grid grid-cols-7 gap-1">
              {#each SCHOOL_WEEKDAY_OPTIONS as day}
                <button
                  type="button"
                  class={`min-w-0 rounded-2xl border px-2 py-3 text-xs font-black uppercase transition ${schoolWeekday === day.value ? 'border-slate-900 bg-slate-900 text-white shadow-sm' : 'border-slate-200 bg-slate-50 text-slate-500'}`}
                  title={$_(day.name)}
                  onclick={() => handleSchoolWeekdayChange(day.value)}
                >
                  {$_(day.label)}
                </button>
              {/each}
            </div>
          </div>
        </div>

        <div class="mt-6 rounded-[1.75rem] border border-slate-200 bg-slate-50 p-3 md:p-4">
          <div class="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p class="text-sm font-black text-slate-950">{$_('calendar.classesAndItems')}</p>
              <p class="mt-1 text-xs font-medium text-slate-500">{$_('calendar.schoolExamples')}</p>
            </div>
            <button type="button" class="inline-flex w-full items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-xs font-black uppercase tracking-[0.14em] text-slate-700 sm:w-auto" onclick={addSchoolRow}>
              <Plus size={14} />
              {$_('calendar.addRow')}
            </button>
          </div>

          <div class="space-y-3">
            {#if schoolLoading && schoolRows.length === 0}
              <div class="rounded-2xl border border-dashed border-slate-200 bg-white px-4 py-8 text-center">
                <p class="text-sm font-black uppercase tracking-[0.18em] text-slate-400">{$_('calendar.loadingSchoolItems')}</p>
              </div>
            {/if}

            {#each schoolRows as row}
              <div class="grid gap-2 rounded-2xl border border-slate-200 bg-white p-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)_auto]">
                <label class="block min-w-0">
                  <span class="mb-1 block text-[10px] font-black uppercase tracking-[0.18em] text-slate-400">{$_('calendar.classLabel')}</span>
                  <input
                    id={`${row.key}-class`}
                    type="text"
                    value={row.class_name}
                    placeholder={$_('calendar.schoolClassPlaceholder')}
                    class="w-full min-w-0 rounded-xl border border-slate-200 bg-slate-50 px-3 py-3 text-sm font-bold text-slate-900 focus:border-slate-400 focus:outline-none"
                    oninput={(event) => updateSchoolRow(row.key, 'class_name', (event.currentTarget as HTMLInputElement).value)}
                  />
                </label>
                <label class="block min-w-0">
                  <span class="mb-1 block text-[10px] font-black uppercase tracking-[0.18em] text-slate-400">{$_('calendar.neededItemLabel')}</span>
                  <input
                    type="text"
                    value={row.needed_item}
                    placeholder={$_('calendar.schoolNeededItemPlaceholder')}
                    class="w-full min-w-0 rounded-xl border border-slate-200 bg-slate-50 px-3 py-3 text-sm font-bold text-slate-900 focus:border-slate-400 focus:outline-none"
                    oninput={(event) => updateSchoolRow(row.key, 'needed_item', (event.currentTarget as HTMLInputElement).value)}
                  />
                </label>
                <button type="button" class="inline-flex h-12 items-center justify-center rounded-xl border border-rose-200 bg-white px-3 text-xs font-black uppercase tracking-[0.14em] text-rose-700 sm:self-end" onclick={() => removeSchoolRow(row.key)}>
                  {$_('calendar.remove')}
                </button>
              </div>
            {/each}
          </div>
        </div>

        <div class="mt-5 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <button type="button" class="inline-flex items-center justify-center rounded-2xl border border-slate-200 bg-white px-5 py-4 text-xs font-black uppercase tracking-[0.18em] text-slate-700" onclick={closeSchoolModal}>
            {$_('calendar.cancel')}
          </button>
          <button type="submit" disabled={schoolSaving} class="inline-flex items-center justify-center gap-2 rounded-2xl bg-slate-900 px-5 py-4 text-xs font-black uppercase tracking-[0.18em] text-white disabled:opacity-60">
            <Check size={16} />
            {schoolSaving ? $_('calendar.saving') : $_('calendar.saveSchoolDay')}
          </button>
        </div>
      </form>
    </div>
  </div>
{/if}

{#if modalOpen}
  <div class="fixed inset-0 z-[100] flex items-end justify-center bg-slate-900/60 p-0 md:items-center md:p-4">
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="absolute inset-0 backdrop-blur-sm" onclick={clearModal}></div>

    <div class="relative z-10 flex h-[100dvh] max-h-[calc(100dvh-var(--safe-top))] w-full flex-col overflow-hidden bg-white shadow-2xl md:h-auto md:max-h-[92dvh] md:max-w-3xl md:rounded-[2rem]">
      <div class="flex items-start justify-between gap-4 border-b border-slate-100 px-4 py-4 md:px-6 md:py-5">
        <div class="min-w-0">
          <p class="text-[10px] font-black uppercase tracking-[0.24em] text-slate-400">{$_('calendar.scheduleModalLabel')}</p>
          <h2 class="mt-1 text-2xl font-black text-slate-950">{editingEntryId ? $_('calendar.editScheduleItem') : $_('calendar.addScheduleItemModal')}</h2>
          <p class="mt-2 text-sm font-medium text-slate-500">{$_('calendar.scheduleModalIntro')}</p>
        </div>
        <button type="button" class="inline-flex h-11 w-11 items-center justify-center rounded-2xl bg-slate-100 text-slate-500 transition hover:bg-slate-200" onclick={clearModal}>
          <X size={18} />
        </button>
      </div>

      <form class="flex min-h-0 flex-1 flex-col" onsubmit={saveEntry}>
        <div class="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 py-5 md:px-6">
          {#if formError}
            <div class="mb-5 rounded-2xl border border-rose-100 bg-rose-50 px-4 py-3 text-sm font-bold text-rose-700">
              {formError}
            </div>
          {/if}

          <div class="grid gap-5 md:grid-cols-2">
            <label class="block">
              <span class="mb-2 block text-[10px] font-black uppercase tracking-[0.22em] text-slate-400">{$_('calendar.childLabel')}</span>
              <select
                bind:value={form.child_id}
                class="w-full rounded-2xl border-2 border-slate-200 bg-slate-50 px-4 py-4 text-sm font-bold text-slate-900 focus:border-slate-400 focus:outline-none disabled:opacity-60"
                disabled={editingEntryId !== null}
              >
                <option value="">{$_('calendar.selectChild')}</option>
                {#each children as child}
                  <option value={child.child.id}>{child.child.display_name}</option>
                {/each}
              </select>
              {#if editingEntryId !== null}
                <p class="mt-2 text-xs font-medium text-slate-400">{$_('calendar.childChangesLocked')}</p>
              {/if}
            </label>

            <label class="block">
              <span class="mb-2 block text-[10px] font-black uppercase tracking-[0.22em] text-slate-400">{$_('calendar.titleLabel')}</span>
              <input
                bind:value={form.title}
                type="text"
                placeholder={$_('calendar.titlePlaceholder')}
                class="w-full rounded-2xl border-2 border-slate-200 bg-slate-50 px-4 py-4 text-sm font-bold text-slate-900 focus:border-slate-400 focus:outline-none"
              />
            </label>

            <label class="block md:col-span-2">
              <span class="mb-2 block text-[10px] font-black uppercase tracking-[0.22em] text-slate-400">{$_('calendar.descriptionLabel')}</span>
              <textarea
                bind:value={form.description}
                rows="3"
                placeholder={$_('calendar.descriptionPlaceholder')}
                class="w-full rounded-2xl border-2 border-slate-200 bg-slate-50 px-4 py-4 text-sm font-medium text-slate-900 focus:border-slate-400 focus:outline-none"
              ></textarea>
            </label>

            <div class="md:col-span-2">
              <span class="mb-2 block text-[10px] font-black uppercase tracking-[0.22em] text-slate-400">{$_('calendar.typeLabel')}</span>
              <div class="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  class={`rounded-2xl border px-4 py-4 text-sm font-black uppercase tracking-[0.18em] transition ${form.entry_type === 'task' ? 'border-emerald-300 bg-emerald-50 text-emerald-700' : 'border-slate-200 bg-slate-50 text-slate-500'}`}
                  onclick={() => toggleRewardable('task')}
                >
                  {$_('calendar.task')}
                </button>
                <button
                  type="button"
                  class={`rounded-2xl border px-4 py-4 text-sm font-black uppercase tracking-[0.18em] transition ${form.entry_type === 'event' ? 'border-sky-300 bg-sky-50 text-sky-700' : 'border-slate-200 bg-slate-50 text-slate-500'}`}
                  onclick={() => toggleRewardable('event')}
                >
                  {$_('calendar.event')}
                </button>
              </div>
            </div>

            <label class="block">
              <span class="mb-2 block text-[10px] font-black uppercase tracking-[0.22em] text-slate-400">{$_('calendar.startDate')}</span>
              <input
                bind:value={form.start_date}
                type="date"
                class="w-full rounded-2xl border-2 border-slate-200 bg-slate-50 px-4 py-4 text-sm font-bold text-slate-900 focus:border-slate-400 focus:outline-none"
              />
            </label>

            <label class="block">
              <span class="mb-2 block text-[10px] font-black uppercase tracking-[0.22em] text-slate-400">{$_('calendar.startTime')}</span>
              <input
                bind:value={form.start_time}
                type="time"
                class="w-full rounded-2xl border-2 border-slate-200 bg-slate-50 px-4 py-4 text-sm font-bold text-slate-900 focus:border-slate-400 focus:outline-none"
              />
            </label>

            <label class="block">
              <span class="mb-2 block text-[10px] font-black uppercase tracking-[0.22em] text-slate-400">{$_('calendar.durationMinutes')}</span>
              <input
                bind:value={form.duration_minutes}
                type="number"
                min="1"
                placeholder="30"
                class="w-full rounded-2xl border-2 border-slate-200 bg-slate-50 px-4 py-4 text-sm font-bold text-slate-900 focus:border-slate-400 focus:outline-none"
              />
            </label>

            <div>
              <span class="mb-2 block text-[10px] font-black uppercase tracking-[0.22em] text-slate-400">{$_('calendar.recurrence')}</span>
              <div class="grid grid-cols-3 gap-3">
                <button
                  type="button"
                  class={`rounded-2xl border px-4 py-4 text-xs font-black uppercase tracking-[0.18em] transition ${form.recurrence_type === 'none' ? 'border-slate-900 bg-slate-900 text-white' : 'border-slate-200 bg-slate-50 text-slate-500'}`}
                  onclick={() => (form.recurrence_type = 'none')}
                >
                  {$_('calendar.none')}
                </button>
                <button
                  type="button"
                  class={`rounded-2xl border px-4 py-4 text-xs font-black uppercase tracking-[0.18em] transition ${form.recurrence_type === 'daily' ? 'border-sky-300 bg-sky-50 text-sky-700' : 'border-slate-200 bg-slate-50 text-slate-500'}`}
                  onclick={() => (form.recurrence_type = 'daily')}
                >
                  {$_('calendar.daily')}
                </button>
                <button
                  type="button"
                  class={`rounded-2xl border px-4 py-4 text-xs font-black uppercase tracking-[0.18em] transition ${form.recurrence_type === 'weekly' ? 'border-indigo-300 bg-indigo-50 text-indigo-700' : 'border-slate-200 bg-slate-50 text-slate-500'}`}
                  onclick={() => (form.recurrence_type = 'weekly')}
                >
                  {$_('calendar.weekly')}
                </button>
              </div>
            </div>

            <div class="md:col-span-2">
              <span class="mb-2 block text-[10px] font-black uppercase tracking-[0.22em] text-slate-400">{$_('calendar.weekdays')}</span>
              <div class="grid grid-cols-4 gap-2 md:grid-cols-7">
                {#each WEEKDAY_OPTIONS as day}
                  <button
                    type="button"
                    class={`rounded-2xl border px-2 py-3 text-[10px] font-black uppercase tracking-[0.16em] transition ${form.recurrence_days.includes(day.value) ? 'border-slate-900 bg-slate-900 text-white' : 'border-slate-200 bg-slate-50 text-slate-500'}`}
                    onclick={() => toggleWeekday(day.value)}
                    disabled={form.recurrence_type !== 'weekly'}
                  >
                    {$_(day.label)}
                  </button>
                {/each}
              </div>
              {#if form.recurrence_type !== 'weekly'}
                <p class="mt-2 text-xs font-medium text-slate-400">{$_('calendar.weeklyRecurrenceHelp')}</p>
              {/if}
            </div>

            <div class="md:col-span-2">
              <span class="mb-2 block text-[10px] font-black uppercase tracking-[0.22em] text-slate-400">{$_('calendar.rewardSettings')}</span>
              <div class="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                {#if form.entry_type === 'task'}
                  <label class="flex items-center justify-between gap-4">
                    <div class="min-w-0">
                      <p class="text-sm font-black text-slate-900">{$_('calendar.rewardableTask')}</p>
                      <p class="mt-1 text-xs font-medium leading-5 text-slate-500">{$_('calendar.rewardTaskHelp')}</p>
                    </div>
                    <input
                      type="checkbox"
                      checked={form.is_rewardable}
                      onchange={(event) => setRewardable((event.currentTarget as HTMLInputElement).checked)}
                      class="h-5 w-5 rounded border-slate-300 text-slate-900 focus:ring-slate-400"
                    />
                  </label>

                  {#if form.is_rewardable}
                    <label class="mt-4 block">
                      <span class="mb-2 block text-[10px] font-black uppercase tracking-[0.22em] text-slate-400">{$_('calendar.points')}</span>
                      <input
                        bind:value={form.points_value}
                        type="number"
                        min="1"
                        placeholder="5"
                        class="w-full rounded-2xl border-2 border-slate-200 bg-white px-4 py-4 text-sm font-bold text-slate-900 focus:border-slate-400 focus:outline-none"
                      />
                    </label>
                  {/if}
                {:else}
                  <div class="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-medium text-slate-500">
                    {$_('calendar.eventNoPoints')}
                  </div>
                {/if}
              </div>
            </div>
          </div>
        </div>

        <div class="border-t border-slate-100 bg-white px-4 py-4 pb-[calc(1rem+var(--safe-bottom))] md:px-6 md:pb-4">
          <div class="flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-end">
            <button type="button" class="inline-flex items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-5 py-4 text-xs font-black uppercase tracking-[0.18em] text-slate-700" onclick={clearModal}>
            {$_('calendar.cancel')}
            </button>
            <button type="submit" disabled={saving} class="inline-flex items-center justify-center gap-2 rounded-2xl bg-slate-900 px-5 py-4 text-xs font-black uppercase tracking-[0.18em] text-white disabled:opacity-60">
              <Plus size={16} />
              {saving ? $_('calendar.saving') : editingEntryId ? $_('calendar.saveChanges') : $_('calendar.createItem')}
            </button>
          </div>
        </div>
      </form>
    </div>
  </div>
{/if}
