<script lang="ts">
  import { filterTimeZoneOptions, getTimeZoneOptions } from "$lib/timezones.js";

  type TimeZoneOption = {
    value: string;
    primaryLabel: string;
    regionName: string;
    offset: string;
  };

  let {
    id = "timezone-selector",
    label,
    value = $bindable(""),
    valid = $bindable(false),
    locale = "en",
    placeholder,
    help,
    noResults,
    invalid,
  } = $props<{
    id?: string;
    label: string;
    value: string;
    valid: boolean;
    locale?: string;
    placeholder: string;
    help: string;
    noResults: string;
    invalid: string;
  }>();

  let open = $state(false);
  let touched = $state(false);
  let query = $state("");
  let activeIndex = $state(0);
  let editing = $state(false);

  const options = $derived(getTimeZoneOptions(locale));
  const selected = $derived(options.find((option) => option.value === value));
  const filtered = $derived(filterTimeZoneOptions(options, query).slice(0, 60));
  const listboxId = $derived(`${id}-listbox`);
  const helpId = $derived(`${id}-help`);
  const errorId = $derived(`${id}-error`);

  $effect(() => {
    if (!editing) {
      query = selected?.primaryLabel || value || "";
      valid = Boolean(selected);
    }
  });

  function selectOption(option: TimeZoneOption) {
    value = option.value;
    query = option.primaryLabel;
    valid = true;
    touched = true;
    editing = false;
    open = false;
  }

  function handleInput(event: Event) {
    query = (event.currentTarget as HTMLInputElement).value;
    value = "";
    valid = false;
    touched = true;
    editing = true;
    activeIndex = 0;
    open = true;
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      open = true;
      activeIndex = Math.min(activeIndex + 1, Math.max(filtered.length - 1, 0));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      open = true;
      activeIndex = Math.max(activeIndex - 1, 0);
    } else if (event.key === "Enter" && open && filtered[activeIndex]) {
      event.preventDefault();
      selectOption(filtered[activeIndex]);
    } else if (event.key === "Escape") {
      event.preventDefault();
      editing = false;
      query = selected?.primaryLabel || "";
      valid = Boolean(selected);
      open = false;
    } else if (event.key === "Tab") {
      open = false;
    }
  }

  function handleBlur() {
    open = false;
    if (!editing && selected) query = selected.primaryLabel;
  }
</script>

<div
  class="relative min-w-0"
  dir={locale.toLocaleLowerCase().startsWith("ar") ? "rtl" : "ltr"}
>
  <label for={id} class="block text-xs font-bold text-slate-600">{label}</label>
  <input
    {id}
    class={`mt-1 min-h-11 w-full min-w-0 rounded-lg border bg-white px-3 py-2 text-sm font-medium text-slate-900 outline-none transition focus:border-hero focus:ring-2 focus:ring-hero/20 ${touched && !valid ? "border-red-400 bg-red-50" : "border-slate-200"}`}
    type="text"
    role="combobox"
    aria-autocomplete="list"
    aria-expanded={open}
    aria-controls={listboxId}
    aria-activedescendant={open && filtered[activeIndex]
      ? `${id}-option-${activeIndex}`
      : undefined}
    aria-invalid={touched && !valid ? "true" : "false"}
    aria-describedby={`${helpId}${touched && !valid ? ` ${errorId}` : ""}`}
    autocomplete="off"
    spellcheck="false"
    {placeholder}
    value={query}
    onfocus={() => {
      open = true;
      activeIndex = 0;
    }}
    oninput={handleInput}
    onkeydown={handleKeydown}
    onblur={handleBlur}
  />

  {#if open}
    <div
      id={listboxId}
      role="listbox"
      class="absolute inset-x-0 z-50 mt-1 max-h-64 w-full overflow-y-auto overflow-x-hidden rounded-xl border border-slate-200 bg-white p-1 shadow-xl"
    >
      {#if filtered.length === 0}
        <p class="px-3 py-4 text-sm text-slate-500">{noResults}</p>
      {:else}
        {#each filtered as option, index (option.value)}
          <button
            id={`${id}-option-${index}`}
            type="button"
            role="option"
            aria-selected={option.value === value}
            class={`block w-full min-w-0 rounded-lg px-3 py-2 text-start hover:bg-slate-100 focus:bg-slate-100 focus:outline-none ${index === activeIndex ? "bg-slate-100" : ""}`}
            onpointerdown={(event) => event.preventDefault()}
            onmouseenter={() => (activeIndex = index)}
            onclick={() => selectOption(option)}
          >
            <span class="block break-words text-sm font-bold text-slate-900"
              >{option.primaryLabel}</span
            >
            <span
              class="mt-0.5 flex min-w-0 flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-slate-500"
            >
              <span class="break-all" dir="ltr">{option.value}</span>
              <span aria-hidden="true">·</span>
              <span dir="ltr">{option.offset}</span>
              {#if option.regionName}<span class="break-words"
                  >{option.regionName}</span
                >{/if}
            </span>
          </button>
        {/each}
      {/if}
    </div>
  {/if}

  <p id={helpId} class="mt-1 text-xs font-medium leading-5 text-slate-500">
    {help}
  </p>
  {#if touched && !valid}
    <p
      id={errorId}
      class="mt-1 text-xs font-semibold text-red-600"
      role="alert"
    >
      {invalid}
    </p>
  {/if}
</div>
