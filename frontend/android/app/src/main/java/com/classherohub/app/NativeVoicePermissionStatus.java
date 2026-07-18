package com.classherohub.app;

final class NativeVoicePermissionStatus {
    private NativeVoicePermissionStatus() {}

    static String state(boolean granted, boolean askedBefore, boolean shouldShowRationale) {
        if (granted) return "granted";
        if (shouldShowRationale) return "denied";
        return askedBefore ? "permanently-denied" : "prompt";
    }

    static boolean canPrompt(boolean granted, boolean askedBefore, boolean shouldShowRationale) {
        return !granted && (!askedBefore || shouldShowRationale);
    }
}
