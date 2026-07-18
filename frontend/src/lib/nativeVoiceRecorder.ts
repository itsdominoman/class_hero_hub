import { Capacitor, registerPlugin } from '@capacitor/core';

export type NativeVoicePermissionState = 'prompt' | 'denied' | 'permanently-denied' | 'granted';

export type NativeVoiceRecording = {
  durationMs: number;
  mimeType: 'audio/mp4';
  container: 'mp4';
  sizeBytes: number;
  fileReference: string;
  uri: string;
};

interface NativeVoiceRecorderPlugin {
  permissionStatus(): Promise<{ state: NativeVoicePermissionState; canPrompt: boolean }>;
  start(): Promise<{ started: true; mimeType: 'audio/mp4'; container: 'mp4' }>;
  pause(): Promise<void>;
  resume(): Promise<void>;
  stop(): Promise<NativeVoiceRecording>;
  cancel(options?: { fileReference?: string }): Promise<{ cancelled: true }>;
  openSettings(): Promise<void>;
  deleteTemporary(options: { fileReference: string }): Promise<void>;
  purgeTemporary(): Promise<void>;
}

export const NativeVoiceRecorder = registerPlugin<NativeVoiceRecorderPlugin>('NativeVoiceRecorder');

export function isNativeAndroidVoiceRecorder(): boolean {
  return Capacitor.isNativePlatform() && Capacitor.getPlatform() === 'android';
}

export async function nativeRecordingBlob(recording: NativeVoiceRecording): Promise<Blob> {
  const response = await fetch(Capacitor.convertFileSrc(recording.uri), { cache: 'no-store' });
  if (!response.ok) throw new Error('native_recording_unreadable');
  const bytes = await response.arrayBuffer();
  if (!bytes.byteLength || bytes.byteLength !== recording.sizeBytes) {
    throw new Error('native_recording_invalid_size');
  }
  return new Blob([bytes], { type: recording.mimeType });
}

export async function deleteNativeRecording(fileReference: string | null): Promise<void> {
  if (!fileReference || !isNativeAndroidVoiceRecorder()) return;
  await NativeVoiceRecorder.deleteTemporary({ fileReference });
}
