import { App } from "@capacitor/app";
import type { PluginListenerHandle } from "@capacitor/core";
import { chooseNativeBackAction } from "./back-policy";

let listener: PluginListenerHandle | null = null;
let backButtonExitArmed = false;
let backButtonExitTimer: ReturnType<typeof setTimeout> | null = null;

function resetExitArm() {
  backButtonExitArmed = false;
  if (backButtonExitTimer) clearTimeout(backButtonExitTimer);
  backButtonExitTimer = null;
}

export async function registerNativeBackButtonHandler(
  rootPaths: readonly string[],
) {
  if (listener) return async () => undefined;

  listener = await App.addListener("backButton", ({ canGoBack }) => {
    const routeEvent = new CustomEvent("chh:native-back", { cancelable: true });
    if (!window.dispatchEvent(routeEvent)) return;

    const action = chooseNativeBackAction(
      window.location.pathname,
      rootPaths,
      canGoBack,
      backButtonExitArmed,
    );
    if (action === "history") {
      resetExitArm();
      window.history.back();
      return;
    }
    if (action === "fallback") {
      resetExitArm();
      window.location.assign("/");
      return;
    }
    if (action === "exit") {
      resetExitArm();
      App.exitApp();
      return;
    }

    backButtonExitArmed = true;
    if (backButtonExitTimer) clearTimeout(backButtonExitTimer);
    backButtonExitTimer = setTimeout(() => {
      backButtonExitArmed = false;
      backButtonExitTimer = null;
    }, 2000);
  });

  return async () => {
    const current = listener;
    listener = null;
    resetExitArm();
    await current?.remove();
  };
}
