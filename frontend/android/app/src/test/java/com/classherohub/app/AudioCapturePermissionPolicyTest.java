package com.classherohub.app;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertEquals;

import android.webkit.PermissionRequest;
import org.junit.Test;

public class AudioCapturePermissionPolicyTest {
    @Test
    public void grantsOnlyAudioCaptureWhenAndroidPermissionIsGranted() {
        assertEquals(
            AudioCapturePermissionPolicy.Action.GRANT,
            AudioCapturePermissionPolicy.actionFor(
                new String[] { PermissionRequest.RESOURCE_AUDIO_CAPTURE },
                true
            )
        );
        assertArrayEquals(
            new String[] { PermissionRequest.RESOURCE_AUDIO_CAPTURE },
            AudioCapturePermissionPolicy.approvedResources()
        );
    }

    @Test
    public void requestsRecordAudioWheneverAudioCaptureIsNotYetGranted() {
        assertEquals(
            AudioCapturePermissionPolicy.Action.REQUEST_RUNTIME_PERMISSION,
            AudioCapturePermissionPolicy.actionFor(
                new String[] { PermissionRequest.RESOURCE_AUDIO_CAPTURE },
                false
            )
        );
    }

    @Test
    public void aLaterSettingsGrantIsObservedWithoutCachedDenialState() {
        String[] request = new String[] { PermissionRequest.RESOURCE_AUDIO_CAPTURE };
        assertEquals(
            AudioCapturePermissionPolicy.Action.REQUEST_RUNTIME_PERMISSION,
            AudioCapturePermissionPolicy.actionFor(request, false)
        );
        assertEquals(
            AudioCapturePermissionPolicy.Action.GRANT,
            AudioCapturePermissionPolicy.actionFor(request, true)
        );
    }

    @Test
    public void deniesEmptyUnknownAndMixedWebViewResources() {
        assertEquals(AudioCapturePermissionPolicy.Action.DENY, AudioCapturePermissionPolicy.actionFor(null, true));
        assertEquals(AudioCapturePermissionPolicy.Action.DENY, AudioCapturePermissionPolicy.actionFor(new String[0], true));
        assertEquals(
            AudioCapturePermissionPolicy.Action.DENY,
            AudioCapturePermissionPolicy.actionFor(
                new String[] { PermissionRequest.RESOURCE_VIDEO_CAPTURE },
                true
            )
        );
        assertEquals(
            AudioCapturePermissionPolicy.Action.DENY,
            AudioCapturePermissionPolicy.actionFor(
                new String[] {
                    PermissionRequest.RESOURCE_AUDIO_CAPTURE,
                    PermissionRequest.RESOURCE_VIDEO_CAPTURE
                },
                true
            )
        );
    }
}
