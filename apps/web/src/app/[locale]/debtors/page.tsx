import { useTranslations } from "next-intl";
import { Card } from "@/components/ui/card";

export default function DebtorsPage() {
  const t = useTranslations("debtors");
  return (
    <main className="container py-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">{t("title")}</h1>
        {/* New debtor flow lives in a sheet — placeholder for now. */}
      </div>
      <Card>
        <p className="text-sm text-zinc-500">{t("empty")}</p>
      </Card>
    </main>
  );
}
