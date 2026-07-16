# APK build-stack replication plan — FHH to CHH

Audit date: 2026-07-14
Scope: read-only audit and implementation plan. No packages, servers, project configuration, signing keys, or services were changed.

## 1. Executive summary

Family Hero Hub (FHH) is a SvelteKit web application wrapped with Capacitor 7 for Android. The Android project is already present at `frontend/android`; it uses the checked-in Gradle wrapper, Android Gradle Plugin 8.7.2, Kotlin 1.9.25, Java 21, and Android SDK platform/compile target 35. The repository has prior debug APKs and a production AAB under `frontend/android/app/build/outputs`.

The normal interactive shell on FHH does not export Java or Android variables and cannot find `java`, `gradle`, or `sdkmanager`. FHH does, however, contain a no-secret loader at `scripts/android-build-env.sh`, which points to `/home/administrator/jdk21` and `/home/administrator/android-sdk`; sourcing it validates a working JDK 21, SDK command-line tools, platform-tools, SDK platform 35, and the Gradle wrapper. This indicates the build stack is user-local/profile-dependent rather than an OS-global installation.

CHH currently has no Android project, Capacitor config, Capacitor packages, JDK, Android SDK, Gradle executable, or APK/AAB outputs. Its frontend is still a web-only SvelteKit package. CHH APKs should not be built directly on FHH: that would mix repositories, branches, app IDs, web assets, and signing context. Replicate the stack on CHH, then build each app where its repository lives and publish only final, checksummed artifacts to a controlled central location.

## 2. Recommendation

Adopt option A: build each app’s APK on its own app server, then copy final artifacts to a central artifact repository/folder. Replicate the FHH Android build stack on CHH restore after this plan is approved. Keep FHH and CHH app IDs, URLs, flavors, branches, web assets, and signing configuration separate.

Do not use FHH as the CHH build host. A dedicated build server (option B) may be worthwhile later, but it adds a third system and does not remove the need to make both repositories reproducible. Central storage should hold release artifacts and provenance, not production signing keys.

## 3. Current FHH APK build stack

Repository status: `/opt/apps/family-hero-hub`, branch `develop`, clean at audit time (`## develop...origin/develop`).

Detected framework:

- SvelteKit/Vite frontend in `frontend`.
- Capacitor 7 Android wrapper; no standalone native app was detected.
- Capacitor packages are locked at CLI/Android/core 7.6.6, with app 7.1.2, browser 7.0.5, and push-notifications 7.0.6 in the installed lockfile.
- No Cordova application was detected, although Capacitor’s generated compatibility module is named `capacitor-cordova-android-plugins`.

Relevant project structure:

```text
frontend/capacitor.config.ts
frontend/android/gradlew
frontend/android/gradle/wrapper/gradle-wrapper.properties
frontend/android/settings.gradle
frontend/android/build.gradle
frontend/android/app/build.gradle
frontend/android/app/src/main/AndroidManifest.xml
frontend/android/capacitor.settings.gradle   # generated
frontend/android/app/capacitor.build.gradle  # generated
```

Relevant package scripts: `npm run build` runs `vite build`; there is no dedicated APK script in `package.json`. The Android build is therefore a two-stage process: produce the web build, synchronize/copy it into the Capacitor Android project, then invoke Gradle. The repository contains `scripts/android-build-env.sh`, which is an environment loader/validator, not an APK builder.

Observed Android configuration:

- Gradle wrapper: 8.11.1 (`gradle-8.11.1-all.zip`).
- Android Gradle Plugin: 8.7.2.
- Kotlin Gradle plugin and Kotlin stdlib: 1.9.25.
- Java source/target and Kotlin JVM target: 21.
- minSdk 23, compileSdk 35, targetSdk 35.
- Flavors: `dev` and `production`; release/debug build types.
- App ID/application ID: `com.familyherohub.app`.
- APK names are customized as `family-hero-hub-<flavor>-<buildType>.apk`.

Toolchain found after sourcing the FHH loader:

- Node v24.15.0; npm 11.14.0.
- Temurin/OpenJDK 21.0.11.
- Gradle wrapper 8.11.1.
- Android SDK command-line tools reporting sdkmanager 12.0.
- Installed SDK packages: `platforms;android-35`, `build-tools;34.0.0`, `build-tools;35.0.0`, and `platform-tools 37.0.0`.
- `JAVA_HOME=/home/administrator/jdk21` and `ANDROID_HOME=/home/administrator/android-sdk`; the loader also sets `ANDROID_SDK_ROOT` to the SDK path and prepends Java, platform-tools, and cmdline-tools to `PATH`.

