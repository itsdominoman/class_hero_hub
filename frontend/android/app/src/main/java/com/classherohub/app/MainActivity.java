package com.classherohub.app;

import android.os.Bundle;
import android.view.View;

import androidx.core.view.WindowCompat;
import androidx.core.view.WindowInsetsControllerCompat;

import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(GoogleAuthPlugin.class);
        registerPlugin(SecureStoragePlugin.class);
        super.onCreate(savedInstanceState);

        // Preserve Capacitor's complete WebChromeClient implementation while
        // replacing only its WebView audio-capture permission decision.
        getBridge().getWebView().setWebChromeClient(new AudioCaptureWebChromeClient(getBridge()));

        // Android 15 enforces edge-to-edge for targetSdk 35. CHH's shell is
        // light, so system-bar icons must be dark and legible.
        final View decorView = getWindow().getDecorView();
        final WindowInsetsControllerCompat controller =
                WindowCompat.getInsetsController(getWindow(), decorView);
        controller.setAppearanceLightStatusBars(true);
        controller.setAppearanceLightNavigationBars(true);
    }
}
