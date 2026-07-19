import type { MessageItem, MessageReceipt, MessageReceiptUpdate, OptimisticMessage } from './types';

function isLocal(message: OptimisticMessage): boolean {
  return message.id.startsWith('local:') || message.local_state !== undefined;
}

export function highestServerSequence(messages: OptimisticMessage[]): number {
  return messages.reduce(
    (highest, message) =>
      isLocal(message) || !Number.isSafeInteger(message.sequence)
        ? highest
        : Math.max(highest, message.sequence),
    0
  );
}

const receiptRank = { sent: 0, delivered: 1, read: 2 } as const;

export function mergeMessageReceipt(
  current: MessageReceipt | undefined,
  incoming: MessageReceipt | undefined
): MessageReceipt | undefined {
  if (!incoming) return current;
  if (!current || incoming.policy_version > current.policy_version) return incoming;
  if (incoming.policy_version < current.policy_version) return current;
  return receiptRank[incoming.state] >= receiptRank[current.state]
    ? { ...incoming, delivered: incoming.delivered || current.delivered, read: incoming.read || current.read }
    : { ...current, delivered: current.delivered || incoming.delivered, read: current.read || incoming.read };
}

export function mergeReceiptUpdates(
  current: OptimisticMessage[],
  updates: MessageReceiptUpdate[]
): OptimisticMessage[] {
  if (!updates.length) return current;
  const byId = new Map(updates.map((update) => [update.id, update]));
  const bySequence = new Map(updates.map((update) => [update.sequence, update]));
  return current.map((message) => {
    if (isLocal(message)) return message;
    const update = byId.get(message.id) || bySequence.get(message.sequence);
    return update
      ? { ...message, receipt: mergeMessageReceipt(message.receipt, update.receipt) }
      : message;
  });
}

/** Append/replace only matching server rows; never removes local or historical state. */
export function mergeIncomingMessages(
  current: OptimisticMessage[],
  incoming: MessageItem[]
): OptimisticMessage[] {
  const result = [...current];
  for (const message of incoming) {
    const index = result.findIndex(
      (known) =>
        (!isLocal(known) && known.id === message.id) ||
        (!isLocal(known) && known.sequence === message.sequence)
    );
    if (index >= 0) result[index] = {
      ...result[index],
      ...message,
      receipt: mergeMessageReceipt(result[index].receipt, message.receipt)
    };
    else result.push(message);
  }
  return result.sort((left, right) => {
    const leftLocal = isLocal(left);
    const rightLocal = isLocal(right);
    if (leftLocal !== rightLocal) return leftLocal ? 1 : -1;
    if (left.sequence !== right.sequence) return left.sequence - right.sequence;
    return left.created_at.localeCompare(right.created_at);
  });
}
