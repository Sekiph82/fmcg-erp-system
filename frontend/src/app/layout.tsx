import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";
import { Suspense } from "react";
import { NavProgressBar } from "@/components/NavProgressBar";
import { ErrorBoundary } from "@/components/ErrorBoundary";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "POVU ERP",
  description: "POVU — Enterprise Resource Planning",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <Providers>
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