Build commands: no build command history or dedicated APK script was found. The existing outputs establish the relevant Gradle tasks. Proposed reproducible commands are documented in section 7 and must be validated with a debug smoke build before release signing is attempted.

Observed outputs:

- `frontend/android/app/build/outputs/apk/dev/debug/family-hero-hub-dev-debug.apk`
- `frontend/android/app/build/outputs/apk/production/debug/family-hero-hub-production-debug.apk`
- `frontend/android/app/build/outputs/bundle/productionRelease/app-production-release.aab`
- Intermediate AAB: `frontend/android/app/build/intermediates/intermediary_bundle/productionRelease/packageProductionReleaseBundle/intermediary-bundle.aab`

Signing references: `frontend/android/app/build.gradle` loads `frontend/android/key.properties` and expects `storeFile`, `storePassword`, `keyAlias`, and `keyPassword`. Release tasks validate these properties and the configured keystore before proceeding. Presence was observed, without reading contents:

- `/opt/apps/family-hero-hub/frontend/android/key.properties` — exists, mode 600.
- `/opt/apps/family-hero-hub/frontend/android/upload-keystore.jks` — exists, mode 600.
- `/home/administrator/.android/debug.keystore` — exists, mode 664.

No secret values, passwords, aliases, or keystore contents were read or printed. No signing material should be copied as part of this audit.

## 4. Current CHH build readiness

Repository status: `/opt/apps/class_hero_hub`, branch `main`, with pre-existing local frontend changes visible at audit time. Those changes were preserved.

CHH has:

- Node v24.18.0 and npm 11.16.0.
- SvelteKit/Vite frontend and `node_modules`, but no Capacitor dependencies in `package.json`.
- No `frontend/capacitor.config.ts` and no `frontend/android` project.
- No Java/Javac, global Gradle, Android SDK variables, SDK manager, APKs, or AABs.

CHH therefore cannot build an APK currently. The Node/npm minor-version difference is not the primary blocker; the Android wrapper/project and Java/SDK stack are missing. Versions should initially match FHH’s tested values, especially JDK 21, Gradle wrapper 8.11.1, AGP 8.7.2, compile/target SDK 35, and the Capacitor major/minor line.

## 5. Software stack to replicate on CHH restore

Replicate, in this order:

1. Temurin/OpenJDK 21 for the `administrator` build account.
2. Android command-line tools, `platform-tools`, `platforms;android-35`, and build-tools 35.0.0. Keep build-tools 34.0.0 only if dependency compatibility requires it.
3. The repository’s Gradle wrapper 8.11.1; do not rely on a separately installed Gradle for builds.
4. The CHH frontend’s exact Capacitor packages from its intended lockfile, after a project decision confirms the app ID, app name, native plugins, and web directory. Do not copy FHH’s app configuration wholesale.
5. A CHH-specific no-secret environment loader analogous to FHH’s loader, with `JAVA_HOME`, `ANDROID_HOME`, `ANDROID_SDK_ROOT`, and `PATH` set for the build account.

Use a dedicated build account or tightly controlled `administrator` profile. If builds are later automated, make the environment explicit in the service/job rather than depending on interactive shell startup files. Keep SDK/JDK ownership and permissions consistent, and record checksums/versions in build logs.

## 6. Proposed installation steps (not executed)

The following are proposed commands only. Review package sources, versions, disk space, and outbound network policy before execution.

```bash
cd /opt/apps/class_hero_hub
git status -sb                         # confirm branch and preserve local work

# Install Temurin/OpenJDK 21 using the approved OS/package source,
# or provision it at /home/administrator/jdk21 to match FHH.
# Example shape; do not run without approval:
sudo apt-get update
sudo apt-get install -y openjdk-21-jdk unzip

# Provision Android command-line tools under the approved private path.
# Download URL/version must be pinned and verified before use.
mkdir -p "$HOME/android-sdk/cmdline-tools"
# download and verify the pinned command-line-tools archive
# unzip it into "$HOME/android-sdk/cmdline-tools/latest"

export JAVA_HOME="$HOME/jdk21"              # or the approved JDK path
export ANDROID_HOME="$HOME/android-sdk"
export ANDROID_SDK_ROOT="$ANDROID_HOME"
export PATH="$JAVA_HOME/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/cmdline-tools/latest/bin:$PATH"

yes | sdkmanager --licenses
sdkmanager "platform-tools" "platforms;android-35" "build-tools;35.0.0"

cd /opt/apps/class_hero_hub/frontend
npm ci
# Add/initialize CHH Capacitor packages and Android project only after
# APK-CHH-Project design review; do not copy FHH signing files.
```

