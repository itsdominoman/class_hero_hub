<script lang="ts">
  import '../app.css';
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { _ } from 'svelte-i18n';
  import { api } from '$lib/api';
  import { initI18n } from '$lib/i18n';
  import { errorStatus, messagingApi } from '$lib/messaging/api';
  import type { MessagingMembership } from '$lib/messaging/types';
  import { safeguardingApi } from '$lib/safeguarding/api';
  import type { SafeguardingMembership } from '$lib/safeguarding/types';
  import { clearNativeAccessToken, isNativePlatform } from '$lib/nativeAuth';
  import { defaultLandingPath, hasRole, type SessionUser } from '$lib/roleRouting';

  let { children } = $props();
  let currentUser = $state<SessionUser | null>(null);
  let mobileMenuOpen = $state(false);
  let messagingMemberships = $state<MessagingMembership[]>([]);
  let messagingAvailable = $state(false);
  let messagingUnread = $state(0);
  let safeguardingMemberships = $state<SafeguardingMembership[]>([]);
  // Capacitor exposes this synchronously before the app shell is hydrated.
  // Keep public website chrome out of the native shell while preserving it on web.
  let nativeApp = $state(isNativePlatform());
  let nativePushStatus = $state<'enabled' | 'disabled' | 'denied' | null>(null);
  let showPushExplanation = $state(false);
  let changingPush = $state(false);

  if (nativeApp && typeof document !== 'undefined') {
    document.documentElement.classList.add('native-app');
  }

  async function loadSession() {
    try {
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
      if (nativeApp) await clearNativeAccessToken();
      currentUser = null;
      messagingMemberships = [];
      safeguardingMemberships = [];
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

  onMount(() => {
    void loadSession();
    let disposed = false;
    let removeNativeBackHandler: (() => Promise<void>) | null = null;
    const onKeydown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') closeMobileMenu();
    };
    const onNativeBack = (event: Event) => {
      const active = document.activeElement;
      const editable =
        active instanceof HTMLInputElement ||
        active instanceof HTMLTextAreaElement ||
        (active instanceof HTMLElement && active.isContentEditable);
      if (editable) {
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
      window.removeEventListener('chh:native-back', onNativeBack, { capture: true });
      clearInterval(badgeTimer);
      document.body.classList.remove('mobile-menu-open');
      document.documentElement.classList.remove('native-app');
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
      ? `/school/safeguarding/message-reviews?membership=${safeguardingMemberships[0].membership_id}`
      : '/school/safeguarding/message-reviews'
  );
  // Messaging already owns a bounded viewport and its single bottom inset at the
  // sticky composer. Every other native route gets the bottom inset from app-main.
  let messagingRoute = $derived($page.url.pathname.startsWith('/messages'));
</script>

<div class="app-shell min-h-dvh max-w-full overflow-x-hidden flex flex-col">
  <header class="app-header bg-white/80 backdrop-blur-xl sticky top-0 z-50 shrink-0 border-b border-slate-200/50 shadow-sm pt-[var(--safe-top)]">
    <div class="max-w-7xl mx-auto px-3 sm:px-4 min-h-20 py-3 flex items-center justify-between gap-3">
      <a href="/" class="flex min-w-0 items-center gap-3 group">
        <img src="/chh-logo-master.png" alt={$_('app.name')} class="h-11 w-11 shrink-0 rounded-2xl object-contain shadow-xl shadow-hero/30 transition-all duration-300 group-hover:rotate-6 sm:h-12 sm:w-12" />
        <div class="brand-title flex min-w-0 flex-col -space-y-1">
          <span class="text-lg font-bold uppercase leading-none tracking-tighter text-slate-900 sm:text-2xl">{$_('app.classHero')}</span>
          <span class="text-xs font-bold uppercase leading-none tracking-wide text-hero opacity-80">{$_('app.hub')}</span>
        </div>
      </a>
      
      <nav class="hidden md:flex items-center gap-8">
        {#if !currentUser}
          <a href="/login" class="text-sm font-bold text-slate-500 hover:text-hero uppercase tracking-wide transition-colors">
            {$_('nav.login')}
          </a>
        {:else}
          {#if hasGuardian}
            <a href="/parent" class="text-sm font-bold text-slate-500 hover:text-hero uppercase tracking-wide transition-colors">
              {$_('nav.family')}
            </a>
          {/if}
          {#if currentUser.is_platform_admin}
            <a href="/platform" class="text-sm font-bold text-slate-500 hover:text-hero uppercase tracking-wide transition-colors">
              {$_('nav.admin')}
            </a>
          {/if}
          {#if hasSchoolAdmin}
            <a href="/school" class="text-sm font-bold text-slate-500 hover:text-hero uppercase tracking-wide transition-colors">
              {$_('nav.school')}
            </a>
            <a href="/school/reports" class="text-sm font-bold text-slate-500 hover:text-hero uppercase tracking-wide transition-colors">
              {$_('nav.reports')}
            </a>
          {/if}
          {#if hasTeacher}
            <a href="/teach" class="text-sm font-bold text-slate-500 hover:text-hero uppercase tracking-wide transition-colors">
              {$_('nav.teach')}
            </a>
          {/if}
          {#if messagingAvailable}
            <a href="/messages" class="relative text-sm font-bold text-slate-500 hover:text-hero uppercase tracking-wide transition-colors">
              {$_('nav.messages')}
              {#if messagingUnread > 0}
                <span class="absolute -right-3 -top-3 grid min-w-5 place-items-center rounded-full bg-hero px-1 text-[0.6rem] leading-5 text-white" aria-label={$_('messaging.unreadCount', { values: { count: messagingUnread } })}>{messagingUnread > 99 ? '99+' : messagingUnread}</span>
              {/if}
            </a>
          {/if}
          {#if safeguardingMemberships.length > 0}
            <a href={safeguardingHref} class="text-sm font-bold text-slate-500 hover:text-amber-700 uppercase tracking-wide transition-colors">
              {$_('nav.safeguarding')}
            </a>
          {/if}
          {#if !hasAnyRole}
            <a href={dashboardHref} class="text-sm font-bold text-slate-500 hover:text-hero uppercase tracking-wide transition-colors">
              {$_('nav.dashboard')}
            </a>
          {/if}
          <button onclick={handleLogout} class="btn-hero px-6 py-3 rounded-2xl text-sm uppercase tracking-wide">{$_('nav.logout')}</button>
        {/if}
      </nav>

      {#if currentUser}
        <button
          type="button"
          class="md:hidden inline-flex shrink-0 items-center justify-center rounded-2xl border border-slate-200 bg-white p-3 text-slate-700 shadow-sm transition hover:border-hero hover:text-hero"
          aria-label={mobileMenuOpen ? $_('nav.closeMenu') : $_('nav.openMenu')}
          aria-expanded={mobileMenuOpen}
          aria-controls="mobile-navigation"
          onclick={toggleMobileMenu}
        >
          <span aria-hidden="true" class="text-xl leading-none">{mobileMenuOpen ? '×' : '☰'}</span>
        </button>
      {:else}
        <a href="/login" class="md:hidden inline-flex shrink-0 items-center justify-center rounded-full bg-slate-900 px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-white shadow-sm">
          {$_('nav.login')}
        </a>
      {/if}
    </div>
</header>

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

  {#if !nativeApp}
  <footer class="bg-slate-900 text-slate-400 pt-16 pb-[calc(4rem+var(--safe-bottom))] md:pt-20 mt-16 md:mt-20 relative overflow-hidden">
    <div class="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-hero/50 to-transparent"></div>
    <div class="max-w-7xl mx-auto px-4">
      <div class="grid gap-10 lg:grid-cols-[1.1fr_0.9fr] lg:gap-12">
        <div class="text-left">
          <div class="flex items-center gap-3 mb-6 opacity-50 grayscale">
            <img src="/chh-logo-master.png" alt={$_('app.name')} class="h-10 w-10 rounded-xl bg-white object-contain" />
            <span class="text-xl font-bold tracking-tighter text-white uppercase">{$_('app.name')}</span>
          </div>
          <p class="text-lg leading-relaxed max-w-md">{$_('footer.description')}</p>
          <p class="mt-6 text-sm font-semibold uppercase tracking-wide text-white">{$_('footer.tagline')}</p>
        </div>

        <div class="grid gap-8 sm:grid-cols-3">
          <div class="min-w-0">
            <p class="text-white font-semibold uppercase tracking-wide text-sm mb-4">{$_('nav.product')}</p>
            <div class="flex flex-col gap-3 text-sm font-semibold">
              <a href="/" class="hover:text-hero transition-colors">{$_('nav.home')}</a>
              <a href="/#how-it-works" class="hover:text-hero transition-colors">{$_('nav.howItWorks')}</a>
              <a href="/faq" class="hover:text-hero transition-colors">{$_('nav.faq')}</a>
            </div>
          </div>

          <div class="min-w-0">
            <p class="text-white font-semibold uppercase tracking-wide text-sm mb-4">{$_('nav.support')}</p>
            <div class="flex flex-col gap-3 text-sm font-semibold">
              <a href="/contact" class="hover:text-hero transition-colors">{$_('nav.contact')}</a>
              <a href="/safety-privacy" class="hover:text-hero transition-colors">{$_('nav.safetyPrivacy')}</a>
            </div>
          </div>

          <div class="min-w-0">
            <p class="text-white font-semibold uppercase tracking-wide text-sm mb-4">{$_('nav.legal')}</p>
            <div class="flex flex-col gap-3 text-sm font-semibold">
              <a href="/privacy" class="hover:text-hero transition-colors">{$_('nav.privacyPolicy')}</a>
              <a href="/terms" class="hover:text-hero transition-colors">{$_('nav.terms')}</a>
            </div>
          </div>
        </div>
      </div>
    </div>
  </footer>
  {/if}
</div>

{#if currentUser && mobileMenuOpen}
  <div class="md:hidden fixed inset-0 z-[100]" role="presentation">
    <button type="button" class="absolute inset-0 h-full w-full bg-slate-950/45" aria-label={$_('nav.closeMenu')} onclick={closeMobileMenu}></button>
    <div id="mobile-navigation" class="absolute inset-y-0 right-0 flex w-[min(22rem,88vw)] flex-col overflow-y-auto bg-white px-5 pb-[calc(1.25rem+var(--safe-bottom))] pt-[calc(1.25rem+var(--safe-top))] shadow-2xl" role="dialog" aria-modal="true" aria-label={$_('nav.menu')}>
      <div class="flex items-center justify-between border-b border-slate-200 pb-4">
        <span class="text-lg font-bold text-slate-900">{$_('nav.menu')}</span>
        <button type="button" class="rounded-xl p-2 text-slate-700 transition hover:bg-slate-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-hero" aria-label={$_('nav.closeMenu')} onclick={closeMobileMenu}><span aria-hidden="true" class="text-2xl leading-none">×</span></button>
      </div>
      <nav class="mt-5 flex flex-col gap-2" aria-label={$_('nav.menu')}>
        {#if hasGuardian}<a href="/parent" onclick={closeMobileMenu} class="mobile-nav-link">{$_('nav.family')}</a>{/if}
        {#if currentUser.is_platform_admin}<a href="/platform" onclick={closeMobileMenu} class="mobile-nav-link">{$_('nav.admin')}</a>{/if}
        {#if hasSchoolAdmin}
          <a href="/school" onclick={closeMobileMenu} class="mobile-nav-link">{$_('nav.school')}</a>
          <a href="/school/reports" onclick={closeMobileMenu} class="mobile-nav-link">{$_('nav.reports')}</a>
        {/if}
        {#if hasTeacher}<a href="/teach" onclick={closeMobileMenu} class="mobile-nav-link">{$_('nav.teach')}</a>{/if}
        {#if messagingAvailable}
          <a href="/messages" onclick={closeMobileMenu} class="mobile-nav-link flex items-center justify-between gap-3">
            <span>{$_('nav.messages')}</span>
            {#if messagingUnread > 0}<span class="rounded-full bg-hero px-2 py-0.5 text-xs text-white" aria-label={$_('messaging.unreadCount', { values: { count: messagingUnread } })}>{messagingUnread > 99 ? '99+' : messagingUnread}</span>{/if}
          </a>
        {/if}
        {#if safeguardingMemberships.length > 0}<a href={safeguardingHref} onclick={closeMobileMenu} class="mobile-nav-link">{$_('nav.safeguarding')}</a>{/if}
        {#if !hasAnyRole}<a href={dashboardHref} onclick={closeMobileMenu} class="mobile-nav-link">{$_('nav.dashboard')}</a>{/if}
      </nav>
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
  .mobile-nav-link { border-radius: .9rem; padding: .9rem 1rem; color: #334155; font-size: .95rem; font-weight: 700; }
  .mobile-nav-link:hover, .mobile-nav-link:focus-visible { background: #f0fdf4; color: #0f766e; outline: none; }
  @media (max-width: 420px) {
    .brand-title > span:first-child { font-size: 1rem; }
    .brand-title > span:last-child { display: block; font-size: .6875rem; }
  }
</style>
