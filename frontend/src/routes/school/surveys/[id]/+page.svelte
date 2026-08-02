<script lang="ts">
  import { onMount, tick } from "svelte";
  import { page } from "$app/stores";
  import { _, locale } from "svelte-i18n";
  import { api } from "$lib/api";
  import { surveyApi, type SurveyMembership } from "$lib/surveys/api";
  import {
    ArrowLeft,
    BellRing,
    Download,
    LockKeyhole,
    RotateCcw,
    XCircle,
    Archive,
    CheckCircle2,
  } from "lucide-svelte";

  let membership = $state<SurveyMembership | null>(null);
  let context = $state<any>(null);
  let survey = $state<any>(null);
  let results = $state<any>(null);
  let loading = $state(true);
  let busy = $state("");
  let error = $state("");
  let search = $state("");
  let reopenOpen = $state(false);
  let reopenClosesAt = $state("");
  let reopenError = $state("");
  let reopenInput = $state<HTMLInputElement | null>(null);
  let reopenButton = $state<HTMLButtonElement | null>(null);
  let ar = $derived($locale === "ar");
  let t = $derived({
    back: $_("surveyManagement.back"),
    results: $_("surveyManagement.results"),
    comments: $_("surveyManagement.comments"),
    publish: $_("surveyManagement.publish"),
    close: $_("surveyManagement.close"),
    reopen: $_("surveyManagement.reopen"),
    archive: $_("surveyManagement.archive"),
    remind: $_("surveyManagement.sendReminder"),
    export: $_("surveyManagement.exportCsv"),
    noComments: $_("surveyManagement.noComments"),
    anonymous: $_("surveyManagement.anonymous"),
    identified: $_("surveyManagement.identified"),
    reopenTitle: $_("surveyManagement.reopenTitle"),
    reopenHelp: $_("surveyManagement.reopenHelp"),
    newClosingTime: $_("surveyManagement.newClosingTime"),
    cancel: $_("surveyManagement.cancel"),
    reopening: $_("surveyManagement.reopening"),
  });

  function statusLabel(value: string) {
    return ar ? $_(`surveyManagement.statuses.${value}`) : value;
  }

  function reminderStatusLabel(value: string) {
    return ar ? $_(`surveyManagement.reminderStatuses.${value}`) : value;
  }

  function questionTypePresentation(value: string) {
    return ar ? $_(`surveyManagement.types.${value}`) : value.replaceAll("_", " ");
  }

  async function resolveMembership() {
    const session = await api.get("/me");
    const requested = Number($page.url.searchParams.get("membership"));
    const admins = (session.memberships || []).filter(
      (row: any) => row.role === "school_admin",
    );
    for (const row of admins)
      if (
        (!requested || row.membership_id === requested) &&
        (await surveyApi.availability(row)).available
      )
        return row;
    throw new Error($_("surveyManagement.permissionRequired"));
  }
  async function load() {
    loading = true;
    error = "";
    try {
      const selected = await resolveMembership();
      const surveyId = $page.params.id;
      if (!surveyId) throw new Error($_("surveyManagement.notFound"));
      membership = selected;
      [survey, results, context] = await Promise.all([
        surveyApi.detail(selected, surveyId),
        surveyApi.results(selected, surveyId, search),
        surveyApi.context(selected),
      ]);
    } catch (cause) {
      error = cause instanceof Error ? cause.message : String(cause);
    } finally {
      loading = false;
    }
  }
  async function action(name: string) {
    if (!membership || busy) return;
    busy = name;
    error = "";
    try {
      await surveyApi.action(membership, survey.id, name);
      await load();
    } catch (cause) {
      error = cause instanceof Error ? cause.message : String(cause);
    } finally {
      busy = "";
    }
  }
  function inputInZone(value: Date, zone: string) {
    const parts = Object.fromEntries(
      new Intl.DateTimeFormat("en-CA", {
        timeZone: zone,
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        hourCycle: "h23",
      })
        .formatToParts(value)
        .filter((part) => part.type !== "literal")
        .map((part) => [part.type, part.value]),
    );
    return `${parts.year}-${parts.month}-${parts.day}T${parts.hour}:${parts.minute}`;
  }
  function schoolLocalToIso(value: string, zone: string) {
    const [date, time] = value.split("T");
    const [year, month, day] = date.split("-").map(Number);
    const [hour, minute] = time.split(":").map(Number);
    const wanted = Date.UTC(year, month - 1, day, hour, minute);
    let guess = wanted;
    for (let attempt = 0; attempt < 2; attempt += 1) {
      const shownParts = Object.fromEntries(
        new Intl.DateTimeFormat("en-CA", {
          timeZone: zone,
          year: "numeric",
          month: "2-digit",
          day: "2-digit",
          hour: "2-digit",
          minute: "2-digit",
          hourCycle: "h23",
        })
          .formatToParts(new Date(guess))
          .filter((part) => part.type !== "literal")
          .map((part) => [part.type, Number(part.value)]),
      );
      const shown = Date.UTC(
        shownParts.year,
        shownParts.month - 1,
        shownParts.day,
        shownParts.hour,
        shownParts.minute,
      );
      guess += wanted - shown;
    }
    return new Date(guess).toISOString();
  }
  async function openReopen() {
    if (!context || busy) return;
    const oldClose = new Date(survey.closes_at);
    const suggested = oldClose.getTime() > Date.now() + 5 * 60 * 1000
      ? oldClose
      : new Date(Date.now() + 24 * 60 * 60 * 1000);
    reopenClosesAt = inputInZone(suggested, context.school.timezone);
    reopenError = "";
    reopenOpen = true;
    await tick();
    reopenInput?.focus();
  }
  async function closeReopen() {
    if (busy === "reopen") return;
    reopenOpen = false;
    reopenError = "";
    await tick();
    reopenButton?.focus();
  }
  async function confirmReopen() {
    if (!membership || !context || busy || !reopenClosesAt) return;
    reopenError = "";
    const closesAt = schoolLocalToIso(reopenClosesAt, context.school.timezone);
    if (new Date(closesAt).getTime() <= Date.now()) {
      reopenError = $_("surveyManagement.futureClosingTime");
      return;
    }
    busy = "reopen";
    try {
      await surveyApi.action(membership, survey.id, "reopen", {
        closes_at: closesAt,
      });
      reopenOpen = false;
      await load();
    } catch (cause) {
      reopenError = cause instanceof Error ? cause.message : String(cause);
    } finally {
      busy = "";
    }
  }
  function handleKeydown(event: KeyboardEvent) {
    if (reopenOpen && event.key === "Escape" && busy !== "reopen") {
      event.preventDefault();
      void closeReopen();
    }
  }
  async function exportCsv() {
    if (!membership || busy) return;
    busy = "export";
    try {
      const blob = await surveyApi.exportCsv(membership, survey.id);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${survey.title.replace(/[^A-Za-z0-9_-]+/g, "-")}-results.csv`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (cause) {
      error = cause instanceof Error ? cause.message : String(cause);
    } finally {
      busy = "";
    }
  }
  function percent(count: number, rows: any[]) {
    const max = Math.max(1, ...rows.map((row) => row.count));
    return Math.max(count ? 4 : 0, Math.round((count / max) * 100));
  }
  function fmt(value: string) {
    return new Intl.DateTimeFormat(ar ? "ar" : "en", {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value));
  }
  onMount(load);
</script>

<svelte:window onkeydown={handleKeydown} />

<svelte:head
  ><title>{survey?.title || t.results} · {$_("app.name")}</title></svelte:head
>
<div class="mx-auto max-w-7xl px-4 py-8 sm:py-12" dir={ar ? "rtl" : "ltr"}>
  <a
    href={`/school/surveys${membership ? `?membership=${membership.membership_id}` : ""}`}
    class="inline-flex items-center gap-2 text-sm font-black text-slate-500 hover:text-hero"
    ><ArrowLeft class={ar ? "rotate-180" : ""} size={17} />{t.back}</a
  >
  {#if error}<div
      class="mt-5 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm font-bold text-red-700"
    >
      {error}
    </div>{/if}
  {#if loading}<p class="mt-10 font-bold text-slate-500">{$_("surveyManagement.loadingOne")}</p>
  {:else if survey && results}
    <header
      class="mt-6 rounded-[2rem] bg-slate-950 p-6 text-white shadow-xl sm:p-8"
    >
      <div
        class="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between"
      >
        <div class="max-w-3xl">
          <div class="flex flex-wrap gap-2">
            <span class="pill bg-white/10">{statusLabel(survey.status)}</span><span
              class="pill bg-white/10"
              >{survey.anonymous ? t.anonymous : t.identified}</span
            ><span class="pill bg-white/10">{$_(`surveyManagement.responseModes.${survey.response_mode}`)}</span>
          </div>
          <h1 class="mt-5 text-3xl font-black sm:text-4xl">{survey.title}</h1>
          <p class="mt-3 text-sm font-semibold leading-6 text-slate-300">
            {survey.introduction}
          </p>
          <p class="mt-4 text-xs font-bold text-slate-400">
            {fmt(survey.opens_at)} <span class="inline-block rtl:-scale-x-100" aria-hidden="true">→</span> {fmt(survey.closes_at)}
          </p>
        </div>
        <div class="flex flex-wrap gap-2 lg:max-w-sm lg:justify-end">
          {#if survey.status === "draft"}<button
              class="action bg-hero text-white"
              disabled={busy !== ""}
              onclick={() => action("publish")}
              ><CheckCircle2 size={16} />{t.publish}</button
            >{/if}{#if ["open", "scheduled"].includes(survey.status)}<button
              class="action bg-red-500 text-white"
              disabled={busy !== ""}
              onclick={() => action("close")}
              ><XCircle size={16} />{t.close}</button
            >{/if}{#if survey.status === "open"}<button
              class="action bg-amber-400 text-amber-950"
              disabled={busy !== "" || survey.reminder_status === "sent"}
              onclick={() => action("remind")}
              ><BellRing size={16} />{t.remind}</button
            >{/if}{#if survey.status === "closed"}<button
              class="action bg-white/10"
              disabled={busy !== ""}
              bind:this={reopenButton}
              onclick={openReopen}
              ><RotateCcw size={16} />{t.reopen}</button
            ><button
              class="action bg-white/10"
              disabled={busy !== ""}
              onclick={() => action("archive")}
              ><Archive size={16} />{t.archive}</button
            >{/if}<button
            class="action bg-white/10"
            disabled={busy !== ""}
            onclick={exportCsv}><Download size={16} />{t.export}</button
          >
        </div>
      </div>
    </header>
    <section class="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <div class="metric">
        <span>{$_("surveyManagement.eligible")}</span><b>{survey.eligible_count}</b>
      </div>
      <div class="metric">
        <span>{$_("surveyManagement.responses")}</span><b>{survey.response_count}</b>
      </div>
      <div class="metric">
        <span>{$_("surveyManagement.responseRate")}</span><b class="text-hero"
          >{survey.response_rate}%</b
        >
      </div>
      <div class="metric">
        <span>{$_("surveyManagement.reminder")}</span><b class="text-lg"
          >{reminderStatusLabel(survey.reminder_status)}</b
        >
      </div>
    </section>
    <section
      class="mt-6 rounded-[1.75rem] border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
    >
      <h2 class="text-xl font-black text-slate-950">{$_("surveyManagement.responseRate")}</h2>
      <div class="mt-5 flex h-5 overflow-hidden rounded-full bg-slate-100">
        <div class="bg-hero" style={`width:${survey.response_rate}%`}></div>
      </div>
      <div class="mt-3 flex justify-between text-xs font-black text-slate-500">
        <span>{$_("surveyManagement.completed", { values: { count: results.response_rate.completed } })}</span><span
          >{$_("surveyManagement.outstanding", { values: { count: results.response_rate.outstanding } })}</span
        >
      </div>
    </section>
    <section class="mt-6">
      <h2 class="text-2xl font-black text-slate-950">{t.results}</h2>
      <div class="mt-4 grid gap-5 lg:grid-cols-2">
        {#each results.questions as question, index}<article
            class="rounded-[1.75rem] border border-slate-200 bg-white p-5 shadow-sm"
          >
            <p class="text-xs font-black uppercase tracking-wider text-hero">
              {index + 1}. {questionTypePresentation(question.question_type)}
            </p>
            <h3 class="mt-2 text-lg font-black text-slate-950">
              {question.prompt}
            </h3>
            <p class="mt-1 text-xs font-bold text-slate-400">
              {$_("surveyManagement.answers", { values: { count: question.answer_count } })}
            </p>
            {#if question.average !== undefined && question.average !== null}<div
                class="mt-4 rounded-2xl bg-hero/5 p-4"
              >
                <span class="text-xs font-black uppercase text-hero"
                  >{$_("surveyManagement.average")}</span
                ><b class="ms-3 text-3xl text-slate-950">{question.average}</b>
              </div>{/if}{#if question.distribution}<div class="mt-5 space-y-3">
                {#each question.distribution as row}<div>
                    <div
                      class="flex justify-between gap-3 text-xs font-black text-slate-700"
                    >
                      <span>{row.label}</span><span>{row.count}</span>
                    </div>
                    <div
                      class="mt-1.5 h-3 overflow-hidden rounded-full bg-slate-100"
                    >
                      <div
                        class="h-full rounded-full bg-hero"
                        style={`width:${percent(row.count, question.distribution)}%`}
                      ></div>
                    </div>
                  </div>{/each}
              </div>{:else}<p class="mt-5 text-sm font-semibold text-slate-500">
                {$_("surveyManagement.textAnswersBelow")}
              </p>{/if}
          </article>{/each}
      </div>
    </section>
    <section
      class="mt-8 rounded-[1.75rem] border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
    >
      <div
        class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between"
      >
        <div>
          <h2 class="text-xl font-black text-slate-950">{t.comments}</h2>
          <p class="mt-1 text-xs font-bold text-slate-400">
            {$_("surveyManagement.responsePage", { values: { count: results.free_text.total, page: results.free_text.page } })}
          </p>
        </div>
        <form
          class="flex w-full min-w-0 flex-col gap-2 sm:w-auto sm:flex-row"
          onsubmit={(event) => {
            event.preventDefault();
            void load();
          }}
        >
          <input
            class="min-w-0 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm sm:w-56"
            bind:value={search}
            placeholder={$_("surveyManagement.search")}
          /><button
            class="w-full shrink-0 rounded-xl bg-slate-900 px-4 py-2 text-xs font-black text-white sm:w-auto"
            >{$_("surveyManagement.search")}</button
          >
        </form>
      </div>
      <div class="mt-5 space-y-3">
        {#each results.free_text.items as item}<article
            class="rounded-2xl bg-slate-50 p-4"
          >
            <p class="text-xs font-black text-hero">{item.prompt}</p>
            <p
              class="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-700"
            >
              {item.text}
            </p>
            {#if item.respondent}<p
                class="mt-3 text-xs font-bold text-slate-400"
              >
                <LockKeyhole class="inline" size={12} />
                {item.respondent}
              </p>{/if}
          </article>{:else}<p
            class="py-8 text-center text-sm font-bold text-slate-400"
          >
            {t.noComments}
          </p>{/each}
      </div>
    </section>
  {/if}
</div>

{#if reopenOpen}
  <div class="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/60 p-0 sm:items-center sm:p-4">
    <button
      class="absolute inset-0 h-full w-full"
      type="button"
      aria-label={t.cancel}
      disabled={busy === "reopen"}
      onclick={closeReopen}
    ></button>
    <div
      class="relative w-full max-w-lg rounded-t-[2rem] bg-white p-6 shadow-2xl sm:rounded-[2rem]"
      role="dialog"
      aria-modal="true"
      aria-labelledby="reopen-survey-title"
    >
      <h2 id="reopen-survey-title" class="text-2xl font-black text-slate-950">{t.reopenTitle}</h2>
      <p class="mt-2 text-sm font-semibold leading-6 text-slate-600">{t.reopenHelp}</p>
      <label class="mt-5 block text-sm font-black text-slate-800" for="reopen-closes-at">
        {t.newClosingTime}
        <input
          id="reopen-closes-at"
          class="mt-2 block w-full rounded-xl border border-slate-300 px-3 py-3 font-semibold"
          type="datetime-local"
          bind:this={reopenInput}
          bind:value={reopenClosesAt}
          disabled={busy === "reopen"}
          required
        />
      </label>
      <p class="mt-2 text-xs font-bold text-slate-500">{context?.school?.timezone}</p>
      {#if reopenError}<p class="mt-4 rounded-xl bg-red-50 p-3 text-sm font-bold text-red-700" role="alert">{reopenError}</p>{/if}
      <div class="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        <button class="action justify-center bg-slate-100 text-slate-800" type="button" disabled={busy === "reopen"} onclick={closeReopen}>{t.cancel}</button>
        <button class="action justify-center bg-hero text-white" type="button" disabled={busy === "reopen" || !reopenClosesAt} onclick={confirmReopen}>
          <RotateCcw size={16} />{busy === "reopen" ? t.reopening : t.reopen}
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  .pill {
    display: inline-flex;
    border-radius: 9999px;
    padding: 0.35rem 0.75rem;
    font-size: 0.65rem;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }
  .action {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    border-radius: 0.85rem;
    padding: 0.65rem 0.85rem;
    font-size: 0.7rem;
    font-weight: 900;
  }
  .action:disabled {
    opacity: 0.45;
  }
  .metric {
    border: 1px solid #e2e8f0;
    border-radius: 1.5rem;
    background: white;
    padding: 1.1rem;
    box-shadow: 0 1px 2px rgb(15 23 42 / 0.05);
  }
  .metric span {
    display: block;
    font-size: 0.65rem;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #94a3b8;
  }
  .metric b {
    margin-top: 0.35rem;
    display: block;
    font-size: 1.8rem;
    font-weight: 900;
    color: #0f172a;
  }
</style>
