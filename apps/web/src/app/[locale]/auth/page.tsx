"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useRouter } from "@/i18n/routing";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { otpRequestSchema, otpVerifySchema } from "@jumlaos/shared";
import { ApiError, api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import type { z } from "zod";

type Stage = "phone" | "code";

interface OtpRequestResponse {
  phone: string;
  dev_otp: string | null;
  expires_in: number;
}

export default function AuthPage() {
  const t = useTranslations("auth");
  const tCommon = useTranslations("common");
  const router = useRouter();
  const [stage, setStage] = useState<Stage>("phone");
  const [phone, setPhone] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  const phoneForm = useForm<z.infer<typeof otpRequestSchema>>({
    resolver: zodResolver(otpRequestSchema),
  });
  const codeForm = useForm<z.infer<typeof otpVerifySchema>>({
    resolver: zodResolver(otpVerifySchema),
  });

  async function onPhone(data: z.infer<typeof otpRequestSchema>) {
    setError(null);
    try {
      const res = await api<OtpRequestResponse>("/auth/otp/request", {
        method: "POST",
        body: data,
      });
      setPhone(res.phone);
      codeForm.setValue("phone", res.phone);
      setStage("code");
    } catch (e) {
      setError(e instanceof ApiError ? e.code : tCommon("error_generic"));
    }
  }

  async function onCode(data: z.infer<typeof otpVerifySchema>) {
    setError(null);
    try {
      await api("/auth/otp/verify", { method: "POST", body: data });
      router.push("/dashboard");
    } catch (e) {
      setError(e instanceof ApiError ? e.code : tCommon("error_generic"));
    }
  }

  return (
    <main className="flex min-h-dvh items-center justify-center p-6">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-2xl">{t("title")}</CardTitle>
          {stage === "code" && <CardDescription>{t("code_sent")}</CardDescription>}
        </CardHeader>
        {stage === "phone" ? (
          <form onSubmit={phoneForm.handleSubmit(onPhone)} className="space-y-4">
            <label className="block">
              <span className="mb-1 block text-sm font-medium">{t("phone_label")}</span>
              <Input
                type="tel"
                placeholder={t("phone_placeholder")}
                autoComplete="tel"
                {...phoneForm.register("phone")}
              />
            </label>
            {error && <p className="text-sm text-red-600">{error}</p>}
            <Button type="submit" className="w-full" disabled={phoneForm.formState.isSubmitting}>
              {t("send_otp")}
            </Button>
          </form>
        ) : (
          <form onSubmit={codeForm.handleSubmit(onCode)} className="space-y-4">
            <p className="text-sm text-zinc-600">{phone}</p>
            <label className="block">
              <span className="mb-1 block text-sm font-medium">{t("code_label")}</span>
              <Input
                inputMode="numeric"
                maxLength={6}
                autoComplete="one-time-code"
                {...codeForm.register("code")}
              />
            </label>
            {error && <p className="text-sm text-red-600">{error}</p>}
            <div className="flex gap-2">
              <Button
                type="button"
                variant="ghost"
                onClick={() => setStage("phone")}
                className="flex-1"
              >
                {t("back")}
              </Button>
              <Button type="submit" className="flex-1" disabled={codeForm.formState.isSubmitting}>
                {t("verify")}
              </Button>
            </div>
          </form>
        )}
      </Card>
    </main>
  );
}
