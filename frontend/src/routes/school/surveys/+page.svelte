<script lang="ts">
  import { onMount, tick } from "svelte";
  import { goto } from "$app/navigation";
  import { page } from "$app/stores";
  import { locale } from "svelte-i18n";
  import { api } from "$lib/api";
  import { surveyApi, type SurveyMembership } from "$lib/surveys/api";
  import {
    ClipboardList,
    Plus,
    ArrowUp,
    ArrowDown,
    Trash2,
    Eye,
    ShieldCheck,
  } from "lucide-svelte";

  type Question = {
    question_type: string;
    prompt: string;
    required: boolean;
    scale_min: number | null;
    scale_max: number | null;
    options: { label: string }[];
  };
  const copy = {
    en: {
      title: "Surveys",
      sub: "Create, publish and report on targeted parent surveys.",
      overview: "Overview",
      create: "Create survey",
      drafts: "Drafts",
      open: "Open",
      closed: "Closed",
      all: "All",
      no: "No surveys in this view.",
      newSurvey: "New survey",
      basics: "Survey details",
      audience: "Audience",
      questions: "Questions",
      preview: "Preview",
      save: "Save draft",
      permission: "Survey administrators",
      loading: "Loading surveys…",
      close: "Close",
    },
    ar: {
      title: "الاستبيانات",
      sub: "إنشاء استبيانات موجهة لأولياء الأمور ونشرها وعرض نتائجها.",
      overview: "نظرة عامة",
      create: "إنشاء استبيان",
      drafts: "المسودات",
      open: "المفتوحة",
      closed: "المغلقة",
      all: "الكل",
      no: "لا توجد استبيانات في هذا العرض.",
      newSurvey: "استبيان جديد",
      basics: "تفاصيل الاستبيان",
      audience: "الجمهور",
      questions: "الأسئلة",
      preview: "معاينة",
      save: "حفظ المسودة",
      permission: "مسؤولو الاستبيانات",
      loading: "جارٍ تحميل الاستبيانات…",
      close: "إغلاق",
    },
  };
  let ar = $derived($locale === "ar");
  let t = $derived(ar ? copy.ar : copy.en);
  let membership = $state<SurveyMembership | null>(null);
  let context = $state<any>(null);
  let surveys = $state<any[]>([]);
  let permissions = $state<any>(null);
  let loading = $state(true);
  let error = $state("");
  let activeView = $state("all");
  let editorOpen = $state(false);
  let previewOpen = $state(false);
  let saving = $state(false);
  let permissionBusy = $state<number | null>(null);
  let createSurveyButton = $state<HTMLButtonElement>();
  let closeSurveyButton = $state<HTMLButtonElement>();
  let form = $state({
    title: "",
    introduction: "",
    instructions: "",
    audience_type: "whole_school",
    target_ids: [] as number[],
    anonymous: true,
    response_mode: "guardian",
    opens_at: "",
    closes_at: "",
    reminder_enabled: false,
    reminder_at: "",
    parent_results_visible: false,
    push_enabled: true,
    dashboard_card_enabled: true,
    notices_feed_enabled: true,
    questions: [] as Question[],
  });

  function localInput(date: Date) {
    const pad = (n: number) => String(n).padStart(2, "0");
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
  }
  function resetForm() {
    const open = new Date(Date.now() + 60 * 60 * 1000);
    const close = new Date(Date.now() + 8 * 24 * 60 * 60 * 1000);
    form = {
      title: "",
      introduction: "",
      instructions: "",
      audience_type: "whole_school",
      target_ids: [],
      anonymous: true,
      response_mode: "guardian",
      opens_at: localInput(open),
      closes_at: localInput(close),
      reminder_enabled: false,
      reminder_at: "",
      parent_results_visible: false,
      push_enabled: true,
      dashboard_card_enabled: true,
      notices_feed_enabled: true,
      questions: [newQuestion("single_choice")],
    };
  }
  async function openEditor() {
    resetForm();
    previewOpen = false;
    editorOpen = true;
    document.body.classList.add("survey-composer-open");
    await tick();
    closeSurveyButton?.focus();
  }
  async function closeEditor(restoreFocus = true) {
    if (!editorOpen) return;
    editorOpen = false;
    previewOpen = false;
    document.body.classList.remove("survey-composer-open");
    await tick();
    if (restoreFocus) createSurveyButton?.focus();
  }
  function handleKeydown(event: KeyboardEvent) {
    if (editorOpen && event.key === "Escape") {
      event.preventDefault();
      void closeEditor();
    }
  }
  function handleNativeBack(event: Event) {
    if (!editorOpen || event.defaultPrevented) return;
    const active = document.activeElement;
    const editable =
      active instanceof HTMLInputElement ||
      active instanceof HTMLTextAreaElement ||
      (active instanceof HTMLElement && active.isContentEditable);
    if (editable && document.documentElement.classList.contains("native-keyboard-open")) {
      active.blur();
      event.preventDefault();
      event.stopImmediatePropagation();
      return;
    }
    event.preventDefault();
    event.stopImmediatePropagation();
    void closeEditor();
  }
  function newQuestion(type = "single_choice"): Question {
    return {
      question_type: type,
      prompt: "",
      required: true,
      scale_min: type === "rating" ? 1 : null,
      scale_max: type === "rating" ? 5 : null,
      options: ["single_choice", "multiple_choice"].includes(type)
        ? [{ label: "" }, { label: "" }]
        : [],
    };
  }
  function setQuestionType(question: Question, type: string) {
    question.question_type = type;
    question.options = ["single_choice", "multiple_choice"].includes(type)
      ? question.options.length >= 2
        ? question.options
        : [{ label: "" }, { label: "" }]
      : [];
    question.scale_min = type === "rating" ? 1 : null;
    question.scale_max = type === "rating" ? 5 : null;
  }
  function move<T>(items: T[], from: number, to: number) {
    if (to < 0 || to >= items.length) return;
    const copy = [...items];
    [copy[from], copy[to]] = [copy[to], copy[from]];
    return copy;
  }
  function toggleTarget(id: number, checked: boolean) {
    form.target_ids = checked
      ? [...new Set([...form.target_ids, id])]
      : form.target_ids.filter((value) => value !== id);
  }
  function targetRows() {
    if (!context) return [];
    return form.audience_type === "branch"
      ? context.branches
      : form.audience_type === "grade"
        ? context.grades
        : form.audience_type === "class"
          ? context.classes
          : form.audience_type === "selected_families"
            ? context.linked_families
            : [];
  }
  function schoolLocalToIso(value: string, zone: string) {
    const [date, time] = value.split("T");
    const [y, m, d] = date.split("-").map(Number);
    const [hh, mm] = time.split(":").map(Number);
    const wanted = Date.UTC(y, m - 1, d, hh, mm);
    let guess = wanted;
    for (let i = 0; i < 2; i += 1) {
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
          .formatToParts(new Date(guess))
          .filter((p) => p.type !== "literal")
          .map((p) => [p.type, Number(p.value)]),
      );
      const shown = Date.UTC(
        parts.year,
        parts.month - 1,
        parts.day,
        parts.hour,
        parts.minute,
      );
      guess += wanted - shown;
    }
    return new Date(guess).toISOString();
  }
  async function load() {
    loading = true;
    error = "";
    try {
      const session = await api.get("/me");
      const requested = Number($page.url.searchParams.get("membership"));
      const admins = (session.memberships || []).filter(
        (row: any) => row.role === "school_admin",
      );
      const available = await Promise.all(
        admins.map(async (row: any) =>
          (await surveyApi.availability(row)).available ? row : null,
        ),
      );
      membership =
        available.find(
          (row) => row && (!requested || row.membership_id === requested),
        ) ||
        available.find(Boolean) ||
        null;
      if (!membership)
        throw new Error(
          ar
            ? "لا تملك صلاحية إدارة الاستبيانات."
            : "You do not have survey management permission.",
        );
      [context, { items: surveys }, permissions] = await Promise.all([
        surveyApi.context(membership),
        surveyApi.list(membership),
        surveyApi.permissions(membership),
      ]);
    } catch (cause) {
      error = cause instanceof Error ? cause.message : String(cause);
    } finally {
      loading = false;
    }
  }
  async function saveDraft() {
    if (!membership || !context || saving) return;
    saving = true;
    error = "";
    try {
      const zone = context.school.timezone;
      const { reminder_enabled, reminder_at, ...surveyForm } = form;
      const payload = {
        ...surveyForm,
        target_ids:
          form.audience_type === "whole_school" ? [] : form.target_ids,
        opens_at: schoolLocalToIso(form.opens_at, zone),
        closes_at: schoolLocalToIso(form.closes_at, zone),
        reminder_at:
          reminder_enabled && reminder_at
            ? schoolLocalToIso(reminder_at, zone)
            : null,
        instructions: form.instructions || null,
        questions: form.questions.map((q) => ({
          ...q,
          options: q.options.map((option) => ({ label: option.label })),
        })),
      };
      const created = await surveyApi.create(membership, payload);
      await goto(
        `/school/surveys/${created.id}?membership=${membership.membership_id}`,
      );
    } catch (cause) {
      error = cause instanceof Error ? cause.message : String(cause);
    } finally {
      saving = false;
    }
  }
  async function changePermission(row: any) {
    if (!membership || permissionBusy) return;
    permissionBusy = row.membership_id;
    try {
      await surveyApi.setPermission(membership, {
        membership_id: row.membership_id,
        enabled: !row.enabled,
        reason: "System Owner survey administration update",
      });
      permissions = await surveyApi.permissions(membership);
    } catch (cause) {
      error = cause instanceof Error ? cause.message : String(cause);
    } finally {
      permissionBusy = null;
    }
  }
  let filtered = $derived(
    activeView === "all"
      ? surveys
      : activeView === "open"
        ? surveys.filter((row) => ["open", "scheduled"].includes(row.status))
        : surveys.filter((row) => row.status === activeView),
  );
  onMount(() => {
    resetForm();
    void load();
    window.addEventListener("keydown", handleKeydown);
    window.addEventListener("chh:native-back", handleNativeBack);
    return () => {
      window.removeEventListener("keydown", handleKeydown);
      window.removeEventListener("chh:native-back", handleNativeBack);
      document.body.classList.remove("survey-composer-open");
    };
  });
