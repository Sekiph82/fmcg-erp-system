"use client";

import { TrendPoint } from "@/lib/dashboard";

interface SparklineProps {
  data: TrendPoint[];
  color?: string;
  height?: number;
  width?: number;
}

export function Sparkline({ data, color = "#6366f1", height = 36, width = 80 }: SparklineProps) {
  if (!data || data.length < 2) {
    return <div style={{ width, height }} className="opacity-30 bg-gray-100 rounded" />;
  }

  const values = data.map((d) => d.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  const padX = 2;
  const padY = 2;
  const innerW = width - padX * 2;
  const innerH = height - padY * 2;

  const points = values.map((v, i) => {
    const x = padX + (i / (values.length - 1)) * innerW;
    const y = padY + innerH - ((v - min) / range) * innerH;
    return `${x},${y}`;
  });

  const polyline = points.join(" ");
  // Area fill
  const areaPoints = [
    `${padX},${padY + innerH}`,
    ...points,
    `${padX + innerW},${padY + innerH}`,
  ].join(" ");

  const lastVal = values[values.length - 1];
  const firstVal = values[0];
  const trending = lastVal >= firstVal;

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className="overflow-visible"
    >
      <polygon points={areaPoints} fill={color} fillOpacity={0.12} />
      <polyline
        points={polyline}
        fill="none"
        stroke={color}
        strokeWidth={1.5}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      {/* last dot */}
      <circle
        cx={padX + innerW}
        cy={padY + innerH - ((lastVal - min) / range) * innerH}
        r={2.5}
        fill={color}
      />
    </svg>
  );
}

export function TrendBadge({ current, previous }: { current: number; previous: number }) {
  const diff = current - previous;
  const pct = previous !== 0 ? Math.abs((diff / previous) * 100) : 0;
  const up = diff >= 0;
  return (
    <span
      className={`inline-flex items-center gap-0.5 text-xs font-medium px-1.5 py-0.5 rounded-full ${
        up ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-600"
      }`}
    >
      {up ? "↑" : "↓"} {pct.toFixed(0)}%
    </span>
  );
}
