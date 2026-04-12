"use client";

import { TrendPoint } from "@/lib/analytics";

export interface LineSeries {
  name: string;
  color: string;
  data: TrendPoint[];
  dashed?: boolean;
}

interface LineChartProps {
  series: LineSeries[];
  height?: number;
  yLabel?: string;
  formatY?: (v: number) => string;
  showLegend?: boolean;
}

const PAD = { top: 12, right: 8, bottom: 32, left: 48 };

export function LineChart({
  series,
  height = 180,
  formatY = (v) => v.toLocaleString(undefined, { maximumFractionDigits: 0 }),
  showLegend = true,
}: LineChartProps) {
  if (!series.length || !series[0].data.length) {
    return <div className="text-xs text-gray-400 text-center py-6">No data</div>;
  }

  const width = 480;
  const innerW = width - PAD.left - PAD.right;
  const innerH = height - PAD.top - PAD.bottom;

  const allValues = series.flatMap((s) => s.data.map((d) => d.value));
  const minV = Math.min(0, ...allValues);
  const maxV = Math.max(...allValues, 1);
  const range = maxV - minV || 1;

  const labels = series[0].data.map((d) => d.date);
  const n = labels.length;

  const xOf = (i: number) => PAD.left + (i / Math.max(n - 1, 1)) * innerW;
  const yOf = (v: number) => PAD.top + innerH - ((v - minV) / range) * innerH;

  const ticks = 4;
  const yTickValues = Array.from({ length: ticks + 1 }, (_, i) =>
    minV + (range / ticks) * i
  );

  // x-axis: show ~5 date labels
  const xTickIndices = n <= 7
    ? Array.from({ length: n }, (_, i) => i)
    : [0, Math.floor(n / 4), Math.floor(n / 2), Math.floor((3 * n) / 4), n - 1];

  return (
    <div className="w-full">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full"
        style={{ height }}
        preserveAspectRatio="xMidYMid meet"
      >
        {/* Y grid lines + labels */}
        {yTickValues.map((v) => (
          <g key={v}>
            <line
              x1={PAD.left}
              x2={PAD.left + innerW}
              y1={yOf(v)}
              y2={yOf(v)}
              stroke="#f0f0f0"
              strokeWidth={1}
            />
            <text
              x={PAD.left - 4}
              y={yOf(v)}
              textAnchor="end"
              dominantBaseline="middle"
              fontSize={9}
              fill="#9ca3af"
            >
              {formatY(v)}
            </text>
          </g>
        ))}

        {/* X axis labels */}
        {xTickIndices.map((i) => (
          <text
            key={i}
            x={xOf(i)}
            y={PAD.top + innerH + 14}
            textAnchor="middle"
            fontSize={8}
            fill="#9ca3af"
          >
            {labels[i]?.slice(5)}
          </text>
        ))}

        {/* Series lines + area */}
        {series.map((s) => {
          const pts = s.data.map((d, i) => `${xOf(i)},${yOf(d.value)}`).join(" ");
          const areaBase = yOf(minV);
          const areaPts = [
            `${xOf(0)},${areaBase}`,
            ...s.data.map((d, i) => `${xOf(i)},${yOf(d.value)}`),
            `${xOf(n - 1)},${areaBase}`,
          ].join(" ");

          return (
            <g key={s.name}>
              <polygon points={areaPts} fill={s.color} fillOpacity={0.07} />
              <polyline
                points={pts}
                fill="none"
                stroke={s.color}
                strokeWidth={1.8}
                strokeDasharray={s.dashed ? "4 3" : undefined}
                strokeLinejoin="round"
                strokeLinecap="round"
              />
              {/* last dot */}
              <circle
                cx={xOf(n - 1)}
                cy={yOf(s.data[n - 1]?.value ?? 0)}
                r={2.5}
                fill={s.color}
              />
            </g>
          );
        })}
      </svg>

      {showLegend && series.length > 1 && (
        <div className="flex flex-wrap gap-3 mt-1 ml-12">
          {series.map((s) => (
            <span key={s.name} className="flex items-center gap-1 text-xs text-gray-500">
              <span
                className="inline-block w-4 h-0.5 rounded"
                style={{
                  backgroundColor: s.color,
                  borderTop: s.dashed ? `2px dashed ${s.color}` : undefined,
                  background: s.dashed ? "none" : s.color,
                }}
              />
              {s.name}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
