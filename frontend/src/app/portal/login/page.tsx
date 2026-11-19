"use client";
import { PartnerLogin } from "@/components/PartnerLogin";

export default function PortalLogin() {
  return <PartnerLogin base="portal-self" home="/portal" title="Partner portal"
    subtitle="Distributors and customers: order, track deliveries and see your statement."
    helper="Forgot your password or no account yet? Ask your sales representative for a set-password link." />;
}
