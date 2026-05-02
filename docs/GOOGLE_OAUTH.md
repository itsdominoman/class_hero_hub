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
        - `https://families.loginto.me/api/auth/google/callback` (Production)
4.  **Environment Variables:**
    - Copy the Client ID and Client Secret into your `.env` file.
    - Set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `GOOGLE_REDIRECT_URI`.
    - Add authorized parent emails to `PARENT_EMAILS` (comma-separated).
