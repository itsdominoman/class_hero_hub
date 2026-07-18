package com.classherohub.app;

import java.io.File;
import java.io.IOException;

final class NativeVoiceRecordingStore {
    static final String DIRECTORY_NAME = "voice-recordings";
    static final String FILE_SUFFIX = ".m4a";
    static final long EXPIRY_MILLIS = 24L * 60L * 60L * 1000L;

    private final File directory;

    NativeVoiceRecordingStore(File cacheDirectory) {
        directory = new File(cacheDirectory, DIRECTORY_NAME);
    }

    synchronized File createRecordingFile() throws IOException {
        ensureDirectory();
        return File.createTempFile("voice-", FILE_SUFFIX, directory);
    }

    synchronized String referenceFor(File file) throws IOException {
        if (!isManaged(file)) {
            throw new IOException("Recording is outside the private voice cache");
        }
        return file.getName();
    }

    synchronized boolean delete(String reference) {
        File file = resolve(reference);
        return file != null && (!file.exists() || file.delete());
    }

    synchronized void purgeExpired(long nowMillis) {
        File[] files = directory.listFiles();
        if (files == null) return;
        for (File file : files) {
            if (file.isFile() && nowMillis - file.lastModified() >= EXPIRY_MILLIS) {
                file.delete();
            }
        }
    }

    synchronized void purgeAll() {
        File[] files = directory.listFiles();
        if (files == null) return;
        for (File file : files) {
            if (file.isFile()) file.delete();
        }
    }

    private void ensureDirectory() throws IOException {
        if ((!directory.exists() && !directory.mkdirs()) || !directory.isDirectory()) {
            throw new IOException("Private voice cache is unavailable");
        }
    }

    private File resolve(String reference) {
        if (reference == null || reference.isBlank() || !reference.endsWith(FILE_SUFFIX)) return null;
        if (!reference.equals(new File(reference).getName())) return null;
        File candidate = new File(directory, reference);
        try {
            return isManaged(candidate) ? candidate : null;
        } catch (IOException ignored) {
            return null;
        }
    }

    private boolean isManaged(File file) throws IOException {
        return file.getCanonicalFile().getParentFile().equals(directory.getCanonicalFile());
    }
}
