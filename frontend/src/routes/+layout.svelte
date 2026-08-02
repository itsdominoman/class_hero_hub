<script lang="ts">
  import '../app.css';
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { _, locale } from 'svelte-i18n';
  import { api } from '$lib/api';
  import LanguageSelector from '$lib/components/LanguageSelector.svelte';
  import { initI18n } from '$lib/i18n';
  import { errorStatus, messagingApi } from '$lib/messaging/api';
  import type { MessagingMembership } from '$lib/messaging/types';
  import {
    activeNavigationItem,
    GLOBAL_NAVIGATION_ORDER,
    type GlobalNavigationItemId
  } from '$lib/navigation';
  import { safeguardingApi } from '$lib/safeguarding/api';
  import type { SafeguardingMembership } from '$lib/safeguarding/types';
  import { clearNativeSession, isNativePlatform } from '$lib/nativeAuth';
  import { defaultLandingPath, hasRole, type SessionUser } from '$lib/roleRouting';
  import { SCHOOL_MENU_GROUPS, SCHOOL_TABS, type SchoolMenuItem } from '$lib/schoolMenu';
  import { surveyApi, type SurveyMembership } from '$lib/surveys/api';
  import { getPublicSiteCopy } from '$lib/publicSite';

  const PUBLIC_WEBSITE_PATHS = new Set([
    '/',
    '/features',
    '/how-it-works',
    '/schools',
    '/family-connection',
    '/faq',
    '/pilot',
    '/contact',
    '/guides/administrator',
    '/guides/teacher',
    '/guides/families',
    '/safety-privacy',
    '/privacy',
    '/terms',
    '/data-requests',
    '/login'
  ]);

  let { children } = $props();
  let currentUser = $state<SessionUser | null>(null);
  let mobileMenuOpen = $state(false);
  let messagingMemberships = $state<MessagingMembership[]>([]);
  let messagingAvailable = $state(false);
  let messagingUnread = $state(0);
  let safeguardingMemberships = $state<SafeguardingMembership[]>([]);
  let surveyMemberships = $state<SurveyMembership[]>([]);
  // Capacitor exposes this synchronously before the app shell is hydrated.
  // Keep public website chrome out of the native shell while preserving it on web.
  let nativeApp = $state(isNativePlatform());
  let nativePushStatus = $state<'enabled' | 'disabled' | 'denied' | null>(null);
  let showPushExplanation = $state(false);
  let changingPush = $state(false);
  let publicCopy = $derived(getPublicSiteCopy($locale));
  let publicWebsiteRoute = $derived(
    !nativeApp && PUBLIC_WEBSITE_PATHS.has($page.url.pathname)
  );

  type NavigationItem = {
    id: GlobalNavigationItemId;
    href: string;
    labelKey: string;
    visible: boolean;
  };

  if (nativeApp && typeof document !== 'undefined') {
    document.documentElement.classList.add('native-app');
  }

  async function loadSession() {
    try {
      await api.refreshAuth();
      currentUser = await api.get('/me');
      messagingMemberships = (currentUser?.memberships || []).filter(
        (row): row is MessagingMembership =>
          (row.role === 'teacher' || row.role === 'school_admin') &&
          Number.isInteger(row.membership_id)
      );
      const safeguardingChecks = await Promise.all(
        (currentUser?.memberships || []).map(async (row) => {
          try {
            const availability = await safeguardingApi.availability(row);
            return availability.available ? row : null;
          } catch {
            return null;
          }
        })
      );
      safeguardingMemberships = safeguardingChecks.filter(
        (row): row is SafeguardingMembership => row !== null
      );
      const surveyChecks = await Promise.all(
        (currentUser?.memberships || [])
          .filter((row) => row.role === 'school_admin')
          .map(async (row) => {
            try {
              return (await surveyApi.availability(row)).available ? row : null;
            } catch {
              return null;
            }
          })
      );
      surveyMemberships = surveyChecks.filter((row): row is SurveyMembership => row !== null);
      await refreshMessagingBadge();
      if (nativeApp && messagingMemberships.length > 0) {
        void prepareNativePush();
      } else if (nativeApp) {
        // Account switches into an ineligible role must revoke any token left
        // by the prior staff account on this physical installation.
        void import('$lib/nativePushNotifications').then(({ unregisterNativePush }) => unregisterNativePush());
      }
    } catch {
      currentUser = null;
      messagingMemberships = [];
      safeguardingMemberships = [];
      surveyMemberships = [];
      messagingAvailable = false;
      messagingUnread = 0;
    }
  }

  async function prepareNativePush() {
    const push = await import('$lib/nativePushNotifications');
    await push.initializeNativePushRuntime();
    const status = await push.loadNativePushStatus();
    nativePushStatus = status.kind === 'unsupported' ? null : status.kind;
    if (
      nativePushStatus === 'disabled' &&
      localStorage.getItem('chh.push.explanation.dismissed') !== 'true'
    ) showPushExplanation = true;
  }

  async function enableNativePush() {
    changingPush = true;
    const push = await import('$lib/nativePushNotifications');
    const outcome = await push.registerForNativePush();
    nativePushStatus = outcome === 'registered' ? 'enabled' : outcome === 'denied' ? 'denied' : 'disabled';
    showPushExplanation = false;
    localStorage.setItem('chh.push.explanation.dismissed', 'true');
    changingPush = false;
  }

  function dismissPushExplanation() {
    showPushExplanation = false;
    localStorage.setItem('chh.push.explanation.dismissed', 'true');
  }

  async function disableNativePush() {
    changingPush = true;
    const { unregisterNativePush } = await import('$lib/nativePushNotifications');
    if (await unregisterNativePush()) nativePushStatus = 'disabled';
    changingPush = false;
  }

  async function refreshMessagingBadge() {
    if (messagingMemberships.length === 0 || document.hidden) return;
    const results = await Promise.all(
      messagingMemberships.map(async (membership) => {
        try {
          return await messagingApi.unreadCount(membership);
        } catch (error) {
          if (errorStatus(error) === 404 || errorStatus(error) === 403) return null;
          throw error;
        }
      })
    ).catch(() => null);
    if (results) {
      const enabled = results.filter((result) => result !== null);
      messagingAvailable = enabled.length > 0;
      messagingUnread = enabled.reduce((sum, result) => sum + (result?.total || 0), 0);
      if (!messagingAvailable) {
        messagingUnread = 0;
      }
    }
  }

  async function handleLogout() {
    if (nativeApp) {
      const { unregisterNativePush } = await import('$lib/nativePushNotifications');
      if (!(await unregisterNativePush())) return;
    }
    try {
      await api.post('/auth/logout', {});
    } finally {
      if (nativeApp) await clearNativeSession();
      currentUser = null;
      messagingMemberships = [];
      safeguardingMemberships = [];
      surveyMemberships = [];
      messagingAvailable = false;
      messagingUnread = 0;
      window.location.href = '/';
    }
  }

  function closeMobileMenu() {
    mobileMenuOpen = false;
    document.body.classList.remove('mobile-menu-open');
  }

  function toggleMobileMenu() {
    mobileMenuOpen = !mobileMenuOpen;
    document.body.classList.toggle('mobile-menu-open', mobileMenuOpen);
  }

  initI18n();

  function trackNativeViewport() {
    const root = document.documentElement;
    const viewport = window.visualViewport;
    let expandedHeight = Math.max(window.innerHeight, viewport?.height || 0);

    const update = () => {
      const height = Math.round(viewport?.height || window.innerHeight);
      expandedHeight = Math.max(expandedHeight, height);
      root.style.setProperty('--native-viewport-height', `${height}px`);
      root.classList.toggle('native-keyboard-open', expandedHeight - height > 120);
    };

    update();
    viewport?.addEventListener('resize', update);
    window.addEventListener('resize', update);
    return () => {
      viewport?.removeEventListener('resize', update);
      window.removeEventListener('resize', update);
      root.style.removeProperty('--native-viewport-height');
      root.classList.remove('native-keyboard-open');
    };
  }

  onMount(() => {
    void loadSession();
    let disposed = false;
    let removeNativeBackHandler: (() => Promise<void>) | null = null;
    const removeNativeViewportTracking = nativeApp ? trackNativeViewport() : null;
    const onKeydown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') closeMobileMenu();
    };
    const onCloseMobileMenu = () => closeMobileMenu();
    const onNativeBack = (event: Event) => {
      const active = document.activeElement;
      const editable =
        active instanceof HTMLInputElement ||
        active instanceof HTMLTextAreaElement ||
        (active instanceof HTMLElement && active.isContentEditable);
      if (editable && document.documentElement.classList.contains('native-keyboard-open')) {
        (active as HTMLElement).blur();
        event.preventDefault();
        event.stopImmediatePropagation();
        return;
      }
      if (mobileMenuOpen) {
        closeMobileMenu();
        event.preventDefault();
        event.stopImmediatePropagation();
      }
    };
    const onFocus = () => void refreshMessagingBadge();
    const badgeTimer = setInterval(() => void refreshMessagingBadge(), 30_000);
    window.addEventListener('keydown', onKeydown);
    window.addEventListener('focus', onFocus);
    window.addEventListener('chh:close-mobile-menu', onCloseMobileMenu);
    window.addEventListener('chh:native-back', onNativeBack, { capture: true });
    if (nativeApp) {
      void import('$lib/native/platform-bridge').then(async ({ registerNativeBackButtonHandler }) => {
        const remove = await registerNativeBackButtonHandler(['/', '/login', '/school', '/teach', '/parent']);
        if (disposed) await remove();
        else removeNativeBackHandler = remove;
      }).catch(() => undefined);
    }
    return () => {
      disposed = true;
      window.removeEventListener('keydown', onKeydown);
      window.removeEventListener('focus', onFocus);
      window.removeEventListener('chh:close-mobile-menu', onCloseMobileMenu);
      window.removeEventListener('chh:native-back', onNativeBack, { capture: true });
      clearInterval(badgeTimer);
      document.body.classList.remove('mobile-menu-open');
      document.documentElement.classList.remove('native-app');
      removeNativeViewportTracking?.();
      if (removeNativeBackHandler) void removeNativeBackHandler();
    };
  });

  let hasSchoolAdmin = $derived(hasRole(currentUser, 'school_admin'));
  let hasTeacher = $derived(hasRole(currentUser, 'teacher'));
  let hasGuardian = $derived(hasRole(currentUser, 'guardian'));
  let hasAnyRole = $derived(hasSchoolAdmin || hasTeacher || hasGuardian || Boolean(currentUser?.is_platform_admin));
  let dashboardHref = $derived(defaultLandingPath(currentUser));
  let safeguardingHref = $derived(
    safeguardingMemberships.length
      ? `/school/safeguarding?membership=${safeguardingMemberships[0].membership_id}`
      : '/school/safeguarding'
  );
  let surveysHref = $derived(
    surveyMemberships.length ? `/school/surveys?membership=${surveyMemberships[0].membership_id}` : '/school/surveys'
  );
  let navigationItemConfig = $derived<Record<GlobalNavigationItemId, Omit<NavigationItem, 'id'>>>(
    {
      family: { href: '/parent', labelKey: 'nav.family', visible: hasGuardian },
      platform: {
        href: '/platform',
        labelKey: 'nav.admin',
        visible: Boolean(currentUser?.is_platform_admin)
      },
      school: { href: '/school', labelKey: 'nav.school', visible: hasSchoolAdmin },
      teach: { href: '/teach', labelKey: 'nav.teach', visible: hasTeacher },
      messages: { href: '/messages', labelKey: 'nav.messages', visible: messagingAvailable },
      surveys: { href: surveysHref, labelKey: 'nav.surveys', visible: surveyMemberships.length > 0 },
      reports: { href: '/school/reports', labelKey: 'nav.reports', visible: hasSchoolAdmin },
      system: {
        href: '/school/administration',
        labelKey: 'nav.administration',
        visible: hasSchoolAdmin
      },
      safeguarding: {
        href: safeguardingHref,
        labelKey: 'nav.safeguarding',
        visible: safeguardingMemberships.length > 0
      },
      dashboard: { href: dashboardHref, labelKey: 'nav.dashboard', visible: !hasAnyRole }
    }
  );
  let navigationItems = $derived(
    GLOBAL_NAVIGATION_ORDER.map((id) => ({ id, ...navigationItemConfig[id] })).filter(
      (item) => item.visible
    )
  );
  let currentNavigationItem = $derived(activeNavigationItem($page.url.pathname));
  let schoolSetupNavigationVisible = $derived(
    hasSchoolAdmin && (
      $page.url.pathname === '/school'
      || SCHOOL_MENU_GROUPS.some((group) => group.items.some(
        (item) => item.type !== 'tab' && item.href === $page.url.pathname
      ))
    )
  );
  let currentSchoolSetupTab = $derived.by(() => {
    if ($page.url.pathname !== '/school') return null;
    const requested = $page.url.searchParams.get('tab');
    return requested && SCHOOL_TABS.some((tab) => tab.key === requested) ? requested : 'checklist';
  });

  function navigationItemIsCurrent(item: NavigationItem) {
    return item.id === 'dashboard'
      ? $page.url.pathname === item.href
      : currentNavigationItem === item.id;
  }

  function desktopNavigationClass(item: NavigationItem) {
    const base =
      'relative rounded-xl px-2.5 py-2 text-[0.8125rem] font-bold uppercase tracking-wide transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-hero 2xl:text-sm';
    return navigationItemIsCurrent(item)
      ? `${base} bg-hero/10 text-hero ring-1 ring-inset ring-hero/20`
      : `${base} text-slate-500 hover:bg-slate-100 hover:text-hero`;
  }

  function mobileNavigationClass(item: NavigationItem) {
    return mobileNavigationItemIsCurrent(item)
      ? 'mobile-nav-link mobile-nav-link-active flex items-center justify-between gap-3'
      : 'mobile-nav-link flex items-center justify-between gap-3';
  }

  function mobileNavigationItemIsCurrent(item: NavigationItem) {
    return !schoolSetupNavigationVisible && navigationItemIsCurrent(item);
  }

  function schoolSetupItemIsCurrent(item: SchoolMenuItem) {
    return item.type === 'tab'
      ? currentSchoolSetupTab === item.key
      : $page.url.pathname === item.href;
  }

  function schoolSetupTabHref(key: string) {
    const search = new URLSearchParams(
      $page.url.pathname === '/school' ? $page.url.searchParams : undefined
    );
    if (key === 'checklist') search.delete('tab');
    else search.set('tab', key);
    const query = search.toString();
    return `/school${query ? `?${query}` : ''}`;
  }

  function mobileSchoolSetupItemClass(item: SchoolMenuItem) {
    return schoolSetupItemIsCurrent(item)
      ? 'mobile-school-link mobile-school-link-active flex items-center justify-between gap-3'
      : 'mobile-school-link flex items-center justify-between gap-3';
  }
  // Messaging already owns a bounded viewport and its single bottom inset at the
  // sticky composer. Every other native route gets the bottom inset from app-main.
  let messagingRoute = $derived($page.url.pathname.startsWith('/messages'));
