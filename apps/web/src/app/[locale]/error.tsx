"use client";

import { useEffect } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";

export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const t = useTranslations("errors");
  useEffect(() => {
    // Report to Sentry when available (optional peer dep)
    if (typeof window !== "undefined" && process.env.NEXT_PUBLIC_SENTRY_DSN) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (window as any).__sentryReportError?.(error);
    }
    console.error(error);
  }, [error]);
  return (
    <main className="flex min-h-dvh flex-col items-center justify-center gap-4 px-6 text-center">
      <h1 className="text-3xl font-semibold">{t("generic_title")}</h1>
      <p className="max-w-md text-zinc-600">{t("generic_body")}</p>
      <Button onClick={reset}>{t("retry")}</Button>
    </main>
  );
}
