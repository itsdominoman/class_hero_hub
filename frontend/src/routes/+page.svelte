<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import {
    ArrowRight,
    CalendarDays,
    Lock,
    PiggyBank,
    Sparkles,
    Star,
    ShieldCheck,
    Trophy,
    Users
  } from 'lucide-svelte';

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

  let primaryCtaHref = $derived(sessionLoaded && authenticated ? '/parent' : '/request-access');
  let primaryCtaLabel = $derived(sessionLoaded && authenticated ? 'Go to dashboard' : 'Request access');

  const featureCards = [
    {
      icon: Trophy,
      title: 'Points',
      text: 'Reward effort, responsibility, routines, and everyday wins.'
    },
    {
      icon: Star,
      title: 'Rewards',
      text: 'Create parent-approved rewards children can work toward.'
    },
    {
      icon: PiggyBank,
      title: 'Savings',
      text: 'Let children set points aside and see when saved points unlock with a bonus.'
    },
    {
      icon: CalendarDays,
      title: 'School Bag',
      text: 'Help children see what they need today and what to pack for tomorrow.'
    },
    {
      icon: CalendarDays,
      title: 'Calendar',
      text: 'Keep tasks, reminders, and family routines visible.'
    },
    {
      icon: Sparkles,
      title: 'Child Dashboard',
      text: 'Give children a simple place to see progress without giving them parent access.'
    },
    {
      icon: Users,
      title: 'Parents & Caregivers',
      text: 'Invite trusted grownups and remove access when needed.'
    },
    {
      icon: Lock,
      title: 'Linked Devices',
      text: 'Connect child dashboards to devices and unlink them from parent settings.'
    }
  ];

  const steps = [
    {
      title: 'Add your children',
      text: 'Create child profiles, choose avatars, and set up your family space.'
    },
    {
      title: 'Use points for everyday progress',
      text: 'Award points for routines, helpful choices, school prep, effort, kindness, or custom reasons.'
    },
    {
      title: "Let children see what's next",
      text: 'Children can view their own dashboard with points, rewards, tasks, School Bag, calendar items, and savings progress.'
    },
    {
      title: 'Approve rewards together',
      text: 'Children can request rewards. Parents approve or reject them, so expectations stay clear.'
    },
    {
      title: 'Grow into savings and allowance',
      text: 'When ready, add saved points, bonus unlocks, and optional allowance values without turning the app into a bank.'
    }
  ];

  const faqs = [
    {
      question: 'Is Family Hero Hub a banking app?',
      answer: 'No. Family Hero Hub can show optional allowance values beside points, but it does not hold or transfer money.'
    },
    {
      question: 'Can children approve their own rewards?',
      answer: 'No. Children can request rewards, but parents approve or reject them.'
    },
    {
      question: 'Can I invite another parent or caregiver?',
      answer: 'Yes. Parents & Caregivers lets families invite trusted grownups and remove access when needed.'
    },
    {
      question: 'Can my child use their own device?',
      answer: 'Yes. Parents can link a child dashboard to a device and unlink it later if needed.'
    },
    {
      question: 'Can children message each other?',
      answer: 'No. Family Hero Hub does not include child-to-child messaging.'
    }
  ];
</script>

<svelte:head>
  <title>Family Hero Hub | Parent-led family rewards and routines</title>
  <meta
    name="description"
    content="A private family hub for points, rewards, routines, and responsibility."
  />
</svelte:head>