</script>

<div class="app-shell min-h-dvh max-w-full overflow-x-hidden flex flex-col">
  {#if publicWebsiteRoute}
    <header class="app-header sticky top-0 z-50 shrink-0 border-b border-slate-200/70 bg-white/90 shadow-sm backdrop-blur-xl pt-[var(--safe-top)]">
      <div class="mx-auto flex min-h-20 max-w-7xl items-center justify-between gap-3 px-3 py-3 sm:px-4">
        <a href="/" class="group flex min-w-0 items-center gap-3" aria-label={$_('app.name')}>
          <img src="/chh-logo-master.png" alt="" class="h-11 w-11 shrink-0 rounded-2xl object-contain shadow-xl shadow-hero/20 transition duration-300 group-hover:rotate-3 sm:h-12 sm:w-12" />
          <div class="brand-title flex min-w-0 flex-col -space-y-1">
            <span class="text-lg font-black uppercase leading-none tracking-tighter text-slate-950 sm:text-2xl">{$_('app.classHero')}</span>
            <span class="text-xs font-black uppercase leading-none tracking-[0.16em] text-hero">{$_('app.hub')}</span>
          </div>
        </a>

        <nav class="hidden items-center gap-1 xl:flex" aria-label={publicCopy.nav.menu}>
          <a href="/features" class="public-nav-link" aria-current={$page.url.pathname === '/features' ? 'page' : undefined}>{publicCopy.nav.product}</a>
          <a href="/how-it-works" class="public-nav-link" aria-current={$page.url.pathname === '/how-it-works' ? 'page' : undefined}>{publicCopy.nav.howItWorks}</a>
          <a href="/schools" class="public-nav-link" aria-current={$page.url.pathname === '/schools' ? 'page' : undefined}>{publicCopy.nav.schools}</a>
          <a href="/family-connection" class="public-nav-link" aria-current={$page.url.pathname === '/family-connection' ? 'page' : undefined}>{publicCopy.nav.familyConnection}</a>
          <LanguageSelector compact navigation />
          <a href={currentUser ? dashboardHref : '/login'} class="inline-flex min-h-11 items-center rounded-xl px-3 py-2 text-sm font-bold text-slate-600 transition hover:bg-slate-100 hover:text-hero focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-hero">
            {currentUser ? publicCopy.nav.dashboard : publicCopy.nav.staffLogin}
          </a>
          <a href="/pilot" class="inline-flex min-h-11 items-center rounded-xl bg-slate-950 px-4 py-2 text-sm font-bold text-white shadow-sm transition hover:bg-hero focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-hero">
            {publicCopy.nav.requestPilot}
          </a>
        </nav>

        <div class="flex shrink-0 items-center gap-2 xl:hidden">
          <a href={currentUser ? dashboardHref : '/login'} class="inline-flex min-h-11 items-center rounded-xl px-2.5 py-2 text-xs font-bold text-slate-600 transition hover:bg-slate-100 hover:text-hero sm:px-3 sm:text-sm">
            {currentUser ? publicCopy.nav.dashboard : publicCopy.nav.staffLogin}
          </a>
          <button
            type="button"
            class="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-700 shadow-sm transition hover:border-hero hover:text-hero focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-hero"
            aria-label={mobileMenuOpen ? publicCopy.nav.closeMenu : publicCopy.nav.openMenu}
            aria-expanded={mobileMenuOpen}
            aria-controls="public-mobile-navigation"
            onclick={toggleMobileMenu}
          >
            <span aria-hidden="true" class="text-xl leading-none">{mobileMenuOpen ? '×' : '☰'}</span>
          </button>
        </div>
      </div>
    </header>
  {:else}
  <header class="app-header bg-white/80 backdrop-blur-xl sticky top-0 z-50 shrink-0 border-b border-slate-200/50 shadow-sm pt-[var(--safe-top)]">
    <div class="max-w-7xl mx-auto px-3 sm:px-4 min-h-20 py-3 flex items-center justify-between gap-3">
      <a href="/" class="flex min-w-0 items-center gap-3 group">
        <img src="/chh-logo-master.png" alt={$_('app.name')} class="h-11 w-11 shrink-0 rounded-2xl object-contain shadow-xl shadow-hero/30 transition-all duration-300 group-hover:rotate-6 sm:h-12 sm:w-12" />
        <div class="brand-title flex min-w-0 flex-col -space-y-1">
          <span class="text-lg font-bold uppercase leading-none tracking-tighter text-slate-900 sm:text-2xl">{$_('app.classHero')}</span>
          <span class="text-xs font-bold uppercase leading-none tracking-wide text-hero opacity-80">{$_('app.hub')}</span>
        </div>
      </a>
      
      <nav class="hidden xl:flex items-center gap-1.5">
        {#if !currentUser}
          <a href="/login" class="text-sm font-bold text-slate-500 hover:text-hero uppercase tracking-wide transition-colors">
            {$_('nav.login')}
          </a>
        {:else}
          {#each navigationItems as item (item.id)}
            <a
              href={item.href}
              class={desktopNavigationClass(item)}
              aria-current={navigationItemIsCurrent(item) ? 'page' : undefined}
            >
              {$_(item.labelKey)}
              {#if item.id === 'messages' && messagingUnread > 0}
                <span class="absolute -right-2 -top-2 grid min-w-5 place-items-center rounded-full bg-hero px-1 text-[0.6rem] leading-5 text-white" aria-label={$_('messaging.unreadCount', { values: { count: messagingUnread } })}>{messagingUnread > 99 ? '99+' : messagingUnread}</span>
              {/if}
            </a>
          {/each}
          <LanguageSelector compact navigation />
          <button onclick={handleLogout} class="btn-hero px-6 py-3 rounded-2xl text-sm uppercase tracking-wide">{$_('nav.logout')}</button>
        {/if}
      </nav>

      {#if currentUser}
        <button
          type="button"
          class="xl:hidden inline-flex shrink-0 items-center justify-center rounded-2xl border border-slate-200 bg-white p-3 text-slate-700 shadow-sm transition hover:border-hero hover:text-hero"
          aria-label={mobileMenuOpen ? $_('nav.closeMenu') : $_('nav.openMenu')}
          aria-expanded={mobileMenuOpen}
          aria-controls="mobile-navigation"
          onclick={toggleMobileMenu}
        >
          <span aria-hidden="true" class="text-xl leading-none">{mobileMenuOpen ? '×' : '☰'}</span>
        </button>
      {:else}
        <a href="/login" class="xl:hidden inline-flex shrink-0 items-center justify-center rounded-full bg-slate-900 px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-white shadow-sm">
          {$_('nav.login')}
        </a>
      {/if}
    </div>
</header>
  {/if}

  {#if nativeApp && currentUser && showPushExplanation}
    <section class="mx-3 mt-3 rounded-2xl border border-hero/20 bg-white p-4 shadow-lg" aria-labelledby="push-explanation-title">
      <p id="push-explanation-title" class="font-black text-slate-900">{$_('pushNotifications.title')}</p>
      <p class="mt-1 text-sm leading-5 text-slate-600">{$_('pushNotifications.explanation')}</p>
      <div class="mt-3 flex flex-wrap gap-2">
        <button type="button" class="btn-hero rounded-xl px-4 py-2 text-sm" disabled={changingPush} onclick={enableNativePush}>{$_('pushNotifications.enable')}</button>
        <button type="button" class="btn-secondary rounded-xl px-4 py-2 text-sm" onclick={dismissPushExplanation}>{$_('pushNotifications.later')}</button>
      </div>
    </section>
  {/if}

  <main class:viewport-managed={nativeApp && messagingRoute} class="app-main flex-1 max-w-full overflow-x-hidden">
    {@render children()}
  </main>

  {#if !nativeApp && !messagingRoute}
    {#if publicWebsiteRoute}
      <footer class="relative overflow-hidden bg-slate-950 pb-[calc(3rem+var(--safe-bottom))] pt-14 text-slate-400 sm:pt-16">
        <div class="absolute left-0 top-0 h-px w-full bg-gradient-to-r from-transparent via-violet-400/70 to-transparent"></div>
        <div class="mx-auto max-w-7xl px-4">
          <div class="grid gap-12 lg:grid-cols-[0.82fr_1.18fr]">
            <div class="text-start">
              <a href="/" class="inline-flex items-center gap-3" aria-label={$_('app.name')}>
                <img src="/chh-logo-master.png" alt="" class="h-12 w-12 rounded-2xl bg-white object-contain" />
                <span class="text-xl font-black uppercase tracking-tight text-white">{$_('app.name')}</span>
              </a>
              <p class="mt-6 max-w-md text-base leading-relaxed text-slate-300 sm:text-lg">{publicCopy.footer.description}</p>
              <p class="mt-5 text-sm font-black uppercase tracking-[0.16em] text-violet-300">{publicCopy.footer.tagline}</p>
              <div class="mt-7 rounded-2xl border border-white/10 bg-white/5 p-4">
                <p class="text-xs font-bold uppercase tracking-[0.14em] text-slate-500">{publicCopy.footer.emailLabel}</p>
                <a class="mt-2 inline-flex text-sm font-bold text-violet-300 transition hover:text-white sm:text-base" href="mailto:support@classherohub.com">support@classherohub.com</a>
              </div>
            </div>

            <div class="grid gap-9 sm:grid-cols-3">
              <div class="min-w-0 text-start">
                <p class="text-sm font-black uppercase tracking-[0.14em] text-white">{publicCopy.footer.product}</p>
                <nav class="mt-5 flex flex-col gap-3 text-sm font-semibold" aria-label={publicCopy.footer.product}>
                  <a href="/" class="footer-link">{publicCopy.footer.home}</a>
                  <a href="/features" class="footer-link">{publicCopy.footer.features}</a>
                  <a href="/how-it-works" class="footer-link">{publicCopy.footer.howItWorks}</a>
                  <a href="/schools" class="footer-link">{publicCopy.footer.schools}</a>
                  <a href="/family-connection" class="footer-link">{publicCopy.footer.familyConnection}</a>
                  <a href="/faq" class="footer-link">{publicCopy.footer.faq}</a>
                  <a href="/pilot" class="footer-link">{publicCopy.footer.requestPilot}</a>
                </nav>
              </div>

              <div class="min-w-0 text-start">
                <p class="text-sm font-black uppercase tracking-[0.14em] text-white">{publicCopy.footer.support}</p>
                <nav class="mt-5 flex flex-col gap-3 text-sm font-semibold" aria-label={publicCopy.footer.support}>
                  <a href="/contact" class="footer-link">{publicCopy.footer.contact}</a>
                  <a href="/guides/administrator" class="footer-link">{publicCopy.footer.administratorGuide}</a>
                  <a href="/guides/teacher" class="footer-link">{publicCopy.footer.teacherGuide}</a>
                  <a href="/guides/families" class="footer-link">{publicCopy.footer.familyGuide}</a>
                  <a href="/safety-privacy" class="footer-link">{publicCopy.footer.safetyPrivacy}</a>
                </nav>
              </div>

              <div class="min-w-0 text-start">
                <p class="text-sm font-black uppercase tracking-[0.14em] text-white">{publicCopy.footer.legal}</p>
                <nav class="mt-5 flex flex-col gap-3 text-sm font-semibold" aria-label={publicCopy.footer.legal}>
                  <a href="/privacy" class="footer-link">{publicCopy.footer.privacy}</a>
                  <a href="/terms" class="footer-link">{publicCopy.footer.terms}</a>
                  <a href="/data-requests" class="footer-link">{publicCopy.footer.dataRequests}</a>
                </nav>
              </div>
            </div>
          </div>
        </div>
      </footer>
    {:else}
      <footer class="relative mt-16 overflow-hidden bg-slate-900 pb-[calc(4rem+var(--safe-bottom))] pt-16 text-slate-400 md:mt-20 md:pt-20">
        <div class="absolute left-0 top-0 h-1 w-full bg-gradient-to-r from-transparent via-hero/50 to-transparent"></div>
        <div class="mx-auto max-w-7xl px-4">
          <div class="grid gap-10 lg:grid-cols-[1.1fr_0.9fr] lg:gap-12">
            <div class="text-start">
              <div class="mb-6 flex items-center gap-3 opacity-50 grayscale">
                <img src="/chh-logo-master.png" alt={$_('app.name')} class="h-10 w-10 rounded-xl bg-white object-contain" />
                <span class="text-xl font-bold uppercase tracking-tighter text-white">{$_('app.name')}</span>
              </div>
              <p class="max-w-md text-lg leading-relaxed">{$_('footer.description')}</p>
              <p class="mt-6 text-sm font-semibold uppercase tracking-wide text-white">{$_('footer.tagline')}</p>
            </div>
            <div class="grid gap-8 sm:grid-cols-3">
              <div class="min-w-0"><p class="mb-4 text-sm font-semibold uppercase tracking-wide text-white">{$_('nav.product')}</p><div class="flex flex-col gap-3 text-sm font-semibold"><a href="/" class="transition-colors hover:text-hero">{$_('nav.home')}</a><a href="/#how-it-works" class="transition-colors hover:text-hero">{$_('nav.howItWorks')}</a><a href="/faq" class="transition-colors hover:text-hero">{$_('nav.faq')}</a></div></div>
              <div class="min-w-0"><p class="mb-4 text-sm font-semibold uppercase tracking-wide text-white">{$_('nav.support')}</p><div class="flex flex-col gap-3 text-sm font-semibold"><a href="/contact" class="transition-colors hover:text-hero">{$_('nav.contact')}</a><a href="/safety-privacy" class="transition-colors hover:text-hero">{$_('nav.safetyPrivacy')}</a></div></div>
              <div class="min-w-0"><p class="mb-4 text-sm font-semibold uppercase tracking-wide text-white">{$_('nav.legal')}</p><div class="flex flex-col gap-3 text-sm font-semibold"><a href="/privacy" class="transition-colors hover:text-hero">{$_('nav.privacyPolicy')}</a><a href="/terms" class="transition-colors hover:text-hero">{$_('nav.terms')}</a></div></div>
            </div>
          </div>
        </div>
      </footer>
    {/if}
  {/if}
</div>

{#if publicWebsiteRoute && mobileMenuOpen}
  <div class="fixed inset-0 z-[100] xl:hidden" role="presentation">
    <button type="button" class="absolute inset-0 h-full w-full bg-slate-950/55 backdrop-blur-sm" aria-label={publicCopy.nav.closeMenu} onclick={closeMobileMenu}></button>
    <div id="public-mobile-navigation" class="absolute inset-y-0 end-0 flex w-[min(24rem,90vw)] flex-col overflow-y-auto overscroll-contain bg-white px-5 pb-[calc(1.25rem+var(--safe-bottom))] pt-[calc(1.25rem+var(--safe-top))] shadow-2xl" role="dialog" aria-modal="true" aria-label={publicCopy.nav.menu}>
      <div class="flex items-center justify-between border-b border-slate-200 pb-4">
        <div class="flex items-center gap-3">
          <img src="/chh-logo-master.png" alt="" class="h-10 w-10 rounded-xl object-contain" />
          <span class="text-base font-black text-slate-950">{publicCopy.nav.menu}</span>
        </div>
        <button type="button" class="grid h-11 w-11 place-items-center rounded-xl text-slate-700 transition hover:bg-slate-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-hero" aria-label={publicCopy.nav.closeMenu} onclick={closeMobileMenu}><span aria-hidden="true" class="text-2xl leading-none">×</span></button>
      </div>

      <div class="mt-5">
        <LanguageSelector />
      </div>

      <nav class="mt-5 flex flex-col gap-2" aria-label={publicCopy.nav.menu}>
        <a href="/features" onclick={closeMobileMenu} class="public-mobile-link" aria-current={$page.url.pathname === '/features' ? 'page' : undefined}>{publicCopy.nav.product}</a>
        <a href="/how-it-works" onclick={closeMobileMenu} class="public-mobile-link" aria-current={$page.url.pathname === '/how-it-works' ? 'page' : undefined}>{publicCopy.nav.howItWorks}</a>
        <a href="/schools" onclick={closeMobileMenu} class="public-mobile-link" aria-current={$page.url.pathname === '/schools' ? 'page' : undefined}>{publicCopy.nav.schools}</a>
        <a href="/family-connection" onclick={closeMobileMenu} class="public-mobile-link" aria-current={$page.url.pathname === '/family-connection' ? 'page' : undefined}>{publicCopy.nav.familyConnection}</a>
        <a href="/faq" onclick={closeMobileMenu} class="public-mobile-link" aria-current={$page.url.pathname === '/faq' ? 'page' : undefined}>{publicCopy.footer.faq}</a>
        <a href="/contact" onclick={closeMobileMenu} class="public-mobile-link" aria-current={$page.url.pathname === '/contact' ? 'page' : undefined}>{publicCopy.footer.contact}</a>
      </nav>

      <div class="mt-6 border-t border-slate-200 pt-5">
        <a href={currentUser ? dashboardHref : '/login'} onclick={closeMobileMenu} class="inline-flex min-h-12 w-full items-center justify-center rounded-2xl border border-slate-200 bg-white px-5 py-3 font-bold text-slate-800 transition hover:border-violet-300 hover:text-violet-700">
          {currentUser ? publicCopy.nav.dashboard : publicCopy.nav.staffLogin}
        </a>
        <a href="/pilot" onclick={closeMobileMenu} class="mt-3 inline-flex min-h-12 w-full items-center justify-center rounded-2xl bg-slate-950 px-5 py-3 font-bold text-white transition hover:bg-violet-800">
          {publicCopy.nav.requestPilot}
        </a>
      </div>
    </div>
  </div>
{:else if currentUser && mobileMenuOpen}
  <div class="xl:hidden fixed inset-0 z-[100]" role="presentation">
    <button type="button" class="absolute inset-0 h-full w-full bg-slate-950/45" aria-label={$_('nav.closeMenu')} onclick={closeMobileMenu}></button>
    <div id="mobile-navigation" class="absolute inset-y-0 end-0 flex w-[min(22rem,88vw)] flex-col overflow-y-auto overscroll-contain bg-white px-5 pb-[calc(1.25rem+var(--safe-bottom))] pt-[calc(1.25rem+var(--safe-top))] shadow-2xl" role="dialog" aria-modal="true" aria-label={$_('nav.menu')}>
      <div class="flex items-center justify-between border-b border-slate-200 pb-4">
        <span class="text-lg font-bold text-slate-900">{$_('nav.menu')}</span>
        <button type="button" class="rounded-xl p-2 text-slate-700 transition hover:bg-slate-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-hero" aria-label={$_('nav.closeMenu')} onclick={closeMobileMenu}><span aria-hidden="true" class="text-2xl leading-none">×</span></button>
      </div>
      <div class="mt-5">
        <LanguageSelector />
      </div>
      <nav class="mt-5 flex flex-col gap-2" aria-label={$_('nav.menu')}>
        {#each navigationItems as item (item.id)}
          <a
            href={item.href}
            onclick={closeMobileMenu}
            class={mobileNavigationClass(item)}
            aria-current={mobileNavigationItemIsCurrent(item) ? 'page' : undefined}
          >
            <span>{$_(item.labelKey)}</span>
            {#if item.id === 'messages' && messagingUnread > 0}
              <span class="rounded-full bg-hero px-2 py-0.5 text-xs text-white" aria-label={$_('messaging.unreadCount', { values: { count: messagingUnread } })}>{messagingUnread > 99 ? '99+' : messagingUnread}</span>
            {/if}
          </a>
        {/each}
      </nav>
      {#if schoolSetupNavigationVisible}
        <section class="mt-6 border-t border-slate-200 pt-5" aria-labelledby="mobile-school-setup-title">
          <h2 id="mobile-school-setup-title" class="text-sm font-black uppercase tracking-wide text-slate-900">{$_('nav.school')}</h2>
          <nav class="mt-4 space-y-5" aria-label={$_('school.menu.navigationLabel')}>
            {#each SCHOOL_MENU_GROUPS as group}
              <section aria-labelledby={`mobile-school-menu-${group.key}`}>
                <h3 id={`mobile-school-menu-${group.key}`} class="px-3 text-xs font-bold uppercase tracking-wide text-slate-500">{$_(group.label)}</h3>
                <div class="mt-1 space-y-1">
                  {#each group.items as item}
                    <a
                      href={item.type === 'tab' ? schoolSetupTabHref(item.key) : item.href}
                      onclick={closeMobileMenu}
                      class={mobileSchoolSetupItemClass(item)}
                      aria-current={schoolSetupItemIsCurrent(item) ? 'page' : undefined}
                    >
                      <span>{$_(item.label)}</span>
                      {#if item.type === 'shortcut'}
                        <span class="shrink-0 rounded-full border border-slate-200 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-500">{$_('school.menu.shortcut')}</span>
                      {/if}
                    </a>
                  {/each}
                </div>
              </section>
            {/each}
          </nav>
        </section>
      {/if}
      {#if nativePushStatus}
        <section class="mt-5 rounded-2xl border border-slate-200 bg-slate-50 p-4">
          <p class="text-sm font-black text-slate-900">{$_('pushNotifications.title')}</p>
          <p class="mt-1 text-xs text-slate-600">
            {nativePushStatus === 'enabled' ? $_('pushNotifications.enabled') : nativePushStatus === 'denied' ? $_('pushNotifications.denied') : $_('pushNotifications.disabled')}
          </p>
          {#if nativePushStatus === 'disabled'}
            <button type="button" class="btn-secondary mt-3 rounded-xl px-3 py-2 text-xs" disabled={changingPush} onclick={enableNativePush}>{$_('pushNotifications.enable')}</button>
          {:else if nativePushStatus === 'enabled'}
            <button type="button" class="btn-secondary mt-3 rounded-xl px-3 py-2 text-xs" disabled={changingPush} onclick={disableNativePush}>{$_('pushNotifications.disable')}</button>
          {/if}
        </section>
      {/if}
      <button onclick={handleLogout} class="btn-hero mt-auto rounded-2xl px-5 py-3 text-sm uppercase tracking-wide">{$_('nav.logout')}</button>
    </div>
  </div>
{/if}

<style>
  :global(body.mobile-menu-open) { overflow: hidden; }
  .public-nav-link { min-height: 2.75rem; display: inline-flex; align-items: center; border-radius: .75rem; padding: .55rem .7rem; color: #475569; font-size: .8125rem; font-weight: 700; transition: color .2s, background-color .2s; }
  .public-nav-link:hover,
  .public-nav-link:focus-visible,
  .public-nav-link[aria-current='page'] { background: rgb(124 58 237 / .08); color: #6d28d9; outline: none; }
  .public-nav-link:focus-visible { box-shadow: 0 0 0 2px white, 0 0 0 4px #7c3aed; }
  .public-mobile-link { min-height: 3rem; display: flex; align-items: center; border-radius: .9rem; padding: .8rem 1rem; color: #334155; font-size: .95rem; font-weight: 700; }
  .public-mobile-link:hover,
  .public-mobile-link:focus-visible,
  .public-mobile-link[aria-current='page'] { background: rgb(124 58 237 / .08); color: #6d28d9; outline: none; }
  .footer-link { color: #94a3b8; transition: color .2s; }
  .footer-link:hover,
  .footer-link:focus-visible { color: #c4b5fd; outline: none; }
  .mobile-nav-link { border-radius: .9rem; padding: .9rem 1rem; color: #334155; font-size: .95rem; font-weight: 700; }
  .mobile-nav-link:hover, .mobile-nav-link:focus-visible { background: #f0fdf4; color: #0f766e; outline: none; }
  .mobile-nav-link-active,
  .mobile-nav-link-active:hover,
  .mobile-nav-link-active:focus-visible { background: rgb(139 92 246 / .1); color: #7c3aed; box-shadow: inset 0 0 0 1px rgb(139 92 246 / .2); }
  .mobile-school-link { min-height: 2.5rem; border-radius: .65rem; padding: .55rem .75rem; color: #334155; font-size: .875rem; font-weight: 600; }
  .mobile-school-link:hover, .mobile-school-link:focus-visible { background: #f8fafc; color: #7c3aed; outline: none; }
  .mobile-school-link-active,
  .mobile-school-link-active:hover,
  .mobile-school-link-active:focus-visible { background: rgb(139 92 246 / .1); color: #7c3aed; box-shadow: inset 0 0 0 1px rgb(139 92 246 / .2); }
  @media (max-width: 420px) {
    .brand-title > span:first-child { font-size: 1rem; }
    .brand-title > span:last-child { display: block; font-size: .6875rem; }
  }
</style>
