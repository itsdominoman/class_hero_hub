<script lang="ts">
  import { _ } from 'svelte-i18n';

  type Row = { id: number; name: string };

  let {
    label,
    value = $bindable(''),
    rows,
    optional = false
  } = $props<{ label: string; value: string; rows: Row[]; optional?: boolean }>();
</script>

<label class="block text-sm font-semibold text-slate-700">
  {label}
  <select class="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 font-normal" bind:value>
    <option value="">{optional ? $_('school.none') : $_('school.select')}</option>
    {#each rows as row}
      <option value={String(row.id)}>{row.name}</option>
    {/each}
  </select>
</label>
