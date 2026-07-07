<script lang="ts">
  import { _ } from 'svelte-i18n';

  type Row = { id: number; name: string; status?: string };

  let {
    label,
    value = $bindable(''),
    rows,
    optional = false,
    error = ''
  } = $props<{ label: string; value: string; rows: Row[]; optional?: boolean; error?: string }>();

  // Only active records can be picked for new relationships; archived/inactive
  // records stay visible in their own tables but are not offered here. The one
  // exception is the row already selected (e.g. an inactive parent kept while
  // editing a child) so its value is not silently dropped by the bound select.
  const selectable = $derived(rows.filter((row: Row) => (row.status ?? 'active') === 'active' || String(row.id) === value));
</script>

<label class="block text-sm font-semibold text-slate-700">
  {label}
  <select class={`mt-1 w-full rounded-lg border px-3 py-2 font-normal ${error ? 'border-red-400 bg-red-50' : 'border-slate-200'}`} bind:value aria-invalid={error ? 'true' : 'false'}>
    <option value="">{optional ? $_('school.none') : $_('school.select')}</option>
    {#each selectable as row}
      <option value={String(row.id)}>{row.name}</option>
    {/each}
  </select>
  {#if error}
    <span class="mt-1 block text-xs font-semibold text-red-600">{error}</span>
  {/if}
</label>
