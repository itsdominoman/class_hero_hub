package com.classherohub.app;

import android.Manifest;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.media.MediaMetadataRetriever;
import android.media.MediaRecorder;
import android.net.Uri;
import android.os.Build;
import android.os.SystemClock;
import android.provider.Settings;

import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import com.getcapacitor.annotation.Permission;
import com.getcapacitor.annotation.PermissionCallback;

import java.io.File;

@CapacitorPlugin(
    name = "NativeVoiceRecorder",
    permissions = @Permission(alias = "microphone", strings = Manifest.permission.RECORD_AUDIO)
)
public final class NativeVoiceRecorderPlugin extends Plugin {
    private static final String PERMISSION_PREFERENCES = "native_voice_recorder";
    private static final String ASKED_FOR_MICROPHONE = "asked_for_microphone";
    static final long MIN_VALID_DURATION_MILLIS = 600L;
    private static final String START_STAGE_CACHE = "cache";
    private static final String START_STAGE_RECORDER = "recorder";
    private static final String START_STAGE_CONFIGURE = "configure";
    private static final String START_STAGE_PREPARE = "prepare";
    private static final String START_STAGE_START = "start";

    private enum RecorderState { IDLE, RECORDING, PAUSED }

    private final Object recorderLock = new Object();
    private NativeVoiceRecordingStore store;
    private MediaRecorder recorder;
    private File recordingFile;
    private RecorderState recorderState = RecorderState.IDLE;
    private long startedAtMillis;
    private long pausedAtMillis;
    private long pausedTotalMillis;

    @Override
    public void load() {
        store = new NativeVoiceRecordingStore(getContext().getCacheDir());
        store.purgeExpired(System.currentTimeMillis());
    }

    @PluginMethod
    public void permissionStatus(PluginCall call) {
        call.resolve(permissionStatusObject());
    }

    @PluginMethod
    public void start(PluginCall call) {
        getActivity().runOnUiThread(() -> {
            if (hasMicrophonePermission()) {
                startRecorder(call);
                return;
            }
            JSObject status = permissionStatusObject();
            if (!Boolean.TRUE.equals(status.getBool("canPrompt"))) {
                call.reject("Microphone permission is permanently denied", "permission_permanently_denied");
                return;
            }
            preferences().edit().putBoolean(ASKED_FOR_MICROPHONE, true).apply();
            requestPermissionForAlias("microphone", call, "microphonePermissionCallback");
        });
    }

    @PermissionCallback
    public void microphonePermissionCallback(PluginCall call) {
        if (hasMicrophonePermission()) {
            startRecorder(call);
            return;
        }
        String state = permissionStatusObject().getString("state", "denied");
        String code = "permanently-denied".equals(state) ? "permission_permanently_denied" : "permission_denied";
        call.reject("Microphone permission was not granted", code);
    }

    @PluginMethod
    public void pause(PluginCall call) {
        getActivity().runOnUiThread(() -> {
            synchronized (recorderLock) {
                if (Build.VERSION.SDK_INT < Build.VERSION_CODES.N) {
                    call.reject("Pause requires Android 7 or newer", "pause_unsupported");
                    return;
                }
                if (recorder == null || recorderState != RecorderState.RECORDING) {
                    call.reject("No active recording can be paused", "invalid_state");
                    return;
                }
                try {
                    recorder.pause();
                    pausedAtMillis = SystemClock.elapsedRealtime();
                    recorderState = RecorderState.PAUSED;
                    call.resolve();
                } catch (RuntimeException error) {
                    call.reject("Native recording could not be paused", "pause_failed");
                }
            }
        });
    }

    @PluginMethod
    public void resume(PluginCall call) {
        getActivity().runOnUiThread(() -> {
            synchronized (recorderLock) {
                if (Build.VERSION.SDK_INT < Build.VERSION_CODES.N) {
                    call.reject("Resume requires Android 7 or newer", "resume_unsupported");
                    return;
                }
                if (recorder == null || recorderState != RecorderState.PAUSED) {
                    call.reject("No paused recording can be resumed", "invalid_state");
                    return;
                }
                try {
                    recorder.resume();
                    pausedTotalMillis += Math.max(0L, SystemClock.elapsedRealtime() - pausedAtMillis);
                    pausedAtMillis = 0L;
                    recorderState = RecorderState.RECORDING;
                    call.resolve();
                } catch (RuntimeException error) {
                    call.reject("Native recording could not be resumed", "resume_failed");
                }
            }
        });
    }

