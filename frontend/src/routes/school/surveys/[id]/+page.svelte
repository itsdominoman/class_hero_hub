<script lang="ts">
  import { onMount } from "svelte";
  import { page } from "$app/stores";
  import { locale } from "svelte-i18n";
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
  let survey = $state<any>(null);
  let results = $state<any>(null);
  let loading = $state(true);
  let busy = $state("");
  let error = $state("");
  let search = $state("");
  let ar = $derived($locale === "ar");
  const label: Record<string, Record<string, string>> = {
    en: {
      back: "Surveys",
      results: "Results",
      questions: "Questions",
      comments: "Comments / free text",
      publish: "Publish",
      close: "Close",
      reopen: "Reopen",
      archive: "Archive",
      remind: "Send reminder",
      export: "Export CSV",
      noComments: "No free-text responses.",
      anonymous: "Anonymous",
      identified: "Identified",
      guardian: "One per guardian",
      household: "One per household",
    },
    ar: {
      back: "الاستبيانات",
      results: "النتائج",
      questions: "الأسئلة",
      comments: "التعليقات والنصوص",
      publish: "نشر",
      close: "إغلاق",
      reopen: "إعادة فتح",
      archive: "أرشفة",
      remind: "إرسال تذكير",
      export: "تصدير CSV",
      noComments: "لا توجد إجابات نصية.",
      anonymous: "مجهول الهوية",
      identified: "محدد الهوية",
      guardian: "إجابة لكل ولي أمر",
      household: "إجابة لكل أسرة",
    },
  };
  let t = $derived(ar ? label.ar : label.en);

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
    throw new Error(
      ar
        ? "لا تملك صلاحية إدارة الاستبيانات."
        : "Survey management permission required.",
    );
  }
  async function load() {
    loading = true;
    error = "";
    try {
      const selected = await resolveMembership();
      const surveyId = $page.params.id;
      if (!surveyId) throw new Error("Survey not found");
      membership = selected;
      [survey, results] = await Promise.all([
        surveyApi.detail(selected, surveyId),
        surveyApi.results(selected, surveyId, search),
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

<svelte:head
  ><title>{survey?.title || t.results} · Class Hero Hub</title></svelte:head
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
  {#if loading}<p class="mt-10 font-bold text-slate-500">Loading…</p>
  {:else if survey && results}
    <header
      class="mt-6 rounded-[2rem] bg-slate-950 p-6 text-white shadow-xl sm:p-8"
    >
      <div
        class="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between"
      >
        <div class="max-w-3xl">
          <div class="flex flex-wrap gap-2">
            <span class="pill bg-white/10">{survey.status}</span><span
              class="pill bg-white/10"
              >{survey.anonymous ? t.anonymous : t.identified}</span
            ><span class="pill bg-white/10">{t[survey.response_mode]}</span>
          </div>
          <h1 class="mt-5 text-3xl font-black sm:text-4xl">{survey.title}</h1>
          <p class="mt-3 text-sm font-semibold leading-6 text-slate-300">
            {survey.introduction}
          </p>
          <p class="mt-4 text-xs font-bold text-slate-400">
            {fmt(survey.opens_at)} → {fmt(survey.closes_at)}
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
              onclick={() => action("reopen")}
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
        <span>Eligible</span><b>{survey.eligible_count}</b>
      </div>
      <div class="metric">
        <span>Responses</span><b>{survey.response_count}</b>
      </div>
      <div class="metric">
        <span>Response rate</span><b class="text-hero"
          >{survey.response_rate}%</b
        >
      </div>
      <div class="metric">
        <span>Reminder</span><b class="text-lg capitalize"
          >{survey.reminder_status}</b
        >
      </div>
    </section>
    <section
      class="mt-6 rounded-[1.75rem] border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
    >
      <h2 class="text-xl font-black text-slate-950">Response rate</h2>
      <div class="mt-5 flex h-5 overflow-hidden rounded-full bg-slate-100">
        <div class="bg-hero" style={`width:${survey.response_rate}%`}></div>
      </div>
      <div class="mt-3 flex justify-between text-xs font-black text-slate-500">
        <span>{results.response_rate.completed} completed</span><span
          >{results.response_rate.outstanding} outstanding</span
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
              {index + 1}. {question.question_type.replaceAll("_", " ")}
            </p>
            <h3 class="mt-2 text-lg font-black text-slate-950">
              {question.prompt}
            </h3>
            <p class="mt-1 text-xs font-bold text-slate-400">
              {question.answer_count} answers
            </p>
            {#if question.average !== undefined && question.average !== null}<div
                class="mt-4 rounded-2xl bg-hero/5 p-4"
              >
                <span class="text-xs font-black uppercase text-hero"
                  >Average</span
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
                {ar
                  ? "تعرض الإجابات النصية أدناه."
                  : "Text answers are listed below."}
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
            {results.free_text.total} responses · page {results.free_text.page}
          </p>
        </div>
        <form
          class="flex gap-2"
          onsubmit={(event) => {
            event.preventDefault();
            void load();
          }}
        >
          <input
            class="rounded-xl border border-slate-200 px-3 py-2 text-sm"
            bind:value={search}
            placeholder="Search"
          /><button
            class="rounded-xl bg-slate-900 px-4 py-2 text-xs font-black text-white"
            >Search</button
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
