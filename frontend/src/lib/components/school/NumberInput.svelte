<script lang="ts">
  let { label, value = $bindable(0) } = $props<{ label: string; value: number }>();
</script>

<label class="block text-sm font-semibold text-slate-700">
  {label}
  <input type="number" class="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 font-normal" bind:value />
</label>
