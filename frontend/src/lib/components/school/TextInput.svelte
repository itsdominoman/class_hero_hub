<script lang="ts">
  let { label, value = $bindable(''), error = '' } = $props<{ label: string; value: string; error?: string }>();
</script>

<label class="block text-sm font-semibold text-slate-700">
  {label}
  <input class={`mt-1 w-full rounded-lg border px-3 py-2 font-normal ${error ? 'border-red-400 bg-red-50' : 'border-slate-200'}`} bind:value aria-invalid={error ? 'true' : 'false'} />
  {#if error}
    <span class="mt-1 block text-xs font-semibold text-red-600">{error}</span>
  {/if}
</label>
