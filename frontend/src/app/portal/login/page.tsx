"use client";
import { PartnerLogin } from "@/components/PartnerLogin";
import { useI18n } from "@/lib/i18n";

export default function PortalLogin() {
  const { t } = useI18n();
  return <PartnerLogin base="portal-self" home="/portal" title={t("portal.login.title")}
    subtitle={t("portal.login.subtitle")}
    helper={t("portal.login.helper")} signupHref="/portal/signup" />;
}
