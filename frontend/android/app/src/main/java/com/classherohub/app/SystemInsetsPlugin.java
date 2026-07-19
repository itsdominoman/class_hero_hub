package com.classherohub.app;

import android.view.View;

import androidx.core.graphics.Insets;
import androidx.core.view.WindowInsetsCompat;
import androidx.core.view.ViewCompat;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

@CapacitorPlugin(name = "SystemInsets")
public class SystemInsetsPlugin extends Plugin {
    private View insetView;

    @Override
    public void load() {
        getActivity().runOnUiThread(() -> {
            insetView = getBridge().getWebView();
            ViewCompat.setOnApplyWindowInsetsListener(insetView, (view, windowInsets) -> {
                notifyListeners("insetsChanged", payload(windowInsets));
                return windowInsets;
            });
            ViewCompat.requestApplyInsets(insetView);
        });
    }

    @PluginMethod
    public void getInsets(PluginCall call) {
        getActivity().runOnUiThread(() -> {
            View view = insetView != null ? insetView : getBridge().getWebView();
            call.resolve(payload(ViewCompat.getRootWindowInsets(view)));
        });
    }

    private JSObject payload(WindowInsetsCompat windowInsets) {
        Insets insets = windowInsets == null
                ? Insets.NONE
                : windowInsets.getInsetsIgnoringVisibility(
                        WindowInsetsCompat.Type.navigationBars()
                                | WindowInsetsCompat.Type.displayCutout()
                );
        float density = getContext().getResources().getDisplayMetrics().density;
        JSObject result = new JSObject();
        result.put("top", cssPixels(insets.top, density));
        result.put("right", cssPixels(insets.right, density));
        result.put("bottom", cssPixels(insets.bottom, density));
        result.put("left", cssPixels(insets.left, density));
        return result;
    }

    static double cssPixels(int physicalPixels, float density) {
        return density > 0 ? physicalPixels / (double) density : physicalPixels;
    }

    @Override
    protected void handleOnDestroy() {
        if (insetView != null) {
            ViewCompat.setOnApplyWindowInsetsListener(insetView, null);
            insetView = null;
        }
        super.handleOnDestroy();
    }
}
