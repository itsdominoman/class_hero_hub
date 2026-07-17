export type NativeBackAction = "history" | "fallback" | "arm-exit" | "exit";

export function chooseNativeBackAction(
  path: string,
  rootPaths: readonly string[],
  canGoBack: boolean,
  exitArmed: boolean,
): NativeBackAction {
  if (!rootPaths.includes(path)) return canGoBack ? "history" : "fallback";
  return exitArmed ? "exit" : "arm-exit";
}
