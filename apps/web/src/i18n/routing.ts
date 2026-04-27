import { defineRouting } from "next-intl/routing";
import { createNavigation } from "next-intl/navigation";

export const routing = defineRouting({
  locales: ["ar-MA", "fr-MA"],
  defaultLocale: "ar-MA",
  localePrefix: "always",
});

export const { Link, redirect, usePathname, useRouter } = createNavigation(routing);
