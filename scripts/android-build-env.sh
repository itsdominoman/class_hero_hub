#!/usr/bin/env bash
# Classroom Hero Hub — Android/JDK build environment loader and validator.
#
# Usage (preferred — keeps the exports in your current shell):
#   source scripts/android-build-env.sh
#
# Running this file directly performs the same validation, but its exports do
# not persist in the calling shell. This file intentionally contains no app
# configuration or secrets.

# Resolve the controlled, user-local toolchain. Explicit caller-provided paths
# remain supported for future automated build jobs.
export JAVA_HOME="${JAVA_HOME:-$HOME/jdk21}"
export ANDROID_HOME="${ANDROID_HOME:-$HOME/android-sdk}"
export ANDROID_SDK_ROOT="${ANDROID_SDK_ROOT:-$ANDROID_HOME}"

# Prepend each directory at most once. Final order: Java, platform-tools,
# command-line tools.
for _chh_path in \
    "$ANDROID_HOME/cmdline-tools/latest/bin" \
    "$ANDROID_HOME/platform-tools" \
    "$JAVA_HOME/bin"; do
    if [ -d "$_chh_path" ]; then
        case ":$PATH:" in
            *":$_chh_path:"*) ;;
            *) PATH="$_chh_path:$PATH" ;;
        esac
    fi
done
unset _chh_path
export PATH

_chh_ok=1

if [ ! -x "$JAVA_HOME/bin/java" ]; then
    echo "ERROR: JAVA_HOME is invalid: '$JAVA_HOME/bin/java' is missing or not executable." >&2
    _chh_ok=0
fi

if [ ! -d "$ANDROID_HOME" ]; then
    echo "ERROR: ANDROID_HOME does not exist: '$ANDROID_HOME'." >&2
    _chh_ok=0
fi

if [ -d "$ANDROID_HOME/platform-tools" ] && ! command -v adb >/dev/null 2>&1; then
    echo "ERROR: platform-tools are present but adb is not on PATH." >&2
    _chh_ok=0
fi

if [ -d "$ANDROID_HOME/cmdline-tools/latest" ] && ! command -v sdkmanager >/dev/null 2>&1; then
    echo "ERROR: command-line tools are present but sdkmanager is not on PATH." >&2
    _chh_ok=0
fi

echo "JAVA_HOME=$JAVA_HOME"
echo "ANDROID_HOME=$ANDROID_HOME"
echo "ANDROID_SDK_ROOT=$ANDROID_SDK_ROOT"
if [ -x "$JAVA_HOME/bin/java" ]; then
    "$JAVA_HOME/bin/java" -version 2>&1 | sed 's/^/java: /'
fi
if command -v adb >/dev/null 2>&1; then
    echo "adb: $(adb version 2>/dev/null | head -1)"
fi
if command -v sdkmanager >/dev/null 2>&1; then
    echo "sdkmanager: $(sdkmanager --version 2>/dev/null | head -1)"
fi

if [ "$_chh_ok" != "1" ]; then
    unset _chh_ok
    echo "android-build-env: environment is INCOMPLETE — see errors above." >&2
    return 1 2>/dev/null || exit 1
fi

unset _chh_ok
echo "android-build-env: OK."