<div class="relative max-w-full overflow-hidden bg-hero-pattern">
  <section class="px-3 sm:px-4 py-14 sm:py-18 lg:py-24">
    <div class="max-w-7xl mx-auto grid gap-10 lg:grid-cols-[1.08fr_0.92fr] lg:items-center">
      <div class="relative z-10 text-left">
        <div class="inline-flex max-w-full items-center gap-2 rounded-full border border-hero/20 bg-hero/10 px-4 py-2 text-sm font-black text-hero mb-6">
          <Sparkles size={16} />
          <span class="uppercase tracking-[0.12em] sm:tracking-[0.2em]">Parent-led family hub</span>
        </div>
        <h1 class="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-black text-slate-900 leading-[0.96] tracking-tighter max-w-2xl">
          Less nagging. Clearer routines. More everyday wins.
        </h1>
        <p class="mt-6 max-w-2xl text-lg sm:text-xl md:text-2xl leading-relaxed text-slate-600">
          Family Hero Hub helps parents guide daily responsibilities with points, rewards, school bag prep, calendar tasks, and child-friendly dashboards - all in a private, parent-led family space.
        </p>

        <div class="mt-8 flex flex-col sm:flex-row gap-4">
          <a href={primaryCtaHref} class="btn-hero inline-flex items-center justify-center gap-3 rounded-2xl px-6 py-4 text-base sm:text-lg">
            {primaryCtaLabel}
            <ArrowRight size={20} />
          </a>
          <a href="#how-it-works" class="btn-secondary inline-flex items-center justify-center rounded-2xl px-6 py-4 text-base sm:text-lg">
            See how it works
          </a>
        </div>

        <p class="mt-5 max-w-2xl text-sm sm:text-base font-semibold text-slate-500 leading-relaxed">
          Parent-led rewards | Child-friendly dashboards | Private family space
        </p>
      </div>

      <div class="relative">
        <div class="absolute -top-16 -left-10 h-56 w-56 rounded-full bg-hero/10 blur-3xl"></div>
        <div class="absolute -bottom-16 -right-10 h-56 w-56 rounded-full bg-savings/10 blur-3xl"></div>
        <div class="card relative z-10 overflow-hidden border border-white/80 bg-white/95 p-5 sm:p-6 lg:p-8 shadow-2xl">
          <div class="grid gap-4 sm:grid-cols-2">
            <div class="rounded-3xl border border-slate-100 bg-slate-50 p-5">
              <p class="text-xs font-black uppercase tracking-[0.18em] text-slate-400">Parent view</p>
              <p class="mt-3 text-xl font-black text-slate-900">Set the rules, keep the rhythm.</p>
              <p class="mt-2 text-sm leading-relaxed text-slate-600">Parents manage children, points, rewards, caregivers, and linked devices.</p>
            </div>
            <div class="rounded-3xl border border-slate-100 bg-hero/5 p-5">
              <p class="text-xs font-black uppercase tracking-[0.18em] text-hero">Child view</p>
              <p class="mt-3 text-xl font-black text-slate-900">Simple, clear, and age-friendly.</p>
              <p class="mt-2 text-sm leading-relaxed text-slate-600">Children see their own dashboard without parent/admin access.</p>
            </div>
          </div>

          <div class="mt-4 rounded-3xl bg-slate-900 p-5 sm:p-6 text-white">
            <div class="flex items-center gap-2 text-sm font-black uppercase tracking-[0.18em] text-hero">
              <ShieldCheck size={16} />
              <span>Private by design</span>
            </div>
            <p class="mt-3 text-lg font-semibold leading-relaxed text-slate-200">
              No public child profiles. No social feed. No child-to-child messaging. Parents stay in control.
            </p>
          </div>

          <div class="mt-4 grid gap-3 sm:grid-cols-3">
            <div class="rounded-2xl border border-slate-100 bg-white p-4">
              <p class="text-xs font-black uppercase tracking-[0.16em] text-slate-400">Rewards</p>
              <p class="mt-2 text-sm font-semibold text-slate-700">Parent approved</p>
            </div>
            <div class="rounded-2xl border border-slate-100 bg-white p-4">
              <p class="text-xs font-black uppercase tracking-[0.16em] text-slate-400">Access</p>
              <p class="mt-2 text-sm font-semibold text-slate-700">Family controlled</p>
            </div>
            <div class="rounded-2xl border border-slate-100 bg-white p-4">
              <p class="text-xs font-black uppercase tracking-[0.16em] text-slate-400">Devices</p>
              <p class="mt-2 text-sm font-semibold text-slate-700">Link or unlink</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <section class="px-3 sm:px-4 pb-12 sm:pb-16">
    <div class="max-w-7xl mx-auto">
      <div class="grid gap-4 sm:grid-cols-3">
        <div class="rounded-3xl bg-white/95 p-5 sm:p-6 shadow-lg border border-slate-100">
          <p class="text-xs font-black uppercase tracking-[0.18em] text-hero">Trust</p>
          <p class="mt-3 text-lg font-black text-slate-900">Parents lead. Children stay in their lane.</p>
        </div>
        <div class="rounded-3xl bg-white/95 p-5 sm:p-6 shadow-lg border border-slate-100">
          <p class="text-xs font-black uppercase tracking-[0.18em] text-savings">Routines</p>
          <p class="mt-3 text-lg font-black text-slate-900">Keep the everyday stuff visible and easier to follow.</p>
        </div>
        <div class="rounded-3xl bg-white/95 p-5 sm:p-6 shadow-lg border border-slate-100">
          <p class="text-xs font-black uppercase tracking-[0.18em] text-reward">Momentum</p>
          <p class="mt-3 text-lg font-black text-slate-900">Small wins turn into clearer habits over time.</p>
        </div>
      </div>
    </div>
  </section>

  <section id="what-it-does" class="bg-white px-3 sm:px-4 py-16 md:py-24">
    <div class="max-w-7xl mx-auto">
      <div class="text-center mb-12 md:mb-16">
        <p class="text-xs font-bold uppercase tracking-[0.2em] text-slate-400">What Family Hero Hub does</p>
          <h2 class="mt-3 text-3xl md:text-4xl font-black text-slate-900">One family hub for the daily stuff that usually lives in everyone's head</h2>
        <p class="mx-auto mt-4 max-w-3xl text-base md:text-lg leading-relaxed text-slate-600">
          Family Hero Hub brings points, rewards, school bag prep, calendar tasks, savings-style goals, and caregiver access into one mobile-first family app.
        </p>
      </div>

      <div class="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
        {#each featureCards as card}
          {@const Icon = card.icon}
          <div class="card group border-b-8 border-slate-200 p-6 md:p-7 transition-all duration-300 hover:-translate-y-1">
            <div class="mb-6 flex h-14 w-14 items-center justify-center rounded-3xl bg-hero/10 text-hero group-hover:scale-105 transition-transform">
              <Icon size={28} />
            </div>
            <h3 class="text-xl font-black text-slate-900">{card.title}</h3>
            <p class="mt-3 leading-relaxed text-slate-600">{card.text}</p>
          </div>
        {/each}
      </div>
    </div>
  </section>

  <section id="how-it-works" class="px-3 sm:px-4 py-16 md:py-24">
    <div class="max-w-7xl mx-auto">
      <div class="text-center mb-12 md:mb-16">
        <p class="text-xs font-bold uppercase tracking-[0.2em] text-slate-400">How it works</p>
        <h2 class="mt-3 text-3xl md:text-4xl font-black text-slate-900">Start simple. Add more when your family is ready.</h2>
      </div>

      <div class="grid gap-5 lg:grid-cols-5">
        {#each steps as step, index}
          <div class="card p-6 md:p-7">
            <div class="inline-flex rounded-full bg-slate-900 px-3 py-1 text-xs font-black uppercase tracking-[0.18em] text-white">
              0{index + 1}
            </div>
            <h3 class="mt-5 text-xl font-black text-slate-900">{step.title}</h3>
            <p class="mt-3 leading-relaxed text-slate-600">{step.text}</p>
          </div>
        {/each}
      </div>
    </div>
  </section>

  <section class="px-3 sm:px-4 py-16 md:py-24">
    <div class="max-w-7xl mx-auto">
      <div class="grid gap-8 lg:grid-cols-[0.95fr_1.05fr]">
        <div class="card !bg-slate-900 text-white p-6 sm:p-8 md:p-10 relative overflow-hidden">
          <div class="absolute top-0 right-0 h-56 w-56 rounded-full bg-hero/10 blur-[120px]"></div>
          <div class="relative z-10">
            <p class="text-xs font-black uppercase tracking-[0.2em] text-hero">Trust and safety</p>
            <h2 class="mt-3 text-3xl md:text-4xl font-black leading-tight">A private family space, led by parents</h2>
            <p class="mt-5 text-base md:text-lg leading-relaxed text-slate-300">
              Family Hero Hub is designed for families, not followers. Parents set up the family, manage children, award points, approve rewards, invite caregivers, and control linked child devices.
            </p>
            <p class="mt-4 text-base md:text-lg leading-relaxed text-slate-300">
              Children get a simple dashboard to see their points, rewards, school bag items, tasks, and progress - without public profiles, social feeds, or child-to-child messaging.
            </p>
          </div>
        </div>

        <div class="card p-6 sm:p-8 md:p-10">
          <h3 class="text-2xl font-black text-slate-900">What parents control</h3>
          <div class="mt-6 grid gap-4 sm:grid-cols-2">
            {#each [
              'Parents control family setup',
              'Rewards require parent approval',
              'Children use linked dashboards',
              'Caregiver access can be invited and removed',
              'Child devices can be linked and unlinked',
              'No public child profiles',
              'No social feed',
              'No child-to-child messaging',
              'Savings are points-based, not banking'
            ] as item}
              <div class="rounded-3xl border border-slate-200 bg-slate-50/80 p-4 text-sm font-semibold leading-relaxed text-slate-700">
                {item}
              </div>
            {/each}
          </div>
        </div>
      </div>
    </div>
  </section>

  <section class="bg-white px-3 sm:px-4 py-16 md:py-24">
    <div class="max-w-7xl mx-auto grid gap-8 lg:grid-cols-[0.92fr_1.08fr] lg:items-start">
      <div class="card p-6 sm:p-8 md:p-10">
        <p class="text-xs font-bold uppercase tracking-[0.2em] text-slate-400">Child Dashboard</p>
        <h2 class="mt-3 text-3xl md:text-4xl font-black text-slate-900">A simple dashboard children can understand</h2>
        <p class="mt-5 leading-relaxed text-slate-600">
          Children can see their points, rewards, tasks, School Bag, savings progress, and daily routines from a child-friendly dashboard.
        </p>
        <p class="mt-4 leading-relaxed text-slate-600">
          It gives them a clear view of what they've earned, what's coming up, and what they can work toward next.
        </p>
        <p class="mt-5 rounded-3xl bg-hero/5 px-4 py-4 text-sm font-semibold text-slate-700">
          Children can request rewards, but parents approve them.
        </p>
      </div>

      <div class="card p-6 sm:p-8 md:p-10">
        <p class="text-xs font-bold uppercase tracking-[0.2em] text-savings">Rewards and savings</p>
        <h2 class="mt-3 text-3xl md:text-4xl font-black text-slate-900">Rewards, savings, and allowance without pretending to be a bank</h2>
        <p class="mt-5 leading-relaxed text-slate-600">
          Family Hero Hub can show optional allowance values beside points, helping children understand effort, saving, and rewards.
        </p>
        <p class="mt-4 leading-relaxed text-slate-600">
          Saved points can be locked for later and unlock with a bonus, giving children a simple way to practise waiting, planning, and working toward bigger rewards.
        </p>
        <div class="mt-6 rounded-3xl border border-amber-200 bg-amber-50 px-4 py-4 text-sm leading-relaxed text-slate-700">
          Family Hero Hub does not hold money, transfer money, or pay children directly. Parents remain responsible for any real-world allowance, reward, or purchase.
        </div>
      </div>
    </div>
  </section>

  <section class="px-3 sm:px-4 py-16 md:py-24">
    <div class="max-w-7xl mx-auto">
      <div class="text-center mb-12 md:mb-16">
        <p class="text-xs font-bold uppercase tracking-[0.2em] text-slate-400">FAQ preview</p>
        <h2 class="mt-3 text-3xl md:text-4xl font-black text-slate-900">Questions parents usually ask</h2>
      </div>

      <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {#each faqs as item}
          <div class="card p-6">
            <h3 class="text-lg font-black text-slate-900">{item.question}</h3>
            <p class="mt-3 leading-relaxed text-slate-600">{item.answer}</p>
          </div>
        {/each}
      </div>

      <div class="mt-8 text-center">
        <a href="/faq" class="btn-secondary inline-flex items-center justify-center gap-2 rounded-2xl px-6 py-4">
          Read the FAQ
          <ArrowRight size={18} />
        </a>
      </div>
    </div>
  </section>
</div>
