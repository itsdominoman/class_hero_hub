<script lang="ts">
  import { _ } from 'svelte-i18n';
  import { Trash2 } from 'lucide-svelte';

  type Row = {
    id: number;
    code: string;
    name: string;
    name_ar?: string | null;
    sort_order: number;
    status: string;
    education_stage_id?: number | null;
    branch_campus_id?: number | null;
    academic_year_id?: number | null;
    grade_level_id?: number | null;
    class_section_id?: number | null;
    subject_id?: number | null;
  };

  let {
    rows,
    extra = () => '',
    onarchive
  } = $props<{
    rows: Row[];
    extra?: (row: Row) => string;
    onarchive: (row: Row) => void;
  }>();

  function statusClass(status: string) {
    return status === 'active' ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-600';
  }
</script>

<div class="mt-5 overflow-x-auto rounded-lg border border-slate-200">
  <table class="min-w-full divide-y divide-slate-200 text-sm">
    <thead class="bg-slate-50 text-left text-xs font-bold uppercase tracking-wide text-slate-500">
      <tr>
        <th class="px-3 py-2">{$_('school.code')}</th>
        <th class="px-3 py-2">{$_('school.nameEn')}</th>
        <th class="px-3 py-2">{$_('school.nameAr')}</th>
        <th class="px-3 py-2">{$_('school.context')}</th>
        <th class="px-3 py-2">{$_('school.status')}</th>
        <th class="px-3 py-2"></th>
      </tr>
    </thead>
    <tbody class="divide-y divide-slate-100 bg-white">
      {#each rows as row}
        <tr>
          <td class="px-3 py-2 font-semibold text-slate-900">{row.code}</td>
          <td class="px-3 py-2">{row.name}</td>
          <td class="px-3 py-2">{row.name_ar || '-'}</td>
          <td class="px-3 py-2 text-slate-500">{extra(row)}</td>
          <td class="px-3 py-2"><span class={`rounded-full px-2 py-1 text-xs font-bold ${statusClass(row.status)}`}>{row.status}</span></td>
          <td class="px-3 py-2 text-right">
            <button class="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 text-slate-500 hover:text-red-600" aria-label={$_('school.archive')} onclick={() => onarchive(row)}>
              <Trash2 class="h-4 w-4" />
            </button>
          </td>
        </tr>
      {:else}
        <tr><td colspan="6" class="px-3 py-6 text-center text-slate-500">{$_('school.empty')}</td></tr>
      {/each}
    </tbody>
  </table>
</div>
