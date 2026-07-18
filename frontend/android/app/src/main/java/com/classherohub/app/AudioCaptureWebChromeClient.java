package com.classherohub.app;

import android.Manifest;
import android.content.pm.PackageManager;
import android.webkit.PermissionRequest;

import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.core.content.ContextCompat;

import com.getcapacitor.Bridge;
import com.getcapacitor.BridgeWebChromeClient;

/**
 * Keeps Capacitor's WebChromeClient behavior while applying a least-privilege
 * permission path for WebView microphone capture.
 */
public final class AudioCaptureWebChromeClient extends BridgeWebChromeClient {
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
            AudioCaptureWebChromeClient.super.onPermissionRequestCanceled(request);
        });
    }

    private void handlePermissionRequest(PermissionRequest request) {
        boolean recordAudioGranted = ContextCompat.checkSelfPermission(
            bridge.getContext(),
            Manifest.permission.RECORD_AUDIO
        ) == PackageManager.PERMISSION_GRANTED;

        AudioCapturePermissionPolicy.Action action = AudioCapturePermissionPolicy.actionFor(
            request.getResources(),
            recordAudioGranted
        );
        if (action == AudioCapturePermissionPolicy.Action.GRANT) {
            grantAudioCapture(request);
            return;
        }
        if (action == AudioCapturePermissionPolicy.Action.DENY) {
            deny(request);
            return;
        }
        if (pendingAudioRequest != null) {
            deny(request);
            return;
        }

        pendingAudioRequest = request;
        try {
            recordAudioPermissionLauncher.launch(Manifest.permission.RECORD_AUDIO);
        } catch (RuntimeException error) {
            pendingAudioRequest = null;
            deny(request);
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
        if (recordAudioGranted) {
            grantAudioCapture(request);
        } else {
            deny(request);
        }
    }

    private static void grantAudioCapture(PermissionRequest request) {
        try {
            request.grant(AudioCapturePermissionPolicy.approvedResources());
        } catch (RuntimeException ignored) {
            deny(request);
        }
    }

    private static void deny(PermissionRequest request) {
        try {
            request.deny();
        } catch (RuntimeException ignored) {
            // Chromium may cancel a request while a runtime permission dialog is open.
        }
    }
}
