// Locale -> the country whose facts/education that locale's audience sees.
// One place to extend when a locale is added (ru->RU, en->US, es->ES, fr->FR).
export const COUNTRY_BY_LOCALE: Record<string, string> = {
  ru: "RU",
  en: "US",
  es: "ES",
  fr: "FR",
};

export function countryFor(locale: string): string {
  return COUNTRY_BY_LOCALE[locale] ?? "RU";
}
