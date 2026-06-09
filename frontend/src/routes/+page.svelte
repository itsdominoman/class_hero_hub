<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { api } from '$lib/api';
  import LanguageSelector from '$lib/components/LanguageSelector.svelte';
  import {
    ArrowRight,
    Backpack,
    CalendarDays,
    CheckCircle2,
    Clock,
    Heart,
    Lightbulb,
    Lock,
    Coins,
    ShieldCheck,
    Sparkles,
    Star,
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
  let primaryCtaLabel = $derived(sessionLoaded && authenticated ? $_('home.dashboardCta') : $_('home.requestAccessCta'));

  const parentProblemItems = [
    'home.parentProblemItem1',
    'home.parentProblemItem2',
    'home.parentProblemItem3',
    'home.parentProblemItem4',
    'home.parentProblemItem5',
    'home.parentProblemItem6'
  ];

  const featureCards = [
    {
      icon: Trophy,
      title: 'home.featurePointsTitle',
      text: 'home.featurePointsText'
    },
    {
      icon: Star,
      title: 'home.featureRewardsTitle',
      text: 'home.featureRewardsText'
    },
    {
      icon: Coins,
      title: 'home.featureSavingsTitle',
      text: 'home.featureSavingsText'
    },
    {
      icon: Backpack,
      title: 'home.featureSchoolBagTitle',
      text: 'home.featureSchoolBagText'
    },
    {
      icon: CalendarDays,
      title: 'home.featureCalendarTitle',
      text: 'home.featureCalendarText'
    },
    {
      icon: Sparkles,
      title: 'home.featureChildDashboardTitle',
      text: 'home.featureChildDashboardText'
    },
    {
      icon: Users,
      title: 'home.featureParentsCaregiversTitle',
      text: 'home.featureParentsCaregiversText'
    },
    {
      icon: Lock,
      title: 'home.featureLinkedDevicesTitle',
      text: 'home.featureLinkedDevicesText'
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
      text: 'Children can view their own dashboard with points, rewards, tasks, School Bag, calendar events, and savings progress.'
    },
    {
      title: 'Approve rewards together',
      text: 'Children can request rewards. Parents approve or reject them, so expectations stay clear.'
    },
    {
      title: 'Grow into savings and allowance',
      text: 'When ready, add saved points, bonus unlocks, and optional allowance values — without turning the app into a bank.'
    }
  ];

  const choreChartCards = [
    {
      title: 'Routines',
      text: 'Keep daily responsibilities visible.'
    },
    {
      title: 'Rewards',
      text: 'Let children work toward parent-approved rewards.'
    },
    {
      title: 'Savings',
      text: 'Help children practise waiting and planning with saved points.'
    },
    {
      title: 'School prep',
      text: 'Make School Bag items easier to remember.'
    },
    {
      title: 'Family access',
      text: 'Invite trusted caregivers and remove access when needed.'
    }
  ];

  const trustItems = [
    'Parents control family setup',
    'Rewards require parent approval',
    'Children use linked dashboards',
    'Caregiver access can be invited and removed',
    'Child devices can be linked and unlinked',
    'No public child profiles',
    'No social feed',
    'No child-to-child messaging',
    'Savings are points-based, not banking'
  ];

  const faqs = [
    {
      question: 'Is Family Hero Hub a banking app?',
      answer: 'No. It can show optional allowance values beside points, but it does not hold or transfer money.'
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
    },
    {
      question: 'Why did you build Family Hero Hub?',
      answer: 'It started as a practical way to bring points, routines, school prep, rewards, savings-style goals, and child dashboards into one parent-led family space.'
    }
  ];
</script>

<svelte:head>
  <title>{$_('home.title')}</title>
  <meta
    name="description"
    content={$_('home.metaDescription')}
  />
</svelte:head>

<div class="relative max-w-full overflow-hidden bg-hero-pattern">
  <section class="px-3 sm:px-4 py-14 sm:py-18 lg:py-24">
    <div class="mx-auto mb-4 flex max-w-7xl justify-end">
      <LanguageSelector compact />
    </div>
    <div class="max-w-7xl mx-auto grid gap-10 lg:grid-cols-[1.08fr_0.92fr] lg:items-center">
      <div class="relative z-10 text-left">
        <div class="inline-flex max-w-full items-center gap-2 rounded-full border border-hero/20 bg-hero/10 px-4 py-2 text-sm font-black text-hero mb-6">
          <Sparkles size={16} />
          <span class="uppercase tracking-[0.12em] sm:tracking-[0.2em]">{$_('home.eyebrow')}</span>
        </div>
        <h1 class="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-black text-slate-900 leading-[0.96] max-w-2xl">
          {$_('home.heading')}
        </h1>
        <p class="mt-6 max-w-2xl text-lg sm:text-xl md:text-2xl leading-relaxed text-slate-600">
          {$_('home.intro')}
        </p>

        <div class="mt-8 flex flex-col sm:flex-row gap-4">
          <a href={primaryCtaHref} class="btn-hero inline-flex items-center justify-center gap-3 rounded-2xl px-6 py-4 text-base sm:text-lg">
            {primaryCtaLabel}
            <ArrowRight size={20} />
          </a>
          <a href="#how-it-works" class="btn-secondary inline-flex items-center justify-center rounded-2xl px-6 py-4 text-base sm:text-lg">
            {$_('home.howItWorksCta')}
          </a>
        </div>

        <p class="mt-5 max-w-2xl text-sm sm:text-base font-semibold text-slate-500 leading-relaxed">
          {$_('home.strapline')}
        </p>
        <p class="mt-3 text-sm font-semibold text-slate-500">
          <a href="/safety-privacy" class="text-hero hover:underline">{$_('nav.safetyPrivacy')}</a>
          <span class="px-2 text-slate-300">|</span>
          <a href="/faq" class="text-hero hover:underline">{$_('nav.faq')}</a>
        </p>
      </div>

      <div class="relative">
        <div class="card relative z-10 overflow-hidden border border-white/80 bg-white/95 p-5 sm:p-6 lg:p-8 shadow-2xl">
          <div class="grid gap-4 sm:grid-cols-2">
            <div class="rounded-3xl border border-slate-100 bg-slate-50 p-5">
              <p class="text-xs font-black uppercase tracking-[0.18em] text-slate-400">{$_('home.parentView')}</p>
              <p class="mt-3 text-xl font-black text-slate-900">{$_('home.parentViewTitle')}</p>
              <p class="mt-2 text-sm leading-relaxed text-slate-600">{$_('home.parentViewText')}</p>
            </div>
            <div class="rounded-3xl border border-slate-100 bg-hero/5 p-5">
              <p class="text-xs font-black uppercase tracking-[0.18em] text-hero">{$_('home.childView')}</p>
              <p class="mt-3 text-xl font-black text-slate-900">{$_('home.childViewTitle')}</p>
              <p class="mt-2 text-sm leading-relaxed text-slate-600">{$_('home.childViewText')}</p>
            </div>
          </div>

          <div class="mt-4 rounded-3xl bg-slate-900 p-5 sm:p-6 text-white">
            <div class="flex items-center gap-2 text-sm font-black uppercase tracking-[0.18em] text-hero">
              <ShieldCheck size={16} />
              <span>{$_('home.privateByDesign')}</span>
            </div>
            <p class="mt-3 text-lg font-semibold leading-relaxed text-slate-200">
              {$_('home.privateByDesignText')}
            </p>
          </div>

          <div class="mt-4 grid gap-3 sm:grid-cols-3">
            <div class="rounded-2xl border border-slate-100 bg-white p-4">
              <p class="text-xs font-black uppercase tracking-[0.16em] text-slate-400">{$_('home.heroRewardLabel')}</p>
              <p class="mt-2 text-sm font-semibold text-slate-700">{$_('home.heroRewardValue')}</p>
            </div>
            <div class="rounded-2xl border border-slate-100 bg-white p-4">
              <p class="text-xs font-black uppercase tracking-[0.16em] text-slate-400">{$_('home.heroAccessLabel')}</p>
              <p class="mt-2 text-sm font-semibold text-slate-700">{$_('home.heroAccessValue')}</p>
            </div>
            <div class="rounded-2xl border border-slate-100 bg-white p-4">
              <p class="text-xs font-black uppercase tracking-[0.16em] text-slate-400">{$_('home.heroDevicesLabel')}</p>
              <p class="mt-2 text-sm font-semibold text-slate-700">{$_('home.heroDevicesValue')}</p>
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
          <p class="text-xs font-black uppercase tracking-[0.18em] text-hero">{$_('home.heroTrustLabel')}</p>
          <p class="mt-3 text-lg font-black text-slate-900">{$_('home.heroTrustText')}</p>
        </div>
        <div class="rounded-3xl bg-white/95 p-5 sm:p-6 shadow-lg border border-slate-100">
          <p class="text-xs font-black uppercase tracking-[0.18em] text-savings">{$_('home.heroRoutinesLabel')}</p>
          <p class="mt-3 text-lg font-black text-slate-900">{$_('home.heroRoutinesText')}</p>
        </div>
        <div class="rounded-3xl bg-white/95 p-5 sm:p-6 shadow-lg border border-slate-100">
          <p class="text-xs font-black uppercase tracking-[0.18em] text-reward">{$_('home.heroMomentumLabel')}</p>
          <p class="mt-3 text-lg font-black text-slate-900">{$_('home.heroMomentumText')}</p>
        </div>
      </div>
    </div>
  </section>

  <section class="bg-white px-3 sm:px-4 py-16 md:py-24">
    <div class="max-w-7xl mx-auto grid gap-8 lg:grid-cols-[0.9fr_1.1fr] lg:items-start">
      <div>
        <p class="text-xs font-bold uppercase tracking-[0.2em] text-slate-400">{$_('home.storyEyebrow')}</p>
        <h2 class="mt-3 text-3xl md:text-4xl font-black text-slate-900">{$_('home.storyHeading')}</h2>
      </div>
      <div class="space-y-5 text-base md:text-lg leading-relaxed text-slate-600">
        <p>
          {$_('home.storyParagraph1')}
        </p>
        <p>
          {$_('home.storyParagraph2')}
        </p>
        <p>
          {$_('home.storyParagraph3')}
        </p>
      </div>
    </div>
  </section>

  <section class="px-3 sm:px-4 py-16 md:py-24">
    <div class="max-w-7xl mx-auto">
      <div class="max-w-3xl mb-10">
        <p class="text-xs font-bold uppercase tracking-[0.2em] text-slate-400">{$_('home.parentProblemEyebrow')}</p>
        <h2 class="mt-3 text-3xl md:text-4xl font-black text-slate-900">{$_('home.parentProblemHeading')}</h2>
        <p class="mt-5 text-base md:text-lg leading-relaxed text-slate-600">
          {$_('home.parentProblemParagraph1')}
        </p>
        <p class="mt-4 text-base md:text-lg leading-relaxed text-slate-600">
          {$_('home.parentProblemParagraph2')}
        </p>
      </div>

      <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {#each parentProblemItems as item}
          <div class="card p-5 flex items-start gap-3">
            <CheckCircle2 size={22} class="mt-0.5 shrink-0 text-savings" />
            <p class="font-black leading-relaxed text-slate-900">{$_(item)}</p>
          </div>
        {/each}
      </div>
    </div>
  </section>

  <section id="what-it-does" class="bg-white px-3 sm:px-4 py-16 md:py-24">
    <div class="max-w-7xl mx-auto">
      <div class="text-center mb-12 md:mb-16">
        <p class="text-xs font-bold uppercase tracking-[0.2em] text-slate-400">{$_('home.whatItDoesEyebrow')}</p>
        <h2 class="mt-3 text-3xl md:text-4xl font-black text-slate-900">{$_('home.whatItDoesHeading')}</h2>
        <p class="mx-auto mt-4 max-w-3xl text-base md:text-lg leading-relaxed text-slate-600">
          {$_('home.whatItDoesIntro')}
        </p>
      </div>

      <div class="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
        {#each featureCards as card}
          {@const Icon = card.icon}
          <div class="card group border-b-8 border-slate-200 p-6 md:p-7 transition-all duration-300 hover:-translate-y-1">
            <div class="mb-6 flex h-14 w-14 items-center justify-center rounded-3xl bg-hero/10 text-hero group-hover:scale-105 transition-transform">
              <Icon size={28} />
            </div>
            <h3 class="text-xl font-black text-slate-900">{$_(card.title)}</h3>
            <p class="mt-3 leading-relaxed text-slate-600">{$_(card.text)}</p>
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
        <p class="mx-auto mt-4 max-w-3xl text-base md:text-lg leading-relaxed text-slate-600">
          You do not need to use every feature on day one. Start with points and rewards, then add School Bag, Calendar, savings, allowance values, child devices, and caregiver access when they make sense for your family.
        </p>
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

  <section class="bg-white px-3 sm:px-4 py-16 md:py-24">
    <div class="max-w-7xl mx-auto grid gap-8 lg:grid-cols-[0.95fr_1.05fr] lg:items-start">
      <div>
        <p class="text-xs font-bold uppercase tracking-[0.2em] text-slate-400">Child benefit</p>
        <h2 class="mt-3 text-3xl md:text-4xl font-black text-slate-900">For children who need to see progress</h2>
        <p class="mt-5 text-base md:text-lg leading-relaxed text-slate-600">
          Children do better when they can see what is expected, what progress they have made, and what they are working toward.
        </p>
        <p class="mt-4 text-base md:text-lg leading-relaxed text-slate-600">
          The Child Dashboard gives them a simple view of their points, rewards, tasks, School Bag, Calendar, and savings progress — without sharing the parent account, parent login, or parent device.
        </p>
        <p class="mt-5 rounded-3xl bg-hero/5 px-4 py-4 text-sm font-semibold text-slate-700">
          Children can request rewards, but parents approve them.
        </p>
      </div>

      <div class="grid gap-4 sm:grid-cols-2">
        <div class="card p-6">
          <Clock size={28} class="text-hero" />
          <h3 class="mt-5 text-xl font-black text-slate-900">What is next</h3>
          <p class="mt-3 leading-relaxed text-slate-600">Tasks, School Bag items, and Calendar routines are easier to see.</p>
        </div>
        <div class="card p-6">
          <Star size={28} class="text-reward" />
          <h3 class="mt-5 text-xl font-black text-slate-900">What they have done</h3>
          <p class="mt-3 leading-relaxed text-slate-600">Points and rewards make effort, responsibility, and follow-through visible.</p>
        </div>
        <div class="card p-6 sm:col-span-2">
          <Coins size={28} class="text-savings" />
          <h3 class="mt-5 text-xl font-black text-slate-900">What they are working toward</h3>
          <p class="mt-3 leading-relaxed text-slate-600">Saved points and parent-approved rewards help children practise waiting, planning, and choosing.</p>
        </div>
      </div>
    </div>
  </section>

  <section class="px-3 sm:px-4 py-16 md:py-24">
    <div class="max-w-7xl mx-auto">
      <div class="max-w-3xl mb-10">
        <p class="text-xs font-bold uppercase tracking-[0.2em] text-slate-400">Not just chores</p>
        <h2 class="mt-3 text-3xl md:text-4xl font-black text-slate-900">More than a chore chart</h2>
        <p class="mt-5 text-base md:text-lg leading-relaxed text-slate-600">
          Family Hero Hub is not just a list of jobs. It connects everyday routines with points, rewards, savings-style goals, school prep, child dashboards, and caregiver access.
        </p>
      </div>

      <div class="grid gap-5 md:grid-cols-2 xl:grid-cols-5">
        {#each choreChartCards as card}
          <div class="card p-6">
            <Lightbulb size={26} class="text-hero" />
            <h3 class="mt-5 text-xl font-black text-slate-900">{card.title}</h3>
            <p class="mt-3 leading-relaxed text-slate-600">{card.text}</p>
          </div>
        {/each}
      </div>
    </div>
  </section>

  <section class="px-3 sm:px-4 py-16 md:py-24">
    <div class="max-w-7xl mx-auto">
      <div class="grid gap-8 lg:grid-cols-[0.95fr_1.05fr]">
        <div class="card !bg-slate-900 text-white p-6 sm:p-8 md:p-10 relative overflow-hidden">
          <div class="relative z-10">
            <p class="text-xs font-black uppercase tracking-[0.2em] text-hero">Trust and safety</p>
            <h2 class="mt-3 text-3xl md:text-4xl font-black leading-tight">A private family space, led by parents</h2>
            <p class="mt-5 text-base md:text-lg leading-relaxed text-slate-300">
              Family Hero Hub is designed for families, not followers. Parents set up the family, manage children, award points, approve rewards, invite caregivers, and control linked child devices.
            </p>
            <p class="mt-4 text-base md:text-lg leading-relaxed text-slate-300">
              Children get a simple dashboard to see their points, rewards, School Bag items, tasks, and progress — without public profiles, social feeds, or child-to-child messaging.
            </p>
            <div class="mt-6 rounded-3xl border border-white/10 bg-white/5 p-4 text-slate-300">
              <h3 class="text-xl font-black text-white">Parent-led by design</h3>
              <p class="mt-3 leading-relaxed">
                Parents manage rewards, caregivers, and linked child devices. Children get simple dashboards without sharing the parent account.
              </p>
              <p class="mt-3 leading-relaxed">
                Family Hero Hub does not hold money, store bank details, transfer funds, or pay children directly. Points and allowance values stay inside your family's own system.
              </p>
            </div>
            <a href="/safety-privacy" class="mt-6 inline-flex items-center gap-2 font-black text-hero hover:underline">
              Read Safety & Privacy
              <ArrowRight size={18} />
            </a>
          </div>
        </div>

        <div class="card p-6 sm:p-8 md:p-10">
          <h3 class="text-2xl font-black text-slate-900">What parents control</h3>
          <div class="mt-6 grid gap-4 sm:grid-cols-2">
            {#each trustItems as item}
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
      <div>
        <p class="text-xs font-bold uppercase tracking-[0.2em] text-savings">Rewards, savings, and allowance</p>
        <h2 class="mt-3 text-3xl md:text-4xl font-black text-slate-900">Rewards, savings, and allowance — without pretending to be a bank</h2>
      </div>

      <div class="space-y-5 text-base md:text-lg leading-relaxed text-slate-600">
        <p>
          Family Hero Hub can show optional allowance values beside points, helping children understand effort, saving, and rewards.
        </p>
        <p>
          Points can also help children understand that effort, responsibility, and follow-through can lead to rewards. When families choose to show optional allowance values, children can start to see how consistent effort adds up over time.
        </p>
        <p>
          Saved points can be locked for later and unlock with a bonus, giving children a simple way to practise waiting, planning, and working toward bigger rewards.
        </p>
        <div class="rounded-3xl border border-amber-200 bg-amber-50 px-4 py-4 text-sm leading-relaxed text-slate-700">
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
