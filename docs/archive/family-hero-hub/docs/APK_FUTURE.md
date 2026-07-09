> Historical note: This document was inherited from Family Hero Hub and is preserved as historical context for the Class Hero Hub fork. It may describe old domains, paths, product assumptions, or infrastructure that are not current.

# Future APK Guide (Capacitor)

Family Hero Hub is designed to be mobile-friendly and can be wrapped into an Android/iOS app using Capacitor.

## Prerequisites

- Node.js and npm
- Android Studio (for Android build)

## Steps to add Capacitor later

1.  **Install Capacitor:**
    ```bash
    cd frontend
    npm install @capacitor/core @capacitor/cli @capacitor/android
    ```
2.  **Initialize Capacitor:**
    ```bash
    npx cap init "Family Hero Hub" "com.familyherohub.app" --web-dir dist
    ```
3.  **Add Android Platform:**
    ```bash
    npx cap add android
    ```
4.  **Build and Sync:**
    ```bash
    npm run build
    npx cap sync android
    ```
5.  **Build APK:**
    - Open the `android` folder in Android Studio.
    - Build -> Build Bundle(s) / APK(s) -> Build APK(s).

## Important Considerations

- **API Base URL:** Ensure `API_BASE_URL` in the frontend is correctly set to your public production URL.
- **OAuth on Mobile:** Google OAuth on mobile may require using the `@capacitor-community/google-auth` plugin or configuring specific Android OAuth credentials.
