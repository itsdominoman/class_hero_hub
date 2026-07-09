> Historical note: This document was inherited from Family Hero Hub and is preserved as historical context for the Class Hero Hub fork. It may describe old domains, paths, product assumptions, or infrastructure that are not current.

# Google OAuth Setup

1.  **Google Cloud Console:**
    - Go to [Google Cloud Console](https://console.cloud.google.com/).
    - Create a new project named "Family Hero Hub".
2.  **OAuth Consent Screen:**
    - Configure the OAuth consent screen.
    - User Type: External.
    - App Name: Family Hero Hub.
    - Add `user.email` and `user.profile` scopes.
3.  **Credentials:**
    - Create "OAuth 2.0 Client IDs" for a "Web application".
    - Authorized Redirect URIs:
        - `http://localhost:8000/api/auth/google/callback` (Local Development)
        - `https://dev.familyherohub.com/api/auth/google/callback` (Europe Dev/Test)
        - `https://familyherohub.com/api/auth/google/callback` (Production)
    - Dev access note: `dev.familyherohub.com` is restricted to trusted IPs and VPN paths, so the browser must be on an allowed network path for the dev OAuth redirect/callback to complete.
    - Authorized JavaScript Origins:
        - `https://dev.familyherohub.com` (Europe Dev/Test)
        - `https://familyherohub.com` (Production)
4.  **Environment Variables:**
    - Copy the Client ID and Client Secret into your `.env` file.
    - Set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `GOOGLE_REDIRECT_URI`.
    - Use `PARENT_EMAILS` only for bootstrap/root-admin emails (comma-separated).
    - Do not use `PARENT_EMAILS` for normal parent onboarding.
    - Normal parent access is handled through registration approval, family invites, and `/admin/users`.
