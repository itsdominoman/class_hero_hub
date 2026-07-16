package com.classherohub.app

import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKeys
import com.getcapacitor.JSObject
import com.getcapacitor.Plugin
import com.getcapacitor.PluginCall
import com.getcapacitor.PluginMethod
import com.getcapacitor.annotation.CapacitorPlugin

@CapacitorPlugin(name = "SecureStorage")
class SecureStoragePlugin : Plugin() {
    private val preferences by lazy {
        EncryptedSharedPreferences.create(
            "chh_secure_prefs",
            MasterKeys.getOrCreate(MasterKeys.AES256_GCM_SPEC),
            context,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
        )
    }

    @PluginMethod
    fun get(call: PluginCall) {
        val key = call.getString("key") ?: return call.reject("key is required", "MISSING_KEY")
        val result = JSObject()
        result.put("value", preferences.getString(key, null))
        call.resolve(result)
    }

    @PluginMethod
    fun set(call: PluginCall) {
        val key = call.getString("key") ?: return call.reject("key is required", "MISSING_KEY")
        val value = call.getString("value") ?: return call.reject("value is required", "MISSING_VALUE")
        preferences.edit().putString(key, value).apply()
        call.resolve()
    }

    @PluginMethod
    fun remove(call: PluginCall) {
        val key = call.getString("key") ?: return call.reject("key is required", "MISSING_KEY")
        preferences.edit().remove(key).apply()
        call.resolve()
    }
}
