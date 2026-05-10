import { useTranslations } from "next-intl";
import { Link } from "@/i18n/routing";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  const t = useTranslations("errors");
  return (
    <main className="flex min-h-dvh flex-col items-center justify-center gap-4 px-6 text-center">
      <h1 className="text-5xl font-bold">404</h1>
      <p className="max-w-md text-zinc-600">{t("not_found")}</p>
      <Link href="/">
        <Button>{t("go_home")}</Button>
      </Link>
    </main>
  );
}
