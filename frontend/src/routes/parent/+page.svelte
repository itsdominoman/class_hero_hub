<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import { AVATAR_OPTIONS, getAvatarAsset, hasAvatarAssetFile, normaliseAvatarKey } from '$lib/avatars';
  import { formatAllowanceAmount } from '$lib/currencies';
  import { _, locale } from 'svelte-i18n';
  import LanguageSelector from '$lib/components/LanguageSelector.svelte';
  import { 
    UserPlus, Award, Ban, Gift, Ticket, Wallet,
    LayoutDashboard, Settings, LogIn, Trophy, Clock, Check, X,
    Users, QrCode, Copy, RefreshCcw, Link2, CalendarDays
  } from 'lucide-svelte';

  let parent = $state<any>(null);
  let children = $state<any[]>([]);
  let redemptions = $state<any[]>([]);
  let rewards = $state<any[]>([]);
  let allowanceSummaries = $state<Record<number, AllowanceSummary>>({});
  let presets = $state<any[]>([]);
  let familyMembers = $state<FamilyMember[]>([]);
  let familyInvites = $state<any[]>([]);
  let familySettings = $state<FamilySettings | null>(null);
  let familySettingsForm = $state<{ week_start_day: WeekStartDay }>({ week_start_day: 'sunday' });
  let familySettingsSaving = $state(false);
  let familySettingsMessage = $state<string | null>(null);
  let familySettingsError = $state<string | null>(null);
  let familyGrownupRemovingId = $state<number | null>(null);
  let loading = $state(true);
  let loadingChildren = $state(false);
  let loadingFamilySettings = $state(false);
  let loadingSchoolPrep = $state(false);
  let schoolTodayByChild = $state<Record<number, SchoolItem[]>>({});
  let schoolTomorrowByChild = $state<Record<number, SchoolItem[]>>({});
  let error = $state<string | null>(null);
  let needsLogin = $state(false);

  // Modal State
  let activeModal = $state<any>(null); // { type: 'award' | 'penalty' | 'bank' | 'redeem' | 'presets', child: any }
  let modalForm = $state({
    points: 1,
    description: '',
    title: '',
    icon: '',
    email: '',
    jar: 'spending'
  });
  let modalLoading = $state(false);
  let modalError = $state<string | null>(null);
  let activeTab = $state('positive');
  let childModalTab = $state('points');
  let pointLogPeriod = $state<'day' | 'week' | 'year'>('week');
  let childCalendarById = $state<Record<number, CalendarOccurrence[]>>({});
  let childCalendarLoading = $state<Record<number, boolean>>({});
  let childCalendarError = $state<Record<number, string>>({});
  let childLedgerByKey = $state<Record<string, LedgerTransaction[]>>({});
  let childLedgerLoading = $state<Record<string, boolean>>({});
  let childLedgerError = $state<Record<string, string>>({});
  let childEditOpen = $state(false);
  let childEditLoading = $state(false);
  let childEditError = $state<string | null>(null);
  let childEditForm = $state({
    display_name: '',
    avatar_name: '',
    active: true
  });
  let editingPresetId = $state<number | null>(null);
  let editingRewardId = $state<number | null>(null);
  let rewardLoading = $state(false);
  let rewardError = $state<string | null>(null);
  let rewardForm = $state({
    title: '',
    description: '',
    icon: '',
    points: 20,
    is_active: true
  });
  let childLinkInvite = $state<any>(null);
  let childLinkQr = $state('');
  let childLinkLoading = $state(false);
  let childLinkError = $state<string | null>(null);
  let childLinkCopied = $state(false);
  let childDevices = $state<ChildDevice[]>([]);
  let childDevicesLoading = $state(false);
  let childDevicesError = $state<string | null>(null);
  let childDeviceUnlinkingId = $state<number | null>(null);
  let avatarImageErrors = $state<Record<number, boolean>>({});
  let pointAudioContext: AudioContext | null = null;

  const DEFAULT_EMOJIS = ['🪥', '📚', '🛏️', '⏰', '🧹', '🧺', '🍎', '🥦', '👍', '❤️', '⭐', '👑', '🎮', '🖥️', '📱', '😴', '😡', '🚫', '🧸', '🏃', '🎒', '✏️', '🧼', '🍽️'];

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

  type CalendarEntry = {
    id: number;
    title: string;
    description: string | null;
    entry_type: 'task' | 'event' | string;
    is_rewardable: boolean;
    points_value: number | null;
    start_time: string | null;
  };

  type CalendarOccurrence = {
    entry: CalendarEntry;
    occurrence_date: string;
    completion: {
      status: 'pending' | 'approved' | 'rejected' | string;
    } | null;
  };

  type LedgerTransaction = {
    jar: string;
    transaction_type: string;
    points: number;
    description: string;
    created_at: string;
    locked_until: string | null;
  };

  type ChildDevice = {
    id: number;
    child_id: number;
    created_at: string;
    expires_at: string;
    revoked_at: string | null;
    last_seen_at: string | null;
    is_active: boolean;
    label: string;
  };

  type WeekStartDay = 'monday' | 'tuesday' | 'wednesday' | 'thursday' | 'friday' | 'saturday' | 'sunday';

  type FamilySettings = {
    timezone: string;
    week_start_day: WeekStartDay;
  };

  type FamilyMember = {
    id: number;
    email: string;
    name: string | null;
    last_login_at: string | null;
    can_remove: boolean;
  };

  const WEEK_START_OPTIONS: WeekStartDay[] = [
    'sunday',
    'monday',
    'tuesday',
    'wednesday',
    'thursday',
    'friday',
    'saturday'
  ];

  type AllowanceSummary = {
    is_enabled: boolean;
    currency: string;
    currency_exponent: number;
    period: 'weekly' | 'monthly' | string;
    period_start: string;
    period_end: string;
    next_reset_at: string;
    allowance_enabled_at: string | null;
    point_value_display: string;
    point_goal: number;
    progress_ratio: number;
    progress_percent: number;
    maxed_for_period: boolean;
    raw_eligible_points: number;
    eligible_points: number;
    raw_earned_points_period: number;
    earned_points_period: number;
    earned_amount_minor: number;
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
    display_amount: string;
    display_max_amount: string;
    included_transaction_count: number;
  };

  const isAuthError = (message: string) =>
    message.toLowerCase().includes('not authenticated') ||
    message.toLowerCase().includes('invalid token') ||
    message.toLowerCase().includes('parent not found');

  function getPointAudioContext() {
    if (typeof window === 'undefined') return null;

    const AudioContextConstructor = window.AudioContext || (window as any).webkitAudioContext;
    if (!AudioContextConstructor) return null;

    if (!pointAudioContext) {
      pointAudioContext = new AudioContextConstructor();
    }

    return pointAudioContext;
  }

  function preparePointSound() {
    try {
      const context = getPointAudioContext();
      if (context?.state === 'suspended') {
        void context.resume().catch(() => {});
      }
    } catch {
      // Audio is optional and must never block point actions.
    }
  }

  function playTone(
    frequency: number,
    durationSeconds: number,
    type: OscillatorType = 'sine',
    gainValue = 0.035,
    endFrequency?: number
  ) {
    try {
      const context = getPointAudioContext();
      if (!context) return;
      if (context.state === 'suspended') {
        void context.resume().catch(() => {});
      }

      const startTime = context.currentTime;
      const oscillator = context.createOscillator();
      const gain = context.createGain();

      oscillator.type = type;
      oscillator.frequency.setValueAtTime(frequency, startTime);
      if (endFrequency) {
        oscillator.frequency.linearRampToValueAtTime(endFrequency, startTime + durationSeconds);
      }

      gain.gain.setValueAtTime(0.0001, startTime);
      gain.gain.exponentialRampToValueAtTime(gainValue, startTime + 0.015);
      gain.gain.exponentialRampToValueAtTime(0.0001, startTime + durationSeconds);

      oscillator.connect(gain).connect(context.destination);
      oscillator.start(startTime);
      oscillator.stop(startTime + durationSeconds + 0.03);
    } catch {
      // Ignore unavailable or blocked audio.
    }
  }

  function playPositiveSound() {
    playTone(880, 0.16, 'sine', 0.25);
    window.setTimeout(() => playTone(1175, 0.12, 'sine', 0.25), 70);
  }

  function playNegativeSound() {
    playTone(165, 0.24, 'sawtooth', 0.25, 110);
  }

  function getLocalDateValue(reference = new Date()) {
    const year = reference.getFullYear();
    const month = `${reference.getMonth() + 1}`.padStart(2, '0');
    const day = `${reference.getDate()}`.padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  function addDaysValue(days: number, reference = new Date()) {
    const next = new Date(reference);
    next.setDate(next.getDate() + days);
    return getLocalDateValue(next);
  }

  function schoolNeedLabel(item: SchoolItem) {
    const listedItem = (item?.needed_item || '').trim();
    if (listedItem) return listedItem;
    const title = item?.class_name?.trim();
    if (!title) return $_('parent.school.itemFallback');
    if (/p\.?\s*e\.?/i.test(title)) return $_('parent.school.gymClothesFallback');
    return $_('parent.school.classBookFallback', { values: { className: title } });
  }

  function formatAllowanceMinorAmount(minor: number, currency: string, exponent: number) {
    return formatAllowanceAmount(minor, currency, exponent);
  }

  function weekStartLabel(day: WeekStartDay) {
    switch (day) {
      case 'sunday':
        return $_('calendar.weekdaySundayShort');
      case 'monday':
        return $_('calendar.weekdayMondayShort');
      case 'tuesday':
        return $_('calendar.weekdayTuesdayShort');
      case 'wednesday':
        return $_('calendar.weekdayWednesdayShort');
      case 'thursday':
        return $_('calendar.weekdayThursdayShort');
      case 'friday':
        return $_('calendar.weekdayFridayShort');
      case 'saturday':
        return $_('calendar.weekdaySaturdayShort');
    }
  }

  async function loadSchoolPrep(childSummaries = children) {
    const nextSchoolItemsToday: Record<number, SchoolItem[]> = {};
    const nextSchoolItemsTomorrow: Record<number, SchoolItem[]> = {};
    if (!childSummaries.length) {
      schoolTodayByChild = {};
      schoolTomorrowByChild = {};
      return;
    }

    try {
      loadingSchoolPrep = true;
      await Promise.all(
        childSummaries.map(async (childSummary: any) => {
          const childId = childSummary.child.id;
          try {
            const [todayResponse, tomorrowResponse] = await Promise.all([
              api.get(`/school-items/today?child_id=${childId}&offset=0`),
              api.get(`/school-items/today?child_id=${childId}&offset=1`)
            ]);
            nextSchoolItemsToday[childId] = Array.isArray(todayResponse) ? todayResponse : [];
            nextSchoolItemsTomorrow[childId] = Array.isArray(tomorrowResponse) ? tomorrowResponse : [];
          } catch {
            nextSchoolItemsToday[childId] = [];
            nextSchoolItemsTomorrow[childId] = [];
          }
        })
      );
      schoolTodayByChild = nextSchoolItemsToday;
      schoolTomorrowByChild = nextSchoolItemsTomorrow;
    } finally {
      loadingSchoolPrep = false;
    }
  }

  async function loadDashboard() {
    try {
      loading = true;
      error = null;
      needsLogin = false;
      const [p, c, r, rw, pr, fm, fi] = await Promise.all([
        api.get('/me'),
        api.get('/children/'),
        api.get('/redemptions'),
        api.get('/rewards'),
        api.get('/presets/'),
        api.get('/family/grownups'),
        api.get('/family/invites')
      ]);
      parent = p;
      children = c;
      redemptions = r;
      rewards = rw;
      presets = pr;
      familyMembers = fm;
      familyInvites = fi;
      const allowanceEntries = await Promise.all(
        c.map(async (childSummary: any) => {
          try {
            const summary = await api.get(`/allowance/children/${childSummary.child.id}/summary`);
            return [childSummary.child.id, summary] as const;
          } catch {
            return [childSummary.child.id, null] as const;
          }
        })
      );
      allowanceSummaries = Object.fromEntries(allowanceEntries.filter((entry) => entry[1] !== null)) as Record<number, AllowanceSummary>;
      void loadSchoolPrep(c).catch((error) => {
        console.warn('Failed to load school prep', error);
      });
    } catch (e) {
      const message = e instanceof Error ? e['message'] : '';
      if (isAuthError(message)) {
        parent = null;
        children = [];
        needsLogin = true;
      } else {
        error = $_('parent.failedLoad');
      }
    } finally {
      loading = false;
    }
  }

  async function loadFamilySettings() {
    try {
      loadingFamilySettings = true;
      familySettingsError = null;
      familySettingsMessage = null;
      familyMembers = [];
      familyInvites = [];
      familySettings = null;
      const [fm, fi, settings] = await Promise.all([
        api.get('/family/grownups'),
        api.get('/family/invites'),
        api.get('/family/settings')
      ]);
      familyMembers = fm;
      familyInvites = fi;
      familySettings = settings;
      familySettingsForm = { week_start_day: settings.week_start_day };
    } catch (e) {
      familySettingsError = $_('parent.family.errorLoadSettings');
    } finally {
      loadingFamilySettings = false;
    }
  }

  async function saveFamilySettings() {
    try {
      familySettingsSaving = true;
      familySettingsError = null;
      familySettingsMessage = null;
      const updated = await api.patch('/family/settings', {
        week_start_day: familySettingsForm.week_start_day
      });
      familySettings = updated;
      familySettingsForm = { week_start_day: updated.week_start_day };
      familySettingsMessage = $_('parent.week.saved');
    } catch (e) {
      familySettingsError = $_('parent.family.errorSaveSettings');
    } finally {
      familySettingsSaving = false;
    }
  }

  async function addChild() {
    const childName = window.prompt($_('parent.childEdit.displayNamePrompt'));
    if (!childName || !childName.trim()) return;

    try {
      loadingChildren = true;
      error = null;
      await api.post('/children/', {
        display_name: childName.trim(),
        avatar_name: null,
        active: true
      });
      await loadDashboard();
    } catch (e) {
      error = $_('parent.errorAddChild');
    } finally {
      loadingChildren = false;
    }
  }

  function openModal(type: string, child: any) {
    activeModal = { type, child };
    activeTab = 'positive';
    childModalTab = 'points';
    pointLogPeriod = 'week';
    childEditOpen = false;
    childEditError = null;
    editingPresetId = null;
    modalForm = {
      points: 1,
      description: '',
      title: '',
      icon: '',
      email: '',
      jar: 'spending'
    };
    modalError = null;

    if (type === 'family' || type === 'calendar-week') {
      void loadFamilySettings();
    }

    if (type === 'picker' && child) {
      void ensureChildModalData(child);
    }
  }

  function closeModal() {
    activeModal = null;
    childEditOpen = false;
    childEditError = null;
    editingPresetId = null;
    childLinkInvite = null;
    childLinkQr = '';
    childLinkLoading = false;
    childLinkError = null;
    childLinkCopied = false;
  }

  function startEditingReward(reward: any) {
    editingRewardId = reward.id;
    rewardForm = {
      title: reward.title,
      description: reward.description || '',
      icon: reward.icon || '',
      points: reward.points,
      is_active: reward.is_active
    };
  }

  function cancelEditingReward() {
    editingRewardId = null;
    rewardForm = {
      title: '',
      description: '',
      icon: '',
      points: 20,
      is_active: true
    };
  }

  async function saveReward() {
    try {
      rewardLoading = true;
      rewardError = null;
      const payload = {
        title: rewardForm.title,
        description: rewardForm.description || '',
        icon: rewardForm.icon || null,
        points: rewardForm.points,
        is_active: rewardForm.is_active
      };
      if (editingRewardId) {
        await api.patch(`/rewards/${editingRewardId}`, payload);
        cancelEditingReward();
      } else {
        await api.post('/rewards/', payload);
      }
      await loadDashboard();
    } catch (e) {
      rewardError = $_('parent.rewards.errorSave');
    } finally {
      rewardLoading = false;
    }
  }

  async function deleteReward(id: number) {
    if (!confirm($_('parent.rewards.confirmDelete'))) return;
    try {
      rewardLoading = true;
      rewardError = null;
      await api.delete(`/rewards/${id}`);
      if (editingRewardId === id) cancelEditingReward();
      await loadDashboard();
    } catch (e) {
      rewardError = $_('parent.rewards.errorDelete');
    } finally {
      rewardLoading = false;
    }
  }

  async function createChildLink(childSummary: any) {
    try {
      childLinkLoading = true;
      childLinkError = null;
      childLinkCopied = false;
      const invite = await api.post(`/children/${childSummary.child.id}/device-invites`, {});
      childLinkInvite = invite;
      const { default: QRCode } = await import('qrcode');
      childLinkQr = await QRCode.toDataURL(invite.invite_url, {
        width: 320,
        margin: 1,
        errorCorrectionLevel: 'M'
      });
    } catch (e) {
      childLinkError = $_('parent.childLink.errorCreate');
      childLinkInvite = null;
      childLinkQr = '';
    } finally {
      childLinkLoading = false;
    }
  }

  async function loadChildDevices(childSummary: any) {
    try {
      childDevicesLoading = true;
      childDevicesError = null;
      childDevices = await api.get(`/children/${childSummary.child.id}/devices`);
    } catch (e) {
      childDevicesError = $_('parent.childLink.errorLoadDevices');
      childDevices = [];
    } finally {
      childDevicesLoading = false;
    }
  }

  function openChildLink(childSummary: any) {
    activeModal = { type: 'child-link', child: childSummary };
    childLinkInvite = null;
    childLinkQr = '';
    childLinkError = null;
    childLinkCopied = false;
    childDevices = [];
    childDevicesError = null;
    childDeviceUnlinkingId = null;
    void createChildLink(childSummary);
    void loadChildDevices(childSummary);
  }

  async function copyChildInviteLink() {
    if (!childLinkInvite?.invite_url) return;
    await navigator.clipboard.writeText(childLinkInvite.invite_url);
    childLinkCopied = true;
    window.setTimeout(() => {
      childLinkCopied = false;
    }, 2000);
  }

  async function revokeChildLink() {
    if (!activeModal?.child) return;
    if (!confirm($_('parent.childLink.revokeConfirmAllAccess'))) return;
    try {
      childLinkLoading = true;
      childLinkError = null;
      await api.post(`/children/${activeModal.child.child.id}/device-invites/revoke`, {});
      childLinkInvite = null;
      childLinkQr = '';
      await loadChildDevices(activeModal.child);
      await loadDashboard();
    } catch (e) {
      childLinkError = $_('parent.childLink.errorRevokeAccess');
    } finally {
      childLinkLoading = false;
    }
  }

  async function unlinkChildDevice(device: ChildDevice) {
    if (!activeModal?.child) return;
    if (!confirm($_('parent.childLink.unlinkConfirm'))) return;
    try {
      childDeviceUnlinkingId = device.id;
      childDevicesError = null;
      await api.delete(`/children/${activeModal.child.child.id}/devices/${device.id}`);
      await loadChildDevices(activeModal.child);
    } catch (e) {
      childDevicesError = $_('parent.childLink.errorUnlinkDevice');
    } finally {
      childDeviceUnlinkingId = null;
    }
  }

  function formatDeviceDate(value: string | null) {
    if (!value) return $_('parent.childLink.notSeenYet');
    return new Date(value).toLocaleString($locale || 'en');
  }

  function childLinkDeviceLabel(device: ChildDevice) {
    const label = device.label?.trim();
    if (!label || label.toLowerCase() === 'linked device') {
      return $_('parent.childLink.linkedDevice');
    }
    return label;
  }

  async function regenerateChildLink() {
    if (!activeModal?.child) return;
    await createChildLink(activeModal.child);
  }

  function startEditing(preset: any) {
    editingPresetId = preset.id;
    modalForm = {
      points: preset.points,
      description: preset.description || '',
      title: preset.title,
      icon: preset.icon || '',
      email: '',
      jar: 'spending'
    };
    // Scroll modal to top
    const modalContent = document.getElementById('modal-scroll-area');
    if (modalContent) modalContent.scrollTop = 0;
  }

  function cancelEditing() {
    editingPresetId = null;
    modalForm = {
      points: 1,
      description: '',
      title: '',
      icon: '',
      email: '',
      jar: 'spending'
    };
  }

  async function handleModalSubmit() {
    if (!activeModal) return;
    
    try {
      modalLoading = true;
      modalError = null;

      if (activeModal.type === 'picker') return;

      if (activeModal.type === 'family') {
        await api.post('/family/invites', { email: modalForm.email });
        await loadDashboard();
        modalForm.email = '';
        return;
      }

      if (activeModal.type === 'presets') {
        const payload = {
          title: modalForm.title,
          points: modalForm.points,
          description: modalForm.description || '',
          icon: modalForm.icon || null,
          is_active: true
        };

        if (editingPresetId) {
          await api.patch(`/presets/${editingPresetId}`, payload);
        } else {
          await api.post('/presets/', payload);
        }
        
        await loadDashboard();
        if (editingPresetId) {
          cancelEditing();
        } else {
          closeModal();
        }
        return;
      }

      const childId = activeModal.child.child.id;

      if (activeModal.type === 'award') {
        await api.post(`/children/${childId}/award`, {
          points: modalForm.points,
          description: modalForm.description || $_('parent.pointsActions.defaultAwardDescription'),
          jar: modalForm.jar
        });
      } else if (activeModal.type === 'penalty') {
        await api.post(`/children/${childId}/penalty`, {
          points: modalForm.points,
          description: modalForm.description || $_('parent.pointsActions.defaultPenaltyDescription'),
          jar: modalForm.jar
        });
      } else if (activeModal.type === 'bank') {
        await api.post(`/children/${childId}/savings/deposit`, {
          points: modalForm.points,
          description: modalForm.description || $_('parent.bank.bankingDescription')
        });
      } else if (activeModal.type === 'redeem') {
        await api.post(`/children/${childId}/redemptions`, {
          points: modalForm.points,
          title: modalForm.title || $_('parent.redemptions.defaultTitle'),
          description: modalForm.description || ''
        });
      }

      await loadDashboard();
      closeModal();
    } catch (e) {
      modalError = $_('parent.pointsActions.errorActionFailed');
    } finally {
      modalLoading = false;
    }
  }

  async function submitCustomPoints(direction: 'award' | 'penalty') {
    if (!activeModal?.child) return;

    const points = Math.abs(Number(modalForm.points) || 0);
    if (points < 1) {
      modalError = $_('parent.pointsActions.errorMinimumOnePoint');
      return;
    }

    preparePointSound();

    try {
      modalLoading = true;
      modalError = null;
      const childId = activeModal.child.child.id;

      if (direction === 'award') {
        await api.post(`/children/${childId}/award`, {
          points,
          description: modalForm.description || $_('parent.pointsActions.defaultAwardDescription'),
          jar: modalForm.jar
        });
        playPositiveSound();
      } else {
        await api.post(`/children/${childId}/penalty`, {
          points,
          description: modalForm.description || $_('parent.pointsActions.defaultPenaltyDescription'),
          jar: modalForm.jar
        });
        playNegativeSound();
      }

      await loadDashboard();
      closeModal();
    } catch (e) {
      modalError = $_('parent.pointsActions.errorActionFailed');
    } finally {
      modalLoading = false;
    }
  }

  async function applyPreset(childSummary: any, preset: any) {
    preparePointSound();

    try {
      const childId = childSummary.child.id;
      if (preset.points > 0) {
        await api.post(`/children/${childId}/award`, {
          points: preset.points,
          description: preset.title,
          jar: 'spending'
        });
        playPositiveSound();
      } else {
        await api.post(`/children/${childId}/penalty`, {
          points: Math.abs(preset.points),
          description: preset.title,
          jar: 'spending'
        });
        playNegativeSound();
      }
      await loadDashboard();
      closeModal();
    } catch (e) {
      alert($_('parent.presets.applyError'));
    }
  }

  async function deletePreset(id: number) {
    if (!confirm($_('parent.presets.deleteConfirm'))) return;
    try {
      await api.delete(`/presets/${id}`);
      await loadDashboard();
    } catch (e) {
      alert($_('parent.presets.deleteError'));
    }
  }

  async function revokeInvite(id: number) {
    if (!confirm($_('parent.family.confirmCancelInvite'))) return;
    try {
      await api.delete(`/family/invites/${id}`);
      await loadDashboard();
      await loadFamilySettings();
    } catch (e) {
      alert($_('parent.family.errorCancelInvite'));
    }
  }

  async function removeGrownup(member: FamilyMember) {
    if (!confirm($_('parent.family.confirmRemoveGrownup'))) return;

    try {
      familyGrownupRemovingId = member.id;
      await api.delete(`/family/grownups/${member.id}`);
      await loadDashboard();
      await loadFamilySettings();
    } catch (e) {
      alert($_('parent.family.errorRemoveGrownup'));
    } finally {
      familyGrownupRemovingId = null;
    }
  }

  async function processRedemption(id: number, action: string) {
    try {
      const note = action === 'reject' ? window.prompt($_('common.rejectionReasonPrompt')) : $_('common.approvedByParent');
      await api.post(`/redemptions/${id}/${action}`, {
        parent_note: note || ''
      });
      await loadDashboard();
    } catch (e) {
      alert($_('parent.redemptions.processError'));
    }
  }

  function openLogin() {
    window.location.href = '/login';
  }

  function childAvatarLabel(childSummary: any) {
    const displayName = childSummary?.child?.display_name?.trim() || '?';
    return displayName.slice(0, 1).toUpperCase();
  }

  function childAvailablePoints(childSummary: any) {
    return Math.max(0, Number(childSummary?.available_spending ?? childSummary?.spending_balance ?? 0) || 0);
  }

  function childAvatarAsset(childSummary: any) {
    return getAvatarAsset(childSummary?.child?.avatar_name);
  }

  function avatarCanRender(childSummary: any, avatarKey: string) {
    return hasAvatarAssetFile(avatarKey) && !avatarImageErrors[childSummary?.child?.id];
  }

  function markAvatarFailed(childSummary: any) {
    const childId = childSummary?.child?.id;
    if (!childId) return;
    avatarImageErrors = { ...avatarImageErrors, [childId]: true };
  }

  function childPendingRequests(childSummary: any) {
    const childId = childSummary?.child?.id;
    return pendingRedemptions.filter((request) => request.child_id === childId);
  }

  function childAllowance(childSummary: any) {
    return allowanceSummaries[childSummary?.child?.id];
  }

  function openChildEdit(childSummary: any) {
    childEditOpen = true;
    childEditError = null;
    childEditForm = {
      display_name: childSummary?.child?.display_name || '',
      avatar_name: normaliseAvatarKey(childSummary?.child?.avatar_name) || '',
      active: childSummary?.child?.active ?? true
    };
  }

  function setChildEditAvatar(value: string) {
    childEditForm = {
      ...childEditForm,
      avatar_name: value
    };
  }

  async function saveChildEdit() {
    if (!activeModal?.child) return;
    const childId = activeModal.child.child.id;
    const displayName = childEditForm.display_name.trim();
    if (!displayName) {
      childEditError = $_('parent.childEdit.displayNameRequired');
      return;
    }

    try {
      childEditLoading = true;
      childEditError = null;
      await api.patch(`/children/${childId}`, {
        display_name: displayName,
        avatar_name: childEditForm.avatar_name || null,
        active: childEditForm.active
      });
      await loadDashboard();
      const refreshed = children.find((childSummary) => childSummary.child.id === childId);
      if (refreshed) {
        activeModal = { ...activeModal, child: refreshed };
      }
      childEditOpen = false;
    } catch (e) {
      childEditError = $_('parent.childEdit.errorSaveChild');
    } finally {
      childEditLoading = false;
    }
  }

  function nextSavingsUnlock(childSummary: any) {
    const schedule = childSummary?.savings_unlock_schedule;
    return Array.isArray(schedule) && schedule.length > 0 ? schedule[0] : null;
  }

  function ledgerApiPeriod(period: 'day' | 'week' | 'year') {
    return period === 'year' ? 'month' : period;
  }

  function ledgerKey(childId: number, period = pointLogPeriod) {
    return `${childId}:${ledgerApiPeriod(period)}`;
  }

  function currentLedger(childSummary: any) {
    const childId = childSummary?.child?.id;
    if (!childId) return [];
    return childLedgerByKey[ledgerKey(childId)] || [];
  }

  function isBehaviorLedgerEntry(tx: LedgerTransaction) {
    if (!['award', 'penalty', 'adjustment', 'calendar_task'].includes(tx.transaction_type)) {
      return false;
    }

    const haystack = `${tx.description || ''} ${tx.transaction_type} ${tx.jar || ''}`.toLowerCase();
    const systemMarkers = [
      'redemption',
      'hold',
      'saved',
      'savings',
      'bank',
      'transfer to savings',
      'transfer from savings',
      'transfer to spending',
      'transfer from spending',
      'allowance'
    ];

    return !systemMarkers.some((marker) => haystack.includes(marker));
  }

  function goodPercentage(entries: LedgerTransaction[]) {
    const behaviorEntries = entries.filter(isBehaviorLedgerEntry);
    const positive = behaviorEntries.reduce((sum, tx) => sum + Math.max(0, Number(tx.points) || 0), 0);
    const reduced = behaviorEntries.reduce((sum, tx) => sum + Math.abs(Math.min(0, Number(tx.points) || 0)), 0);
    const total = positive + reduced;
    if (total <= 0) return null;
    return Math.round((positive / total) * 100);
  }

  function ringStyle(percent: number | null) {
    const safePercent = Math.max(0, Math.min(100, percent ?? 0));
    return `background: conic-gradient(#10B981 ${safePercent}%, #F43F5E ${safePercent}% 100%);`;
  }

  function formatLedgerDate(value: string) {
    return new Date(value).toLocaleDateString($locale || 'en', { month: 'short', day: 'numeric' });
  }

  function formatSavingsUnlockDate(value: string) {
    return new Date(value).toLocaleDateString($locale || 'en', { weekday: 'short', month: 'short', day: 'numeric' });
  }

  function formatCalendarDate(value: string) {
    return new Date(`${value}T00:00:00`).toLocaleDateString($locale || 'en', { weekday: 'short', month: 'short', day: 'numeric' });
  }

  function formatCalendarTime(value: string | null) {
    if (!value) return $_('calendar.anyTime');
    const [hours, minutes] = value.slice(0, 5).split(':').map((part) => Number(part));
    if (Number.isNaN(hours) || Number.isNaN(minutes)) {
      return value.slice(0, 5);
    }

    const date = new Date(Date.UTC(1970, 0, 1, hours, minutes));
    return date.toLocaleTimeString($locale || 'en', {
      hour: 'numeric',
      minute: '2-digit',
      timeZone: 'UTC'
    });
  }

  function calendarEntryTypeLabel(type: string) {
    if (type === 'task') return $_('calendar.taskType');
    if (type === 'event') return $_('calendar.eventType');
    return type;
  }

  function ledgerJarLabel(jar: string | null | undefined) {
    const value = (jar || '').trim();
    if (!value) return value;
    if (value.toLowerCase() === 'spending') return $_('parent.pointsLog.spendingJar');
    return value;
  }

  function modalCalendarItems(childSummary: any) {
    return childCalendarById[childSummary?.child?.id] || [];
  }

  function todayCalendarItems(childSummary: any) {
    const today = getLocalDateValue();
    return modalCalendarItems(childSummary).filter((item) => item.occurrence_date === today);
  }

  function upcomingCalendarItems(childSummary: any) {
    const today = getLocalDateValue();
    return modalCalendarItems(childSummary).filter((item) => item.occurrence_date !== today).slice(0, 6);
  }

  async function loadChildCalendar(childSummary: any) {
    const childId = childSummary?.child?.id;
    if (!childId || childCalendarLoading[childId]) return;

    childCalendarLoading = { ...childCalendarLoading, [childId]: true };
    childCalendarError = { ...childCalendarError, [childId]: '' };
    try {
      const query = new URLSearchParams({
        child_id: String(childId),
        from_date: getLocalDateValue(),
        to_date: addDaysValue(14)
      });
      const response = await api.get(`/calendar?${query.toString()}`);
      childCalendarById = { ...childCalendarById, [childId]: Array.isArray(response) ? response : [] };
    } catch (e) {
      childCalendarError = { ...childCalendarError, [childId]: $_('parent.childCalendar.errorLoad') };
      childCalendarById = { ...childCalendarById, [childId]: [] };
    } finally {
      childCalendarLoading = { ...childCalendarLoading, [childId]: false };
    }
  }

  async function loadChildLedger(childSummary: any, period = pointLogPeriod) {
    const childId = childSummary?.child?.id;
    if (!childId) return;
    const key = ledgerKey(childId, period);
    if (childLedgerLoading[key]) return;

    childLedgerLoading = { ...childLedgerLoading, [key]: true };
    childLedgerError = { ...childLedgerError, [key]: '' };
    try {
      const response = await api.get(`/children/${childId}/ledger?period=${ledgerApiPeriod(period)}&type=all`);
      childLedgerByKey = { ...childLedgerByKey, [key]: Array.isArray(response) ? response : [] };
    } catch (e) {
      childLedgerError = { ...childLedgerError, [key]: $_('parent.childCalendar.errorLoadHistory') };
      childLedgerByKey = { ...childLedgerByKey, [key]: [] };
    } finally {
      childLedgerLoading = { ...childLedgerLoading, [key]: false };
    }
  }

  async function ensureChildModalData(childSummary: any) {
    await Promise.all([
      loadChildCalendar(childSummary),
      loadChildLedger(childSummary, pointLogPeriod)
    ]);
  }

  function setChildModalTab(tab: string) {
    childModalTab = tab;
    if (activeModal?.type !== 'picker' || !activeModal.child) return;

    if (tab === 'calendar') {
      void loadChildCalendar(activeModal.child);
    }
    if (tab === 'points-log') {
      void loadChildLedger(activeModal.child, pointLogPeriod);
    }
  }

  function setPointLogPeriod(period: 'day' | 'week' | 'year') {
    pointLogPeriod = period;
    if (activeModal?.type === 'picker' && activeModal.child) {
      void loadChildLedger(activeModal.child, period);
    }
  }

  onMount(loadDashboard);

  const pendingRedemptions = $derived(redemptions.filter((request) => request.status === 'pending'));

  const totalAvailablePoints = $derived(
    children.reduce((sum, childSummary) => sum + childAvailablePoints(childSummary), 0)
  );

  const schoolItemsTodayCount = $derived(
    children.reduce(
      (sum, childSummary) => sum + (schoolTodayByChild[childSummary.child.id]?.length || 0),
      0
    )
  );
</script>

<div class="bg-slate-50 min-h-dvh max-w-full overflow-x-hidden pb-[var(--safe-bottom)]">
  {#if loading}
    <div class="flex justify-center py-24">
      <div class="flex flex-col items-center gap-4">
        <img
          src="/pets/dragon-1/egg.png"
          alt=""
          aria-hidden="true"
          class="w-16 h-16 object-contain animate-bounce"
        />
        <p class="text-sm font-semibold text-slate-500">{$_('common.loadingDashboard')}</p>
      </div>
    </div>
  {:else if needsLogin}
    <div class="max-w-xl mx-auto px-4 py-20">
      <div class="card-lg p-10 md:p-12 text-center">
        <div class="w-16 h-16 bg-hero/10 text-hero rounded-2xl flex items-center justify-center mx-auto mb-6">
          <LogIn size={32} />
        </div>
        <h1 class="text-3xl font-bold text-slate-900 mb-3">{$_('parent.loginRequired')}</h1>
        <p class="text-slate-600 mb-8">{$_('parent.loginHint')}</p>
        <button onclick={openLogin} class="btn-hero w-full py-4 rounded-2xl">{$_('parent.goToLogin')}</button>
      </div>
    </div>
  {:else if error}
    <div class="max-w-lg mx-auto px-4 py-20">
      <div class="card-lg bg-red-50 border-red-100 p-8 text-center">
        <div class="w-16 h-16 bg-red-100 text-red-600 rounded-full flex items-center justify-center mx-auto mb-6">
          <Ban size={32} />
        </div>
        <p class="text-red-600 font-bold mb-4 uppercase tracking-wide text-sm">{$_('parent.failedLoad')}</p>
        <p class="text-slate-600 mb-8 break-words">{error}</p>
        <button onclick={loadDashboard} class="btn-secondary w-full py-4">{$_('common.tryAgain')}</button>
      </div>
    </div>
  {:else}
    <div class="bg-slate-50 min-h-dvh max-w-full overflow-x-hidden pb-[calc(5rem+var(--safe-bottom))]">
      <div class="bg-white border-b border-slate-200/70">
        <div class="max-w-5xl mx-auto px-3 sm:px-4 py-5 md:py-6">
          <div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div class="min-w-0">
              <h1 class="text-3xl sm:text-4xl font-black text-slate-950 tracking-tight break-words">{$_('parent.title')}</h1>
            </div>

            <div class="flex flex-wrap items-center gap-2">
              <details class="relative w-full sm:w-auto">
                <summary class="inline-flex w-full cursor-pointer list-none items-center justify-center gap-2 rounded-full bg-white px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-700 shadow-sm ring-1 ring-slate-200 transition hover:text-hero sm:w-auto">
                  <Settings size={14} />
                  {$_('parent.settings')}
                </summary>
                <div class="absolute right-0 z-30 mt-2 grid w-full min-w-64 gap-1 rounded-2xl border border-slate-200 bg-white p-2 shadow-2xl sm:w-72">
                  <LanguageSelector />
                  <button type="button" onclick={() => openModal('rewards', null)} class="inline-flex items-center gap-2 rounded-xl px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-700 hover:bg-slate-50">
                    <Gift size={15} />
                    {$_('parent.manageRewards')}
                  </button>
                  <button type="button" onclick={() => openModal('family', null)} class="inline-flex items-center gap-2 rounded-xl px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-700 hover:bg-slate-50">
                    <Users size={15} />
                    {$_('parent.parentsCaregivers')}
                  </button>
                  <button type="button" onclick={() => openModal('calendar-week', null)} class="inline-flex items-center gap-2 rounded-xl px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-700 hover:bg-slate-50">
                    <CalendarDays size={15} />
                    {$_('parent.calendarSchoolWeek')}
                  </button>
                  <button type="button" onclick={() => openModal('presets', null)} class="inline-flex items-center gap-2 rounded-xl px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-700 hover:bg-slate-50">
                    <Settings size={15} />
                    {$_('parent.behaviourPresets')}
                  </button>
                  <a href="/redemptions" class="inline-flex items-center gap-2 rounded-xl px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-700 hover:bg-slate-50">
                    <Ticket size={15} />
                    {$_('parent.rewardRedemptions')}
                  </a>
                  <a href="/allowance" class="inline-flex items-center gap-2 rounded-xl px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-700 hover:bg-slate-50">
                    <Wallet size={15} />
                    {$_('parent.allowance')}
                  </a>
                  <a href="/calendar" class="inline-flex items-center gap-2 rounded-xl px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-700 hover:bg-slate-50">
                    <CalendarDays size={15} />
                    {$_('parent.calendar')}
                  </a>
                  <button type="button" onclick={() => openModal('child-link-select', null)} disabled={children.length === 0} class="inline-flex items-center gap-2 rounded-xl px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50">
                    <QrCode size={15} />
                    {$_('parent.childDeviceLinks')}
                  </button>
                </div>
              </details>
            </div>
          </div>
        </div>
      </div>

      <div class="max-w-5xl mx-auto px-3 sm:px-4 py-6 md:py-8 space-y-6">
        {#if children.length > 0}
          <section aria-label={$_('parent.summary.label')} class="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div class="card p-4 sm:p-5 flex items-center gap-4">
              <div class="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-hero/10 text-hero">
                <Trophy size={22} />
              </div>
              <div class="min-w-0">
                <p class="text-2xl font-black text-slate-950 leading-tight">{totalAvailablePoints}</p>
                <p class="text-xs font-semibold text-slate-500">{$_('parent.summary.totalPoints')}</p>
              </div>
            </div>
            <a
              href="/redemptions"
              class="card p-4 sm:p-5 flex items-center gap-4 transition hover:border-hero/40 hover:shadow-md focus:outline-none focus:ring-4 focus:ring-hero/15"
            >
              <div class="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl {pendingRedemptions.length > 0 ? 'bg-reward/10 text-reward-dark' : 'bg-slate-100 text-slate-400'}">
                <Ticket size={22} />
              </div>
              <div class="min-w-0">
                <p class="text-2xl font-black text-slate-950 leading-tight">{pendingRedemptions.length}</p>
                <p class="text-xs font-semibold text-slate-500">
                  {pendingRedemptions.length > 0 ? $_('parent.summary.pendingRequests') : $_('parent.summary.noPendingRequests')}
                </p>
              </div>
            </a>
            <div class="card p-4 sm:p-5 flex items-center gap-4">
              <div class="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl {schoolItemsTodayCount > 0 ? 'bg-savings/10 text-savings-dark' : 'bg-slate-100 text-slate-400'}">
                <CalendarDays size={22} />
              </div>
              <div class="min-w-0">
                <p class="text-2xl font-black text-slate-950 leading-tight">{schoolItemsTodayCount}</p>
                <p class="text-xs font-semibold text-slate-500">
                  {schoolItemsTodayCount > 0 ? $_('parent.summary.schoolToday') : $_('parent.summary.noSchoolToday')}
                </p>
              </div>
            </div>
          </section>
        {/if}

        <section class="space-y-4">
          <div class="flex flex-wrap items-center justify-end gap-3">
            <button
              type="button"
              onclick={addChild}
              disabled={loadingChildren}
              class="inline-flex items-center gap-2 rounded-full bg-white px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-700 shadow-sm ring-1 ring-slate-200 transition hover:text-hero disabled:cursor-not-allowed disabled:opacity-60"
            >
              <UserPlus size={14} />
              {$_('parent.addChild')}
            </button>
          </div>

          {#if children.length === 0}
            <div class="card-flat border-dashed border-2 p-8 sm:p-10 text-center">
              <img
                src="/pets/dragon-1/egg.png"
                alt=""
                aria-hidden="true"
                class="mx-auto mb-5 h-20 w-20 object-contain"
                loading="lazy"
              />
              <h3 class="text-2xl font-bold text-slate-900">{$_('parent.emptyTitle')}</h3>
              <p class="mx-auto mt-3 max-w-md text-sm leading-6 text-slate-500">
                {$_('parent.emptyText')}
              </p>
            </div>
          {:else}
            <div class="grid grid-cols-2 gap-x-3 gap-y-6 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
              {#each children as c}
                {@const avatar = childAvatarAsset(c)}
                <button
                  type="button"
                  onclick={() => openModal('picker', c)}
                  data-qa="parent-child-card"
                  data-child-id={c.child.id}
                  class="group flex min-w-0 flex-col items-center rounded-2xl border border-transparent bg-transparent px-2 py-3 text-center transition hover:border-slate-200 hover:bg-white hover:shadow-lg focus:outline-none focus:ring-4 focus:ring-hero/15"
                  aria-label={$_('parent.openPointActions', { values: { name: c.child.display_name } })}
                >
                  <div class="relative">
                    <div class="absolute -top-3 left-1/2 z-10 -translate-x-1/2 min-w-[2.75rem] max-w-[4.25rem] truncate rounded-full bg-slate-900 px-2.5 py-1 text-center text-[10px] font-bold leading-none tabular-nums text-white shadow-lg">
                      {childAvailablePoints(c)}
                    </div>
                    <div class="flex h-24 w-24 items-center justify-center overflow-hidden rounded-full bg-white shadow-md ring-4 ring-white transition group-hover:scale-[1.03] sm:h-28 sm:w-28">
                      {#if avatarCanRender(c, avatar.key)}
                        <img
                          src={avatar.path}
                          alt={$_('parent.childEdit.avatarAlt', { values: { name: c.child.display_name } })}
                          class="h-full w-full object-cover"
                          loading="lazy"
                          onerror={() => markAvatarFailed(c)}
                        />
                      {:else}
                        <span class="text-3xl font-bold text-slate-900">{childAvatarLabel(c)}</span>
                      {/if}
                    </div>
                  </div>
                  <span class="mt-3 w-full truncate text-sm font-bold text-slate-950 sm:text-base">
                    {c.child.display_name}
                  </span>
                </button>
              {/each}
            </div>
          {/if}
        </section>

      </div>
    </div>
  {/if}
<!-- Modals -->
{#if activeModal}
  <div class="fixed inset-0 z-[100] flex items-end justify-center p-0 sm:items-center sm:p-4">
    <!-- Backdrop -->
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div 
      class="absolute inset-0 bg-slate-900/60 backdrop-blur-sm transition-opacity" 
      onclick={closeModal}
    ></div>

    <!-- Modal Content -->
    <div class="bg-white rounded-t-[2rem] sm:rounded-[2.5rem] w-full max-w-lg shadow-2xl relative z-10 overflow-hidden animate-in fade-in zoom-in duration-300 max-h-[calc(100dvh-var(--safe-top))] sm:max-h-[92dvh] flex flex-col">
      <div class="p-5 sm:p-8 md:p-10 flex flex-col min-h-0 overflow-hidden pb-[calc(1rem+var(--safe-bottom))] sm:pb-4">
        <div class="flex items-start gap-3 sm:gap-4 mb-6 sm:mb-8 shrink-0">
          {#if activeModal.type === 'picker'}
            {@const headerAvatar = childAvatarAsset(activeModal.child)}
            <div class="flex min-w-0 flex-1 items-center gap-3 sm:gap-4">
              <div class="w-12 h-12 sm:w-16 sm:h-16 rounded-3xl flex items-center justify-center overflow-hidden shadow-lg shrink-0 bg-slate-900 text-white shadow-slate-200">
                {#if avatarCanRender(activeModal.child, headerAvatar.key)}
                  <img
                    src={headerAvatar.path}
                    alt={$_('parent.childEdit.avatarAlt', { values: { name: activeModal.child.child.display_name } })}
                    class="h-full w-full object-cover"
                    onerror={() => markAvatarFailed(activeModal.child)}
                  />
                {:else}
                  <span class="text-lg sm:text-2xl font-bold">{childAvatarLabel(activeModal.child)}</span>
                {/if}
              </div>
              <div class="min-w-0">
                <h3 class="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight break-words leading-tight">
                  {activeModal.child?.child?.display_name}
                </h3>
              </div>
            </div>
            <div class="hidden sm:flex shrink-0 items-center gap-2 rounded-full bg-slate-100 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-slate-700">
              <Trophy size={14} class="text-hero" />
              {childAvailablePoints(activeModal.child)} {$_('common.pts')}
            </div>
            <div class="sm:hidden shrink-0 rounded-full bg-slate-100 px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-slate-700">
              {childAvailablePoints(activeModal.child)} {$_('common.pts')}
            </div>
          {:else}
            <div class="flex min-w-0 items-center gap-3 sm:gap-4">
              <div class="w-12 h-12 sm:w-16 sm:h-16 rounded-3xl flex items-center justify-center shadow-lg shrink-0
                {activeModal.type === 'award' ? 'bg-savings text-white shadow-savings/20' : 
                 activeModal.type === 'penalty' ? 'bg-penalty text-white shadow-penalty/20' :
                 activeModal.type === 'bank' ? 'bg-reward text-white shadow-reward/20' :
                 activeModal.type === 'presets' ? 'bg-hero text-white shadow-hero/20' :
                 activeModal.type === 'family' ? 'bg-hero text-white shadow-hero/20' :
                 activeModal.type === 'calendar-week' ? 'bg-hero text-white shadow-hero/20' :
                 activeModal.type === 'child-link' ? 'bg-slate-900 text-white shadow-slate-200' :
                 activeModal.type === 'child-link-select' ? 'bg-slate-900 text-white shadow-slate-200' :
                 activeModal.type === 'rewards' ? 'bg-reward text-white shadow-reward/20' :
                 activeModal.type === 'requests' ? 'bg-savings text-white shadow-savings/20' :
                 'bg-reward text-white shadow-reward/20'}">
                {#if activeModal.type === 'award'}<Award size={32} />
                {:else if activeModal.type === 'penalty'}<Ban size={32} />
                {:else if activeModal.type === 'bank'}<Wallet size={32} />
                {:else if activeModal.type === 'presets'}<Settings size={32} />
                {:else if activeModal.type === 'family'}<Users size={32} />
                {:else if activeModal.type === 'calendar-week'}<CalendarDays size={32} />
                {:else if activeModal.type === 'child-link'}<QrCode size={32} />
                {:else if activeModal.type === 'child-link-select'}<QrCode size={32} />
                {:else if activeModal.type === 'rewards'}<Gift size={32} />
                {:else if activeModal.type === 'requests'}<Check size={32} />
                {:else}<Trophy size={32} />{/if}
              </div>
              <div class="min-w-0">
                <h3 class="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight break-words leading-tight">
                  {activeModal.type === 'award' ? $_('parent.pointsActions.addPoints') :
                   activeModal.type === 'penalty' ? $_('parent.pointsActions.removePoints') :
                  activeModal.type === 'bank' ? $_('parent.bank.moveToSavedPoints') :
                  activeModal.type === 'presets' ? (editingPresetId ? $_('parent.presets.edit') : $_('parent.presets.manage')) :
                  activeModal.type === 'family' ? $_('parent.parentsCaregivers') :
                  activeModal.type === 'calendar-week' ? $_('parent.calendarSchoolWeek') :
                  activeModal.type === 'child-link' ? $_('parent.childLink.modalTitle') :
                  activeModal.type === 'child-link-select' ? $_('parent.childLink.modalTitle') :
                  activeModal.type === 'rewards' ? $_('parent.rewards.manage') :
                  activeModal.type === 'requests' ? $_('parent.requests.reviewRewardRequests') :
                  $_('parent.redeem.title')}
                </h3>
                <p class="text-slate-400 font-bold text-[10px] sm:text-xs uppercase tracking-wide break-words">
                  {activeModal.type === 'presets' ? (editingPresetId ? $_('parent.presets.update') : $_('parent.presets.subtitle')) :
                   activeModal.type === 'family' ? $_('parent.family.subtitle') :
                   activeModal.type === 'calendar-week' ? $_('parent.week.subtitle') :
                   activeModal.type === 'child-link' ? $_('parent.childLink.dashboardLink') :
                   activeModal.type === 'child-link-select' ? $_('parent.childLink.chooseChildFirst') :
                   activeModal.type === 'rewards' ? $_('parent.rewards.subtitle') :
                   activeModal.type === 'requests' ? $_('parent.tabs.requests') : ''}
                </p>
              </div>
            </div>
          {/if}
          <button onclick={closeModal} class="w-11 h-11 shrink-0 rounded-xl bg-slate-50 text-slate-300 flex items-center justify-center hover:bg-slate-100 hover:text-slate-500 transition-all" aria-label={$_('common.close')}>
            <X size={20} />
          </button>
        </div>

        {#if modalError}
          <div class="p-4 bg-red-50 text-red-600 rounded-2xl font-bold text-sm mb-6 border border-red-100 flex items-center gap-2 shrink-0">
            <Ban size={16} /> {modalError}
          </div>
        {/if}

        <div id="modal-scroll-area" class="min-h-0 flex-1 overflow-y-auto overscroll-contain pr-1 sm:pr-2 -mr-1 sm:-mr-2 custom-scrollbar space-y-6 pb-4">
          {#if activeModal.type === 'picker'}
            <div class="space-y-4">
              <div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
                <a
                  href={`/child/${activeModal.child.child.id}`}
                  class="inline-flex min-w-0 w-full items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-700 transition hover:border-hero hover:text-hero"
                >
                  <LayoutDashboard size={15} />
                  <span class="sm:hidden">{$_('parent.childDashboard')}</span>
                  <span class="hidden sm:inline">{$_('parent.openChildDashboard')}</span>
                </a>
                <button
                  type="button"
                  onclick={() => openChildEdit(activeModal.child)}
                  class="inline-flex min-w-0 w-full items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-700 transition hover:border-hero hover:text-hero"
                >
                  <Settings size={15} />
                  {$_('parent.editChild')}
                </button>
              </div>

              {#if childEditOpen}
                {@const editAvatar = childEditForm.avatar_name ? getAvatarAsset(childEditForm.avatar_name) : null}
                <div class="rounded-[1.75rem] border border-slate-100 bg-slate-50 p-4 sm:p-5">
                  <div class="flex items-start justify-between gap-3">
                    <div class="min-w-0">
                      <p class="text-[10px] font-semibold uppercase tracking-wide text-slate-400">{$_('parent.editChild')}</p>
                      <h4 class="mt-1 text-lg font-bold text-slate-950">{$_('parent.childEdit.heading')}</h4>
                    </div>
                    <button
                      type="button"
                      onclick={() => (childEditOpen = false)}
                      class="rounded-xl bg-white px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-slate-500 shadow-sm ring-1 ring-slate-200"
                    >
                      {$_('common.close')}
                    </button>
                  </div>

                  {#if childEditError}
                    <div class="mt-4 rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm font-bold text-red-700 break-words">
                      {childEditError}
                    </div>
                  {/if}

                  <div class="mt-4 grid gap-4">
                    <label class="block min-w-0">
                      <span class="mb-2 block text-[10px] font-semibold uppercase tracking-wide text-slate-400">{$_('parent.childEdit.displayName')}</span>
                      <input
                        type="text"
                        bind:value={childEditForm.display_name}
                        class="w-full rounded-2xl border-2 border-slate-200 bg-white px-4 py-4 text-slate-900 font-bold focus:outline-none focus:border-hero/30"
                      />
                    </label>

                    <div class="rounded-[1.5rem] border border-slate-100 bg-white p-4">
                      <div class="flex items-center justify-between gap-3">
                        <div class="min-w-0">
                          <p class="text-[10px] font-semibold uppercase tracking-wide text-slate-400">{$_('parent.childEdit.avatar')}</p>
                          <p class="mt-1 text-sm font-bold text-slate-600">{$_('parent.childEdit.avatarHelp')}</p>
                        </div>
                        <button
                          type="button"
                          onclick={() => setChildEditAvatar('')}
                          class="shrink-0 rounded-full border px-3 py-2 text-[10px] font-semibold uppercase tracking-wide transition {childEditForm.avatar_name === '' ? 'border-hero bg-hero/10 text-hero' : 'border-slate-200 bg-white text-slate-500 hover:border-hero hover:text-hero'}"
                        >
                          {$_('parent.childEdit.initials')}
                        </button>
                      </div>

                      <div class="mt-4 grid max-h-72 grid-cols-3 gap-2 overflow-y-auto pr-1 sm:grid-cols-4">
                        {#each AVATAR_OPTIONS as option, index}
                          {@const avatarOptionLabel = $_('parent.childEdit.avatarOption', { values: { number: index + 1 } })}
                          {@const selected = childEditForm.avatar_name === option.key}
                          <button
                            type="button"
                            onclick={() => setChildEditAvatar(option.key)}
                            class="flex min-w-0 flex-col items-center gap-2 rounded-2xl border bg-white p-2 text-center transition {selected ? 'border-hero ring-2 ring-hero/15' : 'border-slate-200 hover:border-hero/50'}"
                            aria-pressed={selected}
                          >
                            <div class="flex h-16 w-16 items-center justify-center overflow-hidden rounded-2xl bg-slate-50">
                              <img
                                src={option.path}
                                alt={avatarOptionLabel}
                                class="h-full w-full object-cover"
                                loading="lazy"
                              />
                            </div>
                            <span class="w-full truncate text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                              {avatarOptionLabel}
                            </span>
                          </button>
                        {/each}
                      </div>
                    </div>

                    <div class="flex items-center gap-3 rounded-2xl bg-white p-3">
                      <div class="flex h-14 w-14 shrink-0 items-center justify-center overflow-hidden rounded-full bg-slate-100 text-lg font-bold text-slate-950">
                        {#if editAvatar}
                          <img
                            src={editAvatar.path}
                            alt={$_('parent.childEdit.avatarPreviewAlt', { values: { name: childEditForm.display_name || activeModal.child.child.display_name } })}
                            class="h-full w-full object-cover"
                          />
                        {:else}
                          <span>{(childEditForm.display_name.trim() || activeModal.child.child.display_name || '?').slice(0, 1).toUpperCase()}</span>
                        {/if}
                      </div>
                      <div class="min-w-0">
                        <p class="text-sm font-bold text-slate-950">{$_('parent.childEdit.preview')}</p>
                        <p class="text-xs font-bold text-slate-400">{$_('parent.childEdit.savedHint')}</p>
                      </div>
                    </div>
                  </div>

                  <div class="mt-4 flex flex-col gap-3 sm:flex-row">
                    <button
                      type="button"
                      onclick={saveChildEdit}
                      disabled={childEditLoading || !childEditForm.display_name.trim()}
                      class="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-slate-900 px-4 py-4 text-xs font-semibold uppercase tracking-wide text-white disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {childEditLoading ? $_('common.saving') : $_('parent.childEdit.saveChild')}
                    </button>
                    <button
                      type="button"
                      onclick={() => (childEditOpen = false)}
                      class="inline-flex w-full items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-4 text-xs font-semibold uppercase tracking-wide text-slate-700"
                    >
                      {$_('common.cancel')}
                    </button>
                  </div>
                </div>
              {/if}

              <div class="grid grid-cols-2 gap-2 rounded-2xl bg-slate-100 p-2 sm:grid-cols-3">
                {#each [
                  ['points', $_('parent.tabs.points')],
                  ['requests', $_('parent.tabs.requests')],
                  ['school', $_('parent.tabs.schoolBag')],
                  ['calendar', $_('parent.tabs.calendar')],
                  ['savings', $_('parent.tabs.savings')],
                  ['points-log', $_('parent.tabs.pointsLog')]
                ] as tab}
                  <button
                    type="button"
                    onclick={() => setChildModalTab(tab[0])}
                    class="min-w-0 rounded-xl px-2.5 py-3 text-[10px] font-semibold uppercase tracking-wide leading-tight whitespace-normal transition-all sm:px-4 sm:py-3.5 sm:text-[10px] {childModalTab === tab[0] ? 'bg-hero text-white shadow-md shadow-hero/20' : 'text-slate-500 hover:bg-white/70 hover:text-hero'}"
                  >
                    <span class="block min-w-0 break-words text-center">{tab[1]}</span>
                  </button>
                {/each}
              </div>

            </div>
          {/if}

          {#if activeModal.type === 'child-link'}
            <div class="space-y-4">
              <div class="rounded-[1.75rem] border border-slate-100 bg-slate-50 p-5">
                <p class="text-[10px] font-semibold uppercase tracking-wide text-slate-400">{$_('parent.childLink.child')}</p>
                <p class="mt-2 text-2xl font-bold text-slate-950 break-words">{activeModal.child.child.display_name}</p>
                <p class="mt-2 text-sm text-slate-600">{$_('parent.childLink.qrHelp')}</p>
              </div>

              {#if childLinkLoading && !childLinkInvite}
                <div class="rounded-[1.75rem] border border-dashed border-slate-200 bg-white p-8 text-center">
                  <div class="mx-auto w-12 h-12 rounded-2xl bg-slate-100 flex items-center justify-center animate-pulse">
                    <QrCode size={22} class="text-slate-400" />
                  </div>
                  <p class="mt-4 text-sm font-semibold uppercase tracking-wide text-slate-400">{$_('parent.childLink.generatingQr')}</p>
                </div>
              {:else if childLinkError}
                <div class="rounded-[1.75rem] border border-red-100 bg-red-50 p-5 text-red-700 font-bold break-words">
                  {childLinkError}
                </div>
              {:else if childLinkInvite}
                <div class="rounded-[1.75rem] border border-slate-100 bg-white p-5 space-y-5">
              <div class="flex flex-col items-center gap-4">
                <div class="rounded-[1.5rem] border border-slate-100 bg-white p-4 shadow-sm w-full max-w-[18rem] sm:max-w-[20rem] flex justify-center">
                  {#if childLinkQr}
                    <img src={childLinkQr} alt={$_('parent.childLink.qrAlt')} class="w-full h-auto rounded-2xl" />
                  {/if}
                </div>
                    <div class="text-center">
                      <p class="text-[10px] font-semibold uppercase tracking-wide text-slate-400">{$_('parent.childLink.expires')}</p>
                      <p class="text-lg font-bold text-slate-950 break-words">{new Date(childLinkInvite.expires_at).toLocaleString($locale || 'en')}</p>
                    </div>
                  </div>

                  <div class="space-y-2">
                    <p class="text-[10px] font-semibold uppercase tracking-wide text-slate-400 ml-1">{$_('parent.childLink.fallbackLink')}</p>
                    <div class="flex flex-col sm:flex-row gap-2">
                      <input
                        readonly
                        value={childLinkInvite.invite_url}
                        class="min-w-0 flex-1 rounded-2xl border-2 border-slate-100 bg-slate-50 px-4 py-3 text-sm font-medium text-slate-700 break-all"
                      />
                      <button
                        type="button"
                        onclick={copyChildInviteLink}
                        class="inline-flex w-full sm:w-auto items-center justify-center gap-2 rounded-2xl bg-slate-900 px-4 py-3 text-xs font-semibold uppercase tracking-wide text-white shrink-0"
                      >
                        <Copy size={14} />
                        {childLinkCopied ? $_('parent.childLink.copied') : $_('parent.childLink.copy')}
                      </button>
                    </div>
                  </div>

                  <div class="flex flex-col sm:flex-row gap-3">
                    <button
                      type="button"
                      onclick={regenerateChildLink}
                      class="inline-flex w-full sm:w-auto items-center justify-center gap-2 rounded-2xl bg-hero px-4 py-3 text-xs font-semibold uppercase tracking-wide text-white shadow-lg shadow-hero/20"
                    >
                      <RefreshCcw size={14} />
                      {$_('parent.childLink.regenerateQr')}
                    </button>
                    <button
                      type="button"
                      onclick={revokeChildLink}
                      class="inline-flex w-full sm:w-auto items-center justify-center gap-2 rounded-2xl bg-white px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-700 border-2 border-slate-100"
                    >
                      <Link2 size={14} />
                      {$_('parent.childLink.revokeAccess')}
                    </button>
                  </div>
                </div>
              {:else}
                <div class="rounded-[1.75rem] border border-dashed border-slate-200 bg-white p-8 text-center space-y-4">
                  <div class="mx-auto w-12 h-12 rounded-2xl bg-slate-100 flex items-center justify-center">
                    <QrCode size={22} class="text-slate-400" />
                  </div>
                  <div>
                    <p class="text-sm font-semibold uppercase tracking-wide text-slate-400">{$_('parent.childLink.noActiveQr')}</p>
                    <p class="text-sm text-slate-500 mt-2">{$_('parent.childLink.freshLinkHelp')}</p>
                  </div>
                  <button
                    type="button"
                    onclick={regenerateChildLink}
                    class="inline-flex w-full sm:w-auto items-center justify-center gap-2 rounded-2xl bg-hero px-4 py-3 text-xs font-semibold uppercase tracking-wide text-white shadow-lg shadow-hero/20"
                  >
                    <RefreshCcw size={14} />
                    {$_('parent.childLink.regenerateQr')}
                  </button>
                </div>
              {/if}

              <div class="rounded-[1.75rem] border border-slate-100 bg-white p-5 space-y-4">
                <div class="flex items-center justify-between gap-3">
                  <div class="min-w-0">
                    <p class="text-[10px] font-semibold uppercase tracking-wide text-slate-400">{$_('parent.childLink.linkedDevices')}</p>
                    <p class="mt-1 text-sm text-slate-600">{$_('parent.childLink.linkedDevicesHelp')}</p>
                  </div>
                  <button
                    type="button"
                    onclick={() => loadChildDevices(activeModal.child)}
                    disabled={childDevicesLoading}
                    class="shrink-0 rounded-2xl border border-slate-100 bg-slate-50 px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-slate-600 disabled:opacity-60"
                  >
                    {childDevicesLoading ? $_('common.loading') : $_('parent.childLink.refresh')}
                  </button>
                </div>

                {#if childDevicesError}
                  <div class="rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm font-bold text-red-700 break-words">
                    {childDevicesError}
                  </div>
                {/if}

                {#if childDevicesLoading && childDevices.length === 0}
                  <div class="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm font-bold text-slate-400">
                    {$_('parent.childLink.loadingDevices')}
                  </div>
                {:else if childDevices.length === 0}
                  <div class="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm font-bold text-slate-400">
                    {$_('parent.childLink.noLinkedDevices')}
                  </div>
                {:else}
                  <div class="space-y-2">
                    {#each childDevices as device}
                      <div class="flex flex-col gap-3 rounded-2xl border border-slate-100 bg-slate-50 p-4 sm:flex-row sm:items-center sm:justify-between">
                        <div class="min-w-0">
                          <p class="text-sm font-bold text-slate-900">{childLinkDeviceLabel(device)} #{device.id}</p>
                          <p class="mt-1 text-xs font-bold text-slate-500">{$_('parent.childLink.lastSeen')} {formatDeviceDate(device.last_seen_at)}</p>
                          <p class="text-xs font-bold text-slate-400">{$_('parent.childLink.expiresLabel')} {formatDeviceDate(device.expires_at)}</p>
                        </div>
                        <button
                          type="button"
                          onclick={() => unlinkChildDevice(device)}
                          disabled={childDeviceUnlinkingId === device.id}
                          class="inline-flex w-full items-center justify-center gap-2 rounded-2xl border-2 border-slate-100 bg-white px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-700 disabled:opacity-60 sm:w-auto"
                        >
                          <Link2 size={14} />
                          {childDeviceUnlinkingId === device.id ? $_('parent.childLink.removing') : $_('parent.childLink.unlink')}
                        </button>
                      </div>
                    {/each}
                  </div>
                {/if}
              </div>
            </div>
          {/if}

          {#if activeModal.type === 'child-link-select'}
            <div class="space-y-3">
              {#if children.length === 0}
                <div class="rounded-[1.75rem] border border-dashed border-slate-200 bg-slate-50 p-6 text-center">
                  <p class="text-sm font-semibold uppercase tracking-wide text-slate-400">{$_('parent.childLink.noChildren')}</p>
                </div>
              {:else}
                {#each children as childSummary}
                  <button
                    type="button"
                    onclick={() => openChildLink(childSummary)}
                    class="inline-flex w-full items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 text-left font-bold text-slate-800 transition hover:border-hero hover:text-hero"
                  >
                    <span class="min-w-0 truncate">{childSummary.child.display_name}</span>
                    <QrCode size={16} class="shrink-0" />
                  </button>
                {/each}
              {/if}
            </div>
          {/if}

          {#if activeModal.type === 'rewards'}
            <div class="space-y-5">
              {#if rewardError}
                <div class="rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm font-bold text-red-700 break-words">
                  {rewardError}
                </div>
              {/if}

              <section class="rounded-[1.75rem] border border-slate-100 bg-slate-50 p-5">
                <div class="flex items-center justify-between gap-4 mb-5">
                  <div class="min-w-0">
                    <p class="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-2">{$_('parent.rewards.editor')}</p>
                    <h4 class="text-xl font-bold text-slate-950">{editingRewardId ? $_('parent.rewards.edit') : $_('parent.rewards.create')}</h4>
                  </div>
                  <Gift size={20} class="shrink-0 text-reward" />
                </div>

                <div class="space-y-4">
                  <label class="block">
                    <span class="block text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-2">{$_('parent.rewards.name')}</span>
                    <input type="text" bind:value={rewardForm.title} placeholder={$_('parent.rewards.moviePlaceholder')} class="w-full rounded-2xl border-2 border-slate-200 bg-white px-4 py-4 text-slate-900 font-bold focus:outline-none focus:border-hero/30" />
                  </label>

                  <label class="block">
                    <span class="block text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-2">{$_('parent.rewards.description')}</span>
                    <input type="text" bind:value={rewardForm.description} placeholder={$_('parent.rewards.descriptionPlaceholder')} class="w-full rounded-2xl border-2 border-slate-200 bg-white px-4 py-4 text-slate-900 font-bold focus:outline-none focus:border-hero/30" />
                  </label>

                  <label class="block">
                    <span class="block text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-2">{$_('common.points')}</span>
                    <input type="number" min="1" bind:value={rewardForm.points} class="w-full rounded-2xl border-2 border-slate-200 bg-white px-4 py-4 text-slate-900 font-bold focus:outline-none focus:border-hero/30" />
                  </label>

                  <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    <button type="button" onclick={saveReward} disabled={rewardLoading || !rewardForm.title.trim() || rewardForm.points < 1} class="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-slate-900 px-4 py-4 text-xs font-semibold uppercase tracking-wide text-white disabled:cursor-not-allowed disabled:opacity-60">
                      {editingRewardId ? $_('parent.rewards.save') : $_('parent.rewards.createButton')}
                    </button>
                    <button type="button" onclick={() => rewardForm.is_active = !rewardForm.is_active} class="inline-flex w-full items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-4 text-xs font-semibold uppercase tracking-wide text-slate-700">
                      {rewardForm.is_active ? $_('common.active') : $_('common.hidden')}
                    </button>
                  </div>
                  {#if editingRewardId}
                    <button type="button" onclick={cancelEditingReward} class="w-full rounded-2xl px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-400 transition hover:text-slate-700">
                      {$_('common.cancel')}
                    </button>
                  {/if}
                </div>
              </section>

              <section class="space-y-3">
                <p class="text-[10px] font-semibold uppercase tracking-wide text-slate-400 ml-1">{$_('parent.rewards.current')}</p>
                {#if rewards.length > 0}
                  {#each rewards as reward}
                    <div class="rounded-[1.5rem] border border-slate-100 bg-white p-4">
                      <div class="flex min-w-0 items-start justify-between gap-3">
                        <div class="min-w-0">
                          <h4 class="font-bold text-slate-950 break-words">{reward.title}</h4>
                          <p class="mt-1 text-sm text-slate-500 break-words">{reward.description || $_('common.noDescription')}</p>
                          <div class="mt-3 inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-slate-600">
                            <Trophy size={13} />
                            {reward.points} {$_('common.points')}
                          </div>
                        </div>
                        <span class={`shrink-0 rounded-2xl px-3 py-2 text-[10px] font-semibold uppercase tracking-wide ${reward.is_active ? 'bg-savings/10 text-savings' : 'bg-slate-100 text-slate-400'}`}>
                          {reward.is_active ? $_('common.visible') : $_('common.hidden')}
                        </span>
                      </div>
                      <div class="mt-4 flex flex-wrap gap-2">
                        <button onclick={() => startEditingReward(reward)} class="inline-flex items-center gap-2 rounded-2xl bg-slate-50 px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-slate-700 border border-slate-100">
                          <Settings size={14} />
                          {$_('common.edit')}
                        </button>
                        <button onclick={() => deleteReward(reward.id)} class="inline-flex items-center gap-2 rounded-2xl bg-white px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-penalty border border-slate-100">
                          <X size={14} />
                          {$_('common.delete')}
                        </button>
                      </div>
                    </div>
                  {/each}
                {:else}
                  <div class="rounded-[1.75rem] border border-dashed border-slate-200 bg-slate-50 p-6 text-center">
                    <p class="text-sm font-semibold uppercase tracking-wide text-slate-400">{$_('parent.rewards.noRewards')}</p>
                  </div>
                {/if}
              </section>
            </div>
          {/if}

          {#if activeModal.type === 'requests'}
            <div class="space-y-4">
              <div class="flex items-center justify-between gap-3 rounded-[1.75rem] border border-slate-100 bg-slate-50 p-4">
                <span class="text-sm font-semibold uppercase tracking-wide text-slate-500">{$_('common.pending')}</span>
                <span class="rounded-2xl bg-hero/10 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-hero">{pendingRedemptions.length}</span>
              </div>

              {#if pendingRedemptions.length === 0}
                <div class="rounded-[1.75rem] border border-dashed border-slate-200 bg-slate-50 p-6 text-center">
                  <p class="text-sm font-semibold uppercase tracking-wide text-slate-400">{$_('parent.requests.noPending')}</p>
                </div>
              {:else}
                {#each pendingRedemptions as r}
                  {@const child = children.find((ch) => ch.child.id === r.child_id)}
                  <div class="rounded-[1.5rem] border border-slate-100 bg-white p-4">
                    <div class="flex flex-wrap items-center gap-2">
                      <span class="inline-flex items-center rounded-full bg-hero/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-hero">{$_('common.pending')}</span>
                      <span class="text-[10px] font-semibold uppercase tracking-wide text-slate-400">{new Date(r.created_at).toLocaleDateString($locale || 'en')}</span>
                    </div>
                    <h4 class="mt-3 font-bold text-slate-950 break-words">{r.title}</h4>
                    <p class="mt-2 text-sm text-slate-600 break-words">{r.description || $_('common.noDescriptionProvided')}</p>
                    <div class="mt-4 flex flex-wrap items-center gap-2">
                      <span class="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-slate-700">
                        {child?.child.display_name || $_('common.unknownChild')}
                      </span>
                      <span class="inline-flex items-center gap-2 rounded-full bg-hero/10 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-hero">
                        <Trophy size={13} />
                        {r.points} {$_('common.points')}
                      </span>
                    </div>
                    <div class="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
                      <button onclick={() => processRedemption(r.id, 'approve')} class="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-savings px-4 py-4 text-xs font-semibold uppercase tracking-wide text-white shadow-lg shadow-savings/20">
                        <Check size={16} />
                        {$_('common.approve')}
                      </button>
                      <button onclick={() => processRedemption(r.id, 'reject')} class="inline-flex w-full items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-4 text-xs font-semibold uppercase tracking-wide text-slate-700">
                        <X size={16} />
                        {$_('common.reject')}
                      </button>
                    </div>
                  </div>
                {/each}
              {/if}
            </div>
          {/if}

          {#if activeModal.type === 'family'}
            {#if loadingFamilySettings}
              <div class="rounded-[1.75rem] border border-dashed border-slate-200 bg-slate-50 p-6 text-center">
                <div class="mx-auto mb-4 w-10 h-10 animate-spin rounded-full border-4 border-hero border-t-transparent"></div>
                <p class="text-sm font-semibold uppercase tracking-wide text-slate-400">{$_('parent.family.refreshing')}</p>
              </div>
            {/if}

            <!-- Invite Form -->
            <div class="space-y-3 pt-4 border-t border-slate-100">
              <label for="co-parent-email" class="text-[10px] font-bold text-slate-400 uppercase tracking-wide ml-2">{$_('parent.family.emailLabel')}</label>
              <div class="space-y-2">
                <input 
                  id="co-parent-email"
                  type="email" 
                  bind:value={modalForm.email}
                  placeholder={$_('parent.family.emailPlaceholder')}
                  class="w-full bg-slate-50 border-2 border-slate-100 rounded-2xl px-6 py-4 font-bold text-slate-900 focus:outline-none focus:border-hero/30 transition-all"
                />
                <p class="text-[10px] text-slate-400 ml-2">{$_('parent.family.inviteHelp')}</p>
              </div>
            </div>

            <!-- Pending Invites -->
            {#if familyInvites.filter(i => i.status === 'pending').length > 0}
              <div class="space-y-3 pt-4 border-t border-slate-100">
                <span class="block text-[10px] font-bold text-slate-400 uppercase tracking-wide ml-2">{$_('parent.family.pendingInvites')}</span>
                <div class="grid gap-2">
                  {#each familyInvites.filter(i => i.status === 'pending') as invite}
                    <div class="flex min-w-0 items-start justify-between gap-3 p-4 bg-slate-50 rounded-2xl border-2 border-dashed border-slate-200">
                      <div class="min-w-0">
                        <p class="font-bold text-slate-900 text-sm break-all">{invite.email}</p>
                        <p class="text-[10px] text-slate-400 font-medium uppercase tracking-wider">{$_('parent.family.waitingForLogin')}</p>
                      </div>
                      <button onclick={() => revokeInvite(invite.id)} class="shrink-0 rounded-xl border border-slate-200 bg-white px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-slate-500 transition-colors hover:border-red-100 hover:bg-red-50 hover:text-red-500" aria-label={$_('parent.family.cancelInvite')}>
                        {$_('parent.family.cancelInvite')}
                      </button>
                    </div>
                  {/each}
                </div>
              </div>
            {/if}

            <!-- Members List -->
            <div class="space-y-3">
              <span class="block text-[10px] font-bold text-slate-400 uppercase tracking-wide ml-2">{$_('parent.family.currentGrownups')}</span>
              <div class="grid gap-2">
                {#each familyMembers as member}
                  <div class="flex min-w-0 flex-col gap-3 p-4 bg-slate-50 rounded-2xl">
                    <div class="flex min-w-0 items-start gap-3">
                      <div class="w-10 h-10 bg-white rounded-xl flex shrink-0 items-center justify-center text-hero font-bold shadow-sm">
                        {member.name ? member.name[0].toUpperCase() : member.email[0].toUpperCase()}
                      </div>
                      <div class="min-w-0 flex-1">
                        <p class="font-bold text-slate-900 text-sm truncate">{member.name || $_('parent.family.parentFallback')}</p>
                        <p class="text-[10px] text-slate-400 font-medium uppercase tracking-normal sm:tracking-wider break-all">{member.email}</p>
                      </div>
                      {#if member.id === parent?.id}
                        <span class="shrink-0 px-3 py-1 bg-hero/10 text-hero rounded-lg text-[10px] font-semibold uppercase tracking-wide">{$_('parent.family.you')}</span>
                      {/if}
                    </div>
                    {#if member.can_remove}
                      <button
                        type="button"
                        onclick={() => removeGrownup(member)}
                        disabled={familyGrownupRemovingId === member.id}
                        class="self-start rounded-xl border border-red-100 bg-white px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-red-500 transition-colors hover:bg-red-50 disabled:opacity-50"
                      >
                        {familyGrownupRemovingId === member.id ? $_('common.removing') : $_('common.remove')}
                      </button>
                    {/if}
                  </div>
                {/each}
              </div>
            </div>
          {/if}

          {#if activeModal.type === 'calendar-week'}
            {#if loadingFamilySettings}
              <div class="rounded-[1.75rem] border border-dashed border-slate-200 bg-slate-50 p-6 text-center">
                <div class="mx-auto mb-4 w-10 h-10 animate-spin rounded-full border-4 border-hero border-t-transparent"></div>
                <p class="text-sm font-semibold uppercase tracking-wide text-slate-400">{$_('parent.week.loading')}</p>
              </div>
            {/if}
            <div class="space-y-3">
              <div class="rounded-[1.75rem] border border-slate-100 bg-white p-4">
                <p class="text-[10px] font-semibold uppercase tracking-wide text-slate-400">{$_('parent.calendarSchoolWeek')}</p>
                <p class="mt-2 text-sm font-bold text-slate-600">{$_('parent.week.text')}</p>
                <div class="mt-4">
                  <label for="family-week-start" class="mb-2 block text-[10px] font-semibold uppercase tracking-wide text-slate-400">{$_('parent.week.startsOn')}</label>
                  <div class="flex flex-col gap-3 sm:flex-row">
                    <select
                      id="family-week-start"
                      bind:value={familySettingsForm.week_start_day}
                      disabled={loadingFamilySettings || familySettingsSaving || !familySettings}
                      class="w-full rounded-2xl border-2 border-slate-100 bg-slate-50 px-4 py-3 text-sm font-bold text-slate-900 focus:border-hero/30 focus:outline-none disabled:opacity-50"
                    >
                      {#each WEEK_START_OPTIONS as option}
                        <option value={option}>{weekStartLabel(option)}</option>
                      {/each}
                    </select>
                    <button
                      type="button"
                      onclick={saveFamilySettings}
                      disabled={loadingFamilySettings || familySettingsSaving || !familySettings || familySettingsForm.week_start_day === familySettings.week_start_day}
                      class="rounded-2xl bg-slate-900 px-5 py-3 text-xs font-semibold uppercase tracking-wide text-white transition-all disabled:opacity-50"
                    >
                      {familySettingsSaving ? $_('common.saving') : $_('common.save')}
                    </button>
                  </div>
                  <p class="mt-2 text-[10px] font-semibold uppercase tracking-wide text-slate-400">{$_('parent.week.usedFor')}</p>
                </div>
                {#if familySettingsMessage}
                  <p class="mt-3 text-xs font-bold text-hero">{familySettingsMessage}</p>
                {/if}
                {#if familySettingsError}
                  <p class="mt-3 text-xs font-bold text-penalty">{familySettingsError}</p>
                {/if}
              </div>
            </div>
          {/if}

          {#if activeModal.type === 'picker'}
            {#if childModalTab === 'points'}
              <div class="space-y-4">
              <div class="flex gap-2 rounded-2xl bg-hero/5 p-1 ring-1 ring-hero/10">
                <button
                  onclick={() => activeTab = 'positive'}
                  class="min-w-0 flex-1 rounded-xl px-2 py-2.5 text-[10px] font-bold uppercase leading-none tracking-wide transition-all sm:px-4 sm:py-3 sm:text-[10px] {activeTab === 'positive' ? 'bg-savings/15 text-savings shadow-sm ring-1 ring-savings/10' : 'text-slate-500 hover:bg-white/70 hover:text-savings'}"
                >
                  {$_('common.add')}
                </button>
                <button
                  onclick={() => activeTab = 'negative'}
                  class="min-w-0 flex-1 rounded-xl px-2 py-2.5 text-[10px] font-bold uppercase leading-none tracking-wide transition-all sm:px-4 sm:py-3 sm:text-[10px] {activeTab === 'negative' ? 'bg-penalty/15 text-penalty shadow-sm ring-1 ring-penalty/10' : 'text-slate-500 hover:bg-white/70 hover:text-penalty'}"
                >
                  {$_('common.remove')}
                </button>
                <button 
                  onclick={() => activeTab = 'other'}
                  class="min-w-0 flex-1 rounded-xl px-2 py-2.5 text-[10px] font-bold uppercase leading-none tracking-wide transition-all sm:px-4 sm:py-3 sm:text-[10px] {activeTab === 'other' ? 'bg-hero/15 text-hero shadow-sm ring-1 ring-hero/10' : 'text-slate-500 hover:bg-white/70 hover:text-hero'}"
                >
                  {$_('parent.pointsActions.custom')}
                </button>
                </div>

                {#if activeTab === 'other'}
                  <div class="space-y-4 pb-4">
                    <div class="space-y-2">
                      <label for="custom-points-description" class="text-[10px] font-bold text-slate-400 uppercase tracking-wide ml-2">{$_('parent.pointsActions.reason')}</label>
                      <textarea
                        id="custom-points-description"
                        bind:value={modalForm.description}
                        placeholder={$_('parent.pointsActions.reasonPlaceholder')}
                        rows="3"
                        class="w-full bg-slate-50 border-2 border-slate-100 rounded-2xl px-5 py-4 font-medium text-slate-900 focus:outline-none focus:border-hero/30 transition-all resize-none"
                      ></textarea>
                    </div>

                    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
                      <div class="space-y-2">
                        <label for="custom-points-amount" class="text-[10px] font-bold text-slate-400 uppercase tracking-wide ml-2">{$_('common.points')}</label>
                        <div class="relative">
                          <input
                            id="custom-points-amount"
                            type="number"
                            min="1"
                            bind:value={modalForm.points}
                            class="w-full bg-slate-50 border-2 border-slate-100 rounded-2xl px-5 py-4 pr-12 font-bold text-slate-900 focus:outline-none focus:border-hero/30 transition-all text-2xl"
                          />
                          <span class="absolute right-5 top-1/2 -translate-y-1/2 font-bold text-slate-300 text-sm">{$_('common.pts')}</span>
                        </div>
                      </div>

                      <div class="space-y-2">
                        <label for="custom-points-jar" class="text-[10px] font-bold text-slate-400 uppercase tracking-wide ml-2">{$_('parent.pointsActions.pointDestination')}</label>
                        <select
                          id="custom-points-jar"
                          bind:value={modalForm.jar}
                          class="w-full bg-slate-50 border-2 border-slate-100 rounded-2xl px-5 py-4 font-bold text-slate-900 focus:outline-none focus:border-hero/30 transition-all appearance-none cursor-pointer"
                        >
                          <option value="spending">{$_('common.points')}</option>
                          <option value="savings">{$_('common.saved')}</option>
                        </select>
                      </div>
                    </div>

                    <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
                      <button
                        type="button"
                        onclick={() => submitCustomPoints('award')}
                        disabled={modalLoading || Math.abs(Number(modalForm.points) || 0) < 1}
                        class="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-savings px-4 py-4 text-xs font-semibold uppercase tracking-wide text-white shadow-lg shadow-savings/20 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        <Award size={16} />
                        {$_('parent.pointsActions.addPoints')}
                      </button>
                      <button
                        type="button"
                        onclick={() => submitCustomPoints('penalty')}
                        disabled={modalLoading || Math.abs(Number(modalForm.points) || 0) < 1}
                        class="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-penalty px-4 py-4 text-xs font-semibold uppercase tracking-wide text-white shadow-lg shadow-penalty/20 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        <Ban size={16} />
                        {$_('parent.pointsActions.removePoints')}
                      </button>
                    </div>
                  </div>
                {:else}
                  <div class="grid grid-cols-2 md:grid-cols-3 gap-3 sm:gap-4 pb-4">
                    {#each presets.filter(p => p.is_active && (activeTab === 'positive' ? p.points > 0 : p.points < 0)) as p}
                      <button
                        onclick={() => applyPreset(activeModal.child, p)}
                        title={p.title}
                        class="group flex min-h-40 flex-col items-center gap-2 rounded-3xl border-2 p-3 text-center transition-all sm:min-h-44 sm:p-4 {p.points > 0 ? 'border-slate-50 hover:border-savings/20 hover:bg-savings/5' : 'border-slate-50 hover:border-penalty/20 hover:bg-penalty/5'}"
                      >
                        <div class="text-4xl mb-1 h-12 flex items-center justify-center">
                          {p.icon || '✨'}
                        </div>
                        <div class="rounded-lg px-2 py-0.5 text-xs font-bold {p.points > 0 ? 'bg-savings text-white' : 'bg-penalty text-white'}">
                          {p.points > 0 ? '+' : ''}{p.points} {$_('common.pts')}
                        </div>
                        <div class="min-w-0 mt-1">
                          <p class="font-bold text-slate-900 text-[11px] leading-tight uppercase tracking-tight line-clamp-2">{p.title}</p>
                        </div>
                      </button>
                    {:else}
                      <div class="col-span-full py-12 text-center text-slate-300">
                        <p class="font-semibold uppercase tracking-wide text-xs">{$_('parent.pointsActions.noPresets')}</p>
                        <button onclick={() => openModal('presets', null)} class="text-hero text-[10px] font-semibold uppercase tracking-wide mt-2 hover:underline">
                          {$_('parent.pointsActions.addPreset')}
                        </button>
                      </div>
                    {/each}
                  </div>
                {/if}
              </div>
            {/if}

            {#if childModalTab === 'requests'}
              {@const childRequests = childPendingRequests(activeModal.child)}
              <div class="space-y-4">
                {#if childRequests.length === 0}
                  <div class="rounded-[1.75rem] border border-dashed border-slate-200 bg-slate-50 p-6 text-center">
                    <p class="text-sm font-semibold uppercase tracking-wide text-slate-400">{$_('parent.requests.noPending')}</p>
                  </div>
                {:else}
                  {#each childRequests as r}
                    <div class="rounded-[1.5rem] border border-slate-100 bg-white p-4">
                      <div class="flex flex-wrap items-center gap-2">
                        <span class="inline-flex items-center rounded-full bg-hero/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-hero">{$_('common.pending')}</span>
                        <span class="text-[10px] font-semibold uppercase tracking-wide text-slate-400">{new Date(r.created_at).toLocaleDateString($locale || 'en')}</span>
                      </div>
                      <h4 class="mt-3 font-bold text-slate-950 break-words">{r.title}</h4>
                      <p class="mt-2 text-sm text-slate-600 break-words">{r.description || $_('common.noDescriptionProvided')}</p>
                      <div class="mt-3 inline-flex items-center gap-2 rounded-full bg-hero/10 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-hero">
                        <Trophy size={13} />
                        {r.points} {$_('common.points')}
                      </div>
                      <div class="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
                        <button onclick={() => processRedemption(r.id, 'approve')} class="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-savings px-4 py-4 text-xs font-semibold uppercase tracking-wide text-white shadow-lg shadow-savings/20">
                          <Check size={16} />
                          {$_('common.approve')}
                        </button>
                        <button onclick={() => processRedemption(r.id, 'reject')} class="inline-flex w-full items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-4 text-xs font-semibold uppercase tracking-wide text-slate-700">
                          <X size={16} />
                          {$_('common.reject')}
                        </button>
                      </div>
                    </div>
                  {/each}
                {/if}
                <a href="/redemptions" class="inline-flex w-full items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-700 transition hover:border-hero hover:text-hero">
                  <Check size={15} />
                  <span class="sm:hidden">{$_('parent.requests.reviewRewardRequests')}</span>
                  <span class="hidden sm:inline">{$_('parent.requests.openReview')}</span>
                </a>
              </div>
            {/if}

            {#if childModalTab === 'school'}
              {@const todayItems = schoolTodayByChild[activeModal.child.child.id] || []}
              {@const tomorrowItems = schoolTomorrowByChild[activeModal.child.child.id] || []}
              <div class="grid gap-4 sm:grid-cols-2">
                {#each ([['Today', todayItems], ['Tomorrow', tomorrowItems]] as [string, SchoolItem[]][]) as group}
                  <div class="rounded-[1.75rem] border border-slate-100 bg-white p-4">
                    <p class="text-[10px] font-semibold uppercase tracking-wide text-slate-400">{group[0] === 'Today' ? $_('common.today') : $_('common.tomorrow')}</p>
                    {#if loadingSchoolPrep}
                      <p class="mt-4 text-sm font-bold text-slate-400">{$_('parent.school.loading')}</p>
                    {:else if group[1].length === 0}
                      <p class="mt-4 text-sm font-bold text-slate-500">{$_('parent.school.nothingListed')}</p>
                    {:else}
                      <div class="mt-4 space-y-2">
                        {#each group[1] as item}
                          <div class="rounded-2xl bg-slate-50 p-3">
                            <p class="text-sm font-bold text-slate-950">{schoolNeedLabel(item)}</p>
                            <p class="mt-1 text-xs font-bold text-slate-400">{item.class_name}</p>
                          </div>
                        {/each}
                      </div>
                    {/if}
                  </div>
                {/each}
              </div>
            {/if}

            {#if childModalTab === 'calendar'}
              {@const todayEvents = todayCalendarItems(activeModal.child)}
              {@const upcomingEvents = upcomingCalendarItems(activeModal.child)}
              <div class="space-y-4">
                {#if childCalendarLoading[activeModal.child.child.id]}
                  <div class="rounded-[1.75rem] border border-dashed border-slate-200 bg-slate-50 p-6 text-center">
                    <p class="text-sm font-semibold uppercase tracking-wide text-slate-400">{$_('calendar.loadingTitle')}</p>
                  </div>
                {:else if childCalendarError[activeModal.child.child.id]}
                  <div class="rounded-[1.75rem] border border-red-100 bg-red-50 p-5 text-sm font-bold text-red-700">
                    {childCalendarError[activeModal.child.child.id]}
                  </div>
                {:else}
                  <div class="rounded-[1.75rem] border border-slate-100 bg-white p-4">
                    <p class="text-[10px] font-semibold uppercase tracking-wide text-slate-400">{$_('common.today')}</p>
                    {#if todayEvents.length === 0}
                      <p class="mt-4 text-sm font-bold text-slate-500">{$_('calendar.noTodayItems')}</p>
                    {:else}
                      <div class="mt-4 space-y-2">
                        {#each todayEvents as item}
                          <div class="rounded-2xl bg-slate-50 p-3">
                            <p class="break-words text-sm font-bold leading-snug text-slate-950">{item.entry.title}</p>
                            <p class="mt-1 break-words text-xs font-bold leading-snug text-slate-400">{formatCalendarTime(item.entry.start_time)} · {calendarEntryTypeLabel(item.entry.entry_type)}</p>
                          </div>
                        {/each}
                      </div>
                    {/if}
                  </div>
                  <div class="rounded-[1.75rem] border border-slate-100 bg-white p-4">
                    <p class="text-[10px] font-semibold uppercase tracking-wide text-slate-400">{$_('common.upcoming')}</p>
                    {#if upcomingEvents.length === 0}
                      <p class="mt-4 text-sm font-bold text-slate-500">{$_('calendar.noUpcomingItems')}</p>
                    {:else}
                      <div class="mt-4 space-y-2">
                        {#each upcomingEvents as item}
                          <div class="rounded-2xl bg-slate-50 p-3">
                            <p class="break-words text-sm font-bold leading-snug text-slate-950">{item.entry.title}</p>
                            <p class="mt-1 break-words text-xs font-bold leading-snug text-slate-400">{formatCalendarDate(item.occurrence_date)} · {formatCalendarTime(item.entry.start_time)}</p>
                          </div>
                        {/each}
                      </div>
                    {/if}
                  </div>
                {/if}
                <a href="/calendar" class="inline-flex w-full items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-700 transition hover:border-hero hover:text-hero">
                  <CalendarDays size={15} />
                  <span class="sm:hidden">{$_('parent.tabs.calendar')}</span>
                  <span class="hidden sm:inline">{$_('parent.calendar')}</span>
                </a>
              </div>
            {/if}

            {#if childModalTab === 'savings'}
              {@const allowance = childAllowance(activeModal.child)}
              {@const unlock = nextSavingsUnlock(activeModal.child)}
              <div class="space-y-4">
                <div class="grid grid-cols-2 gap-3">
                  <div class="rounded-[1.5rem] bg-slate-50 p-4">
                    <p class="text-[10px] font-semibold uppercase tracking-wide text-slate-400">{$_('common.saved')}</p>
                    <p class="mt-2 text-2xl font-bold text-slate-950">{activeModal.child.savings_balance || 0}</p>
                  </div>
                  <div class="rounded-[1.5rem] bg-slate-50 p-4">
                    <p class="text-[10px] font-semibold uppercase tracking-wide text-slate-400">{$_('common.points')}</p>
                    <p class="mt-2 text-2xl font-bold text-slate-950">{childAvailablePoints(activeModal.child)}</p>
                  </div>
                  <div class="rounded-[1.5rem] bg-slate-50 p-4">
                    <p class="text-[10px] font-semibold uppercase tracking-wide text-slate-400">{$_('parent.savings.unlocked')}</p>
                    <p class="mt-2 text-2xl font-bold text-slate-950">{activeModal.child.available_savings || 0}</p>
                  </div>
                  <div class="rounded-[1.5rem] bg-slate-50 p-4">
                    <p class="text-[10px] font-semibold uppercase tracking-wide text-slate-400">{$_('common.held')}</p>
                    <p class="mt-2 text-2xl font-bold text-slate-950">{activeModal.child.locked_savings || 0}</p>
                  </div>
                </div>
                {#if allowance}
                  <div class="rounded-[1.75rem] border border-savings/10 bg-savings/5 p-4">
                    <p class="text-[10px] font-semibold uppercase tracking-wide text-savings-dark">{$_('parent.allowance')}</p>
                    <p class="mt-2 break-words text-sm font-bold leading-snug text-slate-700">{$_('parent.savings.allowanceLine', { values: { saved: formatAllowanceMinorAmount(allowance.saved_allowance_minor, allowance.currency, allowance.currency_exponent), available: formatAllowanceMinorAmount(allowance.available_allowance_minor, allowance.currency, allowance.currency_exponent) } })}</p>
                  </div>
                {/if}
                <div class="rounded-[1.75rem] border border-slate-100 bg-white p-4">
                  <p class="text-[10px] font-semibold uppercase tracking-wide text-slate-400">{$_('parent.savings.nextUnlock')}</p>
                  {#if unlock}
                    <p class="mt-2 break-words text-sm font-bold leading-snug text-slate-700">{$_('parent.savings.nextUnlockLine', { values: { points: unlock.points, date: formatSavingsUnlockDate(unlock.unlock_date) } })}</p>
                  {:else}
                    <p class="mt-2 break-words text-sm font-bold leading-snug text-slate-500">{$_('parent.savings.noUnlock')}</p>
                  {/if}
                </div>
              </div>
            {/if}

            {#if childModalTab === 'points-log'}
              {@const ledger = currentLedger(activeModal.child)}
              {@const behaviorLedger = ledger.filter((tx) => isBehaviorLedgerEntry(tx))}
              {@const percent = goodPercentage(behaviorLedger)}
              {@const key = ledgerKey(activeModal.child.child.id)}
              <div class="space-y-5">
              <div class="grid grid-cols-3 gap-2 rounded-2xl bg-hero/5 p-1 ring-1 ring-hero/10">
                {#each ([['day', $_('parent.pointsLog.day')], ['week', $_('parent.pointsLog.week')], ['year', $_('parent.pointsLog.year')]] as ['day' | 'week' | 'year', string][]) as period}
                  <button
                    type="button"
                    onclick={() => setPointLogPeriod(period[0])}
                    class="rounded-xl py-3 text-[10px] font-semibold uppercase tracking-wide transition-all sm:text-[10px] {pointLogPeriod === period[0] ? 'bg-hero text-white shadow-md shadow-hero/20' : 'text-slate-500 hover:bg-white/70 hover:text-hero'}"
                  >
                    {period[1]}
                  </button>
                {/each}
              </div>

                <div class="rounded-[1.75rem] border border-slate-100 bg-white p-5">
                  {#if behaviorLedger.length === 0}
                    <div class="rounded-[1.75rem] border border-dashed border-slate-200 bg-slate-50 p-8 text-center">
                      <div class="mx-auto grid h-44 w-44 place-items-center rounded-full border-2 border-dashed border-slate-200 bg-white">
                        <div class="text-center">
                          <p class="text-3xl font-bold text-slate-950">—</p>
                          <p class="mt-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400">{$_('parent.pointsLog.noBehaviour')}</p>
                        </div>
                      </div>
                    </div>
                  {:else}
                    <div class="mx-auto grid h-44 w-44 place-items-center rounded-full" style={ringStyle(percent)}>
                      <div class="grid h-28 w-28 place-items-center rounded-full bg-white shadow-inner ring-1 ring-slate-100">
                        <div class="text-center">
                          <p class="text-3xl font-bold text-slate-950">{percent === null ? '—' : `${percent}%`}</p>
                          <p class="mt-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400">{$_('parent.pointsLog.good')}</p>
                        </div>
                      </div>
                    </div>
                  {/if}
                  {#if pointLogPeriod === 'year'}
                    <p class="mt-4 text-center text-xs font-bold text-slate-400">{$_('parent.pointsLog.yearlyNote')}</p>
                  {/if}
                </div>

                {#if childLedgerLoading[key]}
                  <div class="rounded-[1.75rem] border border-dashed border-slate-200 bg-slate-50 p-6 text-center">
                    <p class="text-sm font-semibold uppercase tracking-wide text-slate-400">{$_('parent.pointsLog.loading')}</p>
                  </div>
                {:else if childLedgerError[key]}
                  <div class="rounded-[1.75rem] border border-red-100 bg-red-50 p-5 text-sm font-bold text-red-700">
                    {childLedgerError[key]}
                  </div>
                {:else if behaviorLedger.length === 0}
                  <div class="rounded-[1.75rem] border border-dashed border-slate-200 bg-slate-50 p-6 text-center">
                    <p class="text-sm font-semibold uppercase tracking-wide text-slate-400">{$_('parent.pointsLog.noHistory')}</p>
                  </div>
                {:else}
                  <div class="space-y-2">
                    {#each behaviorLedger.slice(0, 8) as tx}
                      <div class="flex items-center justify-between gap-3 rounded-2xl bg-slate-50 p-3">
                        <div class="min-w-0">
                          <p class="truncate text-sm font-bold text-slate-950">{tx.description || tx.transaction_type}</p>
                          <p class="text-xs font-bold text-slate-400">{formatLedgerDate(tx.created_at)} · {ledgerJarLabel(tx.jar)}</p>
                        </div>
                        <span class="shrink-0 rounded-full px-3 py-2 text-xs font-bold {tx.points > 0 ? 'bg-savings/10 text-savings' : tx.points < 0 ? 'bg-penalty/10 text-penalty' : 'bg-slate-100 text-slate-600'}">
                          {tx.points > 0 ? '+' : ''}{tx.points}
                        </span>
                      </div>
                    {/each}
                  </div>
                {/if}
              </div>
            {/if}
          {/if}

          {#if activeModal.type === 'redeem' || activeModal.type === 'presets'}
            <div class="space-y-2">
              <label for="modal-title" class="text-[10px] font-bold text-slate-400 uppercase tracking-wide ml-2">
                {activeModal.type === 'presets' ? $_('parent.presets.titleLabel') : $_('parent.redeem.rewardNameLabel')}
              </label>
              <div class="flex gap-3 min-w-0">
                {#if activeModal.type === 'presets'}
                  <div class="w-16 h-16 bg-slate-50 border-2 border-slate-100 rounded-2xl flex items-center justify-center text-2xl shadow-inner shrink-0">
                    {modalForm.icon || '✨'}
                  </div>
                {/if}
                <input 
                  id="modal-title"
                  type="text" 
                  bind:value={modalForm.title}
                  placeholder={activeModal.type === 'presets' ? $_('parent.presets.titlePlaceholder') : $_('parent.redeem.rewardNamePlaceholder')}
                  class="min-w-0 flex-1 bg-slate-50 border-2 border-slate-100 rounded-2xl px-4 sm:px-6 py-4 font-bold text-slate-900 focus:outline-none focus:border-reward/30 transition-all"
                />
              </div>
            </div>

            {#if activeModal.type === 'presets'}
              <div class="space-y-2">
                <span class="block text-[10px] font-bold text-slate-400 uppercase tracking-wide ml-2">{$_('parent.presets.visualLabel')}</span>
                <div class="flex flex-wrap gap-2 p-4 bg-slate-50 rounded-2xl border-2 border-slate-100">
                  <button 
                    onclick={() => modalForm.icon = ''}
                    class="w-10 h-10 rounded-xl flex items-center justify-center bg-white border border-slate-100 hover:border-hero/30 transition-all"
                  >
                    <X size={16} class="text-slate-300" />
                  </button>
                  {#each DEFAULT_EMOJIS as emoji}
                    <button 
                      onclick={() => modalForm.icon = emoji}
                      class="w-10 h-10 rounded-xl flex items-center justify-center bg-white border transition-all text-xl
                        {modalForm.icon === emoji ? 'border-hero shadow-sm' : 'border-slate-100 hover:border-hero/30'}"
                    >
                      {emoji}
                    </button>
                  {/each}
                </div>
              </div>
            {/if}
          {/if}

          {#if activeModal.type !== 'picker' && activeModal.type !== 'family' && activeModal.type !== 'calendar-week' && activeModal.type !== 'child-link' && activeModal.type !== 'child-link-select' && activeModal.type !== 'rewards' && activeModal.type !== 'requests'}
            <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 sm:gap-6">
              <div class="space-y-2">
                <label for="points-amount" class="text-[10px] font-bold text-slate-400 uppercase tracking-wide ml-2">{$_('parent.presets.pointsLabel')}</label>
                <div class="relative">
                  <input 
                    id="points-amount"
                    type="number" 
                    bind:value={modalForm.points}
                    class="w-full bg-slate-50 border-2 border-slate-100 rounded-2xl px-4 sm:px-6 py-4 font-bold text-slate-900 focus:outline-none focus:border-hero/30 transition-all text-2xl"
                  />
                  <span class="absolute right-4 sm:right-6 top-1/2 -translate-y-1/2 font-bold text-slate-300 text-sm">{$_('common.pts')}</span>
                </div>
                {#if activeModal.type === 'presets'}
                  <p class="text-[10px] text-slate-400 ml-2">{$_('parent.presets.pointsHint')}</p>
                {/if}
              </div>

              {#if activeModal.type === 'award' || activeModal.type === 'penalty'}
                <div class="space-y-2">
                  <label for="target-jar" class="text-[10px] font-bold text-slate-400 uppercase tracking-wide ml-2">{$_('parent.pointsActions.pointDestination')}</label>
                  <select 
                    id="target-jar"
                    bind:value={modalForm.jar}
                    class="w-full bg-slate-50 border-2 border-slate-100 rounded-2xl px-4 sm:px-6 py-4 font-bold text-slate-900 focus:outline-none focus:border-hero/30 transition-all appearance-none cursor-pointer"
                  >
                    <option value="spending">{$_('common.points')}</option>
                    <option value="savings">{$_('common.saved')}</option>
                  </select>
                </div>
              {/if}
            </div>
          {/if}

          {#if activeModal.type !== 'presets' && activeModal.type !== 'picker' && activeModal.type !== 'family' && activeModal.type !== 'calendar-week' && activeModal.type !== 'child-link' && activeModal.type !== 'child-link-select' && activeModal.type !== 'rewards' && activeModal.type !== 'requests'}
            <div class="space-y-2">
              <label for="modal-description" class="text-[10px] font-bold text-slate-400 uppercase tracking-wide ml-2">{$_('parent.redeem.descriptionLabel')}</label>
              <textarea 
                id="modal-description"
                bind:value={modalForm.description}
                placeholder={$_('parent.redeem.descriptionPlaceholder')}
                rows="3"
                class="w-full bg-slate-50 border-2 border-slate-100 rounded-2xl px-6 py-4 font-medium text-slate-900 focus:outline-none focus:border-hero/30 transition-all resize-none"
              ></textarea>
            </div>
          {/if}

          {#if activeModal.type === 'presets'}
            <div class="space-y-2">
              <label for="preset-details" class="text-[10px] font-bold text-slate-400 uppercase tracking-wide ml-2">{$_('parent.presets.detailsLabel')}</label>
              <textarea 
                id="preset-details"
                bind:value={modalForm.description}
                placeholder={$_('parent.presets.detailsPlaceholder')}
                rows="2"
                class="w-full bg-slate-50 border-2 border-slate-100 rounded-2xl px-6 py-4 font-medium text-slate-900 focus:outline-none focus:border-hero/30 transition-all resize-none"
              ></textarea>
            </div>

            {#if presets.length > 0}
              <div class="space-y-3 pt-4 border-t border-slate-100">
                <span class="block text-[10px] font-bold text-slate-400 uppercase tracking-wide ml-2">{$_('parent.presets.existing')}</span>
                <div class="grid gap-2">
                  {#each presets as p}
                    <div class="flex items-center justify-between p-4 bg-slate-50 rounded-2xl">
                      <div class="flex items-center gap-3">
                        <span class="text-xl w-8 h-8 flex items-center justify-center bg-white rounded-lg shadow-sm">{p.icon || '✨'}</span>
                        <span class={p.points > 0 ? 'text-savings' : 'text-penalty'}>
                          {p.points > 0 ? '+' : ''}{p.points}
                        </span>
                        <span class="font-bold text-slate-900 uppercase tracking-tight text-xs">{p.title}</span>
                      </div>
                      <div class="flex items-center gap-3">
                        <button onclick={() => startEditing(p)} class="text-slate-300 hover:text-hero transition-colors" aria-label={$_('parent.presets.editButton')} title={$_('parent.presets.editButton')}>
                          <Settings size={16} />
                        </button>
                        <button onclick={() => deletePreset(p.id)} class="text-slate-300 hover:text-red-500 transition-colors" aria-label={$_('parent.presets.deleteButton')} title={$_('parent.presets.deleteButton')}>
                          <X size={16} />
                        </button>
                      </div>
                    </div>
                  {/each}
                </div>
              </div>
            {/if}
          {/if}

          {#if activeModal.type === 'bank'}
            <div class="p-4 bg-savings/5 rounded-2xl border border-savings/10 flex items-start gap-3">
              <Clock size={16} class="text-savings mt-0.5" />
              <p class="text-[10px] font-bold text-savings-dark leading-relaxed uppercase tracking-wide">
                {$_('parent.bank.lockedNote')}
              </p>
            </div>
          {/if}
        </div>

          {#if activeModal.type !== 'picker' && activeModal.type !== 'child-link' && activeModal.type !== 'child-link-select' && activeModal.type !== 'rewards' && activeModal.type !== 'requests' && activeModal.type !== 'calendar-week'}
            <div class="pt-6 shrink-0 flex flex-col gap-3 bg-white">
              <button 
                onclick={handleModalSubmit}
                disabled={modalLoading}
                class="w-full py-5 rounded-[1.5rem] font-semibold uppercase tracking-wide text-sm shadow-xl transition-all active:scale-[0.98] disabled:opacity-50
                {activeModal.type === 'award' ? 'bg-savings text-white shadow-savings/20 hover:bg-savings-dark' : 
                 activeModal.type === 'penalty' ? 'bg-penalty text-white shadow-penalty/30 hover:bg-penalty-dark' :
                 activeModal.type === 'bank' ? 'bg-reward text-white shadow-reward/30 hover:bg-reward-dark' :
                 activeModal.type === 'presets' ? 'bg-hero text-white shadow-hero/20 hover:bg-hero-dark' :
                 'bg-reward text-white shadow-reward/30 hover:bg-reward-dark'}"
              >
                {modalLoading ? (activeModal.type === 'family' ? $_('common.processing') : activeModal.type === 'presets' ? $_('common.saving') : $_('common.processing')) :
             activeModal.type === 'presets' ? (editingPresetId ? $_('parent.presets.saveChanges') : $_('parent.presets.createPreset')) :
             activeModal.type === 'family' ? $_('parent.family.inviteGrownup') :
             $_('common.confirmAction')}
              </button>
              {#if editingPresetId}
                <button 
                  onclick={cancelEditing}
                  class="w-full py-3 text-[10px] font-semibold uppercase tracking-wide text-slate-400 hover:text-slate-600 transition-colors"
                >
                  {$_('parent.presets.cancelEdit')}
                </button>
              {/if}
            </div>
          {/if}
      </div>
    </div>
  </div>
{/if}
</div>
<style>
  /* Color, card, and button styles come from tailwind.config.js and app.css. */
  @keyframes fade-in {
    from { opacity: 0; }
    to { opacity: 1; }
  }
  @keyframes zoom-in {
    from { transform: scale(0.95); }
    to { transform: scale(1); }
  }
  .animate-in {
    animation: fade-in 0.3s ease-out, zoom-in 0.3s ease-out;
  }

  @media (max-width: 1024px) {
    :global(.custom-scrollbar) {
      scrollbar-width: none;
      -ms-overflow-style: none;
    }

    :global(.custom-scrollbar::-webkit-scrollbar) {
      display: none;
    }
  }
</style>
