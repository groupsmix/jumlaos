import { useTranslations } from "next-intl";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";

export default function DashboardPage() {
  const t = useTranslations("dashboard");
  // The real fetch happens in a client component child; this layout is a server
  // component so we avoid leaking auth state at the page boundary.
  return (
    <main className="container py-8">
      <h1 className="mb-6 text-2xl font-semibold">{t("title")}</h1>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardTitle>{t("outstanding")}</CardTitle>
          <CardDescription className="mt-2 text-2xl text-zinc-900">—</CardDescription>
        </Card>
        <Card>
          <CardTitle>{t("debtor_count")}</CardTitle>
          <CardDescription className="mt-2 text-2xl text-zinc-900">—</CardDescription>
        </Card>
        <Card>
          <CardTitle>{t("overdue_count")}</CardTitle>
          <CardDescription className="mt-2 text-2xl text-zinc-900">—</CardDescription>
        </Card>
        <Card>
          <CardTitle>{t("collections_30d")}</CardTitle>
          <CardDescription className="mt-2 text-2xl text-zinc-900">—</CardDescription>
        </Card>
      </div>
    </main>
  );
}
