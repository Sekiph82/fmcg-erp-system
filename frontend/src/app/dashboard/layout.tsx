import { DashboardShell } from "@/components/DashboardShell";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { ImpersonationBanner } from "@/components/ImpersonationBanner";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <ProtectedRoute>
      <ImpersonationBanner />
      <DashboardShell>{children}</DashboardShell>
    </ProtectedRoute>
  );
}
