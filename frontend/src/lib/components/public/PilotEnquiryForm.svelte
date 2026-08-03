<script lang="ts">
  import { AlertCircle, CheckCircle2, Mail, Send } from "lucide-svelte";
  import { api } from "$lib/api";
  import type { PilotFormCopy } from "$lib/publicSite";

  let { copy } = $props<{ copy: PilotFormCopy }>();

  let name = $state("");
  let school = $state("");
  let role = $state("");
  let region = $state("");
  let email = $state("");
  let message = $state("");
  let sending = $state(false);
  let sent = $state(false);
  let errorMessage = $state("");

  async function submitEnquiry(event: SubmitEvent) {
    event.preventDefault();
    if (sending) return;

    sending = true;
    errorMessage = "";

    try {
      await api.post("/public/pilot-enquiries", {
        name,
        school,
        role,
        region,
        email,
        message,
      });
      sent = true;
      name = "";
      school = "";
      role = "";
      region = "";
      email = "";
      message = "";
    } catch (error) {
      const status = (error as Error & { status?: number }).status;
      errorMessage =
        status === 429
          ? copy.rateLimitError
          : status === 503
            ? copy.unavailableError
            : copy.generalError;
    } finally {
      sending = false;
    }
  }
</script>

<section
  class="mt-8 overflow-hidden rounded-[2rem] border border-slate-200 bg-slate-50 shadow-sm"
  aria-labelledby="pilot-enquiry-heading"
>
  <div class="grid lg:grid-cols-[1.5fr_0.5fr]">
    <div class="p-6 sm:p-8 lg:p-10">
      <h2
        id="pilot-enquiry-heading"
        class="text-2xl font-black text-slate-950 sm:text-3xl"
      >
        {copy.heading}
      </h2>
      <p class="mt-3 max-w-2xl leading-relaxed text-slate-600">{copy.intro}</p>

      {#if sent}
        <div
          class="mt-8 rounded-[1.5rem] border border-emerald-200 bg-emerald-50 p-6"
          role="status"
        >
          <div class="flex items-start gap-4">
            <CheckCircle2
              class="mt-0.5 h-7 w-7 shrink-0 text-emerald-700"
              aria-hidden="true"
            />
            <div>
              <h3 class="text-xl font-black text-emerald-950">
                {copy.successHeading}
              </h3>
              <p class="mt-2 leading-relaxed text-emerald-900">
                {copy.successText}
              </p>
            </div>
          </div>
        </div>
      {:else}
        <form class="mt-8 grid gap-5 sm:grid-cols-2" onsubmit={submitEnquiry}>
          <label class="grid gap-2 text-start text-sm font-bold text-slate-800">
            <span>{copy.nameLabel}</span>
            <input
              class="min-h-12 rounded-xl border border-slate-300 bg-white px-4 text-base font-normal text-slate-950 outline-none transition focus:border-violet-500 focus:ring-4 focus:ring-violet-100"
              name="name"
              autocomplete="name"
              bind:value={name}
              minlength="2"
              maxlength="120"
              required
            />
          </label>

          <label class="grid gap-2 text-start text-sm font-bold text-slate-800">
            <span>{copy.schoolLabel}</span>
            <input
              class="min-h-12 rounded-xl border border-slate-300 bg-white px-4 text-base font-normal text-slate-950 outline-none transition focus:border-violet-500 focus:ring-4 focus:ring-violet-100"
              name="school"
              autocomplete="organization"
              bind:value={school}
              minlength="2"
              maxlength="160"
              required
            />
          </label>

          <label class="grid gap-2 text-start text-sm font-bold text-slate-800">
            <span>{copy.roleLabel}</span>
            <input
              class="min-h-12 rounded-xl border border-slate-300 bg-white px-4 text-base font-normal text-slate-950 outline-none transition focus:border-violet-500 focus:ring-4 focus:ring-violet-100"
              name="role"
              autocomplete="organization-title"
              bind:value={role}
              minlength="2"
              maxlength="120"
              required
            />
          </label>

          <label class="grid gap-2 text-start text-sm font-bold text-slate-800">
            <span>{copy.regionLabel}</span>
            <input
              class="min-h-12 rounded-xl border border-slate-300 bg-white px-4 text-base font-normal text-slate-950 outline-none transition focus:border-violet-500 focus:ring-4 focus:ring-violet-100"
              name="region"
              autocomplete="country-name"
              bind:value={region}
              minlength="2"
              maxlength="120"
              required
            />
          </label>

          <label
            class="grid gap-2 text-start text-sm font-bold text-slate-800 sm:col-span-2"
          >
            <span>{copy.emailLabel}</span>
            <input
              class="min-h-12 rounded-xl border border-slate-300 bg-white px-4 text-base font-normal text-slate-950 outline-none transition focus:border-violet-500 focus:ring-4 focus:ring-violet-100"
              name="email"
              type="email"
              autocomplete="email"
              inputmode="email"
              bind:value={email}
              maxlength="254"
              required
            />
          </label>

          <label
            class="grid gap-2 text-start text-sm font-bold text-slate-800 sm:col-span-2"
          >
            <span>{copy.messageLabel}</span>
            <textarea
              class="min-h-36 resize-y rounded-xl border border-slate-300 bg-white p-4 text-base font-normal leading-relaxed text-slate-950 outline-none transition focus:border-violet-500 focus:ring-4 focus:ring-violet-100"
              name="message"
              bind:value={message}
              minlength="10"
              maxlength="2000"
              aria-describedby="pilot-message-hint"
              required
            ></textarea>
            <span
              id="pilot-message-hint"
              class="text-sm font-medium leading-relaxed text-slate-500"
              >{copy.messageHint}</span
            >
          </label>

          {#if errorMessage}
            <div
              class="flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-start text-sm font-semibold leading-relaxed text-rose-900 sm:col-span-2"
              role="alert"
            >
              <AlertCircle class="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
              <span>{errorMessage}</span>
            </div>
          {/if}

          <div class="sm:col-span-2">
            <button
              type="submit"
              disabled={sending}
              class="inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-2xl bg-violet-700 px-6 py-3 font-bold text-white shadow-lg shadow-violet-900/15 transition hover:bg-violet-800 disabled:cursor-wait disabled:opacity-70 sm:w-auto"
            >
              <Send class="h-5 w-5 rtl:rotate-180" aria-hidden="true" />
              {sending ? copy.submittingLabel : copy.submitLabel}
            </button>
          </div>
        </form>
      {/if}
    </div>

    <aside
      class="border-t border-slate-200 bg-white p-6 text-start sm:p-8 lg:border-s lg:border-t-0 lg:p-10"
    >
      <div
        class="grid h-12 w-12 place-items-center rounded-2xl bg-violet-100 text-violet-700"
      >
        <Mail class="h-6 w-6" aria-hidden="true" />
      </div>
      <h3 class="mt-5 text-xl font-black text-slate-950">
        {copy.directHeading}
      </h3>
      <p class="mt-3 leading-relaxed text-slate-600">{copy.directText}</p>
      <a
        class="mt-6 inline-flex min-h-11 items-center justify-center rounded-xl border border-slate-200 bg-white px-4 py-2 font-bold text-violet-800 shadow-sm transition hover:border-violet-300 hover:bg-violet-50"
        href="mailto:support@classherohub.com?subject=Class%20Hero%20Hub%20pilot%20enquiry"
      >
        {copy.directLabel}
      </a>
    </aside>
  </div>
</section>