</script>

<svelte:head><title>{t.title} · Class Hero Hub</title></svelte:head>
<div class="mx-auto max-w-7xl px-4 py-8 sm:py-12" dir={ar ? "rtl" : "ltr"}>
  <header
    class="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between"
  >
    <div>
      <p class="text-xs font-black uppercase tracking-[0.25em] text-hero">
        CHH
      </p>
      <h1 class="mt-2 text-3xl font-black text-slate-950 sm:text-4xl">
        {t.title}
      </h1>
      <p class="mt-2 max-w-2xl text-sm font-semibold text-slate-600">{t.sub}</p>
    </div>
    {#if membership}<button
        bind:this={createSurveyButton}
        type="button"
        class="btn-hero inline-flex items-center justify-center gap-2 rounded-2xl px-5 py-3"
        onclick={openEditor}><Plus size={18} />{t.create}</button
      >{/if}
  </header>
  {#if error}<div
      class="mt-6 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm font-bold text-red-700"
      role="alert"
    >
      {error}
    </div>{/if}
  {#if loading}<p class="mt-10 text-sm font-bold text-slate-500">{t.loading}</p>
  {:else if membership}
    <nav class="mt-8 flex gap-2 overflow-x-auto pb-2" aria-label={t.title}>
      {#each [["all", t.all], ["draft", t.drafts], ["open", t.open], ["closed", t.closed], ["archived", "Archived"]] as item}<button
          class:active-tab={activeView === item[0]}
          class="tab"
          onclick={() => (activeView = item[0])}>{item[1]}</button
        >{/each}
    </nav>
    <section class="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {#each filtered as survey}
        <a
          href={`/school/surveys/${survey.id}?membership=${membership.membership_id}`}
          class="rounded-[1.75rem] border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-hero/40 hover:shadow-lg"
        >
          <div class="flex items-start justify-between gap-3">
            <span
              class="rounded-full bg-slate-100 px-3 py-1 text-[10px] font-black uppercase tracking-wider text-slate-600"
              >{survey.status}</span
            ><ClipboardList class="text-hero" size={22} />
          </div>
          <h2 class="mt-4 text-lg font-black text-slate-950">{survey.title}</h2>
          <p class="mt-2 line-clamp-2 text-sm text-slate-600">
            {survey.introduction}
          </p>
          <div class="mt-5 grid grid-cols-3 gap-2 text-center">
            <div>
              <b class="block text-xl text-slate-950">{survey.eligible_count}</b
              ><span class="text-[10px] font-bold uppercase text-slate-400"
                >Eligible</span
              >
            </div>
            <div>
              <b class="block text-xl text-slate-950">{survey.response_count}</b
              ><span class="text-[10px] font-bold uppercase text-slate-400"
                >Responses</span
              >
            </div>
            <div>
              <b class="block text-xl text-hero">{survey.response_rate}%</b
              ><span class="text-[10px] font-bold uppercase text-slate-400"
                >Rate</span
              >
            </div>
          </div>
        </a>
      {:else}<div
          class="md:col-span-2 xl:col-span-3 rounded-[1.75rem] border border-dashed border-slate-300 bg-slate-50 p-10 text-center text-sm font-bold text-slate-500"
        >
          {t.no}
        </div>{/each}
    </section>
    {#if permissions?.can_manage}
      <details
        class="mt-8 rounded-[1.75rem] border border-slate-200 bg-white p-5"
      >
        <summary
          class="flex cursor-pointer list-none items-center gap-3 font-black text-slate-950"
          ><ShieldCheck class="text-hero" />{t.permission}</summary
        >
        <div class="mt-4 divide-y divide-slate-100">
          {#each permissions.administrators as row}<div
              class="flex items-center justify-between gap-4 py-3"
            >
              <div>
                <p class="font-bold text-slate-900">{row.name}</p>
                <p class="text-xs text-slate-400">{row.status}</p>
              </div>
              <button
                class="rounded-xl px-4 py-2 text-xs font-black {row.enabled
                  ? 'bg-emerald-100 text-emerald-800'
                  : 'bg-slate-100 text-slate-600'}"
                disabled={permissionBusy === row.membership_id}
                onclick={() => changePermission(row)}
                >{row.enabled ? "Enabled" : "Disabled"}</button
              >
            </div>{/each}
        </div>
      </details>
    {/if}
  {/if}
</div>

{#if editorOpen}
  <div
    class="survey-dialog-layer fixed inset-x-0 top-0 z-[110] flex items-start justify-center bg-slate-950/55"
    dir={ar ? "rtl" : "ltr"}
    role="presentation"
  >
    <div
      class="flex max-h-full w-full max-w-4xl flex-col overflow-hidden rounded-[2rem] bg-white shadow-2xl"
      role="dialog"
      aria-modal="true"
      aria-labelledby="survey-composer-title"
      data-testid="survey-composer-dialog"
    >
      <div class="flex shrink-0 items-center justify-between gap-4 border-b border-slate-200 px-5 py-4 sm:px-8">
        <div>
          <p class="text-xs font-black uppercase tracking-widest text-hero">
            {t.newSurvey}
          </p>
          <h2 id="survey-composer-title" class="mt-1 text-2xl font-black text-slate-950">{t.basics}</h2>
        </div>
        <button
          bind:this={closeSurveyButton}
          type="button"
          class="inline-flex min-h-11 shrink-0 items-center gap-2 rounded-full bg-slate-100 px-4 py-2 font-black text-slate-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-hero"
          aria-label={t.close}
          data-testid="survey-composer-close"
          onclick={() => void closeEditor()}><span aria-hidden="true" class="text-xl leading-none">×</span><span>{t.close}</span></button
        >
      </div>
      <div class="min-h-0 flex-1 overflow-y-auto overscroll-contain px-5 pb-5 sm:px-8 sm:pb-8" data-testid="survey-composer-scroll">
      {#if previewOpen}
        <section
          class="mt-6 rounded-[1.75rem] border border-hero/20 bg-hero/5 p-5"
        >
          <p class="text-xs font-black uppercase tracking-widest text-hero">
            {t.preview}
          </p>
          <h3 class="mt-3 text-2xl font-black">
            {form.title || "Survey title"}
          </h3>
          <p class="mt-2 text-sm text-slate-600">{form.introduction}</p>
          <div class="mt-6 space-y-4">
            {#each form.questions as question, index}<div
                class="rounded-2xl bg-white p-4"
              >
                <p class="font-black">
                  {index + 1}. {question.prompt || "Question"}
                  {#if question.required}<span class="text-red-500">*</span
                    >{/if}
                </p>
                <p class="mt-2 text-xs text-slate-400">
                  {question.question_type.replaceAll("_", " ")}
                </p>
              </div>{/each}
          </div>
        </section>
      {:else}
        <div class="mt-6 grid gap-4 sm:grid-cols-2">
          <label class="field-label sm:col-span-2"
            ><span>Title</span><input
              class="field"
              bind:value={form.title}
              maxlength="200"
            /></label
          ><label class="field-label sm:col-span-2"
            ><span>Short introduction</span><textarea
              class="field min-h-24"
              bind:value={form.introduction}
              maxlength="1000"
            ></textarea></label
          ><label class="field-label sm:col-span-2"
            ><span>Instructions (optional)</span><textarea
              class="field min-h-20"
              bind:value={form.instructions}
            ></textarea></label
          ><label class="field-label"
            ><span>Opens (school time)</span><input
              class="field"
              type="datetime-local"
              bind:value={form.opens_at}
            /></label
          ><label class="field-label"
            ><span>Closes (school time)</span><input
              class="field"
              type="datetime-local"
              bind:value={form.closes_at}
            /></label
          >
        </div>
        <section class="mt-8">
          <h3 class="text-lg font-black">{t.audience}</h3>
          <div class="mt-3 grid gap-4 sm:grid-cols-2">
            <label class="field-label"
              ><span>Audience</span><select
                class="field"
                bind:value={form.audience_type}
                onchange={() => (form.target_ids = [])}
                ><option value="whole_school">Whole school</option><option
                  value="branch">Branch</option
                ><option value="grade">Grade / level</option><option
                  value="class">Class / homeroom</option
                ><option value="selected_families"
                  >Selected linked families</option
                ></select
              ></label
            ><label class="field-label"
              ><span>Response unit</span><select
                class="field"
                bind:value={form.response_mode}
                ><option value="guardian">One per guardian</option><option
                  value="household">One per household</option
                ></select
              ></label
            >
          </div>
          {#if form.audience_type !== "whole_school"}<div
              class="mt-3 grid gap-2 rounded-2xl border border-slate-200 p-3 sm:grid-cols-2"
            >
              {#each targetRows() as row}<label
                  class="flex items-center gap-2 rounded-xl p-2 text-sm font-bold hover:bg-slate-50"
                  ><input
                    type="checkbox"
                    checked={form.target_ids.includes(row.id)}
                    onchange={(event) =>
                      toggleTarget(row.id, event.currentTarget.checked)}
                  /><span
                    >{ar
                      ? row.name_ar || row.label_ar || row.name || row.label
                      : row.name || row.label}</span
                  ></label
                >{/each}
            </div>{/if}
          <div class="mt-4 grid gap-2 sm:grid-cols-2">
            <label class="check"
              ><input type="checkbox" bind:checked={form.anonymous} /><span
                >Anonymous responses</span
              ></label
            ><label class="check"
              ><input
                type="checkbox"
                bind:checked={form.parent_results_visible}
              /><span>Parents may see results after closing</span></label
            ><label class="check"
              ><input type="checkbox" bind:checked={form.push_enabled} /><span
                >Push notification</span
              ></label
            ><label class="check"
              ><input
                type="checkbox"
                bind:checked={form.dashboard_card_enabled}
              /><span>Dashboard card</span></label
            ><label class="check"
              ><input
                type="checkbox"
                bind:checked={form.notices_feed_enabled}
              /><span>Notices-feed link</span></label
            ><label class="check"
              ><input
                type="checkbox"
                bind:checked={form.reminder_enabled}
              /><span>One reminder</span></label
            >
          </div>
          {#if form.reminder_enabled}<label class="field-label mt-3 max-w-sm"
              ><span>Reminder (school time)</span><input
                class="field"
                type="datetime-local"
                bind:value={form.reminder_at}
              /></label
            >{/if}
        </section>
        <section class="mt-8">
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-black">{t.questions}</h3>
            <button
              class="rounded-xl bg-hero/10 px-3 py-2 text-xs font-black text-hero"
              onclick={() =>
                (form.questions = [
                  ...form.questions,
                  newQuestion("single_choice"),
                ])}>+ Question</button
            >
          </div>
          <div class="mt-4 space-y-4">
            {#each form.questions as question, index}<article
                class="rounded-[1.5rem] border border-slate-200 p-4"
              >
                <div class="flex items-start gap-2">
                  <span
                    class="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-slate-900 text-xs font-black text-white"
                    >{index + 1}</span
                  >
                  <div class="grid flex-1 gap-3 sm:grid-cols-[1fr_12rem]">
                    <input
                      class="field"
                      placeholder="Question"
                      bind:value={question.prompt}
                    /><select
                      class="field"
                      value={question.question_type}
                      onchange={(event) =>
                        setQuestionType(question, event.currentTarget.value)}
                      ><option value="single_choice">Single choice</option
                      ><option value="multiple_choice">Multiple choice</option
                      ><option value="yes_no">Yes / No</option><option
                        value="rating">Rating</option
                      ><option value="short_text">Short text</option><option
                        value="long_text">Long text</option
                      ></select
                    >
                  </div>
                  <div class="flex shrink-0">
                    <button
                      class="icon"
                      aria-label="Move up"
                      onclick={() => {
                        const value = move(form.questions, index, index - 1);
                        if (value) form.questions = value;
                      }}><ArrowUp size={15} /></button
                    ><button
                      class="icon"
                      aria-label="Move down"
                      onclick={() => {
                        const value = move(form.questions, index, index + 1);
                        if (value) form.questions = value;
                      }}><ArrowDown size={15} /></button
                    ><button
                      class="icon text-red-600"
                      aria-label="Delete"
                      onclick={() =>
                        (form.questions = form.questions.filter(
                          (_, i) => i !== index,
                        ))}><Trash2 size={15} /></button
                    >
                  </div>
                </div>
                <label class="check mt-3"
                  ><input
                    type="checkbox"
                    bind:checked={question.required}
                  /><span>Required</span></label
                >{#if ["single_choice", "multiple_choice"].includes(question.question_type)}<div
                    class="mt-3 space-y-2"
                  >
                    {#each question.options as option, optionIndex}<div
                        class="flex items-center gap-2"
                      >
                        <input
                          class="field flex-1"
                          placeholder={`Choice ${optionIndex + 1}`}
                          bind:value={option.label}
                        /><button
                          class="icon"
                          onclick={() => {
                            const value = move(
                              question.options,
                              optionIndex,
                              optionIndex - 1,
                            );
                            if (value) question.options = value;
                          }}><ArrowUp size={14} /></button
                        ><button
                          class="icon"
                          onclick={() => {
                            const value = move(
                              question.options,
                              optionIndex,
                              optionIndex + 1,
                            );
                            if (value) question.options = value;
                          }}><ArrowDown size={14} /></button
                        ><button
                          class="icon text-red-600"
                          onclick={() =>
                            (question.options = question.options.filter(
                              (_, i) => i !== optionIndex,
                            ))}><Trash2 size={14} /></button
                        >
                      </div>{/each}<button
                      class="text-xs font-black text-hero"
                      onclick={() =>
                        (question.options = [
                          ...question.options,
                          { label: "" },
                        ])}>+ Choice</button
                    >
                  </div>{:else if question.question_type === "rating"}<div
                    class="mt-3 flex gap-3"
                  >
                    <label class="field-label"
                      ><span>Minimum</span><input
                        class="field"
                        type="number"
                        min="0"
                        max="9"
                        bind:value={question.scale_min}
                      /></label
                    ><label class="field-label"
                      ><span>Maximum</span><input
                        class="field"
                        type="number"
                        min="1"
                        max="10"
                        bind:value={question.scale_max}
                      /></label
                    >
                  </div>{/if}
              </article>{/each}
          </div>
        </section>
      {/if}
      </div>
      <div class="flex shrink-0 flex-col-reverse gap-3 border-t border-slate-200 bg-white p-4 sm:flex-row sm:justify-end sm:px-8">
        <button
          type="button"
          class="rounded-2xl border border-slate-200 px-5 py-3 font-black text-slate-600"
          onclick={() => (previewOpen = !previewOpen)}
          ><Eye class="inline" size={17} />
          {previewOpen ? "Edit" : t.preview}</button
        ><button
          type="button"
          class="btn-hero rounded-2xl px-6 py-3"
          disabled={saving || previewOpen}
          onclick={saveDraft}>{saving ? "Saving…" : t.save}</button
        >
      </div>
    </div>
  </div>
{/if}

<style>
  .tab {
    white-space: nowrap;
    border-radius: 9999px;
    background: #f1f5f9;
    padding: 0.65rem 1rem;
    font-size: 0.75rem;
    font-weight: 900;
    color: #64748b;
  }
  .active-tab {
    background: #0f172a;
    color: white;
  }
  .field-label {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
    font-size: 0.75rem;
    font-weight: 900;
    color: #475569;
  }
  .field {
    width: 100%;
    border: 1px solid #cbd5e1;
    border-radius: 0.9rem;
    background: white;
    padding: 0.7rem 0.85rem;
    font-size: 0.875rem;
    color: #0f172a;
    outline: none;
  }
  .field:focus {
    border-color: rgb(var(--color-hero, 79 70 229));
    box-shadow: 0 0 0 3px rgb(99 102 241 / 0.12);
  }
  .check {
    display: flex;
    align-items: flex-start;
    gap: 0.55rem;
    border-radius: 0.9rem;
    background: #f8fafc;
    padding: 0.75rem;
    font-size: 0.8rem;
    font-weight: 800;
    color: #334155;
  }
  .check input {
    margin-top: 0.1rem;
    height: 1rem;
    width: 1rem;
  }
  .icon {
    display: inline-grid;
    height: 2rem;
    width: 2rem;
    place-items: center;
    border-radius: 0.65rem;
    background: #f1f5f9;
    color: #475569;
  }
  .icon:hover {
    background: #e2e8f0;
  }
  .survey-dialog-layer {
    height: var(--native-viewport-height, 100dvh);
    padding-top: max(0.75rem, var(--safe-top));
    padding-right: max(0.75rem, var(--safe-right));
    padding-bottom: max(0.75rem, var(--safe-bottom));
    padding-left: max(0.75rem, var(--safe-left));
  }
  :global(body.survey-composer-open) {
    overflow: hidden;
  }
  :global(body.survey-composer-open .app-main) {
    overflow-y: hidden !important;
  }
</style>
