import { browser } from '$app/environment';
import { addMessages, init, locale } from 'svelte-i18n';
import { get } from 'svelte/store';
import { ar, en } from './messages';

export type SupportedLocale = 'en' | 'ar';

export const DEFAULT_LOCALE: SupportedLocale = 'en';
export const SUPPORTED_LOCALES: SupportedLocale[] = ['en', 'ar'];
export const LANGUAGE_STORAGE_KEY = 'familyHeroHub.language';

let initialized = false;

export function isSupportedLocale(value: string | null | undefined): value is SupportedLocale {
  return value === 'en' || value === 'ar';
}

export function localeDirection(value: string | null | undefined): 'ltr' | 'rtl' {
  return value === 'ar' ? 'rtl' : 'ltr';
}

function savedLocale(): SupportedLocale {
  if (!browser) return DEFAULT_LOCALE;
  const stored = window.localStorage.getItem(LANGUAGE_STORAGE_KEY);
  return isSupportedLocale(stored) ? stored : DEFAULT_LOCALE;
}

export function syncDocumentLocale(value: string | null | undefined) {
  if (!browser) return;
  const normalized = isSupportedLocale(value) ? value : DEFAULT_LOCALE;
  document.documentElement.lang = normalized;
  document.documentElement.dir = localeDirection(normalized);
}

export function initI18n() {
  if (!initialized) {
    addMessages('en', en);
    addMessages('ar', ar);
    init({
      fallbackLocale: DEFAULT_LOCALE,
      initialLocale: savedLocale(),
      handleMissingMessage: ({ defaultValue, id }) => defaultValue ?? id
    });
    initialized = true;
  }

  syncDocumentLocale(get(locale));

  if (browser) {
    locale.subscribe((value) => {
      syncDocumentLocale(value);
      if (isSupportedLocale(value)) {
        window.localStorage.setItem(LANGUAGE_STORAGE_KEY, value);
      }
    });
  }
}

export function setLanguage(nextLocale: SupportedLocale) {
  locale.set(nextLocale);
  if (browser) {
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, nextLocale);
  }
  syncDocumentLocale(nextLocale);
}
