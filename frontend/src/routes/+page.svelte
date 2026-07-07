<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { api } from '$lib/api';
  import LanguageSelector from '$lib/components/LanguageSelector.svelte';
  import {
    ArrowRight,
    Bell,
    CalendarDays,
    CheckCircle2,
    ClipboardList,
    Lock,
    MessageSquare,
    School,
    ShieldCheck,
    Sparkles,
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

  let primaryCtaHref = $derived(sessionLoaded && authenticated ? '/parent' : '/login');
  let primaryCtaLabel = $derived(sessionLoaded && authenticated ? $_('home.dashboardCta') : $_('home.loginCta'));

  const featureCards = [
    {
      icon: MessageSquare,
      title: 'home.featureCommunicationTitle',
      text: 'home.featureCommunicationText'
    },
    {
      icon: CalendarDays,
      title: 'home.featureCalendarTitle',
      text: 'home.featureCalendarText'
    },
    {
      icon: ClipboardList,
      title: 'home.featureAdminTitle',
      text: 'home.featureAdminText'
    }
  ];

  const steps = [
    {
      title: 'home.step1Title',
      text: 'home.step1Text'
    },
    {
      title: 'home.step2Title',
      text: 'home.step2Text'
    },
    {
      title: 'home.step3Title',
      text: 'home.step3Text'
    }
  ];
</script>

<svelte:head>
  <title>{$_('home.title')}</title>
  <meta name="description" content={$_('home.metaDescription')} />
</svelte:head>

<div class="relative max-w-full overflow-hidden bg-hero-pattern">
  <section class="px-3 sm:px-4 py-14 sm:py-18 lg:py-24">
    <div class="mx-auto mb-4 flex max-w-7xl justify-end">
      <LanguageSelector compact />
    </div>
    <div class="max-w-7xl mx-auto grid gap-10 lg:grid-cols-[1.08fr_0.92fr] lg:items-center">
      <div class="relative z-10 text-left">
        <div class="inline-flex max-w-full items-center gap-2 rounded-full border border-hero/20 bg-hero/10 px-4 py-2 text-sm font-bold text-hero mb-6">
          <School size={16} />
          <span class="uppercase tracking-wide">{$_('home.eyebrow')}</span>
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

        <p class="mt-4 max-w-2xl text-sm sm:text-base font-semibold text-slate-500 leading-relaxed">
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
              <p class="text-xs font-semibold uppercase tracking-wide text-slate-400">{$_('home.schoolView')}</p>
              <p class="mt-3 text-xl font-bold text-slate-900">{$_('home.schoolViewTitle')}</p>
              <p class="mt-2 text-sm leading-relaxed text-slate-600">{$_('home.schoolViewText')}</p>
            </div>
            <div class="rounded-3xl border border-slate-100 bg-hero/5 p-5">
              <p class="text-xs font-semibold uppercase tracking-wide text-hero">{$_('home.familyView')}</p>
              <p class="mt-3 text-xl font-bold text-slate-900">{$_('home.familyViewTitle')}</p>
              <p class="mt-2 text-sm leading-relaxed text-slate-600">{$_('home.familyViewText')}</p>
            </div>
          </div>

          <div class="mt-4 rounded-3xl bg-slate-900 p-5 sm:p-6 text-white">
            <div class="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-hero">
              <ShieldCheck size={16} />
              <span>{$_('home.privateByDesign')}</span>
            </div>
            <p class="mt-3 text-lg font-semibold leading-relaxed text-slate-200">
              {$_('home.privateByDesignText')}
            </p>
          </div>
        </div>
      </div>
    </div>
  </section>

  <section class="px-3 sm:px-4 py-14 bg-white">
    <div class="mx-auto max-w-7xl">
      <div class="max-w-3xl">
        <p class="text-sm font-bold uppercase tracking-wide text-hero">{$_('home.whatItDoesEyebrow')}</p>
        <h2 class="mt-3 text-3xl sm:text-4xl font-black text-slate-900">{$_('home.whatItDoesHeading')}</h2>
        <p class="mt-4 text-lg leading-relaxed text-slate-600">{$_('home.whatItDoesIntro')}</p>
      </div>

      <div class="mt-10 grid gap-4 md:grid-cols-3">
        {#each featureCards as feature}
          {@const Icon = feature.icon}
          <div class="card p-6">
            <Icon size={24} class="text-hero" />
            <h3 class="mt-4 text-xl font-bold text-slate-900">{$_(feature.title)}</h3>
            <p class="mt-2 text-sm leading-relaxed text-slate-600">{$_(feature.text)}</p>
          </div>
        {/each}
      </div>
    </div>
  </section>

  <section id="how-it-works" class="px-3 sm:px-4 py-14">
    <div class="mx-auto max-w-7xl">
      <div class="max-w-3xl">
        <p class="text-sm font-bold uppercase tracking-wide text-hero">{$_('home.howItWorksEyebrow')}</p>
        <h2 class="mt-3 text-3xl sm:text-4xl font-black text-slate-900">{$_('home.howItWorksHeading')}</h2>
        <p class="mt-4 text-lg leading-relaxed text-slate-600">{$_('home.howItWorksIntro')}</p>
      </div>

      <div class="mt-10 grid gap-4 md:grid-cols-3">
        {#each steps as step, index}
          <div class="rounded-3xl border border-slate-200 bg-white p-6">
            <div class="flex h-10 w-10 items-center justify-center rounded-2xl bg-hero text-sm font-black text-white">
              {index + 1}
            </div>
            <h3 class="mt-4 text-xl font-bold text-slate-900">{$_(step.title)}</h3>
            <p class="mt-2 text-sm leading-relaxed text-slate-600">{$_(step.text)}</p>
          </div>
        {/each}
      </div>
    </div>
  </section>

  <section class="px-3 sm:px-4 py-14 bg-white">
    <div class="mx-auto max-w-7xl grid gap-4 md:grid-cols-3">
      <div class="rounded-3xl bg-slate-900 p-6 text-white">
        <Bell size={24} class="text-hero" />
        <p class="mt-4 text-lg font-bold">{$_('home.signal1')}</p>
      </div>
      <div class="rounded-3xl bg-slate-900 p-6 text-white">
        <Users size={24} class="text-hero" />
        <p class="mt-4 text-lg font-bold">{$_('home.signal2')}</p>
      </div>
      <div class="rounded-3xl bg-slate-900 p-6 text-white">
        <Lock size={24} class="text-hero" />
        <p class="mt-4 text-lg font-bold">{$_('home.signal3')}</p>
      </div>
    </div>
  </section>

  <section class="px-3 sm:px-4 py-14">
    <div class="mx-auto max-w-3xl text-center">
      <CheckCircle2 size={32} class="mx-auto text-hero" />
      <p class="mt-4 text-sm font-bold uppercase tracking-wide text-hero">{$_('home.statusEyebrow')}</p>
      <h2 class="mt-3 text-3xl sm:text-4xl font-black text-slate-900">{$_('home.statusHeading')}</h2>
      <p class="mt-4 text-lg leading-relaxed text-slate-600">{$_('home.statusText')}</p>
    </div>
  </section>
</div>
