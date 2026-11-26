"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { tx } from "@/lib/i18n/core";

export default function EcommerceRoot() {
  const router = useRouter();
  useEffect(() => { router.replace("/dashboard/marketing/ecommerce/stores"); }, [router]);
  return <div className="p-6 text-slate-500 text-sm">{tx("Redirecting...")}</div>;
}
