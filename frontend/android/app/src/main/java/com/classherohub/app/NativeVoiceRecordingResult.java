package com.classherohub.app;

import android.net.Uri;

import com.getcapacitor.JSObject;

import java.io.File;
import java.io.IOException;

final class NativeVoiceRecordingResult {
    static final String MIME_TYPE = "audio/mp4";
    static final String CONTAINER = "mp4";
    static final int AUDIO_BIT_RATE = 96_000;

    private final File file;
    private final String reference;
    private final long durationMillis;

    NativeVoiceRecordingResult(File file, String reference, long durationMillis) throws IOException {
        if (file == null || !file.isFile() || file.length() <= 0L) {
            throw new IOException("Native recording file is empty");
        }
        if (durationMillis <= 0L) {
            throw new IOException("Native recording duration is empty");
        }
        this.file = file;
        this.reference = reference;
        this.durationMillis = durationMillis;
    }

    JSObject toJSObject() {
        JSObject result = new JSObject();
        result.put("durationMs", durationMillis);
        result.put("mimeType", MIME_TYPE);
        result.put("container", CONTAINER);
        result.put("sizeBytes", file.length());
        result.put("fileReference", reference);
        result.put("uri", Uri.fromFile(file).toString());
        return result;
    }

    long sizeBytes() {
        return file.length();
    }

    long durationMillis() {
        return durationMillis;
    }
}
