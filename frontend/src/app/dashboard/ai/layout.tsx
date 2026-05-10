import { AIModeBanner } from "@/components/ai/AIModeBanner";

export default function AILayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <AIModeBanner />
      {children}
    </>
  );
}
