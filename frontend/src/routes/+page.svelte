<script lang="ts">
  import { onMount } from "svelte";
  import { locale } from "svelte-i18n";
  import { api } from "$lib/api";
  import { isNativePlatform } from "$lib/nativeAuth";
  import { defaultLandingPath, type SessionUser } from "$lib/roleRouting";
  import { getPublicSiteCopy } from "$lib/publicSite";
  import {
    ArrowRight,
    BarChart3,
    BookOpenCheck,
    CalendarDays,
    CheckCircle2,
    ClipboardCheck,
    Database,
    FileCheck2,
    Globe2,
    HeartHandshake,
    Languages,
    LockKeyhole,
    MessageSquareText,
    Network,
    School,
    ShieldCheck,
    Sparkles,
  } from "lucide-svelte";

  let authenticated = $state(false);
  let sessionLoaded = $state(false);
  let sessionUser = $state<SessionUser | null>(null);
  let nativeApp = $state(isNativePlatform());
  let siteCopy = $derived(getPublicSiteCopy($locale));
  let copy = $derived(siteCopy.home);
  let faqPreview = $derived(siteCopy.faq.items.slice(0, 6));

  onMount(async () => {
    if (nativeApp) {
      try {
        sessionUser = await api.get("/me");
        window.location.replace(defaultLandingPath(sessionUser));
      } catch {
        window.location.replace("/login");
      }
      return;
    }

    try {
      sessionUser = await api.get("/me");
      authenticated = true;
    } catch {
      authenticated = false;
      sessionUser = null;
    } finally {
      sessionLoaded = true;
    }
  });

  let primaryCtaHref = $derived(
    sessionLoaded && authenticated ? defaultLandingPath(sessionUser) : "/pilot",
  );
  let primaryCtaLabel = $derived(
    sessionLoaded && authenticated ? siteCopy.nav.dashboard : copy.primaryCta,
  );

  const benefitIcons = [
    BookOpenCheck,
    MessageSquareText,
    Sparkles,
    HeartHandshake,
  ];
  const featureIcons = [BarChart3, Database];
  const trustIcons = [LockKeyhole, HeartHandshake, FileCheck2, BarChart3];
</script>

<svelte:head>
  <title>{copy.pageTitle}</title>
  <meta name="description" content={copy.metaDescription} />
  <meta property="og:title" content={copy.pageTitle} />
  <meta property="og:description" content={copy.metaDescription} />
  <meta property="og:type" content="website" />
  <meta property="og:url" content="https://class.familyherohub.com/" />
  <meta
    property="og:image"
    content="https://class.familyherohub.com/chh-logo-master.png"
  />
  <meta name="twitter:card" content="summary" />
</svelte:head>

