"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function GenerationLogRoot() {
  const router = useRouter();
  useEffect(() => { router.replace("/dashboard/recurring-orders"); }, [router]);
  return <div className="p-6 text-slate-500 text-sm">Redirecting...</div>;
}
