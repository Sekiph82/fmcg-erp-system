"use client";
import { PartnerLogin } from "@/components/PartnerLogin";

export default function SupplierLogin() {
  return <PartnerLogin base="supplier-self" home="/supplier" title="Supplier portal"
    subtitle="Suppliers: see purchase orders, confirm or reschedule deliveries, send invoices and certificates."
    helper="Forgot your password or no account yet? Ask your buyer for a set-password link." />;
}