{#if nativeApp}
  <div class="min-h-[calc(100dvh-5rem)]" aria-busy="true"></div>
{:else}
  <div class="public-surface overflow-hidden">
    <section
      class="relative border-b border-slate-200/70 bg-gradient-to-b from-white via-violet-50/45 to-white px-4 py-14 sm:py-18 lg:py-24"
    >
      <div
        class="absolute left-1/2 top-0 h-[32rem] w-[52rem] -translate-x-1/2 rounded-full bg-violet-200/30 blur-3xl"
      ></div>
      <div
        class="relative mx-auto grid max-w-7xl gap-12 lg:grid-cols-[1.02fr_0.98fr] lg:items-center"
      >
        <div class="text-start">
          <p
            class="inline-flex items-center gap-2 rounded-full border border-violet-200 bg-white/90 px-4 py-2 text-xs font-black uppercase tracking-[0.16em] text-violet-700 shadow-sm"
          >
            <Sparkles class="h-4 w-4" aria-hidden="true" />
            {copy.eyebrow}
          </p>
          <h1
            class="mt-7 max-w-3xl text-4xl font-black leading-[0.98] tracking-tight text-slate-950 sm:text-5xl md:text-6xl lg:text-7xl"
          >
            {copy.heading}
          </h1>
          <p
            class="mt-7 max-w-2xl text-lg leading-relaxed text-slate-600 sm:text-xl md:text-2xl"
          >
            {copy.intro}
          </p>

          <div class="mt-9 flex flex-col gap-3 sm:flex-row">
            <a
              href={primaryCtaHref}
              class="btn-hero inline-flex min-h-14 items-center justify-center gap-3 rounded-2xl px-7 py-4 text-base sm:text-lg"
            >
              {primaryCtaLabel}
              <ArrowRight class="h-5 w-5 rtl:rotate-180" aria-hidden="true" />
            </a>
            <a
              href="/features"
              class="btn-secondary inline-flex min-h-14 items-center justify-center rounded-2xl px-7 py-4 text-base font-bold sm:text-lg"
            >
              {copy.secondaryCta}
            </a>
          </div>

          <p
            class="mt-5 max-w-2xl text-sm font-semibold leading-relaxed text-slate-500"
          >
            {copy.strapline}
          </p>
        </div>

        <div class="relative mx-auto w-full max-w-xl lg:max-w-none">
          <div
            class="absolute -left-10 -top-8 h-36 w-36 rounded-full bg-emerald-300/30 blur-2xl"
          ></div>
          <div
            class="relative rounded-[2rem] border border-white bg-white/95 p-4 shadow-2xl shadow-slate-950/10 sm:p-6"
          >
            <div
              class="flex items-center justify-between gap-4 border-b border-slate-100 pb-4"
            >
              <div class="flex items-center gap-3">
                <div
                  class="grid h-11 w-11 place-items-center rounded-2xl bg-violet-100 text-violet-700"
                >
                  <School class="h-6 w-6" aria-hidden="true" />
                </div>
                <div>
                  <p
                    class="text-xs font-black uppercase tracking-[0.14em] text-slate-400"
                  >
                    Class Hero Hub
                  </p>
                  <p class="mt-1 font-black text-slate-900">
                    {copy.schoolWorkspaceLabel}
                  </p>
                </div>
              </div>
              <span
                class="rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-800"
                >EN · AR</span
              >
            </div>

            <div class="mt-5 grid gap-4 sm:grid-cols-2">
              <article
                class="rounded-[1.5rem] border border-slate-200 bg-slate-50 p-5 text-start sm:col-span-2"
              >
                <div class="flex items-center gap-3">
                  <div
                    class="grid h-10 w-10 place-items-center rounded-xl bg-violet-700 text-white"
                  >
                    <ClipboardCheck class="h-5 w-5" aria-hidden="true" />
                  </div>
                  <div>
                    <p
                      class="text-xs font-black uppercase tracking-[0.14em] text-violet-700"
                    >
                      {copy.schoolWorkspaceLabel}
                    </p>
                    <h2 class="mt-1 text-lg font-black text-slate-900">
                      {copy.schoolWorkspaceTitle}
                    </h2>
                  </div>
                </div>
                <p class="mt-3 text-sm leading-relaxed text-slate-600">
                  {copy.schoolWorkspaceText}
                </p>
              </article>

              <article
                class="rounded-[1.5rem] border border-emerald-100 bg-emerald-50 p-5 text-start"
              >
                <div class="flex items-center gap-2 text-emerald-700">
                  <HeartHandshake class="h-5 w-5" aria-hidden="true" />
                  <p class="text-xs font-black uppercase tracking-[0.14em]">
                    {copy.familyDeliveryLabel}
                  </p>
                </div>
                <h2 class="mt-3 text-lg font-black text-slate-900">
                  {copy.familyDeliveryTitle}
                </h2>
                <p class="mt-2 text-sm leading-relaxed text-slate-600">
                  {copy.familyDeliveryText}
                </p>
              </article>

              <article
                class="rounded-[1.5rem] bg-slate-950 p-5 text-start text-white"
              >
                <div class="flex items-center gap-2 text-violet-300">
                  <ShieldCheck class="h-5 w-5" aria-hidden="true" />
                  <p class="text-xs font-black uppercase tracking-[0.14em]">
                    {copy.boundaryLabel}
                  </p>
                </div>
                <p
                  class="mt-3 text-sm font-semibold leading-relaxed text-slate-200"
                >
                  {copy.boundaryText}
                </p>
              </article>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="bg-white px-4 py-16 sm:py-20 lg:py-24">
      <div class="mx-auto max-w-7xl">
        <div class="max-w-3xl text-start">
          <p
            class="text-xs font-black uppercase tracking-[0.16em] text-violet-700"
          >
            {copy.benefitsEyebrow}
          </p>
          <h2
            class="mt-4 text-3xl font-black leading-tight text-slate-950 sm:text-4xl lg:text-5xl"
          >
            {copy.benefitsHeading}
          </h2>
          <p class="mt-5 text-lg leading-relaxed text-slate-600">
            {copy.benefitsIntro}
          </p>
        </div>

        <div class="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {#each copy.benefits as benefit, index}
            {@const Icon = benefitIcons[index]}
            <article
              class="group rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm transition duration-300 hover:-translate-y-1 hover:border-violet-200 hover:shadow-xl hover:shadow-violet-950/5"
            >
              <div
                class="grid h-12 w-12 place-items-center rounded-2xl bg-violet-100 text-violet-700 transition group-hover:bg-violet-700 group-hover:text-white"
              >
                <Icon class="h-6 w-6" aria-hidden="true" />
              </div>
              <h3 class="mt-5 text-xl font-black text-slate-900">
                {benefit.title}
              </h3>
              <p class="mt-3 text-sm leading-relaxed text-slate-600">
                {benefit.text}
              </p>
            </article>
          {/each}
        </div>
      </div>
    </section>

    <section class="bg-slate-950 px-4 py-16 text-white sm:py-20 lg:py-24">
      <div class="mx-auto max-w-7xl">
        <div class="grid gap-10 lg:grid-cols-[0.82fr_1.18fr] lg:items-start">
          <div class="text-start">
            <p
              class="text-xs font-black uppercase tracking-[0.16em] text-violet-300"
            >
              {copy.familyEyebrow}
            </p>
            <h2
              class="mt-4 text-3xl font-black leading-tight sm:text-4xl lg:text-5xl"
            >
              {copy.familyHeading}
            </h2>
            <p class="mt-5 text-lg leading-relaxed text-slate-300">
              {copy.familyIntro}
            </p>
            <p
              class="mt-7 rounded-2xl border border-violet-400/30 bg-violet-400/10 p-5 font-semibold leading-relaxed text-violet-100"
            >
              {copy.familyBoundary}
            </p>
            <a
              class="mt-7 inline-flex min-h-12 items-center justify-center gap-2 rounded-2xl bg-white px-6 py-3 font-bold text-slate-950 transition hover:bg-violet-100"
              href="/family-connection"
            >
              {copy.familyCta}
              <ArrowRight class="h-5 w-5 rtl:rotate-180" aria-hidden="true" />
            </a>
          </div>

          <div class="grid gap-4">
            <article
              class="rounded-[1.75rem] border border-white/10 bg-white/5 p-6 text-start"
            >
              <div class="flex items-start gap-4">
                <div
                  class="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-violet-500 text-white"
                >
                  <School class="h-6 w-6" aria-hidden="true" />
                </div>
                <div>
                  <h3 class="text-xl font-black">{copy.schoolSideTitle}</h3>
                  <p class="mt-2 leading-relaxed text-slate-300">
                    {copy.schoolSideText}
                  </p>
                </div>
              </div>
            </article>
            <div
              class="grid place-items-center text-violet-300"
              aria-hidden="true"
            >
              <span class="text-2xl">↓</span>
            </div>
            <article
              class="rounded-[1.75rem] border border-emerald-400/20 bg-emerald-400/10 p-6 text-start"
            >
              <div class="flex items-start gap-4">
                <div
                  class="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-emerald-500 text-slate-950"
                >
                  <Network class="h-6 w-6" aria-hidden="true" />
                </div>
                <div>
                  <h3 class="text-xl font-black">{copy.connectionTitle}</h3>
                  <p class="mt-2 leading-relaxed text-emerald-50">
                    {copy.connectionText}
                  </p>
                </div>
              </div>
            </article>
            <div
              class="grid place-items-center text-violet-300"
              aria-hidden="true"
            >
              <span class="text-2xl">↓</span>
            </div>
            <article
              class="rounded-[1.75rem] border border-white/10 bg-white/5 p-6 text-start"
            >
              <div class="flex items-start gap-4">
                <div
                  class="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-white text-violet-700"
                >
                  <HeartHandshake class="h-6 w-6" aria-hidden="true" />
                </div>
                <div>
                  <h3 class="text-xl font-black">{copy.familySideTitle}</h3>
                  <p class="mt-2 leading-relaxed text-slate-300">
                    {copy.familySideText}
                  </p>
                </div>
              </div>
            </article>
          </div>
        </div>
      </div>
    </section>

    <section
      class="border-y border-slate-200/70 bg-slate-50 px-4 py-16 sm:py-20 lg:py-24"
    >
      <div class="mx-auto max-w-7xl">
        <div class="max-w-4xl text-start">
          <p
            class="text-xs font-black uppercase tracking-[0.16em] text-violet-700"
          >
            {copy.proofEyebrow}
          </p>
          <h2
            class="mt-4 text-3xl font-black leading-tight text-slate-950 sm:text-4xl lg:text-5xl"
          >
            {copy.proofHeading}
          </h2>
          <p class="mt-5 max-w-3xl text-lg leading-relaxed text-slate-600">
            {copy.proofIntro}
          </p>
          <p
            class="mt-4 inline-flex rounded-full border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm font-bold text-emerald-800"
          >
            {copy.proofDataNote}
          </p>
        </div>

        <div class="mt-10 grid gap-8">
          {#each copy.proofItems as item}
            <figure
              class="overflow-hidden rounded-[2rem] border border-slate-200 bg-white shadow-xl shadow-slate-950/5"
            >
              <a
                href={item.src}
                aria-label={item.alt}
                class="block overflow-hidden border-b border-slate-200 bg-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-violet-700"
              >
                <img
                  src={item.src}
                  alt={item.alt}
                  width="1440"
                  height={item.height}
                  loading="lazy"
                  class="block h-auto w-full transition duration-500 hover:scale-[1.015]"
                />
              </a>
              <figcaption class="p-6 text-start sm:p-7">
                <p
                  class="text-xs font-black uppercase tracking-[0.16em] text-violet-700"
                >
                  {item.eyebrow}
                </p>
                <h3 class="mt-3 text-2xl font-black text-slate-950">
                  {item.title}
                </h3>
                <p class="mt-3 leading-relaxed text-slate-600">{item.text}</p>
              </figcaption>
            </figure>
          {/each}
        </div>
      </div>
    </section>

    <section class="bg-white px-4 py-16 sm:py-20 lg:py-24">
      <div class="mx-auto max-w-7xl">
        <div class="max-w-4xl text-start">
          <p
            class="text-xs font-black uppercase tracking-[0.16em] text-violet-700"
          >
            {copy.featureEyebrow}
          </p>
          <h2
            class="mt-4 text-3xl font-black leading-tight text-slate-950 sm:text-4xl lg:text-5xl"
          >
            {copy.featureHeading}
          </h2>
          <p class="mt-5 max-w-3xl text-lg leading-relaxed text-slate-600">
            {copy.featureIntro}
          </p>
        </div>

        <div class="mt-10 grid gap-5 lg:grid-cols-2">
          {#each copy.featureGroups as group, index}
            {@const Icon = featureIcons[index]}
            <article
              class="rounded-[2rem] border border-slate-200 bg-gradient-to-br from-white to-slate-50 p-6 text-start shadow-sm sm:p-8"
            >
              <div class="flex items-start gap-4">
                <div
                  class="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-violet-700 text-white"
                >
                  <Icon class="h-6 w-6" aria-hidden="true" />
                </div>
                <div>
                  <h3 class="text-2xl font-black text-slate-900">
                    {group.title}
                  </h3>
                  <p class="mt-2 leading-relaxed text-slate-600">
                    {group.text}
                  </p>
                </div>
              </div>
              <ul class="mt-6 grid gap-3 sm:grid-cols-2">
                {#each group.items as item}
                  <li
                    class="flex items-start gap-3 rounded-2xl border border-slate-200 bg-white p-4 text-sm font-semibold leading-relaxed text-slate-700"
                  >
                    <CheckCircle2
                      class="mt-0.5 h-5 w-5 shrink-0 text-emerald-600"
                      aria-hidden="true"
                    />
                    <span>{item}</span>
                  </li>
                {/each}
              </ul>
            </article>
          {/each}
        </div>

        <div class="mt-9 text-center">
          <a
            class="inline-flex min-h-12 items-center justify-center gap-2 rounded-2xl bg-slate-950 px-6 py-3 font-bold text-white transition hover:bg-violet-800"
            href="/features"
          >
            {siteCopy.footer.features}
            <ArrowRight class="h-5 w-5 rtl:rotate-180" aria-hidden="true" />
          </a>
        </div>
      </div>
    </section>

    <section class="bg-white px-4 py-16 sm:py-20 lg:py-24">
      <div class="mx-auto max-w-7xl">
        <div class="max-w-3xl text-start">
          <p
            class="text-xs font-black uppercase tracking-[0.16em] text-violet-700"
          >
            {copy.trustEyebrow}
          </p>
          <h2
            class="mt-4 text-3xl font-black leading-tight text-slate-950 sm:text-4xl lg:text-5xl"
          >
            {copy.trustHeading}
          </h2>
          <p class="mt-5 text-lg leading-relaxed text-slate-600">
            {copy.trustIntro}
          </p>
        </div>

        <div class="mt-10 grid gap-5 sm:grid-cols-2">
          {#each copy.trustItems as item, index}
            {@const Icon = trustIcons[index]}
            <article
              class="rounded-[1.75rem] border border-slate-200 bg-slate-50 p-6 text-start sm:p-7"
            >
              <div class="flex items-start gap-4">
                <div
                  class="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-white text-violet-700 shadow-sm"
                >
                  <Icon class="h-6 w-6" aria-hidden="true" />
                </div>
                <div>
                  <h3 class="text-xl font-black text-slate-900">
                    {item.title}
                  </h3>
                  <p class="mt-2 leading-relaxed text-slate-600">{item.text}</p>
                </div>
              </div>
            </article>
          {/each}
        </div>

        <div
          class="mt-10 grid gap-6 overflow-hidden rounded-[2rem] border border-violet-200 bg-violet-50 p-6 sm:p-8 lg:grid-cols-[0.7fr_1.3fr] lg:items-center"
        >
          <div
            class="flex items-center justify-center gap-4 rounded-[1.5rem] bg-white p-7 shadow-sm"
          >
            <Languages class="h-12 w-12 text-violet-700" aria-hidden="true" />
            <div class="text-start">
              <p class="text-2xl font-black text-slate-950">English</p>
              <p class="text-2xl font-black text-violet-700">العربية</p>
            </div>
          </div>
          <div class="text-start">
            <p
              class="text-xs font-black uppercase tracking-[0.16em] text-violet-700"
            >
              {copy.bilingualEyebrow}
            </p>
            <h3 class="mt-3 text-2xl font-black text-slate-950 sm:text-3xl">
              {copy.bilingualHeading}
            </h3>
            <p class="mt-3 leading-relaxed text-slate-700">
              {copy.bilingualText}
            </p>
            <ul class="mt-5 space-y-3">
              <li class="flex items-start gap-3">
                <Globe2
                  class="mt-0.5 h-5 w-5 shrink-0 text-emerald-600"
                  aria-hidden="true"
                /><span class="text-slate-700">{copy.bilingualPoint1}</span>
              </li>
              <li class="flex items-start gap-3">
                <CalendarDays
                  class="mt-0.5 h-5 w-5 shrink-0 text-emerald-600"
                  aria-hidden="true"
                /><span class="text-slate-700">{copy.bilingualPoint2}</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <section
      class="border-y border-slate-200/70 bg-slate-50 px-4 py-16 sm:py-20"
    >
      <div class="mx-auto max-w-5xl">
        <div class="mx-auto max-w-3xl text-center">
          <p
            class="text-xs font-black uppercase tracking-[0.16em] text-violet-700"
          >
            {copy.faqEyebrow}
          </p>
          <h2
            class="mt-4 text-3xl font-black leading-tight text-slate-950 sm:text-4xl"
          >
            {copy.faqHeading}
          </h2>
          <p class="mt-4 text-lg leading-relaxed text-slate-600">
            {copy.faqIntro}
          </p>
        </div>
        <div class="mt-10 grid gap-4 md:grid-cols-2">
          {#each faqPreview as item}
            <details
              class="group rounded-[1.5rem] border border-slate-200 bg-white p-5 text-start shadow-sm open:border-violet-200 open:shadow-md"
            >
              <summary
                class="flex cursor-pointer list-none items-start justify-between gap-4 font-black text-slate-900 marker:hidden"
              >
                <span>{item.question}</span>
                <span
                  class="text-xl font-light text-violet-600 transition group-open:rotate-45"
                  aria-hidden="true">+</span
                >
              </summary>
              <p class="mt-3 leading-relaxed text-slate-600">{item.answer}</p>
            </details>
          {/each}
        </div>
        <div class="mt-8 text-center">
          <a
            class="inline-flex min-h-12 items-center justify-center gap-2 rounded-2xl bg-slate-950 px-6 py-3 font-bold text-white transition hover:bg-violet-800"
            href="/faq"
            >{copy.faqCta}<ArrowRight
              class="h-5 w-5 rtl:rotate-180"
              aria-hidden="true"
            /></a
          >
        </div>
      </div>
    </section>

    <section class="px-4 py-16 sm:py-20">
      <div
        class="relative mx-auto max-w-7xl overflow-hidden rounded-[2.25rem] bg-gradient-to-br from-violet-700 via-violet-600 to-indigo-700 px-6 py-12 text-white shadow-2xl shadow-violet-900/20 sm:px-10 lg:px-14"
      >
        <div
          class="absolute -right-24 -top-24 h-72 w-72 rounded-full bg-white/10 blur-2xl"
        ></div>
        <div
          class="relative grid gap-8 lg:grid-cols-[1fr_auto] lg:items-center"
        >
          <div class="max-w-3xl text-start">
            <h2
              class="text-3xl font-black leading-tight sm:text-4xl lg:text-5xl"
            >
              {copy.finalHeading}
            </h2>
            <p class="mt-5 text-lg leading-relaxed text-violet-100">
              {copy.finalText}
            </p>
          </div>
          <div class="flex flex-col gap-3 sm:flex-row lg:flex-col">
            <a
              class="inline-flex min-h-12 items-center justify-center gap-2 rounded-2xl bg-white px-6 py-3 font-bold text-violet-800 transition hover:bg-violet-50"
              href="/pilot"
              >{copy.finalPrimary}<ArrowRight
                class="h-5 w-5 rtl:rotate-180"
                aria-hidden="true"
              /></a
            >
            <a
              class="inline-flex min-h-12 items-center justify-center rounded-2xl border border-white/25 bg-white/10 px-6 py-3 font-bold text-white transition hover:bg-white/15"
              href="/contact">{copy.finalSecondary}</a
            >
          </div>
        </div>
      </div>
    </section>
  </div>
{/if}
