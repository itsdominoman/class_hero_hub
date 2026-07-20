package com.classherohub.app;

import android.os.Bundle;
import android.os.Build;
import android.content.pm.ApplicationInfo;
import android.util.Log;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;

import androidx.core.graphics.Insets;
import androidx.core.view.WindowCompat;
import androidx.core.view.WindowInsetsCompat;
import androidx.core.view.WindowInsetsControllerCompat;
import androidx.core.view.ViewCompat;

import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    private static final String TAG = "CHHSystemBars";
    private static final String DEBUG_EXTRA = "chh_system_bar_debug";
    // Keep this as the exact ARGB value instead of calling android.graphics.Color
    // during class initialization so host-side JVM tests can load this class.
    private static final int CHH_LIGHT_BACKGROUND = 0xFFF8FAFC;

    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(GoogleAuthPlugin.class);
        registerPlugin(SecureStoragePlugin.class);
        registerPlugin(NativeVoiceRecorderPlugin.class);

        // Use the same edge-to-edge contract on every supported Android version.
        // The WebView's native parent becomes the single owner of system-bar space.
        WindowCompat.setDecorFitsSystemWindows(getWindow(), false);
        super.onCreate(savedInstanceState);

        installSystemBarBoundary();

        // Android 15 enforces edge-to-edge for targetSdk 35. CHH's shell is
        // light, so system-bar icons must be dark and legible.
        final View decorView = getWindow().getDecorView();
        decorView.setBackgroundColor(CHH_LIGHT_BACKGROUND);
        getWindow().setStatusBarColor(CHH_LIGHT_BACKGROUND);
        getWindow().setNavigationBarColor(CHH_LIGHT_BACKGROUND);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            getWindow().setNavigationBarContrastEnforced(false);
        }
        final WindowInsetsControllerCompat controller =
                WindowCompat.getInsetsController(getWindow(), decorView);
        controller.setAppearanceLightStatusBars(true);
        controller.setAppearanceLightNavigationBars(true);
    }

    private void installSystemBarBoundary() {
        final View webView = getBridge().getWebView();
        if (!(webView.getParent() instanceof ViewGroup)) {
            throw new IllegalStateException("CHH WebView must have a native container");
        }

        final ViewGroup container = (ViewGroup) webView.getParent();
        final TextView debugView = createDebugView(container);
        ViewCompat.setOnApplyWindowInsetsListener(container, (view, windowInsets) -> {
            final Insets systemBars = windowInsets.getInsetsIgnoringVisibility(
                    WindowInsetsCompat.Type.systemBars()
                            | WindowInsetsCompat.Type.displayCutout()
            );

            if (needsPaddingUpdate(
                    view.getPaddingLeft(),
                    view.getPaddingTop(),
                    view.getPaddingRight(),
                    view.getPaddingBottom(),
                    systemBars
            )) {
                view.setPadding(
                        systemBars.left,
                        systemBars.top,
                        systemBars.right,
                        systemBars.bottom
                );
            }

            if (isDebuggable()) {
                final String diagnostic = insetDiagnostic(
                        systemBars,
                        view.getPaddingTop(),
                        view.getPaddingBottom(),
                        getResources().getDisplayMetrics().density
                );
                Log.d(TAG, diagnostic);
                if (debugView != null) {
                    debugView.setText(diagnostic);
                }
            }

            // The WebView is measured inside this physical-pixel boundary. Consuming
            // the insets prevents Chromium/CSS from compensating for the same bars.
            return WindowInsetsCompat.CONSUMED;
        });
        ViewCompat.requestApplyInsets(container);
    }

    private TextView createDebugView(ViewGroup container) {
        if (!isDebuggable() || !getIntent().getBooleanExtra(DEBUG_EXTRA, false)) {
            return null;
        }

        final TextView debugView = new TextView(this);
        debugView.setTextColor(0xFFFFFFFF);
        debugView.setBackgroundColor(0xCC111827);
        debugView.setTextSize(12);
        final int padding = Math.round(8 * getResources().getDisplayMetrics().density);
        debugView.setPadding(padding, padding, padding, padding);
        debugView.setElevation(1000);
        container.addView(debugView, new ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
        ));
        return debugView;
    }

    private boolean isDebuggable() {
        return (getApplicationInfo().flags & ApplicationInfo.FLAG_DEBUGGABLE) != 0;
    }

    static boolean needsPaddingUpdate(
            int left,
            int top,
            int right,
            int bottom,
            Insets systemBars
    ) {
        return left != systemBars.left
                || top != systemBars.top
                || right != systemBars.right
                || bottom != systemBars.bottom;
    }

    static String insetDiagnostic(
            Insets systemBars,
            int shellTop,
            int shellBottom,
            float density
    ) {
        return "topInset=" + systemBars.top + "px"
                + " bottomInset=" + systemBars.bottom + "px"
                + " shellTop=" + shellTop + "px"
                + " shellBottom=" + shellBottom + "px"
                + " density=" + density;
    }
}
