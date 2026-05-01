"use client";

/**
 * Thin top progress bar that activates during Next.js App Router navigation.
 * CSS-only — no external dependencies.
 */
import { useEffect, useRef, useState } from "react";
import { usePathname, useSearchParams } from "next/navigation";

export function NavProgressBar() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [active, setActive] = useState(false);
  const [width, setWidth] = useState(0);
  const prevRef = useRef<string>(pathname + searchParams.toString());
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    const key = pathname + searchParams.toString();
    if (key === prevRef.current) return;
    prevRef.current = key;

    // Start progress
    setActive(true);
    setWidth(15);

    // Simulate progress
    let w = 15;
    const tick = () => {
      w = w < 80 ? w + (80 - w) * 0.15 : w;
      setWidth(w);
      if (w < 80) rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);

    // Finish after short delay
    const id = setTimeout(() => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      setWidth(100);
      setTimeout(() => { setActive(false); setWidth(0); }, 250);
    }, 300);

    return () => {
      clearTimeout(id);
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [pathname, searchParams]);

  if (!active && width === 0) return null;

  return (
    <div
      className="fixed top-0 left-0 z-[10000] h-[2px] transition-all"
      style={{
        width: `${width}%`,
        background: "linear-gradient(90deg, #6366f1, #06b6d4)",
        boxShadow: "0 0 8px rgba(99,102,241,0.7)",
        opacity: active ? 1 : 0,
        transition: width === 100 ? "width 0.15s ease, opacity 0.25s ease 0.15s" : "width 0.3s ease",
      }}
    />
  );
}
