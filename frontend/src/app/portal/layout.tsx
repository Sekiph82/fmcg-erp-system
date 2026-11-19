import type { Metadata } from "next";

// Shops and distributors install the portal as its own app ("POVU Shop"), separate from the employee app (M39.S02.T003).
export const metadata: Metadata = {
  title: "POVU Shop",
  manifest: "/povu-shop.webmanifest",
  appleWebApp: { capable: true, title: "POVU Shop", statusBarStyle: "default" },
};

export default function PortalLayout({ children }: { children: React.ReactNode }) {
  return children;
}
