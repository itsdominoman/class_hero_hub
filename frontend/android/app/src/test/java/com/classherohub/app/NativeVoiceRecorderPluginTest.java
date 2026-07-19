package com.classherohub.app;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.io.File;
import java.nio.file.Files;

import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

public class NativeVoiceRecorderPluginTest {
    @Rule public TemporaryFolder temporaryFolder = new TemporaryFolder();

    @Test
    public void permissionStatusDistinguishesPromptDeniedPermanentAndGranted() {
        assertEquals("prompt", NativeVoicePermissionStatus.state(false, false, false));
        assertEquals("denied", NativeVoicePermissionStatus.state(false, true, true));
        assertEquals("permanently-denied", NativeVoicePermissionStatus.state(false, true, false));
        assertEquals("granted", NativeVoicePermissionStatus.state(true, true, false));
        assertTrue(NativeVoicePermissionStatus.canPrompt(false, false, false));
        assertTrue(NativeVoicePermissionStatus.canPrompt(false, true, true));
        assertFalse(NativeVoicePermissionStatus.canPrompt(false, true, false));
    }

    @Test
    public void recorderStartupErrorsExposeOnlySafeNativeStages() {
        assertEquals("recording_cache_failed", NativeVoiceRecorderPlugin.startFailureCode("cache"));
        assertEquals("recording_recorder_failed", NativeVoiceRecorderPlugin.startFailureCode("recorder"));
        assertEquals("recording_configure_failed", NativeVoiceRecorderPlugin.startFailureCode("configure"));
        assertEquals("recording_prepare_failed", NativeVoiceRecorderPlugin.startFailureCode("prepare"));
        assertEquals("recording_start_failed", NativeVoiceRecorderPlugin.startFailureCode("start"));
        assertEquals("recording_start_failed", NativeVoiceRecorderPlugin.startFailureCode("private path or exception"));
    }

    @Test
    public void completedNativeRecordingResultRequiresRealBytesAndDuration() throws Exception {
        NativeVoiceRecordingStore store = new NativeVoiceRecordingStore(temporaryFolder.getRoot());
        File recording = store.createRecordingFile();
        Files.write(recording.toPath(), new byte[] { 0, 0, 0, 24, 102, 116, 121, 112, 77, 52, 65, 32 });
        NativeVoiceRecordingResult result = new NativeVoiceRecordingResult(
            recording,
            store.referenceFor(recording),
            1_250L
        );
        assertTrue(result.sizeBytes() > 0L);
        assertEquals(1_250L, result.durationMillis());
        assertTrue(recording.getAbsolutePath().contains(NativeVoiceRecordingStore.DIRECTORY_NAME));
        assertTrue(recording.getName().endsWith(".m4a"));
        assertEquals("audio/mp4", NativeVoiceRecordingResult.MIME_TYPE);
        assertEquals("mp4", NativeVoiceRecordingResult.CONTAINER);
    }

    @Test
    public void temporaryFilesDeleteAndExpireOnlyInsidePrivateVoiceCache() throws Exception {
        NativeVoiceRecordingStore store = new NativeVoiceRecordingStore(temporaryFolder.getRoot());
        File recording = store.createRecordingFile();
        String reference = store.referenceFor(recording);
        assertFalse(store.delete("../outside.m4a"));
        assertTrue(store.delete(reference));
        assertFalse(recording.exists());

        File expired = store.createRecordingFile();
        expired.setLastModified(System.currentTimeMillis() - NativeVoiceRecordingStore.EXPIRY_MILLIS - 1L);
        store.purgeExpired(System.currentTimeMillis());
        assertFalse(expired.exists());
    }
}