The actual JDK installation path must be chosen before implementation. If the FHH user-local layout is adopted, install Temurin 21 at `$HOME/jdk21` and use a CHH-specific loader; otherwise use an explicit system JDK path and document it. No command in this section was executed.

## 7. Build commands

Likely FHH flow, to be verified during an approved smoke-build slice:

```bash
cd /opt/apps/family-hero-hub
source scripts/android-build-env.sh
cd frontend
npm ci
npm run build
npx cap sync android
cd android
./gradlew assembleDevDebug
./gradlew assembleProductionDebug
./gradlew bundleProductionRelease
```

The first two Gradle tasks produce debug APKs without relying on the production release key. The bundle task produces a production AAB and requires the configured release signing properties. Release APK tasks, if required, should use the exact flavor/build type selected in the project and must pass signing validation.

Proposed CHH flow, after the CHH Capacitor project exists and its app-specific configuration is reviewed:

```bash
cd /opt/apps/class_hero_hub
source scripts/android-build-env.sh       # CHH-specific equivalent
cd frontend
npm ci
npm run build
npx cap sync android
cd android
./gradlew assembleDevDebug               # proposed CHH debug flavor, if defined
./gradlew assembleProductionDebug        # proposed CHH production flavor, if defined
./gradlew bundleProductionRelease        # proposed CHH release AAB, after signing setup
```

Expected output pattern is `frontend/android/app/build/outputs/apk/<flavor>/<buildType>/*.apk` and `frontend/android/app/build/outputs/bundle/<flavor>Release/*.aab`. Actual CHH flavor names and filenames must be defined in APK-CHH-Project; do not assume FHH’s names or IDs.

## 8. Artifact storage strategy

Keep transient and app-specific build outputs under each repository’s Android build directory. After validation, copy only final artifacts to a central private location, for example:

```text
/opt/artifacts/apk/fhh/
/opt/artifacts/apk/chh/
```

Use names such as `chh-<version>-<date>-<gitsha>.apk` and `fhh-<version>-<date>-<gitsha>.apk`, alongside `.sha256` checksum files. Record branch, commit, flavor, build type, toolchain versions, and signing mode in a provenance manifest. Do not expose public downloads until authentication, authorization, retention, and disclosure controls are defined.

Object storage may make sense later for retention, off-server durability, CI distribution, and audit history. It should be introduced with private buckets, immutable/versioned objects, lifecycle rules, and access control; it is not needed for initial stack replication.

## 9. Signing key strategy

Do not copy or print FHH signing material. Production keys should live in a controlled private location with restricted permissions, preferably outside the application checkout and injected only for approved release jobs. Avoid scattering production keys across app servers unless a documented availability/build requirement justifies it.

Use separate debug/test signing and release signing identities. CHH must have its own application identity and release-key decision; never reuse FHH’s key or app ID by accident. The FHH audit found only the paths/presence listed in section 3. CHH had no keystore files in the inspected repository. Presence elsewhere on CHH was not inferred and must be checked by an authorized operator during the signing slice without printing contents.

## 10. Risks

- JDK, Gradle, AGP, SDK, and Node drift can make builds non-reproducible.
- Signing keys or passwords may leak through checkouts, logs, shell history, or artifact storage.
- FHH and CHH app IDs, URLs, flavors, notification configuration, and deep links can be mixed.
- Building from the wrong branch or with uncommitted web changes can create an untraceable APK.
- Stale or wrong web assets can be embedded if `npm run build`/Capacitor sync is skipped or points at the wrong backend.
- Android target/compile SDK requirements may change and invalidate old tooling.
- Public APK distribution without access controls can expose test or privileged builds.
- Missing commit/checksum/provenance metadata weakens rollback and incident response.
- Long-lived servers accumulate package and SDK drift unless versions are periodically audited.

## 11. Implementation slices

- **APK-Audit** — this plan only; no mutation.
- **APK-Stack-CHH** — install and validate the JDK/Android SDK/toolchain on CHH restore.
- **APK-CHH-Project** — initialize/add CHH Capacitor Android project and review app-specific IDs, flavors, URLs, plugins, and versioning.
- **APK-Build-Smoke** — build an unsigned/debug APK and inspect package identity and embedded assets.
- **APK-Signing** — configure controlled release signing without copying FHH keys.
- **APK-Artifact-Repo** — create private central artifact directories, naming, checksums, retention, and provenance.

## 12. Final recommendation

**APPROVE STACK REPLICATION PLAN**

Approve the plan for stack replication on CHH restore, subject to a separate implementation approval for each mutation slice. Do not begin release signing or public distribution until CHH’s native project identity and key-management design are reviewed.
