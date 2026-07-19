<script lang="ts">
  import { Check, CheckCheck } from 'lucide-svelte';
  import type { MessageReceipt } from '$lib/messaging/types';

  let { receipt, label }: { receipt: MessageReceipt; label: string } = $props();
</script>

<span
  class="inline-flex shrink-0 items-center {receipt.state === 'read' ? 'text-sky-300' : 'text-slate-200'}"
  role="img"
  aria-label={label}
  title={label}
  data-receipt-state={receipt.state}
>
  {#if receipt.state === 'sent'}
    <Check size={13} strokeWidth={2.6} aria-hidden="true" />
  {:else}
    <CheckCheck size={14} strokeWidth={2.5} aria-hidden="true" />
  {/if}
</span>
