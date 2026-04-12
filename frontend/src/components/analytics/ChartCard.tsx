"use client";

interface ChartCardProps {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  className?: string;
}

export function ChartCard({ title, subtitle, children, className = "" }: ChartCardProps) {
  return (
    <div className={`bg-white rounded-xl border border-gray-100 shadow-sm p-4 ${className}`}>
      <div className="mb-3">
        <p className="text-sm font-semibold text-gray-800">{title}</p>
        {subtitle && <p className="text-xs text-gray-400 mt-0.5">{subtitle}</p>}
      </div>
      {children}
    </div>
  );
}
