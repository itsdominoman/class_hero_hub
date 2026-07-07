<script lang="ts">
  let { label, value = $bindable('') } = $props<{ label: string; value: string }>();
</script>

<label class="block text-sm font-semibold text-slate-700">
  {label}
  <input class="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 font-normal" bind:value />
</label>
