"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
export default function ContractPerformanceRoot() {
  const router = useRouter();
  useEffect(() => { router.replace("/dashboard/contracts/reports"); }, [router]);
  return <div className="p-6 text-slate-500 text-sm">Redirecting…</div>;
}
