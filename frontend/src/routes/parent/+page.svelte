<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import { 
    UserPlus, Award, Ban, PiggyBank, ArrowRight, Star, Bell, Gift,
    LayoutDashboard, Settings, LogIn, Trophy, Clock, Check, X, 
    History, TrendingUp, ChevronRight, Users, QrCode, Copy, RefreshCcw, Link2
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

  const DEFAULT_EMOJIS = ['🪥', '📚', '🛏️', '⏰', '🧹', '🧺', '🍎', '🥦', '👍', '❤️', '⭐', '👑', '🎮', '🖥️', '📱', '😴', '😡', '🚫', '🧸', '🏃', '🎒', '✏️', '🧼', '🍽️'];


  const isAuthError = (message: string) =>
    message.toLowerCase().includes('not authenticated') ||
    message.toLowerCase().includes('invalid token') ||
    message.toLowerCase().includes('parent not found');

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

  async function applyPreset(childSummary: any, preset: any) {
    try {
      const childId = childSummary.child.id;
      if (preset.points > 0) {
        await api.post(`/children/${childId}/award`, {
          points: preset.points,
          description: preset.title,
          jar: 'spending'
        });
      } else {
        await api.post(`/children/${childId}/penalty`, {
          points: Math.abs(preset.points),
          description: preset.title,
          jar: 'spending'
        });
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

  onMount(loadDashboard);

  const getPetEmoji = (stage: string) => {
    switch (stage) {
      case 'egg': return '🥚';
      case 'hatchling': return '🐣';
      case 'cub': return '🦊';
      case 'hero': return '🦸';
      case 'beast': return '🐉';
      default: return '🥚';
    }
  };
</script>

<div class="bg-slate-50 min-h-screen">
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
    <!-- Header -->
    <div class="bg-white border-b border-slate-200">
      <div class="max-w-7xl mx-auto px-4 py-5 flex flex-col gap-4 md:h-20 md:flex-row md:items-center md:justify-between">
        <div class="flex items-center gap-3 min-w-0">
          <div class="w-10 h-10 bg-slate-900 rounded-xl flex items-center justify-center text-white shrink-0">
            <LayoutDashboard size={20} />
          </div>
          <div class="min-w-0">
            <h1 class="text-xl font-black text-slate-900 uppercase tracking-tighter">Overview</h1>
            <p class="text-sm text-slate-500 truncate">Signed in as {parent?.name || parent?.email}</p>
          </div>
        </div>
        <div class="flex items-center gap-3 self-start md:self-auto">
          <div class="flex items-center gap-2 px-4 py-2 bg-slate-50 rounded-full border border-slate-100">
            <TrendingUp size={16} class="text-hero" />
            <span class="text-xs font-black text-slate-600 uppercase tracking-widest">
              Family Hub Active
            </span>
          </div>
        </div>
      </div>
    </div>

    <div class="max-w-7xl mx-auto px-4 py-12">
      <!-- Section: My Heroes -->
      <div class="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-12">
        <div>
          <h2 class="text-4xl font-black text-slate-900 mb-2">My Heroes</h2>
          <p class="text-slate-500 font-medium">Tracking responsibility and growth across the family.</p>
        </div>
        
        <div class="flex items-center gap-3 self-start md:self-auto flex-wrap">
          <button onclick={() => openModal('family', null)} class="btn-secondary flex items-center gap-2 px-6 py-4 rounded-2xl">
            <Users size={20} /> Family Settings
          </button>
          <button onclick={() => openModal('presets', null)} class="btn-secondary flex items-center gap-2 px-6 py-4 rounded-2xl">
            <Settings size={20} /> Manage Behaviours
          </button>
          <button onclick={addChild} disabled={loadingChildren} class="btn-hero flex items-center gap-2 px-6 py-4 rounded-2xl shadow-xl shadow-hero/20 disabled:opacity-60 disabled:cursor-not-allowed">
            <UserPlus size={20} /> {loadingChildren ? 'Adding...' : 'Add Child'}
          </button>
        </div>
      </div>

      {#if children.length === 0}
        <div class="card p-16 text-center border-dashed border-4 border-slate-200 bg-white/50 max-w-2xl mx-auto">
          <div class="w-24 h-24 bg-slate-100 text-slate-400 rounded-3xl flex items-center justify-center mx-auto mb-8">
            <UserPlus size={48} />
          </div>
          <h2 class="text-3xl font-black text-slate-800 mb-4 tracking-tight">Your Hero Hub is Empty</h2>
          <p class="text-slate-500 mb-10 max-w-sm mx-auto font-medium">Add your first child to start awarding points and managing their hero journey.</p>
          <button onclick={addChild} class="btn-hero px-12 py-5 rounded-2xl text-lg">Add Your First Child</button>
        </div>
      {:else}
        <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-8 mb-20">
          {#each children as c}
            <div class="card group hover:shadow-2xl transition-all duration-500 border-none bg-white relative overflow-hidden flex flex-col h-full">
              <div class="absolute top-0 right-0 w-32 h-32 bg-hero/5 rounded-full -mr-16 -mt-16 group-hover:scale-150 transition-transform duration-700"></div>
              
              <!-- Card Header -->
              <div class="p-8 border-b border-slate-50 flex items-center justify-between relative z-10">
                <div class="flex items-center gap-5 min-w-0">
                  <div class="w-20 h-20 bg-slate-50 group-hover:bg-hero/10 rounded-3xl flex items-center justify-center text-5xl transition-colors duration-500 shadow-inner shrink-0">
                    {getPetEmoji(c.pet_progress.current_stage)}
                  </div>
                  <div class="min-w-0">
                    <h3 class="text-2xl font-black text-slate-900 tracking-tight truncate">{c.child.display_name}</h3>
                    <div class="flex items-center gap-1.5 mt-1">
                      <div class="w-2 h-2 rounded-full bg-hero animate-pulse"></div>
                      <span class="text-[10px] font-black uppercase tracking-[0.2em] text-hero opacity-70">
                        {c.pet_progress.current_stage} stage • {c.pet_progress.lifetime_points} Lifetime
                      </span>
                    </div>
                  </div>
                </div>
                <a href={`/child/${c.child.id}`} class="w-12 h-12 bg-slate-50 rounded-2xl flex items-center justify-center text-slate-300 hover:bg-hero hover:text-white transition-all duration-300 shrink-0">
                  <ArrowRight size={24} />
                </a>
              </div>

              <!-- Stats Grid -->
              <div class="p-8 grid grid-cols-2 gap-6 relative z-10">
                <div class="space-y-1">
                  <div class="flex items-center gap-2 mb-1">
                    <div class="w-6 h-6 bg-reward/10 rounded-lg flex items-center justify-center text-reward">
                      <Star size={14} fill="currentColor" />
                    </div>
                    <span class="text-[10px] font-black text-slate-400 uppercase tracking-widest">Spending</span>
                  </div>
                  <div class="text-3xl font-black text-slate-900 flex items-baseline gap-1">
                    {c.spending_balance}
                    <span class="text-[10px] font-bold text-slate-400 uppercase">HP</span>
                  </div>
                </div>
                <div class="space-y-1">
                  <div class="flex items-center gap-2 mb-1">
                    <div class="w-6 h-6 bg-savings/10 rounded-lg flex items-center justify-center text-savings">
                      <PiggyBank size={14} />
                    </div>
                    <span class="text-[10px] font-black text-slate-400 uppercase tracking-widest">Savings</span>
                  </div>
                  <div class="text-3xl font-black text-slate-900 flex items-baseline gap-1">
                    {c.savings_balance}
                    <span class="text-[10px] font-bold text-slate-400 uppercase">HP</span>
                  </div>
                </div>
                
                {#if c.locked_savings > 0 || c.pending_redemptions > 0}
                  <div class="col-span-2 pt-4 border-t border-slate-50 grid grid-cols-2 gap-4">
                    {#if c.locked_savings > 0}
                      <div class="text-[10px] font-bold text-slate-400">
                        <span class="text-savings-dark">{c.locked_savings} HP</span> locked
                      </div>
                    {/if}
                    {#if c.pending_redemptions > 0}
                      <div class="text-[10px] font-bold text-slate-400">
                        <span class="text-hero">{c.pending_redemptions} HP</span> pending
                      </div>
                    {/if}
                  </div>
                {/if}
              </div>

              <div class="px-8 pb-4 relative z-10">
                <button 
                  onclick={() => openModal('picker', c)}
                  class="w-full py-5 bg-slate-900 text-white rounded-2xl font-black uppercase tracking-widest text-xs flex items-center justify-center gap-2 shadow-xl shadow-slate-200 hover:scale-[1.02] active:scale-95 transition-all"
                >
                  <Star size={18} class="text-hero" /> Quick Action
                </button>
              </div>

              <!-- Quick Actions -->
              <div class="px-8 pb-8 pt-2 grid grid-cols-1 sm:grid-cols-2 gap-3 mt-auto relative z-10 min-w-0">
                <button 
                  onclick={() => openModal('award', c)}
                  class="w-full min-w-0 btn-hero py-4 rounded-xl text-xs font-black uppercase tracking-widest flex items-center justify-center gap-2 shadow-lg shadow-hero/20 hover:scale-[1.02] transition-all"
                >
                  <Award size={18} /> Award
                </button>
                <button 
                  onclick={() => openModal('penalty', c)}
                  class="w-full min-w-0 btn-secondary py-4 rounded-xl text-xs font-black uppercase tracking-widest flex items-center justify-center gap-2 hover:border-penalty hover:text-penalty hover:bg-penalty/5 transition-all"
                >
                  <Ban size={18} /> Penalty
                </button>
                <button 
                  onclick={() => openModal('bank', c)}
                  class="w-full min-w-0 btn-secondary py-4 rounded-xl text-xs font-black uppercase tracking-widest flex items-center justify-center gap-2 hover:border-savings hover:text-savings hover:bg-savings/5 transition-all sm:col-span-2"
                >
                  <PiggyBank size={18} /> Bank to Savings
                </button>
                <button 
                  onclick={() => openModal('redeem', c)}
                  class="w-full min-w-0 btn-secondary py-4 rounded-xl text-xs font-black uppercase tracking-widest flex items-center justify-center gap-2 hover:border-reward hover:text-reward hover:bg-reward/5 transition-all sm:col-span-2"
                >
                  <Trophy size={18} /> Redeem Reward
                </button>
                <button 
                  onclick={() => openChildLink(c)}
                  class="w-full min-w-0 btn-secondary py-4 rounded-xl text-xs font-black uppercase tracking-widest flex items-center justify-center gap-2 hover:border-slate-900 hover:text-slate-900 hover:bg-slate-50 transition-all sm:col-span-2"
                >
                  <QrCode size={18} /> Link Child Device
                </button>
              </div>
            </div>
          {/each}
        </div>
      {/if}

      <!-- Section: Rewards -->
      <div class="mb-20">
        <div class="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-8">
          <div>
            <h2 class="text-3xl md:text-4xl font-black text-slate-900 mb-2">Rewards</h2>
            <p class="text-slate-500 font-medium">Actual rewards children can request from their dashboards.</p>
          </div>
          <button onclick={saveReward} disabled={rewardLoading || !rewardForm.title.trim() || rewardForm.points < 1} class="btn-hero flex items-center gap-2 px-6 py-4 rounded-2xl shadow-xl shadow-hero/20 disabled:opacity-60 disabled:cursor-not-allowed">
            <Trophy size={18} />
            {editingRewardId ? 'Save Reward' : 'Add Reward'}
          </button>
        </div>

        {#if rewardError}
          <div class="mb-4 rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm font-bold text-red-700 break-words">
            {rewardError}
          </div>
        {/if}

        <div class="grid gap-8 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
          <section class="card bg-white p-6 md:p-8 border border-slate-100 shadow-xl">
            <div class="flex items-center justify-between gap-4 mb-6">
              <div>
                <p class="text-[10px] font-black uppercase tracking-[0.25em] text-slate-400 mb-2">Reward editor</p>
                <h3 class="text-2xl font-black text-slate-950">{editingRewardId ? 'Edit reward' : 'Create a reward'}</h3>
              </div>
              <div class="w-12 h-12 rounded-2xl bg-reward/10 text-reward flex items-center justify-center">
                <Gift size={22} />
              </div>
            </div>

            <div class="space-y-4">
              <label class="block">
                <span class="block text-[10px] font-black uppercase tracking-[0.22em] text-slate-400 mb-2">Reward name</span>
                <input
                  type="text"
                  bind:value={rewardForm.title}
                  placeholder="McDonald's Happy Meal"
                  class="w-full min-w-0 rounded-2xl border-2 border-slate-200 bg-slate-50 px-4 py-4 text-slate-900 font-bold focus:outline-none focus:border-hero/30"
                />
              </label>

              <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_120px] gap-4">
                <label class="block">
                  <span class="block text-[10px] font-black uppercase tracking-[0.22em] text-slate-400 mb-2">Description</span>
                  <input
                    type="text"
                    bind:value={rewardForm.description}
                    placeholder="Movie night, extra screen time..."
                    class="w-full min-w-0 rounded-2xl border-2 border-slate-200 bg-slate-50 px-4 py-4 text-slate-900 font-bold focus:outline-none focus:border-hero/30"
                  />
                </label>

                <label class="block">
                  <span class="block text-[10px] font-black uppercase tracking-[0.22em] text-slate-400 mb-2">Points</span>
                  <input
                    type="number"
                    min="1"
                    bind:value={rewardForm.points}
                    class="w-full rounded-2xl border-2 border-slate-200 bg-slate-50 px-4 py-4 text-slate-900 font-bold focus:outline-none focus:border-hero/30"
                  />
                </label>
              </div>

              <div class="flex flex-wrap items-center gap-3">
                <button type="button" onclick={editingRewardId ? cancelEditingReward : saveReward} class="inline-flex items-center gap-2 rounded-2xl bg-slate-900 px-4 py-3 text-xs font-black uppercase tracking-[0.2em] text-white">
                  {editingRewardId ? 'Cancel edit' : 'Create reward'}
                </button>
                <button type="button" onclick={() => rewardForm.is_active = !rewardForm.is_active} class="inline-flex items-center gap-2 rounded-2xl bg-white px-4 py-3 text-xs font-black uppercase tracking-[0.2em] text-slate-700 border-2 border-slate-100">
                  {rewardForm.is_active ? 'Active' : 'Hidden'}
                </button>
              </div>
            </div>
          </section>

          <section class="space-y-4">
            {#if rewards.length > 0}
              <div class="grid gap-4">
                {#each rewards as reward}
                  <div class="card bg-white p-5 border border-slate-100 shadow-xl">
                    <div class="flex items-start justify-between gap-3 min-w-0">
                      <div class="min-w-0 flex-1">
                        <div class="flex flex-wrap items-center gap-2 mb-2">
                          <span class="inline-flex items-center gap-1 rounded-full bg-reward/10 px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.18em] text-reward whitespace-nowrap">
                            <Gift size={12} />
                            Reward
                          </span>
                          <span class="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.18em] text-slate-500 whitespace-nowrap">
                            {reward.points} HP
                          </span>
                        </div>
                        <h3 class="text-lg font-black text-slate-950 break-words">{reward.title}</h3>
                        <p class="text-sm text-slate-600 mt-1 break-words">{reward.description || 'A reward children can request.'}</p>
                      </div>
                      <span class={`shrink-0 rounded-2xl px-3 py-2 text-[10px] font-black uppercase tracking-[0.18em] whitespace-nowrap ${reward.is_active ? 'bg-savings/10 text-savings' : 'bg-slate-100 text-slate-400'}`}>
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
              </div>
            {:else}
              <div class="card bg-white p-8 border border-dashed border-slate-200 text-center">
                <p class="text-sm font-black uppercase tracking-[0.22em] text-slate-400">No rewards yet</p>
                <p class="text-sm text-slate-500 mt-2">Add real rewards here. Children will see only these items.</p>
              </div>
            {/if}
          </section>
        </div>
      </div>

      <!-- Section: Redemption Requests -->
      <div class="mb-20">
        <div class="flex items-center gap-4 mb-8">
          <div class="w-12 h-12 bg-reward/10 text-reward rounded-2xl flex items-center justify-center">
            <Trophy size={24} />
          </div>
          <div>
            <h2 class="text-3xl font-black text-slate-900 tracking-tight">Reward Requests</h2>
            <p class="text-slate-500 font-medium">Approve or reject pending requests from your heroes.</p>
          </div>
        </div>

        {#if redemptions.filter(r => r.status === 'pending').length === 0}
          <div class="card p-12 text-center bg-slate-50 border-dashed border-2 border-slate-200">
            <p class="text-slate-400 font-black uppercase tracking-widest text-sm">No pending requests</p>
          </div>
        {:else}
          <div class="grid lg:grid-cols-2 gap-6">
            {#each redemptions.filter(r => r.status === 'pending') as r}
              {@const child = children.find(ch => ch.child.id === r.child_id)}
              <div class="card p-8 flex flex-col md:flex-row gap-8 items-start bg-white border-l-8 border-hero shadow-xl hover:shadow-2xl transition-all duration-300">
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-3 mb-3">
                    <span class="text-xs font-black bg-hero/10 text-hero px-3 py-1 rounded-full uppercase tracking-widest">
                      Pending
                    </span>
                    <span class="text-xs font-bold text-slate-400 flex items-center gap-1">
                      <Clock size={14} /> {new Date(r.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <h3 class="text-2xl font-black text-slate-900 mb-1">{r.title}</h3>
                  <p class="text-slate-600 mb-6 font-medium line-clamp-2">{r.description || 'No description provided.'}</p>
                  
                  <div class="flex items-center gap-6">
                    <div class="flex items-center gap-2">
                      <div class="w-8 h-8 bg-slate-100 rounded-lg flex items-center justify-center text-slate-500 font-black text-sm">
                        {getPetEmoji(child?.pet_progress.current_stage || 'egg')}
                      </div>
                      <span class="text-sm font-black text-slate-700">{child?.child.display_name}</span>
                    </div>
                    <div class="flex items-center gap-2 text-hero">
                      <Trophy size={18} />
                      <span class="text-xl font-black">{r.points} HP</span>
                    </div>
                  </div>
                </div>

                <div class="flex flex-row md:flex-col gap-3 w-full md:w-auto shrink-0 pt-2">
                  <button 
                    onclick={() => processRedemption(r.id, 'approve')}
                    class="flex-1 md:w-40 py-4 bg-savings text-white rounded-2xl font-black uppercase tracking-widest text-xs flex items-center justify-center gap-2 shadow-lg shadow-savings/20 hover:scale-[1.02] active:scale-95 transition-all"
                  >
                    <Check size={18} /> Approve
                  </button>
                  <button 
                    onclick={() => processRedemption(r.id, 'reject')}
                    class="flex-1 md:w-40 py-4 bg-white border-2 border-slate-100 text-slate-400 rounded-2xl font-black uppercase tracking-widest text-xs flex items-center justify-center gap-2 hover:border-penalty hover:text-penalty transition-all"
                  >
                    <X size={18} /> Reject
                  </button>
                </div>
              </div>
            {/each}
          </div>
        {/if}

        {#if redemptions.filter(r => r.status !== 'pending').length > 0}
          <details class="mt-8 group">
            <summary class="flex items-center gap-2 cursor-pointer text-slate-400 font-black uppercase tracking-widest text-[10px] hover:text-slate-600 transition-colors list-none">
              <ChevronRight size={14} class="group-open:rotate-90 transition-transform" />
              View Redemption History
            </summary>
            <div class="mt-4 space-y-3 opacity-60">
              {#each redemptions.filter(r => r.status !== 'pending').slice(0, 5) as r}
                {@const child = children.find(ch => ch.child.id === r.child_id)}
                <div class="card p-4 flex items-center justify-between bg-white text-xs font-bold border-none">
                  <div class="flex items-center gap-4">
                    <span class={r.status === 'approved' ? 'text-savings' : 'text-penalty'}>
                      {r.status === 'approved' ? '✓' : '✗'}
                    </span>
                    <span class="text-slate-900">{r.title}</span>
                    <span class="text-slate-400">• {child?.child.display_name}</span>
                  </div>
                  <div class="text-slate-400">{r.points} HP</div>
                </div>
              {/each}
            </div>
          </details>
        {/if}
      </div>
    </div>
  {/if}
</div>

<!-- Modals -->
{#if activeModal}
  <div class="fixed inset-0 z-[100] flex items-center justify-center p-4">
    <!-- Backdrop -->
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div 
      class="absolute inset-0 bg-slate-900/60 backdrop-blur-sm transition-opacity" 
      onclick={closeModal}
    ></div>

    <!-- Modal Content -->
    <div class="bg-white rounded-[2.5rem] w-full max-w-lg shadow-2xl relative z-10 overflow-hidden animate-in fade-in zoom-in duration-300 max-h-[90vh] flex flex-col">
      <div class="p-8 md:p-12 flex flex-col h-full overflow-hidden pb-4">
        <div class="flex justify-between items-start mb-8 shrink-0">
          <div class="flex items-center gap-4">
            <div class="w-16 h-16 rounded-3xl flex items-center justify-center shadow-lg
              {activeModal.type === 'award' ? 'bg-hero text-white shadow-hero/20' : 
               activeModal.type === 'penalty' ? 'bg-penalty text-white shadow-penalty/20' :
               activeModal.type === 'bank' ? 'bg-savings text-white shadow-savings/20' :
               activeModal.type === 'presets' ? 'bg-slate-900 text-white shadow-slate-200' :
               activeModal.type === 'picker' ? 'bg-slate-900 text-white shadow-slate-200' :
               activeModal.type === 'family' ? 'bg-hero text-white shadow-hero/20' :
               activeModal.type === 'child-link' ? 'bg-slate-900 text-white shadow-slate-200' :
               'bg-reward text-white shadow-reward/20'}">
              {#if activeModal.type === 'award'}<Award size={32} />
              {:else if activeModal.type === 'penalty'}<Ban size={32} />
              {:else if activeModal.type === 'bank'}<PiggyBank size={32} />
              {:else if activeModal.type === 'presets'}<Settings size={32} />
              {:else if activeModal.type === 'picker'}<Star size={32} class="text-hero" />
              {:else if activeModal.type === 'family'}<Users size={32} />
              {:else if activeModal.type === 'child-link'}<QrCode size={32} />
              {:else}<Trophy size={32} />{/if}
            </div>
            <div>
              <h3 class="text-2xl font-black text-slate-900 uppercase tracking-tight">
                {activeModal.type === 'award' ? 'Award Points' : 
                 activeModal.type === 'penalty' ? 'Apply Penalty' :
                 activeModal.type === 'bank' ? 'Bank to Savings' :
                 activeModal.type === 'presets' ? (editingPresetId ? 'Edit Behaviour' : 'Manage Behaviours') :
                 activeModal.type === 'picker' ? 'Quick Action' :
                 activeModal.type === 'family' ? 'Family Settings' :
                 activeModal.type === 'child-link' ? 'Link Child Device' :
                 'Redeem Points'}
              </h3>
              <p class="text-slate-400 font-black text-xs uppercase tracking-[0.2em]">
                {activeModal.type === 'presets' ? (editingPresetId ? 'Update this action' : 'Configure reusable actions') : 
                 activeModal.type === 'family' ? 'Manage members & co-parents' :
                 activeModal.type === 'child-link' ? 'Create a QR code for one specific child' :
                 `For ${activeModal.child?.child?.display_name}`}
              </p>
            </div>
          </div>
          <button onclick={closeModal} class="w-10 h-10 rounded-xl bg-slate-50 text-slate-300 flex items-center justify-center hover:bg-slate-100 hover:text-slate-500 transition-all">
            <X size={20} />
          </button>
        </div>

        {#if modalError}
          <div class="p-4 bg-red-50 text-red-600 rounded-2xl font-bold text-sm mb-6 border border-red-100 flex items-center gap-2 shrink-0">
            <Ban size={16} /> {modalError}
          </div>
        {/if}

        <div id="modal-scroll-area" class="flex-1 overflow-y-auto pr-2 -mr-2 custom-scrollbar space-y-6 pb-4">
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

          {#if activeModal.type === 'family'}
            <!-- Members List -->
            <div class="space-y-3">
              <label class="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-2">Family Members</label>
              <div class="grid gap-2">
                {#each familyMembers as member}
                  <div class="flex items-center justify-between p-4 bg-slate-50 rounded-2xl">
                    <div class="flex items-center gap-3">
                      <div class="w-10 h-10 bg-white rounded-xl flex items-center justify-center text-hero font-black shadow-sm">
                        {member.name ? member.name[0].toUpperCase() : member.email[0].toUpperCase()}
                      </div>
                      <div>
                        <p class="font-bold text-slate-900 text-sm">{member.name || 'Parent'}</p>
                        <p class="text-[10px] text-slate-400 font-medium uppercase tracking-wider">{member.email}</p>
                      </div>
                    </div>
                    {#if member.id === parent?.id}
                      <span class="px-3 py-1 bg-hero/10 text-hero rounded-lg text-[10px] font-black uppercase tracking-widest">You</span>
                    {/if}
                  </div>
                {/each}
              </div>
            </div>

            <!-- Invites List -->
            {#if familyInvites.filter(i => i.status === 'pending').length > 0}
              <div class="space-y-3 pt-4 border-t border-slate-100">
                <label class="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-2">Pending Invites</label>
                <div class="grid gap-2">
                  {#each familyInvites.filter(i => i.status === 'pending') as invite}
                    <div class="flex items-center justify-between p-4 bg-slate-50 rounded-2xl border-2 border-dashed border-slate-200">
                      <div>
                        <p class="font-bold text-slate-900 text-sm">{invite.email}</p>
                        <p class="text-[10px] text-slate-400 font-medium uppercase tracking-wider">Waiting for login</p>
                      </div>
                      <button onclick={() => revokeInvite(invite.id)} class="text-slate-300 hover:text-red-500 transition-colors">
                        <X size={16} />
                      </button>
                    </div>
                  {/each}
                </div>
              </div>
            {/if}

            <!-- Invite Form -->
            <div class="space-y-3 pt-4 border-t border-slate-100">
              <label class="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-2">Invite Co-Parent</label>
              <div class="space-y-2">
                <input 
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
            <!-- ClassDojo Style Picker -->
            <div class="flex gap-2 p-1 bg-slate-100 rounded-2xl sticky top-0 z-20">
              <button 
                onclick={() => activeTab = 'positive'}
                class="flex-1 py-3 rounded-xl font-black uppercase tracking-widest text-[10px] transition-all
                  {activeTab === 'positive' ? 'bg-white text-hero shadow-sm' : 'text-slate-500 hover:text-slate-700'}"
              >
                Positive
              </button>
              <button 
                onclick={() => activeTab = 'needs-work'}
                class="flex-1 py-3 rounded-xl font-black uppercase tracking-widest text-[10px] transition-all
                  {activeTab === 'needs-work' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'}"
              >
                Needs Work
              </button>
            </div>

            <div class="grid grid-cols-2 md:grid-cols-3 gap-4 pb-4">
              {#each presets.filter(p => p.is_active && (activeTab === 'positive' ? p.points > 0 : p.points < 0)) as p}
                <button 
                  onclick={() => applyPreset(activeModal.child, p)}
                  title={p.title}
                  class="group p-4 rounded-3xl border-2 transition-all text-center flex flex-col items-center gap-2 h-44
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
                    Add Some Now
                  </button>
                </div>
              {/each}
            </div>
          {/if}

          {#if activeModal.type === 'redeem' || activeModal.type === 'presets'}
            <div class="space-y-2">
              <label class="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-2">
                {activeModal.type === 'presets' ? 'Preset Title' : 'Reward Name'}
              </label>
              <div class="flex gap-3">
                {#if activeModal.type === 'presets'}
                  <div class="w-16 h-16 bg-slate-50 border-2 border-slate-100 rounded-2xl flex items-center justify-center text-2xl shadow-inner shrink-0">
                    {modalForm.icon || '✨'}
                  </div>
                {/if}
                <input 
                  type="text" 
                  bind:value={modalForm.title}
                  placeholder={activeModal.type === 'presets' ? "e.g., Brushed Teeth" : "e.g., 30 mins Screen Time"}
                  class="flex-1 bg-slate-50 border-2 border-slate-100 rounded-2xl px-6 py-4 font-bold text-slate-900 focus:outline-none focus:border-reward/30 transition-all"
                />
              </div>
            </div>

            {#if activeModal.type === 'presets'}
              <div class="space-y-2">
                <label class="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-2">Select Visual (Optional)</label>
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

          {#if activeModal.type !== 'picker' && activeModal.type !== 'family'}
            <div class="grid grid-cols-2 gap-6">
              <div class="space-y-2">
                <label class="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-2">Points Amount</label>
                <div class="relative">
                  <input 
                    type="number" 
                    bind:value={modalForm.points}
                    class="w-full bg-slate-50 border-2 border-slate-100 rounded-2xl px-6 py-4 font-black text-slate-900 focus:outline-none focus:border-hero/30 transition-all text-2xl"
                  />
                  <span class="absolute right-6 top-1/2 -translate-y-1/2 font-black text-slate-300 text-sm">HP</span>
                </div>
                {#if activeModal.type === 'presets'}
                  <p class="text-[10px] text-slate-400 ml-2">Use negative for penalties</p>
                {/if}
              </div>

              {#if activeModal.type === 'award' || activeModal.type === 'penalty'}
                <div class="space-y-2">
                  <label class="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-2">Target Jar</label>
                  <select 
                    bind:value={modalForm.jar}
                    class="w-full bg-slate-50 border-2 border-slate-100 rounded-2xl px-6 py-4 font-bold text-slate-900 focus:outline-none focus:border-hero/30 transition-all appearance-none cursor-pointer"
                  >
                    <option value="spending">Spending Jar</option>
                    <option value="savings">Savings Jar</option>
                  </select>
                </div>
              {/if}
            </div>
          {/if}

          {#if activeModal.type !== 'presets' && activeModal.type !== 'picker' && activeModal.type !== 'family'}
            <div class="space-y-2">
              <label class="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-2">Description / Reason</label>
              <textarea 
                bind:value={modalForm.description}
                placeholder="What happened? (optional)"
                rows="3"
                class="w-full bg-slate-50 border-2 border-slate-100 rounded-2xl px-6 py-4 font-medium text-slate-900 focus:outline-none focus:border-hero/30 transition-all resize-none"
              ></textarea>
            </div>
          {/if}

          {#if activeModal.type === 'presets'}
            <div class="space-y-2">
              <label class="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-2">Internal Notes</label>
              <textarea 
                bind:value={modalForm.description}
                placeholder="Brief description of when to use this (optional)"
                rows="2"
                class="w-full bg-slate-50 border-2 border-slate-100 rounded-2xl px-6 py-4 font-medium text-slate-900 focus:outline-none focus:border-hero/30 transition-all resize-none"
              ></textarea>
            </div>

            {#if presets.length > 0}
              <div class="space-y-3 pt-4 border-t border-slate-100">
                <label class="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-2">Existing Presets</label>
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

          {#if activeModal.type !== 'picker' && activeModal.type !== 'child-link'}
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
