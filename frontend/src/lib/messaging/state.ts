import type { MessageItem, OptimisticMessage } from './types';

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
    if (index >= 0) result[index] = { ...result[index], ...message };
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
