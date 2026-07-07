<script lang="ts">
  import { _ } from 'svelte-i18n';
  import { Plus } from 'lucide-svelte';
  import NumberInput from './NumberInput.svelte';
  import RowsTable from './RowsTable.svelte';
  import StatusInput from './StatusInput.svelte';
  import TextInput from './TextInput.svelte';

  type Form = {
    code: string;
    name: string;
    name_ar: string;
    sort_order: number;
    status: string;
  };
  type Row = {
    id: number;
    code: string;
    name: string;
    name_ar?: string | null;
    sort_order: number;
    status: string;
  };

  let {
    title,
    rows,
    path,
    form = $bindable(),
    saving = false,
    editing = false,
    onsubmit,
    onedit,
    oncancel,
    onarchive,
    errors = {}
  } = $props<{
    title: string;
    rows: Row[];
    path: string;
    form: Form;
    saving?: boolean;
    editing?: boolean;
    onsubmit: () => void;
    onedit: (row: Row) => void;
    oncancel: () => void;
    onarchive: (path: string, row: Row) => void;
    errors?: Record<string, string>;
  }>();
</script>

<div class="rounded-lg border border-slate-200 bg-white p-5">
  <h2 class="text-lg font-black text-slate-900">{title}</h2>
  <div class="mt-4 grid gap-3 md:grid-cols-5">
    <TextInput label={$_('school.code')} bind:value={form.code} error={errors.code} />
    <TextInput label={$_('school.nameEn')} bind:value={form.name} error={errors.name} />
    <TextInput label={$_('school.nameAr')} bind:value={form.name_ar} />
    <StatusInput bind:value={form.status} />
    <div class="flex items-end gap-2">
      <button class="btn-hero inline-flex w-full items-center justify-center gap-2 rounded-lg" disabled={saving} onclick={onsubmit}>
        {#if editing}{$_('school.save')}{:else}<Plus class="h-4 w-4" />{$_('school.add')}{/if}
      </button>
      {#if editing}
        <button class="btn-secondary rounded-lg px-3" disabled={saving} onclick={oncancel}>{$_('school.cancel')}</button>
      {/if}
    </div>
  </div>
  <details class="mt-3 rounded-lg border border-slate-100 bg-slate-50 px-3 py-2">
    <summary class="cursor-pointer text-xs font-bold uppercase tracking-wide text-slate-500">{$_('school.advanced')}</summary>
    <div class="mt-3 max-w-xs">
      <NumberInput label={$_('school.sortOrderOptional')} bind:value={form.sort_order} />
    </div>
  </details>
  <RowsTable {rows} {onedit} onarchive={(row) => onarchive(path, row)} />
</div>
