<script lang="ts">
  import { _ } from 'svelte-i18n';

  let { value = $bindable('active') } = $props<{ value: string }>();
</script>

<label class="block text-sm font-semibold text-slate-700">
  {$_('school.status')}
  <select class="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 font-normal" bind:value>
    <option value="active">{$_('school.active')}</option>
    <option value="inactive">{$_('school.inactive')}</option>
  </select>
</label>
