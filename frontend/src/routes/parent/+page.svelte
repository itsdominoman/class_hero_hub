<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import { AVATAR_OPTIONS, getAvatarAsset, hasAvatarAssetFile, normaliseAvatarKey } from '$lib/avatars';
  import { 
    UserPlus, Award, Ban, PiggyBank, Gift,
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

  const WEEK_START_OPTIONS: { value: WeekStartDay; label: string }[] = [
    { value: 'sunday', label: 'Sunday' },
    { value: 'monday', label: 'Monday' },
    { value: 'tuesday', label: 'Tuesday' },
    { value: 'wednesday', label: 'Wednesday' },
    { value: 'thursday', label: 'Thursday' },
    { value: 'friday', label: 'Friday' },
    { value: 'saturday', label: 'Saturday' }
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
    const title = item?.class_name || 'School item';
    if (/p\.?\s*e\.?/i.test(title)) return 'Gym clothes';
    return `${title} book`;
  }

  function formatAllowanceMinorAmount(minor: number, currency: string, exponent: number) {
    const safeMinor = Math.max(0, Math.trunc(minor || 0));
    const scale = 10 ** exponent;
    const whole = Math.floor(safeMinor / scale);
    const fraction = String(safeMinor % scale).padStart(exponent, '0');
    return exponent > 0 ? `${whole}.${fraction} ${currency}` : `${whole} ${currency}`;
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
      const message = e instanceof Error ? e.message : 'Unable to load dashboard';
      if (isAuthError(message)) {
        parent = null;
        children = [];
        needsLogin = true;
      } else {
        error = message;
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
      familySettingsError = e instanceof Error ? e.message : 'Unable to load family settings';
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
      familySettingsMessage = 'Calendar and school week saved.';
    } catch (e) {
      familySettingsError = e instanceof Error ? e.message : 'Unable to save family settings';
    } finally {
      familySettingsSaving = false;
    }
  }

  async function addChild() {
    const childName = window.prompt('Enter your child\'s display name');
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
      error = e instanceof Error ? e.message : 'Unable to add child';
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
      rewardError = e instanceof Error ? e.message : 'Unable to save reward';
    } finally {
      rewardLoading = false;
    }
  }

  async function deleteReward(id: number) {
    if (!confirm('Delete this reward?')) return;
    try {
      rewardLoading = true;
      rewardError = null;
      await api.delete(`/rewards/${id}`);
      if (editingRewardId === id) cancelEditingReward();
      await loadDashboard();
    } catch (e) {
      rewardError = e instanceof Error ? e.message : 'Unable to delete reward';
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
      childLinkError = e instanceof Error ? e.message : 'Unable to create child dashboard link';
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
      childDevicesError = e instanceof Error ? e.message : 'Unable to load linked devices';
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
    if (!confirm('Revoke all child device access for this child?')) return;
    try {
      childLinkLoading = true;
      childLinkError = null;
      await api.post(`/children/${activeModal.child.child.id}/device-invites/revoke`, {});
      childLinkInvite = null;
      childLinkQr = '';
      await loadChildDevices(activeModal.child);
      await loadDashboard();
    } catch (e) {
      childLinkError = e instanceof Error ? e.message : 'Failed to revoke child device access';
    } finally {
      childLinkLoading = false;
    }
  }

  async function unlinkChildDevice(device: ChildDevice) {
    if (!activeModal?.child) return;
    if (!confirm('Unlink this child device?')) return;
    try {
      childDeviceUnlinkingId = device.id;
      childDevicesError = null;
      await api.delete(`/children/${activeModal.child.child.id}/devices/${device.id}`);
      await loadChildDevices(activeModal.child);
    } catch (e) {
      childDevicesError = e instanceof Error ? e.message : 'Failed to unlink child device';
    } finally {
      childDeviceUnlinkingId = null;
    }
  }

  function formatDeviceDate(value: string | null) {
    if (!value) return 'Not seen yet';
    return new Date(value).toLocaleString();
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
          description: modalForm.description || 'Parent Award',
          jar: modalForm.jar
        });
      } else if (activeModal.type === 'penalty') {
        await api.post(`/children/${childId}/penalty`, {
          points: modalForm.points,
          description: modalForm.description || 'Parent Penalty',
          jar: modalForm.jar
        });
      } else if (activeModal.type === 'bank') {
        await api.post(`/children/${childId}/savings/deposit`, {
          points: modalForm.points,
          description: modalForm.description || 'Banking points'
        });
      } else if (activeModal.type === 'redeem') {
        await api.post(`/children/${childId}/redemptions`, {
          points: modalForm.points,
          title: modalForm.title || 'Reward Request',
          description: modalForm.description || ''
        });
      }

      await loadDashboard();
      closeModal();
    } catch (e) {
      modalError = e instanceof Error ? e.message : 'Action failed';
    } finally {
      modalLoading = false;
    }
  }

  async function submitCustomPoints(direction: 'award' | 'penalty') {
    if (!activeModal?.child) return;

    const points = Math.abs(Number(modalForm.points) || 0);
    if (points < 1) {
      modalError = 'Enter at least 1 point';
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
          description: modalForm.description || 'Parent Award',
          jar: modalForm.jar
        });
        playPositiveSound();
      } else {
        await api.post(`/children/${childId}/penalty`, {
          points,
          description: modalForm.description || 'Parent Penalty',
          jar: modalForm.jar
        });
        playNegativeSound();
      }

      await loadDashboard();
      closeModal();
    } catch (e) {
      modalError = e instanceof Error ? e.message : 'Action failed';
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
      alert(e instanceof Error ? e.message : 'Failed to apply preset');
    }
  }

  async function deletePreset(id: number) {
    if (!confirm('Delete this preset?')) return;
    try {
      await api.delete(`/presets/${id}`);
      await loadDashboard();
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Failed to delete preset');
    }
  }

  async function revokeInvite(id: number) {
    if (!confirm('Cancel this invite? The invite link will no longer work.')) return;
    try {
      await api.delete(`/family/invites/${id}`);
      await loadDashboard();
      await loadFamilySettings();
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Failed to cancel invite');
    }
  }

  async function removeGrownup(member: FamilyMember) {
    if (!confirm('Remove this grownup from your family? They will no longer be able to manage children or points.')) return;

    try {
      familyGrownupRemovingId = member.id;
      await api.delete(`/family/grownups/${member.id}`);
      await loadDashboard();
      await loadFamilySettings();
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Failed to remove grownup');
    } finally {
      familyGrownupRemovingId = null;
    }
  }

  async function processRedemption(id: number, action: string) {
    try {
      const note = action === 'reject' ? window.prompt('Reason for rejection? (Optional)') : 'Approved by parent';
      await api.post(`/redemptions/${id}/${action}`, {
        parent_note: note || ''
      });
      await loadDashboard();
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Failed to process redemption');
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
      childEditError = 'Display name is required';
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
      childEditError = e instanceof Error ? e.message : 'Unable to save child';
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
    return `background: conic-gradient(#ff7a1a ${safePercent}%, #e2e8f0 ${safePercent}% 100%);`;
  }

  function formatLedgerDate(value: string) {
    return new Date(value).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  }

  function formatCalendarDate(value: string) {
    return new Date(`${value}T00:00:00`).toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
  }

  function formatCalendarTime(value: string | null) {
    if (!value) return 'Any time';
    return value.slice(0, 5);
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
      childCalendarError = { ...childCalendarError, [childId]: e instanceof Error ? e.message : 'Unable to load calendar' };
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
      childLedgerError = { ...childLedgerError, [key]: e instanceof Error ? e.message : 'Unable to load point history' };
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
</script>

<div class="bg-slate-50 min-h-dvh max-w-full overflow-x-hidden pb-[var(--safe-bottom)]">
  {#if loading}
    <div class="flex justify-center py-24">
      <div class="animate-spin w-12 h-12 border-4 border-hero border-t-transparent rounded-full"></div>
    </div>
  {:else if needsLogin}
    <div class="max-w-xl mx-auto px-4 py-20">
      <div class="card p-10 md:p-12 text-center bg-white">
        <div class="w-16 h-16 bg-hero/10 text-hero rounded-2xl flex items-center justify-center mx-auto mb-6">
          <LogIn size={32} />
        </div>
        <h1 class="text-3xl font-black text-slate-900 mb-3">Parent access required</h1>
        <p class="text-slate-600 mb-8">Sign in with Google to open the parent dashboard and manage your family account.</p>
        <button onclick={openLogin} class="btn-hero w-full py-4 rounded-2xl">Go to Login</button>
      </div>
    </div>
  {:else if error}
    <div class="max-w-lg mx-auto px-4 py-20">
      <div class="card bg-red-50 border-red-100 p-8 text-center">
        <div class="w-16 h-16 bg-red-100 text-red-600 rounded-full flex items-center justify-center mx-auto mb-6">
          <Ban size={32} />
        </div>
                      <p class="text-red-600 font-black mb-4 uppercase tracking-[0.12em] text-sm sm:tracking-[0.2em]">Failed to load dashboard</p>
        <p class="text-slate-600 mb-8 break-words">{error}</p>
        <button onclick={loadDashboard} class="btn-secondary w-full py-4">Try Again</button>
      </div>
    </div>
  {:else}
    <div class="bg-slate-50 min-h-dvh max-w-full overflow-x-hidden pb-[calc(5rem+var(--safe-bottom))]">
      <div class="bg-white border-b border-slate-200/70">
        <div class="max-w-5xl mx-auto px-3 sm:px-4 py-5 md:py-6">
          <div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div class="min-w-0">
              <h1 class="text-3xl sm:text-4xl font-black text-slate-950 tracking-tight break-words">My Family</h1>
            </div>

            <div class="flex flex-wrap items-center gap-2">
              <details class="relative w-full sm:w-auto">
                <summary class="inline-flex w-full cursor-pointer list-none items-center justify-center gap-2 rounded-full bg-white px-4 py-3 text-xs font-black uppercase tracking-[0.12em] text-slate-700 shadow-sm ring-1 ring-slate-200 transition hover:text-hero sm:w-auto sm:tracking-[0.16em]">
                  <Settings size={14} />
                  Settings
                </summary>
                <div class="absolute right-0 z-30 mt-2 grid w-full min-w-64 gap-1 rounded-2xl border border-slate-200 bg-white p-2 shadow-2xl sm:w-72">
                  <button type="button" onclick={() => openModal('rewards', null)} class="inline-flex items-center gap-2 rounded-xl px-3 py-3 text-left text-xs font-black uppercase tracking-[0.12em] text-slate-700 hover:bg-slate-50 sm:tracking-[0.14em]">
                    <Gift size={15} />
                    Manage rewards
                  </button>
                  <button type="button" onclick={() => openModal('family', null)} class="inline-flex items-center gap-2 rounded-xl px-3 py-3 text-left text-xs font-black uppercase tracking-[0.12em] text-slate-700 hover:bg-slate-50 sm:tracking-[0.14em]">
                    <Users size={15} />
                    Parents &amp; Caregivers
                  </button>
                  <button type="button" onclick={() => openModal('calendar-week', null)} class="inline-flex items-center gap-2 rounded-xl px-3 py-3 text-left text-xs font-black uppercase tracking-[0.12em] text-slate-700 hover:bg-slate-50 sm:tracking-[0.14em]">
                    <CalendarDays size={15} />
                    Calendar &amp; School Week
                  </button>
                  <button type="button" onclick={() => openModal('presets', null)} class="inline-flex items-center gap-2 rounded-xl px-3 py-3 text-left text-xs font-black uppercase tracking-[0.12em] text-slate-700 hover:bg-slate-50 sm:tracking-[0.14em]">
                    <Settings size={15} />
                    Behaviour presets
                  </button>
                  <button type="button" onclick={() => openModal('requests', null)} class="inline-flex items-center gap-2 rounded-xl px-3 py-3 text-left text-xs font-black uppercase tracking-[0.12em] text-slate-700 hover:bg-slate-50 sm:tracking-[0.14em]">
                    <Check size={15} />
                    Review reward requests
                  </button>
                  <a href="/redemptions" class="inline-flex items-center gap-2 rounded-xl px-3 py-3 text-left text-xs font-black uppercase tracking-[0.12em] text-slate-700 hover:bg-slate-50 sm:tracking-[0.14em]">
                    <Check size={15} />
                    Redemptions
                  </a>
                  <a href="/allowance" class="inline-flex items-center gap-2 rounded-xl px-3 py-3 text-left text-xs font-black uppercase tracking-[0.12em] text-slate-700 hover:bg-slate-50 sm:tracking-[0.14em]">
                    <PiggyBank size={15} />
                    Allowance
                  </a>
                  <a href="/calendar" class="inline-flex items-center gap-2 rounded-xl px-3 py-3 text-left text-xs font-black uppercase tracking-[0.12em] text-slate-700 hover:bg-slate-50 sm:tracking-[0.14em]">
                    <CalendarDays size={15} />
                    Calendar
                  </a>
                  <button type="button" onclick={() => openModal('child-link-select', null)} disabled={children.length === 0} class="inline-flex items-center gap-2 rounded-xl px-3 py-3 text-left text-xs font-black uppercase tracking-[0.12em] text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50 sm:tracking-[0.14em]">
                    <QrCode size={15} />
                    Child device links
                  </button>
                </div>
              </details>
            </div>
          </div>
        </div>
      </div>

      <div class="max-w-5xl mx-auto px-3 sm:px-4 py-6 md:py-8 space-y-6">
        <section class="space-y-4">
          <div class="flex flex-wrap items-center justify-end gap-3">
            <button
              type="button"
              onclick={addChild}
              disabled={loadingChildren}
              class="inline-flex items-center gap-2 rounded-full bg-white px-4 py-3 text-xs font-black uppercase tracking-[0.12em] text-slate-700 shadow-sm ring-1 ring-slate-200 transition hover:text-hero disabled:cursor-not-allowed disabled:opacity-60 sm:tracking-[0.14em]"
            >
              <UserPlus size={14} />
              Add child
            </button>
          </div>

          {#if children.length === 0}
            <div class="card overflow-hidden border-dashed border-2 border-slate-200 bg-white p-8 sm:p-10 text-center shadow-none">
              <div class="mx-auto mb-5 flex h-20 w-20 items-center justify-center rounded-[1.75rem] bg-slate-100 text-slate-400">
                <UserPlus size={36} />
              </div>
              <h3 class="text-2xl font-black text-slate-900">Your family is empty</h3>
              <p class="mx-auto mt-3 max-w-md text-sm leading-6 text-slate-500">
                Add a child to start tracking points, rewards, and daily routines.
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
                  aria-label={`Open point actions for ${c.child.display_name}`}
                >
                  <div class="relative">
                    <div class="absolute -top-3 left-1/2 z-10 -translate-x-1/2 min-w-[2.75rem] max-w-[4.25rem] truncate rounded-full bg-slate-900 px-2.5 py-1 text-center text-[10px] font-black leading-none tabular-nums text-white shadow-lg">
                      {childAvailablePoints(c)}
                    </div>
                    <div class="flex h-24 w-24 items-center justify-center overflow-hidden rounded-full bg-white shadow-md ring-4 ring-white transition group-hover:scale-[1.03] sm:h-28 sm:w-28">
                      {#if avatarCanRender(c, avatar.key)}
                        <img
                          src={avatar.path}
                          alt={`Avatar for ${c.child.display_name}`}
                          class="h-full w-full object-cover"
                          loading="lazy"
                          onerror={() => markAvatarFailed(c)}
                        />
                      {:else}
                        <span class="text-3xl font-black text-slate-900">{childAvatarLabel(c)}</span>
                      {/if}
                    </div>
                  </div>
                  <span class="mt-3 w-full truncate text-sm font-black text-slate-950 sm:text-base">
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
                    alt={`Avatar for ${activeModal.child.child.display_name}`}
                    class="h-full w-full object-cover"
                    onerror={() => markAvatarFailed(activeModal.child)}
                  />
                {:else}
                  <span class="text-lg sm:text-2xl font-black">{childAvatarLabel(activeModal.child)}</span>
                {/if}
              </div>
              <div class="min-w-0">
                <h3 class="text-xl sm:text-2xl font-black text-slate-900 tracking-tight break-words leading-tight">
                  {activeModal.child?.child?.display_name}
                </h3>
              </div>
            </div>
            <div class="hidden sm:flex shrink-0 items-center gap-2 rounded-full bg-slate-100 px-4 py-2 text-xs font-black uppercase tracking-[0.12em] text-slate-700">
              <Trophy size={14} class="text-hero" />
              {childAvailablePoints(activeModal.child)} pts
            </div>
            <div class="sm:hidden shrink-0 rounded-full bg-slate-100 px-3 py-2 text-[10px] font-black uppercase tracking-[0.08em] text-slate-700">
              {childAvailablePoints(activeModal.child)} pts
            </div>
          {:else}
            <div class="flex min-w-0 items-center gap-3 sm:gap-4">
              <div class="w-12 h-12 sm:w-16 sm:h-16 rounded-3xl flex items-center justify-center shadow-lg shrink-0
                {activeModal.type === 'award' ? 'bg-hero text-white shadow-hero/20' : 
                 activeModal.type === 'penalty' ? 'bg-penalty text-white shadow-penalty/20' :
                 activeModal.type === 'bank' ? 'bg-savings text-white shadow-savings/20' :
                 activeModal.type === 'presets' ? 'bg-slate-900 text-white shadow-slate-200' :
                 activeModal.type === 'family' ? 'bg-hero text-white shadow-hero/20' :
                 activeModal.type === 'calendar-week' ? 'bg-hero text-white shadow-hero/20' :
                 activeModal.type === 'child-link' ? 'bg-slate-900 text-white shadow-slate-200' :
                 activeModal.type === 'child-link-select' ? 'bg-slate-900 text-white shadow-slate-200' :
                 activeModal.type === 'rewards' ? 'bg-reward text-white shadow-reward/20' :
                 activeModal.type === 'requests' ? 'bg-savings text-white shadow-savings/20' :
                 'bg-reward text-white shadow-reward/20'}">
                {#if activeModal.type === 'award'}<Award size={32} />
                {:else if activeModal.type === 'penalty'}<Ban size={32} />
                {:else if activeModal.type === 'bank'}<PiggyBank size={32} />
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
                <h3 class="text-xl sm:text-2xl font-black text-slate-900 tracking-tight break-words leading-tight">
                  {activeModal.type === 'award' ? 'Add points' : 
                   activeModal.type === 'penalty' ? 'Remove points' :
                   activeModal.type === 'bank' ? 'Move to saved points' :
                  activeModal.type === 'presets' ? (editingPresetId ? 'Edit Behaviour' : 'Manage Behaviours') :
                   activeModal.type === 'family' ? 'Parents & Caregivers' :
                   activeModal.type === 'calendar-week' ? 'Calendar & School Week' :
                   activeModal.type === 'child-link' ? 'Link child device' :
                   activeModal.type === 'child-link-select' ? 'Link child device' :
                   activeModal.type === 'rewards' ? 'Manage Rewards' :
                   activeModal.type === 'requests' ? 'Review reward requests' :
                   'Redeem Points'}
                </h3>
                <p class="text-slate-400 font-black text-[10px] sm:text-xs uppercase tracking-[0.14em] sm:tracking-[0.2em] break-words">
                  {activeModal.type === 'presets' ? (editingPresetId ? 'Update this action' : 'Configure reusable actions') : 
                   activeModal.type === 'family' ? 'Invite another grownup to help manage points, rewards, and routines' :
                   activeModal.type === 'calendar-week' ? 'Week start affects weekly views and planning' :
                   activeModal.type === 'child-link' ? 'Child dashboard link' :
                   activeModal.type === 'child-link-select' ? 'Choose a child first' :
                   activeModal.type === 'rewards' ? 'Family rewards' :
                   activeModal.type === 'requests' ? 'Requests' : ''}
                </p>
              </div>
            </div>
          {/if}
          <button onclick={closeModal} class="w-11 h-11 shrink-0 rounded-xl bg-slate-50 text-slate-300 flex items-center justify-center hover:bg-slate-100 hover:text-slate-500 transition-all" aria-label="Close modal">
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
                  class="inline-flex min-w-0 w-full items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-xs font-black uppercase tracking-[0.1em] text-slate-700 transition hover:border-hero hover:text-hero sm:tracking-[0.14em]"
                >
                  <LayoutDashboard size={15} />
                  <span class="sm:hidden">Child Dashboard</span>
                  <span class="hidden sm:inline">Open Child Dashboard</span>
                </a>
                <button
                  type="button"
                  onclick={() => openChildEdit(activeModal.child)}
                  class="inline-flex min-w-0 w-full items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-xs font-black uppercase tracking-[0.1em] text-slate-700 transition hover:border-hero hover:text-hero sm:tracking-[0.14em]"
                >
                  <Settings size={15} />
                  Edit Child
                </button>
              </div>

              {#if childEditOpen}
                {@const editAvatar = childEditForm.avatar_name ? getAvatarAsset(childEditForm.avatar_name) : null}
                <div class="rounded-[1.75rem] border border-slate-100 bg-slate-50 p-4 sm:p-5">
                  <div class="flex items-start justify-between gap-3">
                    <div class="min-w-0">
                      <p class="text-[10px] font-black uppercase tracking-[0.12em] text-slate-400 sm:tracking-[0.22em]">Edit child</p>
                      <h4 class="mt-1 text-lg font-black text-slate-950">Update display name and avatar</h4>
                    </div>
                    <button
                      type="button"
                      onclick={() => (childEditOpen = false)}
                      class="rounded-xl bg-white px-3 py-2 text-[10px] font-black uppercase tracking-[0.18em] text-slate-500 shadow-sm ring-1 ring-slate-200"
                    >
                      Close
                    </button>
                  </div>

                  {#if childEditError}
                    <div class="mt-4 rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm font-bold text-red-700 break-words">
                      {childEditError}
                    </div>
                  {/if}

                  <div class="mt-4 grid gap-4">
                    <label class="block min-w-0">
                      <span class="mb-2 block text-[10px] font-black uppercase tracking-[0.16em] text-slate-400 sm:tracking-[0.22em]">Display name</span>
                      <input
                        type="text"
                        bind:value={childEditForm.display_name}
                        class="w-full rounded-2xl border-2 border-slate-200 bg-white px-4 py-4 text-slate-900 font-bold focus:outline-none focus:border-hero/30"
                      />
                    </label>

                    <div class="rounded-[1.5rem] border border-slate-100 bg-white p-4">
                      <div class="flex items-center justify-between gap-3">
                        <div class="min-w-0">
                          <p class="text-[10px] font-black uppercase tracking-[0.16em] text-slate-400 sm:tracking-[0.22em]">Avatar</p>
                          <p class="mt-1 text-sm font-bold text-slate-600">Pick an avatar or use initials.</p>
                        </div>
                        <button
                          type="button"
                          onclick={() => setChildEditAvatar('')}
                          class="shrink-0 rounded-full border px-3 py-2 text-[10px] font-black uppercase tracking-[0.14em] transition {childEditForm.avatar_name === '' ? 'border-hero bg-hero/10 text-hero' : 'border-slate-200 bg-white text-slate-500 hover:border-hero hover:text-hero'}"
                        >
                          Initials
                        </button>
                      </div>

                      <div class="mt-4 grid max-h-72 grid-cols-3 gap-2 overflow-y-auto pr-1 sm:grid-cols-4">
                        {#each AVATAR_OPTIONS as option}
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
                                alt={option.label}
                                class="h-full w-full object-cover"
                                loading="lazy"
                              />
                            </div>
                            <span class="w-full truncate text-[10px] font-black uppercase tracking-[0.08em] text-slate-500">
                              {option.label}
                            </span>
                          </button>
                        {/each}
                      </div>
                    </div>

                    <div class="flex items-center gap-3 rounded-2xl bg-white p-3">
                      <div class="flex h-14 w-14 shrink-0 items-center justify-center overflow-hidden rounded-full bg-slate-100 text-lg font-black text-slate-950">
                        {#if editAvatar}
                          <img
                            src={editAvatar.path}
                            alt={`Avatar preview for ${childEditForm.display_name || activeModal.child.child.display_name}`}
                            class="h-full w-full object-cover"
                          />
                        {:else}
                          <span>{(childEditForm.display_name.trim() || activeModal.child.child.display_name || '?').slice(0, 1).toUpperCase()}</span>
                        {/if}
                      </div>
                      <div class="min-w-0">
                        <p class="text-sm font-black text-slate-950">Profile preview</p>
                        <p class="text-xs font-bold text-slate-400">Avatar and name changes apply after save</p>
                      </div>
                    </div>
                  </div>

                  <div class="mt-4 flex flex-col gap-3 sm:flex-row">
                    <button
                      type="button"
                      onclick={saveChildEdit}
                      disabled={childEditLoading || !childEditForm.display_name.trim()}
                      class="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-slate-900 px-4 py-4 text-xs font-black uppercase tracking-[0.16em] text-white disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {childEditLoading ? 'Saving...' : 'Save child'}
                    </button>
                    <button
                      type="button"
                      onclick={() => (childEditOpen = false)}
                      class="inline-flex w-full items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-4 text-xs font-black uppercase tracking-[0.16em] text-slate-700"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              {/if}

              <div class="grid grid-cols-2 gap-2 rounded-2xl bg-slate-100 p-2 sm:grid-cols-3">
                {#each [
                  ['points', 'Points'],
                  ['requests', 'Requests'],
                  ['school', 'School Bag'],
                  ['calendar', 'Calendar'],
                  ['savings', 'Savings'],
                  ['points-log', 'Points Log']
                ] as tab}
                  <button
                    type="button"
                    onclick={() => setChildModalTab(tab[0])}
                    class="min-w-0 rounded-xl px-2.5 py-3 text-[9px] font-black uppercase tracking-[0.03em] leading-tight whitespace-normal transition-all sm:px-4 sm:py-3.5 sm:text-[10px] sm:tracking-[0.08em] {childModalTab === tab[0] ? 'bg-white text-slate-950 shadow-sm' : 'text-slate-500 hover:text-slate-700'}"
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
                <p class="text-[10px] font-black uppercase tracking-[0.12em] text-slate-400 sm:tracking-[0.22em]">Child</p>
                <p class="mt-2 text-2xl font-black text-slate-950 break-words">{activeModal.child.child.display_name}</p>
                <p class="mt-2 text-sm text-slate-600">This QR links one tablet or phone directly to this child profile.</p>
              </div>

              {#if childLinkLoading && !childLinkInvite}
                <div class="rounded-[1.75rem] border border-dashed border-slate-200 bg-white p-8 text-center">
                  <div class="mx-auto w-12 h-12 rounded-2xl bg-slate-100 flex items-center justify-center animate-pulse">
                    <QrCode size={22} class="text-slate-400" />
                  </div>
                  <p class="mt-4 text-sm font-black uppercase tracking-[0.12em] text-slate-400 sm:tracking-[0.22em]">Generating QR</p>
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
                    <img src={childLinkQr} alt="QR code for child dashboard link" class="w-full h-auto rounded-2xl" />
                  {/if}
                </div>
                    <div class="text-center">
                      <p class="text-[10px] font-black uppercase tracking-[0.12em] text-slate-400 sm:tracking-[0.22em]">Expires</p>
                      <p class="text-lg font-black text-slate-950 break-words">{new Date(childLinkInvite.expires_at).toLocaleString()}</p>
                    </div>
                  </div>

                  <div class="space-y-2">
                    <p class="text-[10px] font-black uppercase tracking-[0.12em] text-slate-400 ml-1 sm:tracking-[0.22em]">Fallback link</p>
                    <div class="flex flex-col sm:flex-row gap-2">
                      <input
                        readonly
                        value={childLinkInvite.invite_url}
                        class="min-w-0 flex-1 rounded-2xl border-2 border-slate-100 bg-slate-50 px-4 py-3 text-sm font-medium text-slate-700 break-all"
                      />
                      <button
                        type="button"
                        onclick={copyChildInviteLink}
                        class="inline-flex w-full sm:w-auto items-center justify-center gap-2 rounded-2xl bg-slate-900 px-4 py-3 text-xs font-black uppercase tracking-[0.2em] text-white shrink-0"
                      >
                        <Copy size={14} />
                        {childLinkCopied ? 'Copied' : 'Copy'}
                      </button>
                    </div>
                  </div>

                  <div class="flex flex-col sm:flex-row gap-3">
                    <button
                      type="button"
                      onclick={regenerateChildLink}
                      class="inline-flex w-full sm:w-auto items-center justify-center gap-2 rounded-2xl bg-hero px-4 py-3 text-xs font-black uppercase tracking-[0.2em] text-white shadow-lg shadow-hero/20"
                    >
                      <RefreshCcw size={14} />
                      Regenerate QR
                    </button>
                    <button
                      type="button"
                      onclick={revokeChildLink}
                      class="inline-flex w-full sm:w-auto items-center justify-center gap-2 rounded-2xl bg-white px-4 py-3 text-xs font-black uppercase tracking-[0.2em] text-slate-700 border-2 border-slate-100"
                    >
                      <Link2 size={14} />
                      Revoke access
                    </button>
                  </div>
                </div>
              {:else}
                <div class="rounded-[1.75rem] border border-dashed border-slate-200 bg-white p-8 text-center space-y-4">
                  <div class="mx-auto w-12 h-12 rounded-2xl bg-slate-100 flex items-center justify-center">
                    <QrCode size={22} class="text-slate-400" />
                  </div>
                  <div>
                    <p class="text-sm font-black uppercase tracking-[0.12em] text-slate-400 sm:tracking-[0.22em]">No active QR</p>
                    <p class="text-sm text-slate-500 mt-2">Generate a fresh link to connect a tablet or phone.</p>
                  </div>
                  <button
                    type="button"
                    onclick={regenerateChildLink}
                    class="inline-flex w-full sm:w-auto items-center justify-center gap-2 rounded-2xl bg-hero px-4 py-3 text-xs font-black uppercase tracking-[0.2em] text-white shadow-lg shadow-hero/20"
                  >
                    <RefreshCcw size={14} />
                    Generate QR
                  </button>
                </div>
              {/if}

              <div class="rounded-[1.75rem] border border-slate-100 bg-white p-5 space-y-4">
                <div class="flex items-center justify-between gap-3">
                  <div class="min-w-0">
                    <p class="text-[10px] font-black uppercase tracking-[0.12em] text-slate-400 sm:tracking-[0.22em]">Linked devices</p>
                    <p class="mt-1 text-sm text-slate-600">Remove one tablet or phone without deleting this child.</p>
                  </div>
                  <button
                    type="button"
                    onclick={() => loadChildDevices(activeModal.child)}
                    disabled={childDevicesLoading}
                    class="shrink-0 rounded-2xl border border-slate-100 bg-slate-50 px-3 py-2 text-[10px] font-black uppercase tracking-[0.14em] text-slate-600 disabled:opacity-60"
                  >
                    {childDevicesLoading ? 'Loading' : 'Refresh'}
                  </button>
                </div>

                {#if childDevicesError}
                  <div class="rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm font-bold text-red-700 break-words">
                    {childDevicesError}
                  </div>
                {/if}

                {#if childDevicesLoading && childDevices.length === 0}
                  <div class="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm font-bold text-slate-400">
                    Loading linked devices.
                  </div>
                {:else if childDevices.length === 0}
                  <div class="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm font-bold text-slate-400">
                    No linked devices yet.
                  </div>
                {:else}
                  <div class="space-y-2">
                    {#each childDevices as device}
                      <div class="flex flex-col gap-3 rounded-2xl border border-slate-100 bg-slate-50 p-4 sm:flex-row sm:items-center sm:justify-between">
                        <div class="min-w-0">
                          <p class="text-sm font-black text-slate-900">{device.label || 'Linked device'} #{device.id}</p>
                          <p class="mt-1 text-xs font-bold text-slate-500">Last seen: {formatDeviceDate(device.last_seen_at)}</p>
                          <p class="text-xs font-bold text-slate-400">Expires: {formatDeviceDate(device.expires_at)}</p>
                        </div>
                        <button
                          type="button"
                          onclick={() => unlinkChildDevice(device)}
                          disabled={childDeviceUnlinkingId === device.id}
                          class="inline-flex w-full items-center justify-center gap-2 rounded-2xl border-2 border-slate-100 bg-white px-4 py-3 text-xs font-black uppercase tracking-[0.16em] text-slate-700 disabled:opacity-60 sm:w-auto"
                        >
                          <Link2 size={14} />
                          {childDeviceUnlinkingId === device.id ? 'Removing' : 'Unlink'}
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
                  <p class="text-sm font-black uppercase tracking-[0.12em] text-slate-400 sm:tracking-[0.22em]">No children yet</p>
                </div>
              {:else}
                {#each children as childSummary}
                  <button
                    type="button"
                    onclick={() => openChildLink(childSummary)}
                    class="inline-flex w-full items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 text-left font-black text-slate-800 transition hover:border-hero hover:text-hero"
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
                    <p class="text-[10px] font-black uppercase tracking-[0.12em] text-slate-400 mb-2 sm:tracking-[0.22em]">Reward editor</p>
                    <h4 class="text-xl font-black text-slate-950">{editingRewardId ? 'Edit reward' : 'Create a reward'}</h4>
                  </div>
                  <Gift size={20} class="shrink-0 text-reward" />
                </div>

                <div class="space-y-4">
                  <label class="block">
                    <span class="block text-[10px] font-black uppercase tracking-[0.12em] text-slate-400 mb-2 sm:tracking-[0.22em]">Reward name</span>
                    <input type="text" bind:value={rewardForm.title} placeholder="Movie night" class="w-full rounded-2xl border-2 border-slate-200 bg-white px-4 py-4 text-slate-900 font-bold focus:outline-none focus:border-hero/30" />
                  </label>

                  <label class="block">
                    <span class="block text-[10px] font-black uppercase tracking-[0.12em] text-slate-400 mb-2 sm:tracking-[0.22em]">Description</span>
                    <input type="text" bind:value={rewardForm.description} placeholder="Extra screen time" class="w-full rounded-2xl border-2 border-slate-200 bg-white px-4 py-4 text-slate-900 font-bold focus:outline-none focus:border-hero/30" />
                  </label>

                  <label class="block">
                    <span class="block text-[10px] font-black uppercase tracking-[0.12em] text-slate-400 mb-2 sm:tracking-[0.22em]">Points</span>
                    <input type="number" min="1" bind:value={rewardForm.points} class="w-full rounded-2xl border-2 border-slate-200 bg-white px-4 py-4 text-slate-900 font-bold focus:outline-none focus:border-hero/30" />
                  </label>

                  <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    <button type="button" onclick={saveReward} disabled={rewardLoading || !rewardForm.title.trim() || rewardForm.points < 1} class="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-slate-900 px-4 py-4 text-xs font-black uppercase tracking-[0.16em] text-white disabled:cursor-not-allowed disabled:opacity-60">
                      {editingRewardId ? 'Save reward' : 'Create reward'}
                    </button>
                    <button type="button" onclick={() => rewardForm.is_active = !rewardForm.is_active} class="inline-flex w-full items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-4 text-xs font-black uppercase tracking-[0.16em] text-slate-700">
                      {rewardForm.is_active ? 'Active' : 'Hidden'}
                    </button>
                  </div>
                  {#if editingRewardId}
                    <button type="button" onclick={cancelEditingReward} class="w-full rounded-2xl px-4 py-3 text-xs font-black uppercase tracking-[0.18em] text-slate-400 transition hover:text-slate-700">
                      Cancel edit
                    </button>
                  {/if}
                </div>
              </section>

              <section class="space-y-3">
                <p class="text-[10px] font-black uppercase tracking-[0.12em] text-slate-400 ml-1 sm:tracking-[0.22em]">Current rewards</p>
                {#if rewards.length > 0}
                  {#each rewards as reward}
                    <div class="rounded-[1.5rem] border border-slate-100 bg-white p-4">
                      <div class="flex min-w-0 items-start justify-between gap-3">
                        <div class="min-w-0">
                          <h4 class="font-black text-slate-950 break-words">{reward.title}</h4>
                          <p class="mt-1 text-sm text-slate-500 break-words">{reward.description || 'No description.'}</p>
                          <div class="mt-3 inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-2 text-xs font-black uppercase tracking-[0.16em] text-slate-600">
                            <Trophy size={13} />
                            {reward.points} points
                          </div>
                        </div>
                        <span class={`shrink-0 rounded-2xl px-3 py-2 text-[10px] font-black uppercase tracking-[0.16em] ${reward.is_active ? 'bg-savings/10 text-savings' : 'bg-slate-100 text-slate-400'}`}>
                          {reward.is_active ? 'Visible' : 'Hidden'}
                        </span>
                      </div>
                      <div class="mt-4 flex flex-wrap gap-2">
                        <button onclick={() => startEditingReward(reward)} class="inline-flex items-center gap-2 rounded-2xl bg-slate-50 px-3 py-2 text-[10px] font-black uppercase tracking-[0.18em] text-slate-700 border border-slate-100">
                          <Settings size={14} />
                          Edit
                        </button>
                        <button onclick={() => deleteReward(reward.id)} class="inline-flex items-center gap-2 rounded-2xl bg-white px-3 py-2 text-[10px] font-black uppercase tracking-[0.18em] text-penalty border border-slate-100">
                          <X size={14} />
                          Delete
                        </button>
                      </div>
                    </div>
                  {/each}
                {:else}
                  <div class="rounded-[1.75rem] border border-dashed border-slate-200 bg-slate-50 p-6 text-center">
                    <p class="text-sm font-black uppercase tracking-[0.12em] text-slate-400 sm:tracking-[0.22em]">No rewards yet</p>
                  </div>
                {/if}
              </section>
            </div>
          {/if}

          {#if activeModal.type === 'requests'}
            <div class="space-y-4">
              <div class="flex items-center justify-between gap-3 rounded-[1.75rem] border border-slate-100 bg-slate-50 p-4">
                <span class="text-sm font-black uppercase tracking-[0.18em] text-slate-500">Pending</span>
                <span class="rounded-2xl bg-hero/10 px-3 py-2 text-xs font-black uppercase tracking-[0.18em] text-hero">{pendingRedemptions.length}</span>
              </div>

              {#if pendingRedemptions.length === 0}
                <div class="rounded-[1.75rem] border border-dashed border-slate-200 bg-slate-50 p-6 text-center">
                  <p class="text-sm font-black uppercase tracking-[0.12em] text-slate-400 sm:tracking-[0.22em]">No pending requests</p>
                </div>
              {:else}
                {#each pendingRedemptions as r}
                  {@const child = children.find((ch) => ch.child.id === r.child_id)}
                  <div class="rounded-[1.5rem] border border-slate-100 bg-white p-4">
                    <div class="flex flex-wrap items-center gap-2">
                      <span class="inline-flex items-center rounded-full bg-hero/10 px-3 py-1 text-[10px] font-black uppercase tracking-[0.16em] text-hero">Pending</span>
                      <span class="text-[10px] font-bold uppercase tracking-[0.18em] text-slate-400">{new Date(r.created_at).toLocaleDateString()}</span>
                    </div>
                    <h4 class="mt-3 font-black text-slate-950 break-words">{r.title}</h4>
                    <p class="mt-2 text-sm text-slate-600 break-words">{r.description || 'No description provided.'}</p>
                    <div class="mt-4 flex flex-wrap items-center gap-2">
                      <span class="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-2 text-xs font-black uppercase tracking-[0.16em] text-slate-700">
                        {child?.child.display_name || 'Unknown child'}
                      </span>
                      <span class="inline-flex items-center gap-2 rounded-full bg-hero/10 px-3 py-2 text-xs font-black uppercase tracking-[0.16em] text-hero">
                        <Trophy size={13} />
                        {r.points} points
                      </span>
                    </div>
                    <div class="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
                      <button onclick={() => processRedemption(r.id, 'approve')} class="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-savings px-4 py-4 text-xs font-black uppercase tracking-[0.16em] text-white shadow-lg shadow-savings/20">
                        <Check size={16} />
                        Approve
                      </button>
                      <button onclick={() => processRedemption(r.id, 'reject')} class="inline-flex w-full items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-4 text-xs font-black uppercase tracking-[0.16em] text-slate-700">
                        <X size={16} />
                        Reject
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
                <p class="text-sm font-black uppercase tracking-[0.12em] text-slate-400 sm:tracking-[0.22em]">Refreshing family members</p>
              </div>
            {/if}

            <!-- Members List -->
            <div class="space-y-3">
              <span class="block text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-2">Parents &amp; Caregivers</span>
              <div class="grid gap-2">
                {#each familyMembers as member}
                  <div class="flex min-w-0 items-center justify-between gap-3 p-4 bg-slate-50 rounded-2xl">
                    <div class="flex min-w-0 items-center gap-3">
                      <div class="w-10 h-10 bg-white rounded-xl flex shrink-0 items-center justify-center text-hero font-black shadow-sm">
                        {member.name ? member.name[0].toUpperCase() : member.email[0].toUpperCase()}
                      </div>
                      <div class="min-w-0">
                        <p class="font-bold text-slate-900 text-sm truncate">{member.name || 'Parent'}</p>
                        <p class="text-[10px] text-slate-400 font-medium uppercase tracking-normal sm:tracking-wider break-all">{member.email}</p>
                      </div>
                    </div>
                    {#if member.id === parent?.id}
                      <span class="shrink-0 px-3 py-1 bg-hero/10 text-hero rounded-lg text-[10px] font-black uppercase tracking-[0.12em] sm:tracking-[0.22em]">You</span>
                    {:else if member.can_remove}
                      <button
                        type="button"
                        onclick={() => removeGrownup(member)}
                        disabled={familyGrownupRemovingId === member.id}
                        class="shrink-0 rounded-xl border border-red-100 bg-white px-3 py-2 text-[10px] font-black uppercase tracking-[0.12em] text-red-500 transition-colors hover:bg-red-50 disabled:opacity-50 sm:tracking-[0.18em]"
                      >
                        {familyGrownupRemovingId === member.id ? 'Removing...' : 'Remove Grownup'}
                      </button>
                    {/if}
                  </div>
                {/each}
              </div>
            </div>

            <!-- Invites List -->
            {#if familyInvites.filter(i => i.status === 'pending').length > 0}
              <div class="space-y-3 pt-4 border-t border-slate-100">
                <span class="block text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-2">Pending Invites</span>
                <div class="grid gap-2">
                  {#each familyInvites.filter(i => i.status === 'pending') as invite}
                    <div class="flex min-w-0 items-center justify-between gap-3 p-4 bg-slate-50 rounded-2xl border-2 border-dashed border-slate-200">
                      <div class="min-w-0">
                        <p class="font-bold text-slate-900 text-sm break-all">{invite.email}</p>
                        <p class="text-[10px] text-slate-400 font-medium uppercase tracking-wider">Waiting for login</p>
                      </div>
                      <button onclick={() => revokeInvite(invite.id)} class="shrink-0 rounded-xl border border-slate-200 bg-white px-3 py-2 text-[10px] font-black uppercase tracking-[0.12em] text-slate-500 transition-colors hover:border-red-100 hover:bg-red-50 hover:text-red-500 sm:tracking-[0.18em]" aria-label="Cancel invite">
                        Cancel Invite
                      </button>
                    </div>
                  {/each}
                </div>
              </div>
            {/if}

            <!-- Invite Form -->
            <div class="space-y-3 pt-4 border-t border-slate-100">
              <label for="co-parent-email" class="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-2">Add Grownup</label>
              <div class="space-y-2">
                <input 
                  id="co-parent-email"
                  type="email" 
                  bind:value={modalForm.email}
                  placeholder="parent-or-caregiver@example.com"
                  class="w-full bg-slate-50 border-2 border-slate-100 rounded-2xl px-6 py-4 font-bold text-slate-900 focus:outline-none focus:border-hero/30 transition-all"
                />
                <p class="text-[10px] text-slate-400 ml-2">Invite another parent or caregiver to help manage points, rewards, school bag items, and family routines.</p>
              </div>
            </div>
          {/if}

          {#if activeModal.type === 'calendar-week'}
            {#if loadingFamilySettings}
              <div class="rounded-[1.75rem] border border-dashed border-slate-200 bg-slate-50 p-6 text-center">
                <div class="mx-auto mb-4 w-10 h-10 animate-spin rounded-full border-4 border-hero border-t-transparent"></div>
                <p class="text-sm font-black uppercase tracking-[0.12em] text-slate-400 sm:tracking-[0.22em]">Loading calendar and school week</p>
              </div>
            {/if}
            <div class="space-y-3">
              <div class="rounded-[1.75rem] border border-slate-100 bg-white p-4">
                <p class="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">Calendar &amp; School Week</p>
                <p class="mt-2 text-sm font-bold text-slate-600">This affects weekly views, points log weeks, calendar planning, and school week planning.</p>
                <div class="mt-4">
                  <label for="family-week-start" class="mb-2 block text-[10px] font-black uppercase tracking-[0.18em] text-slate-400">Week starts on</label>
                  <div class="flex flex-col gap-3 sm:flex-row">
                    <select
                      id="family-week-start"
                      bind:value={familySettingsForm.week_start_day}
                      disabled={loadingFamilySettings || familySettingsSaving || !familySettings}
                      class="w-full rounded-2xl border-2 border-slate-100 bg-slate-50 px-4 py-3 text-sm font-bold text-slate-900 focus:border-hero/30 focus:outline-none disabled:opacity-50"
                    >
                      {#each WEEK_START_OPTIONS as option}
                        <option value={option.value}>{option.label}</option>
                      {/each}
                    </select>
                    <button
                      type="button"
                      onclick={saveFamilySettings}
                      disabled={loadingFamilySettings || familySettingsSaving || !familySettings || familySettingsForm.week_start_day === familySettings.week_start_day}
                      class="rounded-2xl bg-slate-900 px-5 py-3 text-xs font-black uppercase tracking-[0.16em] text-white transition-all disabled:opacity-50"
                    >
                      {familySettingsSaving ? 'Saving...' : 'Save'}
                    </button>
                  </div>
                  <p class="mt-2 text-[10px] font-bold uppercase tracking-[0.12em] text-slate-400">Used for allowance, calendar, and weekly point views.</p>
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
              <div class="flex gap-2 p-1 bg-slate-100 rounded-2xl">
                <button
                  onclick={() => activeTab = 'positive'}
                  class="min-w-0 flex-1 px-2 py-2.5 rounded-xl font-black uppercase tracking-[0.08em] text-[9px] leading-none transition-all sm:px-4 sm:py-3 sm:text-[10px] sm:tracking-[0.08em] {activeTab === 'positive' ? 'bg-white text-hero shadow-sm' : 'text-slate-500 hover:text-slate-700'}"
                >
                  Add
                </button>
                <button
                  onclick={() => activeTab = 'negative'}
                  class="min-w-0 flex-1 px-2 py-2.5 rounded-xl font-black uppercase tracking-[0.08em] text-[9px] leading-none transition-all sm:px-4 sm:py-3 sm:text-[10px] sm:tracking-[0.08em] {activeTab === 'negative' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'}"
                >
                  Remove
                </button>
                <button 
                  onclick={() => activeTab = 'other'}
                  class="min-w-0 flex-1 px-2 py-2.5 rounded-xl font-black uppercase tracking-[0.08em] text-[9px] leading-none transition-all sm:px-4 sm:py-3 sm:text-[10px] sm:tracking-[0.08em] {activeTab === 'other' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'}"
                >
                  Custom
                </button>
                </div>

                {#if activeTab === 'other'}
                  <div class="space-y-4 pb-4">
                    <div class="space-y-2">
                      <label for="custom-points-description" class="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-2">Reason</label>
                      <textarea
                        id="custom-points-description"
                        bind:value={modalForm.description}
                        placeholder="What happened?"
                        rows="3"
                        class="w-full bg-slate-50 border-2 border-slate-100 rounded-2xl px-5 py-4 font-medium text-slate-900 focus:outline-none focus:border-hero/30 transition-all resize-none"
                      ></textarea>
                    </div>

                    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
                      <div class="space-y-2">
                        <label for="custom-points-amount" class="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-2">Points</label>
                        <div class="relative">
                          <input
                            id="custom-points-amount"
                            type="number"
                            min="1"
                            bind:value={modalForm.points}
                            class="w-full bg-slate-50 border-2 border-slate-100 rounded-2xl px-5 py-4 pr-12 font-black text-slate-900 focus:outline-none focus:border-hero/30 transition-all text-2xl"
                          />
                          <span class="absolute right-5 top-1/2 -translate-y-1/2 font-black text-slate-300 text-sm">pts</span>
                        </div>
                      </div>

                      <div class="space-y-2">
                        <label for="custom-points-jar" class="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-2">Jar</label>
                        <select
                          id="custom-points-jar"
                          bind:value={modalForm.jar}
                          class="w-full bg-slate-50 border-2 border-slate-100 rounded-2xl px-5 py-4 font-bold text-slate-900 focus:outline-none focus:border-hero/30 transition-all appearance-none cursor-pointer"
                        >
                          <option value="spending">Points</option>
                          <option value="savings">Saved</option>
                        </select>
                      </div>
                    </div>

                    <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
                      <button
                        type="button"
                        onclick={() => submitCustomPoints('award')}
                        disabled={modalLoading || Math.abs(Number(modalForm.points) || 0) < 1}
                        class="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-hero px-4 py-4 text-xs font-black uppercase tracking-[0.16em] text-white shadow-lg shadow-hero/20 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        <Award size={16} />
                        Add points
                      </button>
                      <button
                        type="button"
                        onclick={() => submitCustomPoints('penalty')}
                        disabled={modalLoading || Math.abs(Number(modalForm.points) || 0) < 1}
                        class="inline-flex w-full items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-4 text-xs font-black uppercase tracking-[0.16em] text-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        <Ban size={16} />
                        Remove points
                      </button>
                    </div>
                  </div>
                {:else}
                  <div class="grid grid-cols-2 md:grid-cols-3 gap-3 sm:gap-4 pb-4">
                    {#each presets.filter(p => p.is_active && (activeTab === 'positive' ? p.points > 0 : p.points < 0)) as p}
                      <button
                        onclick={() => applyPreset(activeModal.child, p)}
                        title={p.title}
                        class="group p-3 sm:p-4 rounded-3xl border-2 transition-all text-center flex flex-col items-center gap-2 min-h-40 sm:min-h-44 {p.points > 0 ? 'border-slate-50 hover:border-hero/20 hover:bg-hero/5' : 'border-slate-50 hover:border-slate-900/10 hover:bg-slate-50'}"
                      >
                        <div class="text-4xl mb-1 h-12 flex items-center justify-center">
                          {p.icon || '✨'}
                        </div>
                        <div class="px-2 py-0.5 rounded-lg font-black text-xs {p.points > 0 ? 'bg-hero text-white' : 'bg-slate-900 text-white'}">
                          {p.points > 0 ? '+' : ''}{p.points} pts
                        </div>
                        <div class="min-w-0 mt-1">
                          <p class="font-bold text-slate-900 text-[11px] leading-tight uppercase tracking-tight line-clamp-2">{p.title}</p>
                        </div>
                      </button>
                    {:else}
                      <div class="col-span-full py-12 text-center text-slate-300">
                        <p class="font-black uppercase tracking-[0.12em] text-xs">No presets found</p>
                        <button onclick={() => openModal('presets', null)} class="text-hero text-[10px] font-black uppercase tracking-[0.12em] mt-2 hover:underline">
                          Add preset
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
                    <p class="text-sm font-black uppercase tracking-[0.12em] text-slate-400 sm:tracking-[0.22em]">No pending requests</p>
                  </div>
                {:else}
                  {#each childRequests as r}
                    <div class="rounded-[1.5rem] border border-slate-100 bg-white p-4">
                      <div class="flex flex-wrap items-center gap-2">
                        <span class="inline-flex items-center rounded-full bg-hero/10 px-3 py-1 text-[10px] font-black uppercase tracking-[0.16em] text-hero">Pending</span>
                        <span class="text-[10px] font-bold uppercase tracking-[0.18em] text-slate-400">{new Date(r.created_at).toLocaleDateString()}</span>
                      </div>
                      <h4 class="mt-3 font-black text-slate-950 break-words">{r.title}</h4>
                      <p class="mt-2 text-sm text-slate-600 break-words">{r.description || 'No description provided.'}</p>
                      <div class="mt-3 inline-flex items-center gap-2 rounded-full bg-hero/10 px-3 py-2 text-xs font-black uppercase tracking-[0.16em] text-hero">
                        <Trophy size={13} />
                        {r.points} points
                      </div>
                      <div class="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
                        <button onclick={() => processRedemption(r.id, 'approve')} class="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-savings px-4 py-4 text-xs font-black uppercase tracking-[0.16em] text-white shadow-lg shadow-savings/20">
                          <Check size={16} />
                          Approve
                        </button>
                        <button onclick={() => processRedemption(r.id, 'reject')} class="inline-flex w-full items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-4 text-xs font-black uppercase tracking-[0.16em] text-slate-700">
                          <X size={16} />
                          Reject
                        </button>
                      </div>
                    </div>
                  {/each}
                {/if}
                <a href="/redemptions" class="inline-flex w-full items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-xs font-black uppercase tracking-[0.14em] text-slate-700 transition hover:border-hero hover:text-hero">
                  <Check size={15} />
                  <span class="sm:hidden">Review Requests</span>
                  <span class="hidden sm:inline">Open Request Review</span>
                </a>
              </div>
            {/if}

            {#if childModalTab === 'school'}
              {@const todayItems = schoolTodayByChild[activeModal.child.child.id] || []}
              {@const tomorrowItems = schoolTomorrowByChild[activeModal.child.child.id] || []}
              <div class="grid gap-4 sm:grid-cols-2">
                {#each [['Today', todayItems], ['Tomorrow', tomorrowItems]] as group}
                  <div class="rounded-[1.75rem] border border-slate-100 bg-white p-4">
                    <p class="text-[10px] font-black uppercase tracking-[0.12em] text-slate-400 sm:tracking-[0.22em]">{group[0]}</p>
                    {#if loadingSchoolPrep}
                      <p class="mt-4 text-sm font-bold text-slate-400">Loading school bag.</p>
                    {:else if group[1].length === 0}
                      <p class="mt-4 text-sm font-bold text-slate-500">Nothing listed.</p>
                    {:else}
                      <div class="mt-4 space-y-2">
                        {#each group[1] as item}
                          <div class="rounded-2xl bg-slate-50 p-3">
                            <p class="text-sm font-black text-slate-950">{schoolNeedLabel(item)}</p>
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
                    <p class="text-sm font-black uppercase tracking-[0.12em] text-slate-400 sm:tracking-[0.22em]">Loading calendar</p>
                  </div>
                {:else if childCalendarError[activeModal.child.child.id]}
                  <div class="rounded-[1.75rem] border border-red-100 bg-red-50 p-5 text-sm font-bold text-red-700">
                    {childCalendarError[activeModal.child.child.id]}
                  </div>
                {:else}
                  <div class="rounded-[1.75rem] border border-slate-100 bg-white p-4">
                    <p class="text-[10px] font-black uppercase tracking-[0.12em] text-slate-400 sm:tracking-[0.22em]">Today</p>
                    {#if todayEvents.length === 0}
                      <p class="mt-4 text-sm font-bold text-slate-500">No calendar items today.</p>
                    {:else}
                      <div class="mt-4 space-y-2">
                        {#each todayEvents as item}
                          <div class="rounded-2xl bg-slate-50 p-3">
                            <p class="break-words text-sm font-black leading-snug text-slate-950">{item.entry.title}</p>
                            <p class="mt-1 break-words text-xs font-bold leading-snug text-slate-400">{formatCalendarTime(item.entry.start_time)} · {item.entry.entry_type}</p>
                          </div>
                        {/each}
                      </div>
                    {/if}
                  </div>
                  <div class="rounded-[1.75rem] border border-slate-100 bg-white p-4">
                    <p class="text-[10px] font-black uppercase tracking-[0.12em] text-slate-400 sm:tracking-[0.22em]">Upcoming</p>
                    {#if upcomingEvents.length === 0}
                      <p class="mt-4 text-sm font-bold text-slate-500">No upcoming calendar items found.</p>
                    {:else}
                      <div class="mt-4 space-y-2">
                        {#each upcomingEvents as item}
                          <div class="rounded-2xl bg-slate-50 p-3">
                            <p class="break-words text-sm font-black leading-snug text-slate-950">{item.entry.title}</p>
                            <p class="mt-1 break-words text-xs font-bold leading-snug text-slate-400">{formatCalendarDate(item.occurrence_date)} · {formatCalendarTime(item.entry.start_time)}</p>
                          </div>
                        {/each}
                      </div>
                    {/if}
                  </div>
                {/if}
                <a href="/calendar" class="inline-flex w-full items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-xs font-black uppercase tracking-[0.14em] text-slate-700 transition hover:border-hero hover:text-hero">
                  <CalendarDays size={15} />
                  <span class="sm:hidden">Calendar</span>
                  <span class="hidden sm:inline">Open Calendar</span>
                </a>
              </div>
            {/if}

            {#if childModalTab === 'savings'}
              {@const allowance = childAllowance(activeModal.child)}
              {@const unlock = nextSavingsUnlock(activeModal.child)}
              <div class="space-y-4">
                <div class="grid grid-cols-2 gap-3">
                  <div class="rounded-[1.5rem] bg-slate-50 p-4">
                    <p class="text-[10px] font-black uppercase tracking-[0.08em] text-slate-400 sm:tracking-[0.18em]">Saved</p>
                    <p class="mt-2 text-2xl font-black text-slate-950">{activeModal.child.savings_balance || 0}</p>
                  </div>
                  <div class="rounded-[1.5rem] bg-slate-50 p-4">
                    <p class="text-[10px] font-black uppercase tracking-[0.08em] text-slate-400 sm:tracking-[0.18em]">Points</p>
                    <p class="mt-2 text-2xl font-black text-slate-950">{childAvailablePoints(activeModal.child)}</p>
                  </div>
                  <div class="rounded-[1.5rem] bg-slate-50 p-4">
                    <p class="text-[10px] font-black uppercase tracking-[0.08em] text-slate-400 sm:tracking-[0.18em]">Unlocked</p>
                    <p class="mt-2 text-2xl font-black text-slate-950">{activeModal.child.available_savings || 0}</p>
                  </div>
                  <div class="rounded-[1.5rem] bg-slate-50 p-4">
                    <p class="text-[10px] font-black uppercase tracking-[0.08em] text-slate-400 sm:tracking-[0.18em]">Held</p>
                    <p class="mt-2 text-2xl font-black text-slate-950">{activeModal.child.locked_savings || 0}</p>
                  </div>
                </div>
                {#if allowance}
                  <div class="rounded-[1.75rem] border border-savings/10 bg-savings/5 p-4">
                    <p class="text-[10px] font-black uppercase tracking-[0.08em] text-savings-dark sm:tracking-[0.18em]">Allowance</p>
                    <p class="mt-2 break-words text-sm font-bold leading-snug text-slate-700">{formatAllowanceMinorAmount(allowance.saved_allowance_minor, allowance.currency, allowance.currency_exponent)} saved · {formatAllowanceMinorAmount(allowance.available_allowance_minor, allowance.currency, allowance.currency_exponent)} available</p>
                  </div>
                {/if}
                <div class="rounded-[1.75rem] border border-slate-100 bg-white p-4">
                  <p class="text-[10px] font-black uppercase tracking-[0.08em] text-slate-400 sm:tracking-[0.18em]">Next unlock</p>
                  {#if unlock}
                    <p class="mt-2 break-words text-sm font-bold leading-snug text-slate-700">{unlock.points} points on {formatCalendarDate(unlock.unlock_date)}</p>
                  {:else}
                    <p class="mt-2 break-words text-sm font-bold leading-snug text-slate-500">No upcoming unlock listed.</p>
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
                <div class="grid grid-cols-3 gap-2 rounded-2xl bg-slate-100 p-1">
                  {#each [['day', 'Day'], ['week', 'Week'], ['year', 'Year']] as period}
                    <button
                      type="button"
                      onclick={() => setPointLogPeriod(period[0])}
                      class="rounded-xl py-3 text-[9px] font-black uppercase tracking-[0.03em] transition-all sm:text-[10px] sm:tracking-[0.08em] {pointLogPeriod === period[0] ? 'bg-white text-slate-950 shadow-sm' : 'text-slate-500 hover:text-slate-700'}"
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
                          <p class="text-3xl font-black text-slate-950">—</p>
                          <p class="mt-1 text-[10px] font-black uppercase tracking-[0.08em] text-slate-400 sm:tracking-[0.18em]">No behaviour points yet</p>
                        </div>
                      </div>
                    </div>
                  {:else}
                    <div class="mx-auto grid h-44 w-44 place-items-center rounded-full" style={ringStyle(percent)}>
                      <div class="grid h-28 w-28 place-items-center rounded-full bg-white shadow-inner">
                        <div class="text-center">
                          <p class="text-3xl font-black text-slate-950">{percent === null ? '—' : `${percent}%`}</p>
                          <p class="mt-1 text-[10px] font-black uppercase tracking-[0.08em] text-slate-400 sm:tracking-[0.18em]">Good</p>
                        </div>
                      </div>
                    </div>
                  {/if}
                  {#if pointLogPeriod === 'year'}
                    <p class="mt-4 text-center text-xs font-bold text-slate-400">Showing available recent history for the yearly view.</p>
                  {/if}
                </div>

                {#if childLedgerLoading[key]}
                  <div class="rounded-[1.75rem] border border-dashed border-slate-200 bg-slate-50 p-6 text-center">
                    <p class="text-sm font-black uppercase tracking-[0.12em] text-slate-400 sm:tracking-[0.22em]">Loading points log</p>
                  </div>
                {:else if childLedgerError[key]}
                  <div class="rounded-[1.75rem] border border-red-100 bg-red-50 p-5 text-sm font-bold text-red-700">
                    {childLedgerError[key]}
                  </div>
                {:else if behaviorLedger.length === 0}
                  <div class="rounded-[1.75rem] border border-dashed border-slate-200 bg-slate-50 p-6 text-center">
                    <p class="text-sm font-black uppercase tracking-[0.12em] text-slate-400 sm:tracking-[0.22em]">No point history for this period</p>
                  </div>
                {:else}
                  <div class="space-y-2">
                    {#each behaviorLedger.slice(0, 8) as tx}
                      <div class="flex items-center justify-between gap-3 rounded-2xl bg-slate-50 p-3">
                        <div class="min-w-0">
                          <p class="truncate text-sm font-black text-slate-950">{tx.description || tx.transaction_type}</p>
                          <p class="text-xs font-bold text-slate-400">{formatLedgerDate(tx.created_at)} · {tx.jar}</p>
                        </div>
                        <span class="shrink-0 rounded-full px-3 py-2 text-xs font-black {tx.points >= 0 ? 'bg-hero/10 text-hero' : 'bg-slate-200 text-slate-700'}">
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
              <label for="modal-title" class="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-2">
                {activeModal.type === 'presets' ? 'Preset Title' : 'Reward Name'}
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
                  placeholder={activeModal.type === 'presets' ? "e.g., Brushed Teeth" : "e.g., 30 mins Screen Time"}
                  class="min-w-0 flex-1 bg-slate-50 border-2 border-slate-100 rounded-2xl px-4 sm:px-6 py-4 font-bold text-slate-900 focus:outline-none focus:border-reward/30 transition-all"
                />
              </div>
            </div>

            {#if activeModal.type === 'presets'}
              <div class="space-y-2">
                <span class="block text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-2">Select Visual (Optional)</span>
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
                <label for="points-amount" class="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-2">Points Amount</label>
                <div class="relative">
                  <input 
                    id="points-amount"
                    type="number" 
                    bind:value={modalForm.points}
                    class="w-full bg-slate-50 border-2 border-slate-100 rounded-2xl px-4 sm:px-6 py-4 font-black text-slate-900 focus:outline-none focus:border-hero/30 transition-all text-2xl"
                  />
                  <span class="absolute right-4 sm:right-6 top-1/2 -translate-y-1/2 font-black text-slate-300 text-sm">pts</span>
                </div>
                {#if activeModal.type === 'presets'}
                  <p class="text-[10px] text-slate-400 ml-2">Use negative numbers to remove points</p>
                {/if}
              </div>

              {#if activeModal.type === 'award' || activeModal.type === 'penalty'}
                <div class="space-y-2">
                  <label for="target-jar" class="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-2">Point destination</label>
                  <select 
                    id="target-jar"
                    bind:value={modalForm.jar}
                    class="w-full bg-slate-50 border-2 border-slate-100 rounded-2xl px-4 sm:px-6 py-4 font-bold text-slate-900 focus:outline-none focus:border-hero/30 transition-all appearance-none cursor-pointer"
                  >
                    <option value="spending">Points</option>
                    <option value="savings">Saved</option>
                  </select>
                </div>
              {/if}
            </div>
          {/if}

          {#if activeModal.type !== 'presets' && activeModal.type !== 'picker' && activeModal.type !== 'family' && activeModal.type !== 'calendar-week' && activeModal.type !== 'child-link' && activeModal.type !== 'child-link-select' && activeModal.type !== 'rewards' && activeModal.type !== 'requests'}
            <div class="space-y-2">
              <label for="modal-description" class="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-2">Description / Reason</label>
              <textarea 
                id="modal-description"
                bind:value={modalForm.description}
                placeholder="What happened? (optional)"
                rows="3"
                class="w-full bg-slate-50 border-2 border-slate-100 rounded-2xl px-6 py-4 font-medium text-slate-900 focus:outline-none focus:border-hero/30 transition-all resize-none"
              ></textarea>
            </div>
          {/if}

          {#if activeModal.type === 'presets'}
            <div class="space-y-2">
              <label for="preset-details" class="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-2">Details</label>
              <textarea 
                id="preset-details"
                bind:value={modalForm.description}
                placeholder="Brief description of when to use this (optional)"
                rows="2"
                class="w-full bg-slate-50 border-2 border-slate-100 rounded-2xl px-6 py-4 font-medium text-slate-900 focus:outline-none focus:border-hero/30 transition-all resize-none"
              ></textarea>
            </div>

            {#if presets.length > 0}
              <div class="space-y-3 pt-4 border-t border-slate-100">
                <span class="block text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-2">Existing Presets</span>
                <div class="grid gap-2">
                  {#each presets as p}
                    <div class="flex items-center justify-between p-4 bg-slate-50 rounded-2xl">
                      <div class="flex items-center gap-3">
                        <span class="text-xl w-8 h-8 flex items-center justify-center bg-white rounded-lg shadow-sm">{p.icon || '✨'}</span>
                        <span class={p.points > 0 ? 'text-hero' : 'text-slate-900'}>
                          {p.points > 0 ? '+' : ''}{p.points}
                        </span>
                        <span class="font-bold text-slate-900 uppercase tracking-tight text-xs">{p.title}</span>
                      </div>
                      <div class="flex items-center gap-3">
                        <button onclick={() => startEditing(p)} class="text-slate-300 hover:text-hero transition-colors">
                          <Settings size={16} />
                        </button>
                        <button onclick={() => deletePreset(p.id)} class="text-slate-300 hover:text-red-500 transition-colors">
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
              <p class="text-[10px] font-bold text-savings-dark leading-relaxed uppercase tracking-[0.12em] sm:tracking-[0.22em]">
                Banked points are locked for 30 days and cannot be used until unlocked.
              </p>
            </div>
          {/if}
        </div>

          {#if activeModal.type !== 'picker' && activeModal.type !== 'child-link' && activeModal.type !== 'child-link-select' && activeModal.type !== 'rewards' && activeModal.type !== 'requests' && activeModal.type !== 'calendar-week'}
            <div class="pt-6 shrink-0 flex flex-col gap-3 bg-white">
              <button 
                onclick={handleModalSubmit}
                disabled={modalLoading}
                class="w-full py-5 rounded-[1.5rem] font-black uppercase tracking-[0.2em] text-sm shadow-xl transition-all active:scale-[0.98] disabled:opacity-50
                {activeModal.type === 'award' ? 'bg-hero text-white shadow-hero/20 hover:bg-hero-dark' : 
                 activeModal.type === 'penalty' ? 'bg-penalty text-white shadow-penalty/30 hover:bg-penalty-dark' :
                 activeModal.type === 'bank' ? 'bg-savings text-white shadow-savings/30 hover:bg-savings-dark' :
                 activeModal.type === 'presets' ? 'bg-slate-900 text-white shadow-slate-200 hover:bg-black' :
                 'bg-reward text-white shadow-reward/30 hover:bg-reward-dark'}"
              >
                {modalLoading ? 'Processing...' : 
             activeModal.type === 'presets' ? (editingPresetId ? 'Save Changes' : 'Create Preset') : 
             activeModal.type === 'family' ? 'Add Grownup' :
             'Confirm Action'}
              </button>
              {#if editingPresetId}
                <button 
                  onclick={cancelEditing}
                  class="w-full py-3 text-[10px] font-black uppercase tracking-[0.12em] text-slate-400 hover:text-slate-600 transition-colors sm:tracking-[0.22em]"
                >
                  Cancel Edit
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
  :global(.card) {
    border: 1px solid rgba(0,0,0,0.05);
    border-radius: 2rem;
    box-shadow: 0 10px 30px -10px rgba(0,0,0,0.05);
  }
  
  :global(.btn-hero) {
    background: #FF5A5F;
    color: white;
    font-weight: 900;
  }
  
  :global(.btn-secondary) {
    background: white;
    border: 2px solid #F1F5F9;
    color: #64748B;
    font-weight: 800;
  }

  .text-hero { color: #FF5A5F; }
  .bg-hero { background: #FF5A5F; }
  .shadow-hero\/20 { box-shadow: 0 10px 20px -5px rgba(255, 90, 95, 0.2); }
  
  .text-savings { color: #00A699; }
  .text-savings-dark { color: #008489; }
  .bg-savings { background: #00A699; }
  .shadow-savings\/20 { box-shadow: 0 10px 20px -5px rgba(0, 166, 153, 0.2); }
  .shadow-savings\/30 { box-shadow: 0 10px 25px -5px rgba(0, 166, 153, 0.3); }

  .text-reward { color: #FC642D; }
  .bg-reward { background: #FC642D; }
  .shadow-reward\/20 { box-shadow: 0 10px 20px -5px rgba(252, 100, 45, 0.2); }
  .shadow-reward\/30 { box-shadow: 0 10px 25px -5px rgba(252, 100, 45, 0.3); }

  .text-penalty { color: #484848; }
  .bg-penalty { background: #484848; }
  .shadow-penalty\/30 { box-shadow: 0 10px 25px -5px rgba(72, 72, 72, 0.3); }

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
</style>
