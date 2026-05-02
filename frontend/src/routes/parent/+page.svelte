<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import { 
    UserPlus, Award, Ban, PiggyBank, ArrowRight, Star, Bell, 
    LayoutDashboard, Settings, LogIn, Trophy, Clock, Check, X, 
    History, TrendingUp, ChevronRight
  } from 'lucide-svelte';

  let parent = $state(null);
  let children = $state([]);
  let redemptions = $state([]);
  let loading = $state(true);
  let loadingChildren = $state(false);
  let error = $state(null);
  let needsLogin = $state(false);

  // Modal State
  let activeModal = $state(null); // { type: 'award' | 'penalty' | 'bank' | 'redeem', child: any }
  let modalForm = $state({
    points: 1,
    description: '',
    title: '',
    jar: 'spending'
  });
  let modalLoading = $state(false);
  let modalError = $state(null);

  const isAuthError = (message: string) =>
    message.toLowerCase().includes('not authenticated') ||
    message.toLowerCase().includes('invalid token') ||
    message.toLowerCase().includes('parent not found');

  async function loadDashboard() {
    try {
      loading = true;
      error = null;
      needsLogin = false;
      const [p, c, r] = await Promise.all([
        api.get('/me'),
        api.get('/children/'),
        api.get('/redemptions')
      ]);
      parent = p;
      children = c;
      redemptions = r;
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

  function openModal(type, child) {
    activeModal = { type, child };
    modalForm = {
      points: 1,
      description: '',
      title: '',
      jar: 'spending'
    };
    modalError = null;
  }

  function closeModal() {
    activeModal = null;
  }

  async function handleModalSubmit() {
    if (!activeModal) return;
    
    try {
      modalLoading = true;
      modalError = null;
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

  async function processRedemption(id, action) {
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

  const getPetEmoji = (stage) => {
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
        
        <button onclick={addChild} disabled={loadingChildren} class="btn-hero flex items-center gap-2 px-6 py-4 rounded-2xl shadow-xl shadow-hero/20 disabled:opacity-60 disabled:cursor-not-allowed">
          <UserPlus size={20} /> {loadingChildren ? 'Adding...' : 'Add Child'}
        </button>
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

              <!-- Quick Actions -->
              <div class="px-8 pb-8 pt-2 flex flex-wrap gap-3 mt-auto relative z-10">
                <button 
                  onclick={() => openModal('award', c)}
                  class="flex-1 min-w-[120px] btn-hero py-4 rounded-xl text-xs font-black uppercase tracking-widest flex items-center justify-center gap-2 shadow-lg shadow-hero/20 hover:scale-[1.02] transition-all"
                >
                  <Award size={18} /> Award
                </button>
                <button 
                  onclick={() => openModal('penalty', c)}
                  class="flex-1 min-w-[120px] btn-secondary py-4 rounded-xl text-xs font-black uppercase tracking-widest flex items-center justify-center gap-2 hover:border-penalty hover:text-penalty hover:bg-penalty/5 transition-all"
                >
                  <Ban size={18} /> Penalty
                </button>
                <button 
                  onclick={() => openModal('bank', c)}
                  class="w-full btn-secondary py-4 rounded-xl text-xs font-black uppercase tracking-widest flex items-center justify-center gap-2 hover:border-savings hover:text-savings hover:bg-savings/5 transition-all"
                >
                  <PiggyBank size={18} /> Bank to Savings
                </button>
                <button 
                  onclick={() => openModal('redeem', c)}
                  class="w-full btn-secondary py-4 rounded-xl text-xs font-black uppercase tracking-widest flex items-center justify-center gap-2 hover:border-reward hover:text-reward hover:bg-reward/5 transition-all"
                >
                  <Trophy size={18} /> Redeem Reward
                </button>
              </div>
            </div>
          {/each}
        </div>
      {/if}

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
    <div class="bg-white rounded-[2.5rem] w-full max-w-lg shadow-2xl relative z-10 overflow-hidden animate-in fade-in zoom-in duration-300">
      <div class="p-8 md:p-12">
        <div class="flex justify-between items-start mb-8">
          <div class="flex items-center gap-4">
            <div class="w-16 h-16 rounded-3xl flex items-center justify-center shadow-lg
              {activeModal.type === 'award' ? 'bg-hero text-white shadow-hero/20' : 
               activeModal.type === 'penalty' ? 'bg-penalty text-white shadow-penalty/20' :
               activeModal.type === 'bank' ? 'bg-savings text-white shadow-savings/20' :
               'bg-reward text-white shadow-reward/20'}">
              {#if activeModal.type === 'award'}<Award size={32} />
              {:else if activeModal.type === 'penalty'}<Ban size={32} />
              {:else if activeModal.type === 'bank'}<PiggyBank size={32} />
              {:else}<Trophy size={32} />{/if}
            </div>
            <div>
              <h3 class="text-2xl font-black text-slate-900 uppercase tracking-tight">
                {activeModal.type === 'award' ? 'Award Points' : 
                 activeModal.type === 'penalty' ? 'Apply Penalty' :
                 activeModal.type === 'bank' ? 'Bank to Savings' :
                 'Redeem Points'}
              </h3>
              <p class="text-slate-400 font-black text-xs uppercase tracking-[0.2em]">
                For {activeModal.child.child.display_name}
              </p>
            </div>
          </div>
          <button onclick={closeModal} class="w-10 h-10 rounded-xl bg-slate-50 text-slate-300 flex items-center justify-center hover:bg-slate-100 hover:text-slate-500 transition-all">
            <X size={20} />
          </button>
        </div>

        {#if modalError}
          <div class="p-4 bg-red-50 text-red-600 rounded-2xl font-bold text-sm mb-6 border border-red-100 flex items-center gap-2">
            <Ban size={16} /> {modalError}
          </div>
        {/if}

        <div class="space-y-6">
          {#if activeModal.type === 'redeem'}
            <div class="space-y-2">
              <label class="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-2">Reward Name</label>
              <input 
                type="text" 
                bind:value={modalForm.title}
                placeholder="e.g., 30 mins Screen Time"
                class="w-full bg-slate-50 border-2 border-slate-100 rounded-2xl px-6 py-4 font-bold text-slate-900 focus:outline-none focus:border-reward/30 transition-all"
              />
            </div>
          {/if}

          <div class="grid grid-cols-2 gap-6">
            <div class="space-y-2">
              <label class="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-2">Points Amount</label>
              <div class="relative">
                <input 
                  type="number" 
                  bind:value={modalForm.points}
                  min="1"
                  class="w-full bg-slate-50 border-2 border-slate-100 rounded-2xl px-6 py-4 font-black text-slate-900 focus:outline-none focus:border-hero/30 transition-all text-2xl"
                />
                <span class="absolute right-6 top-1/2 -translate-y-1/2 font-black text-slate-300 text-sm">HP</span>
              </div>
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

          <div class="space-y-2">
            <label class="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-2">Description / Reason</label>
            <textarea 
              bind:value={modalForm.description}
              placeholder="What happened? (optional)"
              rows="3"
              class="w-full bg-slate-50 border-2 border-slate-100 rounded-2xl px-6 py-4 font-medium text-slate-900 focus:outline-none focus:border-hero/30 transition-all resize-none"
            ></textarea>
          </div>

          {#if activeModal.type === 'bank'}
            <div class="p-4 bg-savings/5 rounded-2xl border border-savings/10 flex items-start gap-3">
              <Clock size={16} class="text-savings mt-0.5" />
              <p class="text-[10px] font-bold text-savings-dark leading-relaxed uppercase tracking-widest">
                Banked points are locked for 30 days and cannot be spent or withdrawn until unlocked.
              </p>
            </div>
          {/if}

          <button 
            onclick={handleModalSubmit}
            disabled={modalLoading}
            class="w-full py-5 rounded-[1.5rem] font-black uppercase tracking-[0.2em] text-sm shadow-xl transition-all active:scale-[0.98] disabled:opacity-50
              {activeModal.type === 'award' ? 'bg-hero text-white shadow-hero/30 hover:bg-hero-dark' : 
               activeModal.type === 'penalty' ? 'bg-penalty text-white shadow-penalty/30 hover:bg-penalty-dark' :
               activeModal.type === 'bank' ? 'bg-savings text-white shadow-savings/30 hover:bg-savings-dark' :
               'bg-reward text-white shadow-reward/30 hover:bg-reward-dark'}"
          >
            {modalLoading ? 'Processing...' : 'Confirm Action'}
          </button>
        </div>
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
  .shadow-hero\/30 { box-shadow: 0 10px 25px -5px rgba(255, 90, 95, 0.3); }
  
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
