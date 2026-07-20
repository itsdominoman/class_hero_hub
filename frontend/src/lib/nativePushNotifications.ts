import { Capacitor } from '@capacitor/core';
import { PushNotifications } from '@capacitor/push-notifications';
import { api } from '$lib/api';
import {
  getNativePendingNotificationEvent,
  getNativePushToken,
  getOrCreateNativeInstallationId,
  isNativePlatform,
  setNativePendingNotificationEvent,
  setNativePushToken
} from '$lib/nativeAuth';


const APP_PACKAGE = 'com.classherohub.app';
let initialized = false;

export type NativePushStatus =
  | { kind: 'unsupported' }
  | { kind: 'enabled' }
  | { kind: 'denied' }
  | { kind: 'disabled' };


function validEventId(value: unknown): value is string {
  return typeof value === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value);
}

async function registerToken(token: string): Promise<void> {
  await api.post('/notifications/devices/register', {
    installation_id: await getOrCreateNativeInstallationId(),
    platform: 'android',
    app_package: APP_PACKAGE,
    locale: document.documentElement.lang === 'ar' ? 'ar' : 'en',
    fcm_token: token
  });
  await setNativePushToken(token);
}

export async function loadNativePushStatus(): Promise<NativePushStatus> {
  if (!isNativePlatform() || Capacitor.getPlatform() !== 'android') return { kind: 'unsupported' };
  const permission = await PushNotifications.checkPermissions();
  if (permission.receive === 'denied') return { kind: 'denied' };
  if (permission.receive !== 'granted') return { kind: 'disabled' };
  return (await getNativePushToken()) ? { kind: 'enabled' } : { kind: 'disabled' };
}

export async function registerForNativePush(): Promise<'registered' | 'denied' | 'error'> {
  try {
    if (!isNativePlatform() || Capacitor.getPlatform() !== 'android') return 'error';
    let permission = await PushNotifications.checkPermissions();
    if (permission.receive !== 'granted' && permission.receive !== 'denied') {
      permission = await PushNotifications.requestPermissions();
    }
    if (permission.receive !== 'granted') return 'denied';
    const token = await new Promise<string>((resolve, reject) => {
      void (async () => {
        const success = await PushNotifications.addListener('registration', async (result) => {
          await success.remove();
          await failure.remove();
          resolve(result.value);
        });
        const failure = await PushNotifications.addListener('registrationError', async (error) => {
          await success.remove();
          await failure.remove();
          reject(new Error(error.error));
        });
        await PushNotifications.register();
      })();
    });
    await registerToken(token);
    return 'registered';
  } catch {
    return 'error';
  }
}

export async function unregisterNativePush(): Promise<boolean> {
  if (!isNativePlatform() || Capacitor.getPlatform() !== 'android') return true;
  try {
    const token = await getNativePushToken();
    if (token) {
      await api.post('/notifications/devices/unregister', {
        installation_id: await getOrCreateNativeInstallationId(),
        app_package: APP_PACKAGE,
        fcm_token: token
      });
    }
    await setNativePushToken(null);
    await PushNotifications.unregister();
    return true;
  } catch {
    return false;
  }
}

export async function continueNativeNotificationNavigation(): Promise<'opened' | 'pending' | 'discarded' | 'none'> {
  const eventId = await getNativePendingNotificationEvent();
  if (!eventId) return 'none';
  try {
    const target = await api.get(`/notifications/events/${eventId}/target`);
    if (
      target?.route_type !== 'school_chat' ||
      !validEventId(target.conversation_id) ||
      !Number.isSafeInteger(target.membership_id) ||
      target.membership_id <= 0
    ) {
      await setNativePendingNotificationEvent(null);
      return 'discarded';
    }
    await setNativePendingNotificationEvent(null);
    const query = new URLSearchParams({
      conversation: target.conversation_id,
      membership: String(target.membership_id)
    });
    window.location.replace(`/messages?${query.toString()}`);
    return 'opened';
  } catch (error) {
    const status = (error as Error & { status?: number })?.status;
    if (status === 401) return 'pending';
    if (status === 403 || status === 404) {
      await setNativePendingNotificationEvent(null);
      return 'discarded';
    }
    return 'pending';
  }
}

export async function initializeNativePushRuntime(): Promise<void> {
  if (!isNativePlatform() || Capacitor.getPlatform() !== 'android') return;
  if (initialized) {
    await continueNativeNotificationNavigation();
    return;
  }
  initialized = true;
  await PushNotifications.createChannel({
    id: 'school_messages',
    name: 'School messages',
    description: 'New school chat messages',
    importance: 4,
    visibility: 0,
    vibration: true
  });
  await PushNotifications.createChannel({
    id: 'urgent_school_messages',
    name: 'Urgent school messages',
    description: 'Urgent school chat messages',
    importance: 5,
    visibility: 0,
    vibration: true
  });
  await PushNotifications.addListener('registration', (token) => {
    void registerToken(token.value);
  });
  await PushNotifications.addListener('pushNotificationActionPerformed', (action) => {
    const eventId = action.notification?.data?.notification_event_id;
    if (!validEventId(eventId) || action.notification?.data?.route_type !== 'school_chat') return;
    void setNativePendingNotificationEvent(eventId).then(() => continueNativeNotificationNavigation());
  });
  const permission = await PushNotifications.checkPermissions();
  if (permission.receive === 'granted') await PushNotifications.register();
  await continueNativeNotificationNavigation();
}
