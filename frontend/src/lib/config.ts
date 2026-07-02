// Locale-agnostic app config. UI strings never live here — only in Paraglide
// message catalogs (messages/*.json). This is data the SSR layer and future
// features share.

export const SUPPORTED_LOCALES = ["ru", "en"] as const;
export type Locale = (typeof SUPPORTED_LOCALES)[number];

export const DEFAULT_LOCALE: Locale = "ru";

export function isSupportedLocale(value: string): value is Locale {
  return (SUPPORTED_LOCALES as readonly string[]).includes(value);
}
