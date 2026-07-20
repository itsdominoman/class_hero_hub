import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';


const source = fs.readFileSync(new URL('../src/lib/nativePushNotifications.ts', import.meta.url), 'utf8');
const layout = fs.readFileSync(new URL('../src/routes/+layout.svelte', import.meta.url), 'utf8');
const config = fs.readFileSync(new URL('../capacitor.config.ts', import.meta.url), 'utf8');


test('school-chat push payload handling is opaque and receipt-neutral', () => {
  assert.match(source, /notification_event_id/);
  assert.match(source, /route_type\s*!==\s*'school_chat'/);
  assert.match(source, /\/notifications\/events\/\$\{eventId\}\/target/);
  assert.doesNotMatch(source, /message_body|sender_name|family_id|parent_id/i);
  assert.doesNotMatch(source, /receipt|delivered|read_at|markRead/i);
});


test('runtime registers listeners and channels without prompting', () => {
  const runtime = source.slice(source.indexOf('export async function initializeNativePushRuntime'));
  assert.match(runtime, /school_messages/);
  assert.match(runtime, /urgent_school_messages/);
  assert.match(runtime, /pushNotificationActionPerformed/);
  assert.doesNotMatch(runtime, /requestPermissions/);
  assert.match(config, /presentationOptions:\s*\['sound',\s*'alert'\]/);
});


test('permission request is explicit and logout revokes the installation first', () => {
  assert.match(source, /export async function registerForNativePush[\s\S]*requestPermissions/);
  assert.match(source, /devices\/unregister[\s\S]*installation_id[\s\S]*fcm_token/);
  assert.match(layout, /handleLogout[\s\S]*unregisterNativePush[\s\S]*auth\/logout/);
  assert.match(layout, /pushNotifications\.explanation/);
});
