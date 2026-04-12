"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { AuthProvider } from "@/context/AuthContext";
import { UnsavedChangesProvider } from "@/context/UnsavedChangesContext";

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () => new QueryClient({ defaultOptions: { queries: { staleTime: 60_000 } } })
  );
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <UnsavedChangesProvider>
          {children}
        </UnsavedChangesProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}
