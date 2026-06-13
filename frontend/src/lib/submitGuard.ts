/**
 * FIX 3 — anti-double-tap MITIGATION for balance-affecting submits (audit #2/#5).
 *
 * IMPORTANT: this is a MITIGATION, NOT a real concurrency fix. Each guarded
 * button already disables itself while its request is in flight; this only
 * EXTENDS that disabled window to a minimum of ~2 seconds from the moment the
 * action started, so a fast double-tap can't fire a second request in the gap
 * between a quick response and the user's second tap. It reduces accidental
 * duplicate holds / deposits / reversals from rapid taps.
 *
 * It does NOT prevent a deliberate or scripted concurrent request — two requests
 * sent in parallel still both reach the backend. The proper fix is server-side
 * (transaction-level locking, idempotency keys, or DB constraints) and remains
 * outstanding — see PLAN.md "Scope C — Future".
 *
 * Usage: capture `Date.now()` when you set the busy flag true, then in the
 * handler's `finally` call `releaseAfterMinLock(startedAt, () => busy = false)`
 * instead of clearing the flag immediately. Works with whatever per-flow busy
 * state the component already binds its button's `disabled` to.
 */
export const SUBMIT_LOCK_MS = 2000;

export function releaseAfterMinLock(
  startedAt: number,
  release: () => void,
  minLockMs: number = SUBMIT_LOCK_MS,
): void {
  const remaining = minLockMs - (Date.now() - startedAt);
  if (remaining > 0) {
    setTimeout(release, remaining);
  } else {
    release();
  }
}
