<script lang="ts">
  import { onDestroy } from 'svelte';
  import { Search, X } from 'lucide-svelte';

  let {
    id,
    label,
    placeholder,
    help,
    clearLabel,
    value = $bindable(''),
    minCharacters = 2,
    debounceMs = 250,
    disabled = false,
    onquery
  } = $props<{
    id: string;
    label: string;
    placeholder: string;
    help: string;
    clearLabel: string;
    value: string;
    minCharacters?: number;
    debounceMs?: number;
    disabled?: boolean;
    onquery: (query: string) => void | Promise<void>;
  }>();

  let timer: ReturnType<typeof setTimeout> | undefined;
  let lastQuery = '';
  const helpId = $derived(`${id}-help`);

  function scheduleQuery() {
    if (timer) clearTimeout(timer);
    const query = value.trim();
    if (query && !/^\d+$/.test(query) && query.length < minCharacters) return;
    timer = setTimeout(() => {
      if (query === lastQuery) return;
      lastQuery = query;
      void onquery(query);
    }, query ? debounceMs : 0);
  }

  function clear() {
    value = '';
    scheduleQuery();
    document.getElementById(id)?.focus();
  }

  onDestroy(() => {
    if (timer) clearTimeout(timer);
  });
</script>

<label class="block text-sm font-semibold text-slate-700" for={id}>{label}</label>
<div class="relative mt-1">
  <Search class="pointer-events-none absolute start-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
  <input
    {id}
    type="search"
    class="w-full rounded-lg border border-slate-300 py-2.5 pe-10 ps-10 font-medium text-slate-900 placeholder:text-slate-400 focus:border-hero focus:outline-none focus:ring-2 focus:ring-hero/20"
    bind:value
    {placeholder}
    {disabled}
    aria-describedby={helpId}
    oninput={scheduleQuery}
  />
  {#if value}
    <button
      type="button"
      class="absolute end-1.5 top-1/2 inline-flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-md text-slate-500 hover:bg-slate-100 hover:text-slate-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-hero"
      aria-label={clearLabel}
      onclick={clear}
    >
      <X class="h-4 w-4" aria-hidden="true" />
    </button>
  {/if}
</div>
<p id={helpId} class="mt-1 text-xs text-slate-500">{help}</p>
