import type { Metadata, Viewport } from "next";

// Public employee business cards (M42): never indexed by search engines.
export const metadata: Metadata = {
  title: "POVU · Business card",
  robots: { index: false, follow: false, nocache: true },
};

export const viewport: Viewport = { width: "device-width", initialScale: 1, viewportFit: "cover", themeColor: "#0e1620" };

export default function CardLayout({ children }: { children: React.ReactNode }) {
  return children;
}
