"use client";

import { useQuery } from "@tanstack/react-query";
import { aiApi } from "@/lib/aiApi";

export function AIModeBanner() {
  const { data: status } = useQuery({
    queryKey: ["ai-status"],
    queryFn: () => aiApi.status(),
    staleTime: 30_000,
  });

  if (!status || status.mode !== "mock") return null;

  return (
    <div className="mx-6 mt-6 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900 shadow-sm">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="font-semibold">MOCK MODE: Demo AI only. No live LLM is connected.</p>
          <p className="text-xs text-amber-800">
            High-risk AI actions are disabled until a real provider is configured and execution is explicitly enabled.
          </p>
        </div>
        <span className="inline-flex w-fit rounded-full border border-amber-300 bg-white px-3 py-1 text-xs font-semibold text-amber-800">
          {status.provider} / {status.model}
        </span>
      </div>
    </div>
  );
}
