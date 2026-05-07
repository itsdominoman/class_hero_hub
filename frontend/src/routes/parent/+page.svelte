<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import { 
    UserPlus, Award, Ban, PiggyBank, ArrowRight, Star, Bell, Gift,
    LayoutDashboard, Settings, LogIn, Trophy, Clock, Check, X, 
    History, TrendingUp, ChevronRight, Users, QrCode, Copy, RefreshCcw, Link2, CalendarDays
  } from 'lucide-svelte';

  let parent = $state<any>(null);
  let children = $state<any[]>([]);
  let redemptions = $state<any[]>([]);
  let rewards = $state<any[]>([]);
  let presets = $state<any[]>([]);
  let familyMembers = $state<any[]>([]);
  let familyInvites = $state<any[]>([]);
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
  let parentToolsSection = $state<HTMLElement | null>(null);
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

  const isAuthError = (message: string) =>
    message.toLowerCase().includes('not authenticated') ||
    message.toLowerCase().includes('invalid token') ||
    message.toLowerCase().includes('parent not found');

  function scrollToParentTools() {
    parentToolsSection?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

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

  function schoolNeedLabel(item: SchoolItem) {
    const listedItem = (item?.needed_item || '').trim();
    if (listedItem) return listedItem;
    const title = item?.class_name || 'School item';
    if (/p\.?\s*e\.?/i.test(title)) return 'Gym clothes';
    return `${title} book`;
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
        api.get('/family/members'),
        api.get('/family/invites')
      ]);
      parent = p;
      children = c;
      redemptions = r;
      rewards = rw;
      presets = pr;
      familyMembers = fm;
      familyInvites = fi;
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
      familyMembers = [];
      familyInvites = [];
      const [fm, fi] = await Promise.all([
        api.get('/family/members'),
        api.get('/family/invites')
      ]);
      familyMembers = fm;
      familyInvites = fi;
    } finally {
      loadingFamilySettings = false;
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

    if (type === 'family') {
      void loadFamilySettings();
    }
  }

  function closeModal() {
    activeModal = null;
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
      childLinkError = e instanceof Error ? e.message : 'Unable to create child device link';
      childLinkInvite = null;
      childLinkQr = '';
    } finally {
      childLinkLoading = false;
    }
  }

  function openChildLink(childSummary: any) {
    activeModal = { type: 'child-link', child: childSummary };
    childLinkInvite = null;
    childLinkQr = '';
    childLinkError = null;
    childLinkCopied = false;
    void createChildLink(childSummary);
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
      await loadDashboard();
    } catch (e) {
      childLinkError = e instanceof Error ? e.message : 'Failed to revoke child device access';
    } finally {
      childLinkLoading = false;
    }
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
    if (!confirm('Revoke this invite?')) return;
    try {
      await api.patch(`/family/invites/${id}/revoke`, {});
      await loadDashboard();
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Failed to revoke invite');
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
    const avatarName = childSummary?.child?.avatar_name?.trim();
    if (avatarName) return avatarName.slice(0, 2).toUpperCase();

    const displayName = childSummary?.child?.display_name?.trim() || '?';
    return displayName.slice(0, 1).toUpperCase();
  }

  function childAvatarDescription(childSummary: any) {
    const avatarName = childSummary?.child?.avatar_name?.trim();
    if (avatarName) return `Avatar: ${avatarName}`;
    return 'No avatar chosen yet';
  }

  onMount(loadDashboard);

  const PET_STAGES_ASSETS: Record<string, { label: string; image: string }> = {
    egg: { label: 'Egg', image: '/pets/dragon-1/egg.png' },
    hatchling: { label: 'Hatchling', image: '/pets/dragon-1/hatchling.png' },
    cub: { label: 'Young Dragon', image: '/pets/dragon-1/young-dragon.png' },
    hero: { label: 'Hero Dragon', image: '/pets/dragon-1/hero-dragon.png' },
    beast: { label: 'Legendary Dragon', image: '/pets/dragon-1/legendary-dragon.png' }
  };

  const housePoints = $derived(children.reduce((sum, child) => sum + (child.spending_balance || 0), 0));
  const pendingRedemptions = $derived(redemptions.filter((request) => request.status === 'pending'));

  const getPetImage = (stage: string) => (PET_STAGES_ASSETS[stage] || PET_STAGES_ASSETS.egg).image;
  const getPetLabel = (stage: string) => (PET_STAGES_ASSETS[stage] || PET_STAGES_ASSETS.egg).label;
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
        <p class="text-red-600 font-black mb-4 uppercase tracking-widest text-sm">Failed to load dashboard</p>
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
              <button
                type="button"
                onclick={scrollToParentTools}
                class="inline-flex w-full max-w-full items-center justify-center gap-2 rounded-full bg-hero px-4 py-3 text-xs font-black uppercase tracking-[0.16em] text-white shadow-lg shadow-hero/20 transition hover:bg-hero-dark sm:w-auto"
              >
                <Settings size={14} />
                Manage
              </button>
              <div class="inline-flex max-w-full items-center gap-2 rounded-full bg-slate-900 px-3 py-2 text-xs font-black uppercase tracking-[0.16em] text-white">
                <TrendingUp size={14} />
                {children.length} children
              </div>
              {#if parent}
                <div class="inline-flex max-w-full items-center gap-2 rounded-full bg-slate-100 px-3 py-2 text-xs font-black uppercase tracking-[0.16em] text-slate-700">
                  {parent.name || parent.email}
                </div>
              {/if}
            </div>
          </div>
        </div>
      </div>

      <div class="max-w-5xl mx-auto px-3 sm:px-4 py-6 md:py-8 space-y-6">
        <section class="space-y-4">
          <div class="flex items-center justify-between gap-3">
            <div class="min-w-0">
              <h2 class="text-2xl sm:text-3xl font-black text-slate-950">Children</h2>
            </div>
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
            <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {#each children as c}
                <article class="card flex min-w-0 flex-col overflow-hidden border-slate-100 bg-white p-5 sm:p-6 shadow-xl">
                  <div class="flex min-w-0 items-start gap-4">
                    <div class="flex h-14 w-14 shrink-0 items-center justify-center overflow-hidden rounded-2xl bg-slate-900 text-white shadow-sm">
                      <span class="text-lg font-black tracking-tight">{childAvatarLabel(c)}</span>
                    </div>

                    <div class="min-w-0 flex-1">
                      <h3 class="truncate text-xl font-black text-slate-950">{c.child.display_name}</h3>
                      <p class="mt-1 truncate text-xs font-black uppercase tracking-[0.16em] text-slate-400">
                        {childAvatarDescription(c)}
                      </p>

                      <div class="mt-3 flex flex-wrap items-center gap-2">
                        <span class="inline-flex items-center gap-2 rounded-full bg-hero/10 px-3 py-2 text-xs font-black uppercase tracking-[0.14em] text-hero">
                          <Star size={13} fill="currentColor" />
                          {c.spending_balance || 0} HP
                        </span>
                        <span class="inline-flex items-center gap-2 rounded-full bg-savings/10 px-3 py-2 text-xs font-black uppercase tracking-[0.14em] text-savings">
                          <PiggyBank size={13} />
                          {c.savings_balance || 0} saved
                        </span>
                        {#if c.pending_redemptions > 0}
                          <span class="inline-flex items-center gap-2 rounded-full bg-amber-100 px-3 py-2 text-xs font-black uppercase tracking-[0.14em] text-amber-700">
                            <Clock size={13} />
                            {c.pending_redemptions} pending
                          </span>
                        {/if}
                      </div>
                    </div>
                  </div>

                  <div class="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2">
                    <a href={`/child/${c.child.id}`} class="btn-hero inline-flex w-full items-center justify-center gap-2 rounded-2xl px-4 py-4 text-xs font-black uppercase tracking-[0.16em] shadow-xl shadow-hero/20">
                      Open child
                      <ArrowRight size={16} />
                    </a>
                    <button
                      type="button"
                      onclick={() => openModal('picker', c)}
                      class="btn-secondary inline-flex w-full items-center justify-center gap-2 rounded-2xl px-4 py-4 text-xs font-black uppercase tracking-[0.16em]"
                    >
                      <Star size={16} />
                      Points
                    </button>
                  </div>
                </article>
              {/each}
            </div>
          {/if}
        </section>

        <section class="grid gap-4 md:grid-cols-[minmax(0,1.08fr)_minmax(0,0.92fr)]">
          <div class="card overflow-hidden border-slate-100 bg-white p-5 sm:p-6 shadow-xl">
            <div class="flex items-start justify-between gap-4 min-w-0">
              <div class="min-w-0">
                <h2 class="text-2xl font-black text-slate-950">House Points</h2>
              </div>
              <div class="shrink-0 rounded-2xl bg-hero/10 px-3 py-3 text-hero">
                <Star size={22} fill="currentColor" />
              </div>
            </div>

            <div class="mt-5 flex items-end gap-3">
              <div class="text-4xl font-black tracking-tight text-slate-950">{housePoints}</div>
              <div class="pb-1 text-xs font-black uppercase tracking-[0.18em] text-slate-400">HP</div>
            </div>
          </div>

          <button
            type="button"
            onclick={() => openModal('requests', null)}
            class="card flex min-w-0 flex-col justify-between overflow-hidden border-slate-100 bg-white p-5 sm:p-6 text-left shadow-xl transition hover:-translate-y-0.5 hover:shadow-2xl"
          >
            <div class="flex items-start justify-between gap-4">
              <div class="min-w-0">
                <h2 class="text-2xl font-black text-slate-950">Reward Requests</h2>
              </div>
              <div class={`shrink-0 rounded-2xl px-3 py-2 text-xs font-black uppercase tracking-[0.18em] ${pendingRedemptions.length > 0 ? 'bg-hero/10 text-hero' : 'bg-slate-100 text-slate-400'}`}>
                {pendingRedemptions.length}
              </div>
            </div>

            <div class="mt-4 inline-flex w-fit items-center gap-2 rounded-full bg-slate-100 px-3 py-2 text-[10px] font-black uppercase tracking-[0.16em] text-slate-600">
              <Clock size={13} />
              {pendingRedemptions.length > 0 ? `${pendingRedemptions.length} pending` : 'No pending requests'}
            </div>
          </button>
        </section>

        <section bind:this={parentToolsSection} class="card scroll-mt-6 overflow-hidden border-slate-100 bg-white p-5 sm:p-6 shadow-xl">
          <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div class="min-w-0">
              <h2 class="text-2xl font-black text-slate-950">Parent Tools</h2>
            </div>
          </div>

          <div class="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <button type="button" onclick={() => openModal('rewards', null)} class="inline-flex w-full items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 text-xs font-black uppercase tracking-[0.16em] text-slate-700 transition hover:border-hero hover:text-hero">
              <Gift size={16} />
              Manage rewards
            </button>
            <button type="button" onclick={() => openModal('family', null)} class="inline-flex w-full items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 text-xs font-black uppercase tracking-[0.16em] text-slate-700 transition hover:border-hero hover:text-hero">
              <Users size={16} />
              Family settings
            </button>
            <button type="button" onclick={() => openModal('presets', null)} class="inline-flex w-full items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 text-xs font-black uppercase tracking-[0.16em] text-slate-700 transition hover:border-hero hover:text-hero">
              <Settings size={16} />
              Manage behaviours
            </button>
            <a href="/calendar" class="inline-flex w-full items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 text-xs font-black uppercase tracking-[0.16em] text-slate-700 transition hover:border-hero hover:text-hero">
              <CalendarDays size={16} />
              Open calendar
            </a>
            <button type="button" onclick={() => openModal('requests', null)} class="inline-flex w-full items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 text-xs font-black uppercase tracking-[0.16em] text-slate-700 transition hover:border-hero hover:text-hero">
              <Check size={16} />
              View pending requests
            </button>
            <button type="button" onclick={addChild} disabled={loadingChildren} class="inline-flex w-full items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 text-xs font-black uppercase tracking-[0.16em] text-slate-700 transition hover:border-hero hover:text-hero disabled:opacity-60 disabled:cursor-not-allowed">
              <UserPlus size={16} />
              Add child
            </button>
            <button type="button" onclick={() => openModal('child-link-select', null)} disabled={children.length === 0} class="inline-flex w-full items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 text-xs font-black uppercase tracking-[0.16em] text-slate-700 transition hover:border-hero hover:text-hero disabled:cursor-not-allowed disabled:opacity-60">
              <QrCode size={16} />
              Link child device
            </button>
          </div>
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
        <div class="flex justify-between items-start gap-4 mb-6 sm:mb-8 shrink-0">
          <div class="flex min-w-0 items-center gap-3 sm:gap-4">
            <div class="w-12 h-12 sm:w-16 sm:h-16 rounded-3xl flex items-center justify-center shadow-lg shrink-0
              {activeModal.type === 'award' ? 'bg-hero text-white shadow-hero/20' : 
               activeModal.type === 'penalty' ? 'bg-penalty text-white shadow-penalty/20' :
               activeModal.type === 'bank' ? 'bg-savings text-white shadow-savings/20' :
               activeModal.type === 'presets' ? 'bg-slate-900 text-white shadow-slate-200' :
               activeModal.type === 'picker' ? 'bg-slate-900 text-white shadow-slate-200' :
               activeModal.type === 'family' ? 'bg-hero text-white shadow-hero/20' :
               activeModal.type === 'child-link' ? 'bg-slate-900 text-white shadow-slate-200' :
               activeModal.type === 'child-link-select' ? 'bg-slate-900 text-white shadow-slate-200' :
               activeModal.type === 'rewards' ? 'bg-reward text-white shadow-reward/20' :
               activeModal.type === 'requests' ? 'bg-savings text-white shadow-savings/20' :
               'bg-reward text-white shadow-reward/20'}">
              {#if activeModal.type === 'award'}<Award size={32} />
              {:else if activeModal.type === 'penalty'}<Ban size={32} />
              {:else if activeModal.type === 'bank'}<PiggyBank size={32} />
              {:else if activeModal.type === 'presets'}<Settings size={32} />
              {:else if activeModal.type === 'picker'}<Star size={32} class="text-hero" />
              {:else if activeModal.type === 'family'}<Users size={32} />
              {:else if activeModal.type === 'child-link'}<QrCode size={32} />
              {:else if activeModal.type === 'child-link-select'}<QrCode size={32} />
              {:else if activeModal.type === 'rewards'}<Gift size={32} />
              {:else if activeModal.type === 'requests'}<Check size={32} />
              {:else}<Trophy size={32} />{/if}
            </div>
            <div class="min-w-0">
              <h3 class="text-xl sm:text-2xl font-black text-slate-900 uppercase tracking-tight break-words leading-tight">
                {activeModal.type === 'award' ? 'Award Points' : 
                 activeModal.type === 'penalty' ? 'Apply Penalty' :
                 activeModal.type === 'bank' ? 'Bank to Savings' :
                activeModal.type === 'presets' ? (editingPresetId ? 'Edit Behaviour' : 'Manage Behaviours') :
                activeModal.type === 'picker' ? 'Points' :
                 activeModal.type === 'family' ? 'Family Settings' :
                 activeModal.type === 'child-link' ? 'Link Child Device' :
                 activeModal.type === 'child-link-select' ? 'Link Child Device' :
                 activeModal.type === 'rewards' ? 'Manage Rewards' :
                 activeModal.type === 'requests' ? 'Reward Approvals' :
                 'Redeem Points'}
              </h3>
              <p class="text-slate-400 font-black text-[10px] sm:text-xs uppercase tracking-[0.14em] sm:tracking-[0.2em] break-words">
                {activeModal.type === 'presets' ? (editingPresetId ? 'Update this action' : 'Configure reusable actions') : 
                 activeModal.type === 'family' ? 'Manage members & co-parents' :
                 activeModal.type === 'child-link' ? 'Child device link' :
                 activeModal.type === 'child-link-select' ? 'Choose a child first' :
                 activeModal.type === 'rewards' ? 'Family rewards' :
                 activeModal.type === 'requests' ? 'Requests' :
                 `For ${activeModal.child?.child?.display_name}`}
              </p>
            </div>
          </div>
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
          {#if activeModal.type === 'child-link'}
            <div class="space-y-4">
              <div class="rounded-[1.75rem] border border-slate-100 bg-slate-50 p-5">
                <p class="text-[10px] font-black uppercase tracking-[0.22em] text-slate-400">Child</p>
                <p class="mt-2 text-2xl font-black text-slate-950 break-words">{activeModal.child.child.display_name}</p>
                <p class="mt-2 text-sm text-slate-600">This QR links one tablet or phone directly to this child profile.</p>
              </div>

              {#if childLinkLoading && !childLinkInvite}
                <div class="rounded-[1.75rem] border border-dashed border-slate-200 bg-white p-8 text-center">
                  <div class="mx-auto w-12 h-12 rounded-2xl bg-slate-100 flex items-center justify-center animate-pulse">
                    <QrCode size={22} class="text-slate-400" />
                  </div>
                  <p class="mt-4 text-sm font-black uppercase tracking-[0.22em] text-slate-400">Generating QR</p>
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
                    <img src={childLinkQr} alt="QR code for child device link" class="w-full h-auto rounded-2xl" />
                  {/if}
                </div>
                    <div class="text-center">
                      <p class="text-[10px] font-black uppercase tracking-[0.22em] text-slate-400">Expires</p>
                      <p class="text-lg font-black text-slate-950 break-words">{new Date(childLinkInvite.expires_at).toLocaleString()}</p>
                    </div>
                  </div>

                  <div class="space-y-2">
                    <p class="text-[10px] font-black uppercase tracking-[0.22em] text-slate-400 ml-1">Fallback link</p>
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
                    <p class="text-sm font-black uppercase tracking-[0.22em] text-slate-400">No active QR</p>
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
            </div>
          {/if}

          {#if activeModal.type === 'child-link-select'}
            <div class="space-y-3">
              {#if children.length === 0}
                <div class="rounded-[1.75rem] border border-dashed border-slate-200 bg-slate-50 p-6 text-center">
                  <p class="text-sm font-black uppercase tracking-[0.22em] text-slate-400">No children yet</p>
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
                    <p class="text-[10px] font-black uppercase tracking-[0.22em] text-slate-400 mb-2">Reward editor</p>
                    <h4 class="text-xl font-black text-slate-950">{editingRewardId ? 'Edit reward' : 'Create a reward'}</h4>
                  </div>
                  <Gift size={20} class="shrink-0 text-reward" />
                </div>

                <div class="space-y-4">
                  <label class="block">
                    <span class="block text-[10px] font-black uppercase tracking-[0.22em] text-slate-400 mb-2">Reward name</span>
                    <input type="text" bind:value={rewardForm.title} placeholder="Movie night" class="w-full rounded-2xl border-2 border-slate-200 bg-white px-4 py-4 text-slate-900 font-bold focus:outline-none focus:border-hero/30" />
                  </label>

                  <label class="block">
                    <span class="block text-[10px] font-black uppercase tracking-[0.22em] text-slate-400 mb-2">Description</span>
                    <input type="text" bind:value={rewardForm.description} placeholder="Extra screen time" class="w-full rounded-2xl border-2 border-slate-200 bg-white px-4 py-4 text-slate-900 font-bold focus:outline-none focus:border-hero/30" />
                  </label>

                  <label class="block">
                    <span class="block text-[10px] font-black uppercase tracking-[0.22em] text-slate-400 mb-2">Points</span>
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
                <p class="text-[10px] font-black uppercase tracking-[0.22em] text-slate-400 ml-1">Current rewards</p>
                {#if rewards.length > 0}
                  {#each rewards as reward}
                    <div class="rounded-[1.5rem] border border-slate-100 bg-white p-4">
                      <div class="flex min-w-0 items-start justify-between gap-3">
                        <div class="min-w-0">
                          <h4 class="font-black text-slate-950 break-words">{reward.title}</h4>
                          <p class="mt-1 text-sm text-slate-500 break-words">{reward.description || 'No description.'}</p>
                          <div class="mt-3 inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-2 text-xs font-black uppercase tracking-[0.16em] text-slate-600">
                            <Trophy size={13} />
                            {reward.points} HP
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
                    <p class="text-sm font-black uppercase tracking-[0.22em] text-slate-400">No rewards yet</p>
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
                  <p class="text-sm font-black uppercase tracking-[0.22em] text-slate-400">No pending requests</p>
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
                        {r.points} HP
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
                <p class="text-sm font-black uppercase tracking-[0.22em] text-slate-400">Refreshing family members</p>
              </div>
            {/if}

            <!-- Members List -->
            <div class="space-y-3">
              <span class="block text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-2">Family Members</span>
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
                      <span class="shrink-0 px-3 py-1 bg-hero/10 text-hero rounded-lg text-[10px] font-black uppercase tracking-widest">You</span>
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
                      <button onclick={() => revokeInvite(invite.id)} class="h-11 w-11 shrink-0 text-slate-300 hover:text-red-500 transition-colors flex items-center justify-center" aria-label="Revoke invite">
                        <X size={16} />
                      </button>
                    </div>
                  {/each}
                </div>
              </div>
            {/if}

            <!-- Invite Form -->
            <div class="space-y-3 pt-4 border-t border-slate-100">
              <label for="co-parent-email" class="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-2">Invite Co-Parent</label>
              <div class="space-y-2">
                <input 
                  id="co-parent-email"
                  type="email" 
                  bind:value={modalForm.email}
                  placeholder="co-parent@example.com"
                  class="w-full bg-slate-50 border-2 border-slate-100 rounded-2xl px-6 py-4 font-bold text-slate-900 focus:outline-none focus:border-hero/30 transition-all"
                />
                <p class="text-[10px] text-slate-400 ml-2">They will join your family automatically when they log in with this email.</p>
              </div>
            </div>
          {/if}

          {#if activeModal.type === 'picker'}
            <!-- Child action picker -->
            <div class="flex gap-2 p-1 bg-slate-100 rounded-2xl sticky top-0 z-20">
              <button
                onclick={() => activeTab = 'positive'}
                class="flex-1 py-3 rounded-xl font-black uppercase tracking-widest text-[10px] transition-all
                  {activeTab === 'positive' ? 'bg-white text-hero shadow-sm' : 'text-slate-500 hover:text-slate-700'}"
              >
                Positive
              </button>
              <button
                onclick={() => activeTab = 'negative'}
                class="flex-1 py-3 rounded-xl font-black uppercase tracking-widest text-[10px] transition-all
                  {activeTab === 'negative' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'}"
              >
                Negative
              </button>
              <button 
                onclick={() => activeTab = 'other'}
                class="flex-1 py-3 rounded-xl font-black uppercase tracking-widest text-[10px] transition-all
                  {activeTab === 'other' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'}"
              >
                Other
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
                      <span class="absolute right-5 top-1/2 -translate-y-1/2 font-black text-slate-300 text-sm">HP</span>
                    </div>
                  </div>

                  <div class="space-y-2">
                    <label for="custom-points-jar" class="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-2">Jar</label>
                    <select
                      id="custom-points-jar"
                      bind:value={modalForm.jar}
                      class="w-full bg-slate-50 border-2 border-slate-100 rounded-2xl px-5 py-4 font-bold text-slate-900 focus:outline-none focus:border-hero/30 transition-all appearance-none cursor-pointer"
                    >
                      <option value="spending">Spending</option>
                      <option value="savings">Savings</option>
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
                    Subtract points
                  </button>
                </div>
              </div>
            {:else}
              <div class="grid grid-cols-2 md:grid-cols-3 gap-3 sm:gap-4 pb-4">
                {#each presets.filter(p => p.is_active && (activeTab === 'positive' ? p.points > 0 : p.points < 0)) as p}
                  <button
                    onclick={() => applyPreset(activeModal.child, p)}
                    title={p.title}
                    class="group p-3 sm:p-4 rounded-3xl border-2 transition-all text-center flex flex-col items-center gap-2 min-h-40 sm:min-h-44
                      {p.points > 0 ? 'border-slate-50 hover:border-hero/20 hover:bg-hero/5' : 'border-slate-50 hover:border-slate-900/10 hover:bg-slate-50'}"
                  >
                    <div class="text-4xl mb-1 h-12 flex items-center justify-center">
                      {p.icon || '✨'}
                    </div>
                    <div class="px-2 py-0.5 rounded-lg font-black text-xs
                      {p.points > 0 ? 'bg-hero text-white' : 'bg-slate-900 text-white'}">
                      {p.points > 0 ? '+' : ''}{p.points} HP
                    </div>
                    <div class="min-w-0 mt-1">
                      <p class="font-bold text-slate-900 text-[11px] leading-tight uppercase tracking-tight line-clamp-2">{p.title}</p>
                    </div>
                  </button>
                {:else}
                  <div class="col-span-full py-12 text-center text-slate-300">
                    <p class="font-black uppercase tracking-widest text-xs">No presets found</p>
                    <button onclick={() => openModal('presets', null)} class="text-hero text-[10px] font-black uppercase tracking-widest mt-2 hover:underline">
                      Add preset
                    </button>
                  </div>
                {/each}
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

          {#if activeModal.type !== 'picker' && activeModal.type !== 'family' && activeModal.type !== 'child-link' && activeModal.type !== 'child-link-select' && activeModal.type !== 'rewards' && activeModal.type !== 'requests'}
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
                  <span class="absolute right-4 sm:right-6 top-1/2 -translate-y-1/2 font-black text-slate-300 text-sm">HP</span>
                </div>
                {#if activeModal.type === 'presets'}
                  <p class="text-[10px] text-slate-400 ml-2">Use negative for penalties</p>
                {/if}
              </div>

              {#if activeModal.type === 'award' || activeModal.type === 'penalty'}
                <div class="space-y-2">
                  <label for="target-jar" class="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-2">Target Jar</label>
                  <select 
                    id="target-jar"
                    bind:value={modalForm.jar}
                    class="w-full bg-slate-50 border-2 border-slate-100 rounded-2xl px-4 sm:px-6 py-4 font-bold text-slate-900 focus:outline-none focus:border-hero/30 transition-all appearance-none cursor-pointer"
                  >
                    <option value="spending">Spending Jar</option>
                    <option value="savings">Savings Jar</option>
                  </select>
                </div>
              {/if}
            </div>
          {/if}

          {#if activeModal.type !== 'presets' && activeModal.type !== 'picker' && activeModal.type !== 'family' && activeModal.type !== 'child-link' && activeModal.type !== 'child-link-select' && activeModal.type !== 'rewards' && activeModal.type !== 'requests'}
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
              <label for="internal-notes" class="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-2">Internal Notes</label>
              <textarea 
                id="internal-notes"
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
              <p class="text-[10px] font-bold text-savings-dark leading-relaxed uppercase tracking-widest">
                Banked points are locked for 30 days and cannot be spent or withdrawn until unlocked.
              </p>
            </div>
          {/if}
        </div>

          {#if activeModal.type !== 'picker' && activeModal.type !== 'child-link' && activeModal.type !== 'child-link-select' && activeModal.type !== 'rewards' && activeModal.type !== 'requests'}
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
             activeModal.type === 'family' ? 'Send Invitation' :
             'Confirm Action'}
              </button>
              {#if editingPresetId}
                <button 
                  onclick={cancelEditing}
                  class="w-full py-3 text-[10px] font-black uppercase tracking-widest text-slate-400 hover:text-slate-600 transition-colors"
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
