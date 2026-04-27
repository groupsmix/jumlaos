import "../globals.css";
import type { Metadata, Viewport } from "next";
import { Cairo, Inter } from "next/font/google";
import { NextIntlClientProvider } from "next-intl";
import { getMessages } from "next-intl/server";
import { notFound } from "next/navigation";
import { SUPPORTED_LOCALES, type Locale } from "@/i18n/request";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const cairo = Cairo({ subsets: ["arabic", "latin"], variable: "--font-cairo" });

export const metadata: Metadata = {
  title: "JumlaOS — جملة OS",
  description: "Operating system for Moroccan wholesalers",
  manifest: "/manifest.webmanifest",
};

export const viewport: Viewport = {
  themeColor: "#e88812",
  width: "device-width",
  initialScale: 1,
};

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!SUPPORTED_LOCALES.includes(locale as Locale)) notFound();
  const messages = await getMessages();
  const dir = locale === "ar-MA" ? "rtl" : "ltr";

  return (
    <html lang={locale} dir={dir} className={`${inter.variable} ${cairo.variable}`}>
      <body
        className={`${
          locale === "ar-MA" ? "font-arabic" : "font-sans"
        } min-h-dvh bg-zinc-50 text-zinc-900 antialiased`}
      >
        <NextIntlClientProvider locale={locale} messages={messages}>
          {children}
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
