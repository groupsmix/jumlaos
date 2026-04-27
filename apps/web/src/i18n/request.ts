import { getRequestConfig } from "next-intl/server";

export const SUPPORTED_LOCALES = ["ar-MA", "fr-MA"] as const;
export type Locale = (typeof SUPPORTED_LOCALES)[number];
export const DEFAULT_LOCALE: Locale = "ar-MA";

export default getRequestConfig(async ({ requestLocale }) => {
  const requested = await requestLocale;
  const locale: Locale = SUPPORTED_LOCALES.includes(requested as Locale)
    ? (requested as Locale)
    : DEFAULT_LOCALE;
  const messages = (await import(`../../messages/${locale}.json`)).default;
  return { locale, messages };
});
