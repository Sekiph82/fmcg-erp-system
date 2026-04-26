"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
export default function VisitsRoot() {
  const router = useRouter();
  useEffect(() => { router.replace("/dashboard/van-sales/route"); }, [router]);
  return <div className="p-6 text-slate-500 text-sm">Redirecting…</div>;
}
