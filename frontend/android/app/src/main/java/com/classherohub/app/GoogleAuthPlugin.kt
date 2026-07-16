package com.classherohub.app

import androidx.credentials.CredentialManager
import androidx.credentials.CustomCredential
import androidx.credentials.GetCredentialRequest
import androidx.credentials.exceptions.GetCredentialCancellationException
import androidx.credentials.exceptions.GetCredentialException
import androidx.credentials.exceptions.GetCredentialProviderConfigurationException
import androidx.credentials.exceptions.NoCredentialException
import com.getcapacitor.JSObject
import com.getcapacitor.Plugin
import com.getcapacitor.PluginCall
import com.getcapacitor.PluginMethod
import com.getcapacitor.annotation.CapacitorPlugin
import com.google.android.libraries.identity.googleid.GetGoogleIdOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential
import com.google.android.libraries.identity.googleid.GoogleIdTokenParsingException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

@CapacitorPlugin(name = "GoogleAuth")
class GoogleAuthPlugin : Plugin() {
    @PluginMethod
    fun getGoogleIdToken(call: PluginCall) {
        val clientId = activity.getString(R.string.google_web_client_id)
        if (clientId.isBlank()) {
            call.reject("Native Google login is not configured", "native_google_not_configured")
            return
        }
        val option = GetGoogleIdOption.Builder()
            .setFilterByAuthorizedAccounts(call.getBoolean("filterByAuthorizedAccounts") ?: true)
            .setServerClientId(clientId)
            .build()
        val request = GetCredentialRequest.Builder().addCredentialOption(option).build()

        CoroutineScope(Dispatchers.Main).launch {
            try {
                val result = CredentialManager.create(context).getCredential(activity, request)
                val credential = result.credential
                if (credential is CustomCredential && credential.type == GoogleIdTokenCredential.TYPE_GOOGLE_ID_TOKEN_CREDENTIAL) {
                    try {
                        val data = JSObject()
                        data.put("idToken", GoogleIdTokenCredential.createFrom(credential.data).idToken)
                        call.resolve(data)
                    } catch (error: GoogleIdTokenParsingException) {
                        call.reject("Google ID token credential could not be parsed", "google_id_token_parsing")
                    }
                } else {
                    call.reject("Google sign-in returned an unexpected credential", "credential_unknown")
                }
            } catch (error: NoCredentialException) {
                call.reject("No eligible Google account was found", "no_credential")
            } catch (error: GetCredentialCancellationException) {
                call.reject("Google sign-in was cancelled", "credential_cancelled")
            } catch (error: GetCredentialProviderConfigurationException) {
                call.reject("Google Credential Manager provider is not configured", "provider_configuration")
            } catch (error: GetCredentialException) {
                call.reject("Google Credential Manager failed", "credential_unknown")
            }
        }
    }
}
