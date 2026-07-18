package com.classherohub.app;

import static org.junit.Assert.assertTrue;

import android.Manifest;
import android.content.Context;
import android.content.pm.PackageManager;
import android.media.MediaMetadataRetriever;
import android.media.MediaRecorder;
import android.os.Build;
import android.os.ParcelFileDescriptor;
import android.os.SystemClock;

import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;

import java.io.File;

import org.junit.Test;
import org.junit.runner.RunWith;

@RunWith(AndroidJUnit4.class)
public class NativeVoiceRecorderInstrumentedTest {
    @Test
    public void mediaRecorderProducesNonEmptyPrivateM4aWithDuration() throws Exception {
        Context context = InstrumentationRegistry.getInstrumentation().getTargetContext();
        if (context.checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            try (ParcelFileDescriptor ignored = InstrumentationRegistry.getInstrumentation()
                .getUiAutomation()
                .executeShellCommand("pm grant " + context.getPackageName() + " " + Manifest.permission.RECORD_AUDIO)) {
                SystemClock.sleep(300L);
            }
        }
        assertTrue(context.checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED);

        NativeVoiceRecordingStore store = new NativeVoiceRecordingStore(context.getCacheDir());
        File output = store.createRecordingFile();
        MediaRecorder recorder = Build.VERSION.SDK_INT >= Build.VERSION_CODES.S
            ? new MediaRecorder(context)
            : new MediaRecorder();
        try {
            recorder.setAudioSource(MediaRecorder.AudioSource.MIC);
            recorder.setOutputFormat(MediaRecorder.OutputFormat.MPEG_4);
            recorder.setAudioEncoder(MediaRecorder.AudioEncoder.AAC);
            recorder.setAudioChannels(1);
            recorder.setAudioEncodingBitRate(NativeVoiceRecordingResult.AUDIO_BIT_RATE);
            recorder.setOutputFile(output.getAbsolutePath());
            recorder.prepare();
            recorder.start();
            SystemClock.sleep(1_250L);
            recorder.stop();
        } finally {
            recorder.release();
        }

        MediaMetadataRetriever metadata = new MediaMetadataRetriever();
        long duration;
        try {
            metadata.setDataSource(output.getAbsolutePath());
            duration = Long.parseLong(metadata.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION));
        } finally {
            try {
                metadata.release();
            } catch (Exception ignored) {
                // Assertions below still validate the recording output.
            }
        }
        assertTrue("recording should contain bytes", output.length() > 0L);
        assertTrue("recording should contain duration", duration > 0L);
        assertTrue("recording must stay in app cache", output.getCanonicalPath().startsWith(context.getCacheDir().getCanonicalPath()));
        assertTrue(store.delete(store.referenceFor(output)));
    }
}