    @PluginMethod
    public void stop(PluginCall call) {
        getActivity().runOnUiThread(() -> stopRecorder(call));
    }

    @PluginMethod
    public void cancel(PluginCall call) {
        getActivity().runOnUiThread(() -> {
            String reference = call.getString("fileReference");
            synchronized (recorderLock) {
                releaseRecorder(false);
                if (recordingFile != null) recordingFile.delete();
                recordingFile = null;
                resetTiming();
            }
            if (reference != null) store.delete(reference);
            call.resolve(new JSObject().put("cancelled", true));
        });
    }

    @PluginMethod
    public void deleteTemporary(PluginCall call) {
        String reference = call.getString("fileReference");
        if (reference == null || !store.delete(reference)) {
            call.reject("Temporary recording reference is invalid", "invalid_file_reference");
            return;
        }
        call.resolve();
    }

    @PluginMethod
    public void purgeTemporary(PluginCall call) {
        synchronized (recorderLock) {
            releaseRecorder(false);
            recordingFile = null;
            resetTiming();
        }
        store.purgeAll();
        call.resolve();
    }

    @PluginMethod
    public void openSettings(PluginCall call) {
        Intent intent = new Intent(
            Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
            Uri.fromParts("package", getContext().getPackageName(), null)
        );
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        getContext().startActivity(intent);
        call.resolve();
    }

    @Override
    protected void handleOnDestroy() {
        synchronized (recorderLock) {
            releaseRecorder(false);
            if (recordingFile != null) recordingFile.delete();
            recordingFile = null;
            resetTiming();
        }
        if (store != null) store.purgeAll();
    }

    private void startRecorder(PluginCall call) {
        synchronized (recorderLock) {
            if (recorder != null || recorderState != RecorderState.IDLE) {
                call.reject("A native voice recording is already active", "already_recording");
                return;
            }
            String stage = START_STAGE_CACHE;
            try {
                store.purgeExpired(System.currentTimeMillis());
                recordingFile = store.createRecordingFile();
                stage = START_STAGE_RECORDER;
                recorder = Build.VERSION.SDK_INT >= Build.VERSION_CODES.S
                    ? new MediaRecorder(getContext())
                    : new MediaRecorder();
                stage = START_STAGE_CONFIGURE;
                recorder.setAudioSource(MediaRecorder.AudioSource.MIC);
                recorder.setOutputFormat(MediaRecorder.OutputFormat.MPEG_4);
                recorder.setAudioEncoder(MediaRecorder.AudioEncoder.AAC);
                recorder.setAudioChannels(1);
                recorder.setAudioEncodingBitRate(NativeVoiceRecordingResult.AUDIO_BIT_RATE);
                recorder.setOutputFile(recordingFile.getAbsolutePath());
                stage = START_STAGE_PREPARE;
                recorder.prepare();
                stage = START_STAGE_START;
                recorder.start();
                startedAtMillis = SystemClock.elapsedRealtime();
                pausedAtMillis = 0L;
                pausedTotalMillis = 0L;
                recorderState = RecorderState.RECORDING;
                JSObject result = new JSObject();
                result.put("started", true);
                result.put("stage", "recording");
                result.put("permissionState", "granted");
                result.put("fileCreated", true);
                result.put("mimeType", NativeVoiceRecordingResult.MIME_TYPE);
                result.put("container", NativeVoiceRecordingResult.CONTAINER);
                call.resolve(result);
            } catch (Exception error) {
                releaseRecorder(false);
                if (recordingFile != null) recordingFile.delete();
                recordingFile = null;
                resetTiming();
                call.reject("Native audio recording could not start", startFailureCode(stage));
            }
        }
    }

