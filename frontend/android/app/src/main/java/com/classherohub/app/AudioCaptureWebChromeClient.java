package com.classherohub.app;

import android.Manifest;
import android.content.pm.PackageManager;
import android.util.Log;
import android.webkit.PermissionRequest;

import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.core.content.ContextCompat;

import com.getcapacitor.Bridge;
import com.getcapacitor.BridgeWebChromeClient;

import java.util.Arrays;

/**
 * Keeps Capacitor's WebChromeClient behavior while applying a least-privilege
 * permission path for WebView microphone capture.
 */
public final class AudioCaptureWebChromeClient extends BridgeWebChromeClient {
    private static final String VOICE_MIC_TAG = "VoiceMicBridge";
    private final Bridge bridge;
    private final ActivityResultLauncher<String> recordAudioPermissionLauncher;
    private PermissionRequest pendingAudioRequest;

    public AudioCaptureWebChromeClient(Bridge bridge) {
        super(bridge);
        this.bridge = bridge;
        this.recordAudioPermissionLauncher = bridge.registerForActivityResult(
            new ActivityResultContracts.RequestPermission(),
            ignored -> bridge.getActivity().runOnUiThread(this::finishRuntimePermissionRequest)
        );
    }

    @Override
    public void onPermissionRequest(PermissionRequest request) {
        bridge.getActivity().runOnUiThread(() -> handlePermissionRequest(request));
    }

    @Override
    public void onPermissionRequestCanceled(PermissionRequest request) {
        bridge.getActivity().runOnUiThread(() -> {
            if (pendingAudioRequest == request) {
                pendingAudioRequest = null;
            }
            Log.i(VOICE_MIC_TAG, "WebView permission request canceled");
            AudioCaptureWebChromeClient.super.onPermissionRequestCanceled(request);
        });
    }

    private void handlePermissionRequest(PermissionRequest request) {
        boolean recordAudioGranted = ContextCompat.checkSelfPermission(
            bridge.getContext(),
            Manifest.permission.RECORD_AUDIO
        ) == PackageManager.PERMISSION_GRANTED;
        Log.i(
            VOICE_MIC_TAG,
            "WebView permission request resources=" + Arrays.toString(request.getResources())
                + " recordAudioGranted=" + recordAudioGranted
        );

        AudioCapturePermissionPolicy.Action action = AudioCapturePermissionPolicy.actionFor(
            request.getResources(),
            recordAudioGranted
        );
        if (action == AudioCapturePermissionPolicy.Action.GRANT) {
            grantAudioCapture(request);
            return;
        }
        if (action == AudioCapturePermissionPolicy.Action.DENY) {
            deny(request, "unsupported_or_mixed_resources");
            return;
        }
        if (pendingAudioRequest != null) {
            deny(request, "another_audio_request_is_pending");
            return;
        }

        pendingAudioRequest = request;
        try {
            Log.i(VOICE_MIC_TAG, "requesting Android RECORD_AUDIO runtime permission");
            recordAudioPermissionLauncher.launch(Manifest.permission.RECORD_AUDIO);
        } catch (RuntimeException error) {
            pendingAudioRequest = null;
            deny(request, "runtime_permission_launcher_" + error.getClass().getSimpleName());
        }
    }

    private void finishRuntimePermissionRequest() {
        PermissionRequest request = pendingAudioRequest;
        pendingAudioRequest = null;
        if (request == null) {
            return;
        }
        boolean recordAudioGranted = ContextCompat.checkSelfPermission(
            bridge.getContext(),
            Manifest.permission.RECORD_AUDIO
        ) == PackageManager.PERMISSION_GRANTED;
        Log.i(VOICE_MIC_TAG, "Android RECORD_AUDIO result granted=" + recordAudioGranted);
        if (recordAudioGranted) {
            grantAudioCapture(request);
        } else {
            deny(request, "record_audio_not_granted");
        }
    }

    private static void grantAudioCapture(PermissionRequest request) {
        try {
            request.grant(AudioCapturePermissionPolicy.approvedResources());
            Log.i(VOICE_MIC_TAG, "request.grant called resource=RESOURCE_AUDIO_CAPTURE");
        } catch (RuntimeException error) {
            Log.i(VOICE_MIC_TAG, "request.grant failed type=" + error.getClass().getSimpleName());
            deny(request, "grant_failed");
        }
    }

    private static void deny(PermissionRequest request, String reason) {
        try {
            request.deny();
            Log.i(VOICE_MIC_TAG, "request.deny called reason=" + reason);
        } catch (RuntimeException ignored) {
            // Chromium may cancel a request while a runtime permission dialog is open.
        }
    }
}
