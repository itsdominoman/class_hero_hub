import { Capacitor, registerPlugin, type PluginListenerHandle } from '@capacitor/core';

type SystemInsets = {
  top: number;
  right: number;
  bottom: number;
  left: number;
};

type SystemInsetsPlugin = {
  getInsets(): Promise<SystemInsets>;
  addListener(
    eventName: 'insetsChanged',
    listener: (insets: SystemInsets) => void
  ): Promise<PluginListenerHandle>;
};

const NativeSystemInsets = registerPlugin<SystemInsetsPlugin>('SystemInsets');

function applyBottomInset(insets: SystemInsets) {
  const bottom = Number.isFinite(insets.bottom) ? Math.max(0, insets.bottom) : 0;
  document.documentElement.style.setProperty('--native-safe-bottom', `${bottom}px`);
}

export async function registerNativeSystemInsets() {
  if (!Capacitor.isNativePlatform() || Capacitor.getPlatform() !== 'android') {
    return async () => undefined;
  }

  applyBottomInset(await NativeSystemInsets.getInsets());
  const listener = await NativeSystemInsets.addListener('insetsChanged', applyBottomInset);
  return async () => {
    await listener.remove();
    document.documentElement.style.removeProperty('--native-safe-bottom');
  };
}
