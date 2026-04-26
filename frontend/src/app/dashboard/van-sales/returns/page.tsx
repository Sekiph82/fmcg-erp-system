"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
export default function ReturnsRoot() {
  const router = useRouter();
  useEffect(() => { router.replace("/dashboard/van-sales/pos"); }, [router]);
  return <div className="p-6 text-slate-500 text-sm">Redirecting to POS (select RETURN type)…</div>;
}
