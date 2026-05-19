"use client";

interface HelpButtonProps {
  onClick: () => void;
  className?: string;
}

export function HelpButton({ onClick, className = "" }: HelpButtonProps) {
  return (
    <button
      onClick={onClick}
      aria-label="Open help"
      className={`flex h-8 w-8 items-center justify-center rounded-full border border-cyan-500/30 bg-cyan-500/10 text-cyan-300 text-sm font-bold hover:bg-cyan-500/20 hover:border-cyan-400/50 transition-colors focus:outline-none focus:ring-2 focus:ring-cyan-500/50 ${className}`}
    >
      ?
    </button>
  );
}
