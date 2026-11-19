import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";
import { Suspense } from "react";
import { NavProgressBar } from "@/components/NavProgressBar";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { PwaRegister } from "@/components/PwaRegister";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "POVU ERP",
  description: "POVU — Enterprise Resource Planning",
  applicationName: "POVU ERP",
  appleWebApp: { capable: true, title: "POVU", statusBarStyle: "default" },
  icons: { icon: "/favicon.ico", apple: "/icons/apple-touch-icon.png" },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#4338ca",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <Providers>
          <PwaRegister />
          <ErrorBoundary>
            {/* NavProgressBar uses useSearchParams — must be in Suspense per Next.js */}
            <Suspense>
              <NavProgressBar />
            </Suspense>
            {children}
          </ErrorBoundary>
        </Providers>
      </body>
    </html>
  );
}
