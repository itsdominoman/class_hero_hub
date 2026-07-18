package com.classherohub.app;

import android.webkit.PermissionRequest;

final class AudioCapturePermissionPolicy {
    enum Action {
        GRANT,
        REQUEST_RUNTIME_PERMISSION,
        DENY
    }

    private AudioCapturePermissionPolicy() {}

    static Action actionFor(String[] requestedResources, boolean recordAudioGranted) {
        if (!requestsOnlyAudioCapture(requestedResources)) {
            return Action.DENY;
        }
        return recordAudioGranted ? Action.GRANT : Action.REQUEST_RUNTIME_PERMISSION;
    }

    static boolean requestsOnlyAudioCapture(String[] requestedResources) {
        return requestedResources != null
            && requestedResources.length == 1
            && PermissionRequest.RESOURCE_AUDIO_CAPTURE.equals(requestedResources[0]);
    }

    static String[] approvedResources() {
        return new String[] { PermissionRequest.RESOURCE_AUDIO_CAPTURE };
    }
}