    static String startFailureCode(String stage) {
        if (START_STAGE_CACHE.equals(stage)) return "recording_cache_failed";
        if (START_STAGE_RECORDER.equals(stage)) return "recording_recorder_failed";
        if (START_STAGE_CONFIGURE.equals(stage)) return "recording_configure_failed";
        if (START_STAGE_PREPARE.equals(stage)) return "recording_prepare_failed";
        return "recording_start_failed";
    }

    private void stopRecorder(PluginCall call) {
        synchronized (recorderLock) {
            if (recorder == null || recordingFile == null || recorderState == RecorderState.IDLE) {
                call.reject("No native voice recording is active", "invalid_state");
                return;
            }
            File completedFile = recordingFile;
            long calculatedDuration = activeDurationMillis();
            if (isTooShort(calculatedDuration)) {
                releaseRecorder(false);
                completedFile.delete();
                recordingFile = null;
                resetTiming();
                call.reject("Native voice recording is too short", "recording_too_short");
                return;
            }
            try {
                recorder.stop();
                releaseRecorder(true);
                long metadataDuration = mediaDurationMillis(completedFile);
                long duration = metadataDuration > 0L ? metadataDuration : calculatedDuration;
                String reference = store.referenceFor(completedFile);
                NativeVoiceRecordingResult result = new NativeVoiceRecordingResult(completedFile, reference, duration);
                recordingFile = null;
                resetTiming();
                call.resolve(result.toJSObject());
            } catch (Exception error) {
                releaseRecorder(false);
                completedFile.delete();
                recordingFile = null;
                resetTiming();
                call.reject("Native audio recording could not be completed", "recording_stop_failed");
            }
        }
    }

    static boolean isTooShort(long durationMillis) {
        return durationMillis < MIN_VALID_DURATION_MILLIS;
    }

    private long activeDurationMillis() {
        long now = SystemClock.elapsedRealtime();
        long currentPause = recorderState == RecorderState.PAUSED ? Math.max(0L, now - pausedAtMillis) : 0L;
        return Math.max(0L, now - startedAtMillis - pausedTotalMillis - currentPause);
    }

    private long mediaDurationMillis(File file) {
        MediaMetadataRetriever retriever = new MediaMetadataRetriever();
        try {
            retriever.setDataSource(file.getAbsolutePath());
            String value = retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION);
            return value == null ? 0L : Long.parseLong(value);
        } catch (Exception ignored) {
            return 0L;
        } finally {
            try {
                retriever.release();
            } catch (Exception ignored) {
                // Metadata probing is best-effort; elapsed time remains available.
            }
        }
    }

    private void releaseRecorder(boolean alreadyStopped) {
        if (recorder == null) {
            recorderState = RecorderState.IDLE;
            return;
        }
        try {
            if (!alreadyStopped) recorder.reset();
        } catch (RuntimeException ignored) {
            // Release remains safe even when a vendor recorder is already invalidated.
        }
        try {
            recorder.release();
        } catch (RuntimeException ignored) {
            // Nothing else can safely recover a failed platform recorder.
        }
        recorder = null;
        recorderState = RecorderState.IDLE;
    }

    private void resetTiming() {
        startedAtMillis = 0L;
        pausedAtMillis = 0L;
        pausedTotalMillis = 0L;
        recorderState = RecorderState.IDLE;
    }

    private boolean hasMicrophonePermission() {
        return ContextCompat.checkSelfPermission(getContext(), Manifest.permission.RECORD_AUDIO)
            == PackageManager.PERMISSION_GRANTED;
    }

    private JSObject permissionStatusObject() {
        boolean granted = hasMicrophonePermission();
        boolean askedBefore = preferences().getBoolean(ASKED_FOR_MICROPHONE, false);
        boolean rationale = ActivityCompat.shouldShowRequestPermissionRationale(
            getActivity(),
            Manifest.permission.RECORD_AUDIO
        );
        JSObject result = new JSObject();
        result.put("state", NativeVoicePermissionStatus.state(granted, askedBefore, rationale));
        result.put("canPrompt", NativeVoicePermissionStatus.canPrompt(granted, askedBefore, rationale));
        return result;
    }

    private SharedPreferences preferences() {
        return getContext().getSharedPreferences(PERMISSION_PREFERENCES, 0);
    }
}
