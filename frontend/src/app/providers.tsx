"use client";

import { QueryClient, QueryClientProvider, QueryCache, MutationCache } from "@tanstack/react-query";
import { useState } from "react";
import { AuthProvider } from "@/context/AuthContext";
import { UnsavedChangesProvider } from "@/context/UnsavedChangesContext";
import { ToastProvider } from "@/context/ToastContext";

function makeQueryClient() {
  return new QueryClient({
    queryCache: new QueryCache({
      onError: (err) => {
        // Log network/API errors globally; UI-level handling is per-component
        console.error("[QueryCache]", err);
      },
    }),
    mutationCache: new MutationCache({
      onError: (err) => {
        console.error("[MutationCache]", err);
      },
    }),
    defaultOptions: {
      queries: {
        staleTime: 60_000,          // 1 min — data fresh without refetch
        gcTime: 5 * 60_000,         // 5 min — keep unused data in cache
        retry: 1,                   // one retry on failure
        refetchOnWindowFocus: false, // avoid surprise refetches
        refetchOnReconnect: true,
      },
      mutations: {
        retry: 0,                   // mutations must not auto-retry (side effects)
      },
    },
  });
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(makeQueryClient);
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <UnsavedChangesProvider>
          <ToastProvider>
            {children}
          </ToastProvider>
        </UnsavedChangesProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}
