package com.classherohub.app;

import android.Manifest;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.util.Log;
import android.view.View;

import androidx.core.content.ContextCompat;
import androidx.core.view.WindowCompat;
import androidx.core.view.WindowInsetsControllerCompat;

import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    private static final String VOICE_MIC_TAG = "VoiceMicBridge";
    private AudioCaptureWebChromeClient voiceMicWebChromeClient;

    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(GoogleAuthPlugin.class);
        registerPlugin(SecureStoragePlugin.class);
        super.onCreate(savedInstanceState);

        // Preserve Capacitor's complete WebChromeClient implementation while
        // replacing only its WebView audio-capture permission decision.
        voiceMicWebChromeClient = new AudioCaptureWebChromeClient(getBridge());
        getBridge().getWebView().setWebChromeClient(voiceMicWebChromeClient);
        logVoiceMicBridgeState("installed");

        // Android 15 enforces edge-to-edge for targetSdk 35. CHH's shell is
        // light, so system-bar icons must be dark and legible.
        final View decorView = getWindow().getDecorView();
        final WindowInsetsControllerCompat controller =
                WindowCompat.getInsetsController(getWindow(), decorView);
        controller.setAppearanceLightStatusBars(true);
        controller.setAppearanceLightNavigationBars(true);
    }

    @Override
    protected void onResume() {
        super.onResume();
        logVoiceMicBridgeState("resumed");
    }

    private void logVoiceMicBridgeState(String event) {
        if (getBridge() == null || voiceMicWebChromeClient == null) {
            Log.i(VOICE_MIC_TAG, event + " clientReady=false");
            return;
        }
        String activeClient = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
            ? String.valueOf(getBridge().getWebView().getWebChromeClient() == voiceMicWebChromeClient)
            : "not-verifiable-before-api-26";
        boolean recordAudioGranted = ContextCompat.checkSelfPermission(
            this,
            Manifest.permission.RECORD_AUDIO
        ) == PackageManager.PERMISSION_GRANTED;
        Log.i(
            VOICE_MIC_TAG,
            event + " clientReady=true activeClient=" + activeClient + " recordAudioGranted=" + recordAudioGranted
        );
    }
}
