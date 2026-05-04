<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import { ShieldCheck, Coins, PiggyBank, Trophy, Sparkles, ArrowRight, Star, Lock, Heart } from 'lucide-svelte';

  let authenticated = $state(false);
  let sessionLoaded = $state(false);

  onMount(async () => {
    try {
      await api.get('/me');
      authenticated = true;
    } catch {
      authenticated = false;
    } finally {
      sessionLoaded = true;
    }
  });

  let primaryCtaHref = $derived(sessionLoaded && authenticated ? '/parent' : '/login');
  let primaryCtaLabel = $derived(sessionLoaded && authenticated ? 'Go to Dashboard' : 'Start Your Journey');
</script>

<div class="relative overflow-hidden bg-hero-pattern">
  <!-- Hero Section -->
  <section class="py-20 lg:py-32 px-4 relative">
    <div class="max-w-7xl mx-auto grid lg:grid-cols-2 gap-12 items-center">
      <div class="text-left relative z-10">
        <div class="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-hero/10 text-hero text-sm font-black mb-8 animate-pulse border border-hero/20">
          <Sparkles size={16} />
          <span class="uppercase tracking-widest">Family goals made simple</span>
        </div>
        <h1 class="text-4xl sm:text-5xl md:text-7xl lg:text-8xl font-black text-slate-900 mb-8 leading-[0.92] tracking-tighter break-words">
          Turn Responsibility into <span class="text-hero text-transparent bg-clip-text bg-gradient-to-r from-hero to-hero-light">Superpowers.</span>
        </h1>
        <p class="text-lg sm:text-xl md:text-2xl text-slate-600 mb-12 max-w-xl leading-relaxed">
          A fun family app where kids earn <span class="font-bold text-slate-800 underline decoration-hero/30">Hero Points</span>, build better habits, save toward goals, and request real rewards — all with parent approval.
        </p>
        
        <div class="flex flex-col sm:flex-row gap-4">
          <a href={primaryCtaHref} class="btn-hero px-8 sm:px-10 py-4 sm:py-5 text-lg sm:text-xl flex items-center justify-center gap-3 rounded-2xl">
            {primaryCtaLabel} <ArrowRight size={24} />
          </a>
          <a href="#features" class="btn-secondary px-8 sm:px-10 py-4 sm:py-5 text-lg sm:text-xl rounded-2xl flex items-center justify-center">
            See How it Works
          </a>
        </div>
      </div>

      <!-- Sample Hero Card -->
      <div class="relative hidden lg:block">
        <div class="absolute -top-20 -left-20 w-64 h-64 bg-hero/10 rounded-full blur-3xl"></div>
        <div class="absolute -bottom-20 -right-20 w-64 h-64 bg-savings/10 rounded-full blur-3xl"></div>
        
        <div class="card p-8 rotate-2 hover:rotate-0 transition-transform duration-500 relative z-10 border-2 border-white shadow-2xl">
          <div class="flex items-center gap-4 mb-8">
            <div class="w-20 h-20 bg-hero/10 rounded-3xl flex items-center justify-center overflow-hidden">
              <img src="/pets/dragon-1/young-dragon.png" alt="Young Dragon" class="w-16 h-16 object-contain" />
            </div>
            <div>
              <h3 class="text-2xl font-black text-slate-900">Hero Alex</h3>
              <span class="px-3 py-1 bg-hero text-white text-xs font-black uppercase rounded-full tracking-widest">Young Dragon</span>
            </div>
          </div>
          
          <div class="grid grid-cols-2 gap-4 mb-8">
            <div class="bg-slate-50 rounded-2xl p-6 border border-slate-100">
              <div class="flex items-center gap-2 mb-2">
                <Star size={18} class="text-reward fill-reward" />
                <span class="text-xs font-black text-slate-400 uppercase tracking-widest">Spending</span>
              </div>
              <p class="text-3xl font-black text-slate-900">125 <span class="text-sm">HP</span></p>
            </div>
            <div class="bg-slate-50 rounded-2xl p-6 border border-slate-100">
              <div class="flex items-center gap-2 mb-2">
                <PiggyBank size={18} class="text-savings" />
                <span class="text-xs font-black text-slate-400 uppercase tracking-widest">Savings</span>
              </div>
              <p class="text-3xl font-black text-slate-900">450 <span class="text-sm">HP</span></p>
            </div>
          </div>

          <div class="space-y-3">
            <div class="flex justify-between text-xs font-black uppercase text-slate-400 tracking-widest">
              <span>Next Evolution</span>
              <span>125 / 150 HP</span>
            </div>
            <div class="h-4 bg-slate-100 rounded-full overflow-hidden">
              <div class="h-full bg-hero w-[83%] rounded-full shadow-lg shadow-hero/20"></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- Feature Cards -->
  <section id="features" class="py-24 bg-white relative">
    <div class="max-w-7xl mx-auto px-4">
      <div class="text-center mb-20">
        <h2 class="text-4xl md:text-5xl font-black text-slate-900 mb-4">Built for <span class="text-hero underline decoration-hero/20">busy families</span></h2>
        <p class="text-xl text-slate-600 max-w-2xl mx-auto">A simple system for parents. A fun progress dashboard for kids.</p>
      </div>

      <div class="grid md:grid-cols-4 gap-8">
        <div class="card p-8 group hover:-translate-y-2 transition-all duration-300 border-b-8 border-hero">
          <div class="w-16 h-16 bg-hero/10 text-hero rounded-3xl flex items-center justify-center mb-8 group-hover:scale-110 transition-transform">
            <Trophy size={32} />
          </div>
          <h3 class="text-2xl font-black mb-4">Earn Hero Points</h3>
          <p class="text-slate-600 leading-relaxed">Reward chores, good behaviour, routines, and milestones with instant points.</p>
        </div>

        <div class="card p-8 group hover:-translate-y-2 transition-all duration-300 border-b-8 border-hero-dark">
          <div class="w-16 h-16 bg-hero-dark/10 text-hero-dark rounded-3xl flex items-center justify-center mb-8 group-hover:scale-110 transition-transform">
            <Star size={32} />
          </div>
          <h3 class="text-2xl font-black mb-4">Better Habits</h3>
          <p class="text-slate-600 leading-relaxed">Use quick actions and rewards to make daily routines easier to follow.</p>
        </div>

        <div class="card p-8 group hover:-translate-y-2 transition-all duration-300 border-b-8 border-savings">
          <div class="w-16 h-16 bg-savings/10 text-savings rounded-3xl flex items-center justify-center mb-8 group-hover:scale-110 transition-transform">
            <PiggyBank size={32} />
          </div>
          <h3 class="text-2xl font-black mb-4">Save Toward Goals</h3>
          <p class="text-slate-600 leading-relaxed">Help kids learn patience by setting points aside in a savings jar.</p>
        </div>

        <div class="card p-8 group hover:-translate-y-2 transition-all duration-300 border-b-8 border-reward">
          <div class="w-16 h-16 bg-reward/10 text-reward rounded-3xl flex items-center justify-center mb-8 group-hover:scale-110 transition-transform">
            <Coins size={32} />
          </div>
          <h3 class="text-2xl font-black mb-4">Request Rewards</h3>
          <p class="text-slate-600 leading-relaxed">Kids choose rewards they can afford. Parents approve or reject requests.</p>
        </div>
      </div>
    </div>
  </section>

  <!-- Pet Evolution Visual -->
  <section class="py-24 bg-slate-50 border-y border-slate-200 overflow-hidden">
    <div class="max-w-7xl mx-auto px-4">
      <div class="text-center mb-16">
        <h2 class="text-4xl font-black text-slate-900 mb-4 uppercase tracking-tighter">The Path of a Hero</h2>
        <p class="text-slate-600 font-bold uppercase tracking-widest text-sm">Watch their pet grow and evolve as they earn points</p>
      </div>

      <div class="relative">
        <!-- Connecting Line -->
        <div class="absolute top-1/2 left-0 w-full h-1 bg-slate-200 -translate-y-1/2 hidden md:block"></div>
        
        <div class="grid md:grid-cols-5 gap-8 relative z-10">
          <div class="text-center">
            <div class="w-24 h-24 bg-white rounded-full border-4 border-slate-200 flex items-center justify-center p-4 mx-auto mb-4 relative shadow-xl">
              <img src="/pets/dragon-1/egg.png" alt="Egg" class="w-full h-full object-contain" />
              <div class="absolute -bottom-2 -right-2 bg-slate-700 text-white text-[10px] font-black px-2 py-0.5 rounded-full uppercase z-10 border-2 border-white shadow-sm">0 HP</div>
            </div>
            <p class="font-black text-slate-900 uppercase tracking-widest text-xs">Egg</p>
          </div>
          <div class="text-center">
            <div class="w-24 h-24 bg-white rounded-full border-4 border-hero/30 flex items-center justify-center p-4 mx-auto mb-4 relative shadow-xl shadow-hero/10">
              <img src="/pets/dragon-1/hatchling.png" alt="Hatchling" class="w-full h-full object-contain" />
              <div class="absolute -bottom-2 -right-2 bg-hero text-white text-[10px] font-black px-2 py-0.5 rounded-full uppercase z-10 border-2 border-white shadow-sm">50 HP</div>
            </div>
            <p class="font-black text-hero uppercase tracking-widest text-xs">Hatchling</p>
          </div>
          <div class="text-center">
            <div class="w-24 h-24 bg-white rounded-full border-4 border-slate-200 flex items-center justify-center p-4 mx-auto mb-4 relative shadow-xl">
              <img src="/pets/dragon-1/young-dragon.png" alt="Young Dragon" class="w-full h-full object-contain" />
              <div class="absolute -bottom-2 -right-2 bg-slate-700 text-white text-[10px] font-black px-2 py-0.5 rounded-full uppercase z-10 border-2 border-white shadow-sm">150 HP</div>
            </div>
            <p class="font-black text-slate-900 uppercase tracking-widest text-xs">Young Dragon</p>
          </div>
          <div class="text-center">
            <div class="w-24 h-24 bg-white rounded-full border-4 border-slate-200 flex items-center justify-center p-4 mx-auto mb-4 relative shadow-xl">
              <img src="/pets/dragon-1/hero-dragon.png" alt="Hero Dragon" class="w-full h-full object-contain" />
              <div class="absolute -bottom-2 -right-2 bg-slate-700 text-white text-[100px] font-black px-2 py-0.5 rounded-full uppercase z-10 border-2 border-white shadow-sm" style="font-size: 10px;">300 HP</div>
            </div>
            <p class="font-black text-slate-900 uppercase tracking-widest text-xs">Hero Dragon</p>
          </div>
          <div class="text-center">
            <div class="w-24 h-24 bg-white rounded-full border-4 border-slate-200 flex items-center justify-center p-4 mx-auto mb-4 relative shadow-xl">
              <img src="/pets/dragon-1/legendary-dragon.png" alt="Legendary Dragon" class="w-full h-full object-contain" />
              <div class="absolute -bottom-2 -right-2 bg-slate-700 text-white text-[100px] font-black px-2 py-0.5 rounded-full uppercase z-10 border-2 border-white shadow-sm" style="font-size: 10px;">600 HP</div>
            </div>
            <p class="font-black text-slate-900 uppercase tracking-widest text-xs">Legendary Dragon</p>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- Parent Trust Section -->
  <section class="py-24 px-4">
    <div class="max-w-5xl mx-auto card p-12 md:p-20 !bg-slate-900 text-white relative overflow-hidden">
      <div class="absolute top-0 right-0 w-96 h-96 bg-hero/10 rounded-full blur-[120px]"></div>
      <div class="relative z-10 text-center">
        <h2 class="text-4xl md:text-5xl font-black mb-4 leading-tight">Everything you need for a <span class="text-hero">happier household</span></h2>
        <p class="text-slate-400 font-bold uppercase tracking-widest text-sm mb-12">Helping families build better habits, one small win at a time.</p>
        
        <div class="bg-white/5 border border-white/10 p-8 rounded-3xl mb-16 text-left max-w-3xl mx-auto">
          <p class="text-slate-300 leading-relaxed">
            Family Hero Hub is a family rewards and responsibility app for parents and children. 
            Parents create child profiles, children earn points for positive actions, and rewards can be requested and approved. 
            Login is handled securely through <strong>Google OAuth</strong>. We never ask for or store your Google password.
          </p>
        </div>

        <div class="grid md:grid-cols-3 gap-12 text-left mb-16">
          <div class="flex gap-4">
            <div class="text-hero shrink-0"><Lock size={24} /></div>
            <div>
              <h4 class="font-bold text-lg mb-2">Secure Login</h4>
              <p class="text-slate-300 text-sm font-medium">Quick and safe access for parents via Google OAuth.</p>
            </div>
          </div>
          <div class="flex gap-4">
            <div class="text-hero shrink-0"><Heart size={24} /></div>
            <div>
              <h4 class="font-bold text-lg mb-2">Full Control</h4>
              <p class="text-slate-300 text-sm font-medium">You decide how many points to award and which rewards to approve.</p>
            </div>
          </div>
          <div class="flex gap-4">
            <div class="text-hero shrink-0"><ShieldCheck size={24} /></div>
            <div>
              <h4 class="font-bold text-lg mb-2">Clear History</h4>
              <p class="text-slate-300 text-sm font-medium">A transparent log of every point earned, saved, or requested.</p>
            </div>
          </div>
        </div>
        <a href={primaryCtaHref} class="btn-hero inline-flex items-center gap-2 px-12 py-5 text-xl">
          {primaryCtaLabel} <ArrowRight size={24} />
        </a>
      </div>
    </div>
  </section>
</div>
