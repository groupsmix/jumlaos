import { useTranslations } from "next-intl";
import { Link } from "@/i18n/routing";
import { Button } from "@/components/ui/button";

export default function Landing() {
  const t = useTranslations("brand");
  return (
    <main className="flex min-h-dvh flex-col items-center justify-center px-6 text-center">
      <div className="space-y-6">
        <h1 className="text-4xl font-bold tracking-tight md:text-5xl">{t("name")}</h1>
        <p className="mx-auto max-w-xl text-lg text-zinc-600">{t("tagline")}</p>
        <Link href="/auth">
          <Button size="lg">→</Button>
        </Link>
      </div>
    </main>
  );
}
