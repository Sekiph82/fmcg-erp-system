"use client";

import { TrendPoint, DistributionSlice } from "@/lib/analytics";

interface BarChartProps {
  data: (TrendPoint | DistributionSlice)[];
  color?: string;
  height?: number;
  formatY?: (v: number) => string;
  labelKey?: "date" | "label";
}

const PAD = { top: 10, right: 8, bottom: 28, left: 44 };

export function BarChart({
  data,
  color = "#6366f1",
  height = 160,
  formatY = (v) => v.toLocaleString(undefined, { maximumFractionDigits: 0 }),
  labelKey = "date",
}: BarChartProps) {
  if (!data.length) {
    return <div className="text-xs text-gray-400 text-center py-6">No data</div>;
  }

  const width = 480;
  const innerW = width - PAD.left - PAD.right;
  const innerH = height - PAD.top - PAD.bottom;
  const n = data.length;
  const barW = Math.max(2, innerW / n - 2);

  const values = data.map((d) => (d as TrendPoint).value ?? (d as DistributionSlice).value);
  const maxV = Math.max(...values, 1);

  const ticks = 3;
  const yTickValues = Array.from({ length: ticks + 1 }, (_, i) => (maxV / ticks) * i);

  const xTickIndices = n <= 7
    ? Array.from({ length: n }, (_, i) => i)
    : [0, Math.floor(n / 4), Math.floor(n / 2), Math.floor((3 * n) / 4), n - 1];

  const getLabel = (d: TrendPoint | DistributionSlice, i: number) => {
    if (labelKey === "label") return (d as DistributionSlice).label ?? String(i);
    const raw = (d as TrendPoint).date ?? String(i);
    return raw.length > 5 ? raw.slice(5) : raw;
  };

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="w-full"
      style={{ height }}
      preserveAspectRatio="xMidYMid meet"
    >
      {yTickValues.map((v) => (
        <g key={v}>
          <line
            x1={PAD.left}
            x2={PAD.left + innerW}
            y1={PAD.top + innerH - (v / maxV) * innerH}
            y2={PAD.top + innerH - (v / maxV) * innerH}
            stroke="#f0f0f0"
            strokeWidth={1}
          />
          <text
            x={PAD.left - 3}
            y={PAD.top + innerH - (v / maxV) * innerH}
            textAnchor="end"
            dominantBaseline="middle"
            fontSize={9}
            fill="#9ca3af"
          >
            {formatY(v)}
          </text>
        </g>
      ))}

      {data.map((d, i) => {
        const v = (d as TrendPoint).value ?? (d as DistributionSlice).value;
        const barH = Math.max(1, (v / maxV) * innerH);
        const x = PAD.left + i * (innerW / n) + (innerW / n - barW) / 2;
        const y = PAD.top + innerH - barH;
        return (
          <rect
            key={i}
            x={x}
            y={y}
            width={barW}
            height={barH}
            rx={1.5}
            fill={color}
            fillOpacity={0.8}
          />
        );
      })}

      {xTickIndices.map((i) => (
        <text
          key={i}
          x={PAD.left + i * (innerW / n) + innerW / n / 2}
          y={PAD.top + innerH + 14}
          textAnchor="middle"
          fontSize={8}
          fill="#9ca3af"
        >
          {getLabel(data[i], i)}
        </text>
      ))}
    </svg>
  );
}
