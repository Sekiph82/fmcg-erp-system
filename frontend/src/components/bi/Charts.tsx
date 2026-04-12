"use client";

import {
  ResponsiveContainer, LineChart, Line, BarChart, Bar, AreaChart, Area,
  XAxis, YAxis, Tooltip, CartesianGrid, Legend,
} from "recharts";
import { TrendPoint } from "@/lib/analytics";

// ── Shared tooltip style ──────────────────────────────────────────────────────

const tipStyle = {
  backgroundColor: "#1e293b",
  border: "1px solid rgba(255,255,255,0.08)",
  borderRadius: 8,
  color: "#e2e8f0",
  fontSize: 12,
};

// ── Compact sparkline (no axes, no labels) ────────────────────────────────────

export function Sparkline({ data, color = "#6366f1" }: { data: TrendPoint[]; color?: string }) {
  if (!data?.length) return <div className="h-12 w-full" />;
  return (
    <div className="h-12 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 2, right: 0, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id={`sg-${color.replace("#", "")}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={color} stopOpacity={0.3} />
              <stop offset="95%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <Area
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={1.5}
            fill={`url(#sg-${color.replace("#", "")})`}
            dot={false}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── Full area/line chart with axes ────────────────────────────────────────────

interface LineChartProps {
  data: TrendPoint[];
  color?: string;
  label?: string;
  height?: number;
  formatY?: (v: number) => string;
  formatX?: (v: string) => string;
}

export function TrendLineChart({ data, color = "#6366f1", label = "Value", height = 220, formatY, formatX }: LineChartProps) {
  if (!data?.length) return <div className={`h-[${height}px] flex items-center justify-center text-slate-600 text-sm`}>No data</div>;
  return (
    <div style={{ height }} className="w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="tl-grad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={color} stopOpacity={0.25} />
              <stop offset="95%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="rgba(255,255,255,0.05)" vertical={false} />
          <XAxis
            dataKey="date"
            tick={{ fill: "#475569", fontSize: 10 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={formatX ?? ((v: string) => v.slice(5))}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fill: "#475569", fontSize: 10 }}
            tickLine={false}
            axisLine={false}
            width={50}
            tickFormatter={formatY}
          />
          <Tooltip
            contentStyle={tipStyle}
            labelStyle={{ color: "#94a3b8", marginBottom: 4 }}
            formatter={(v: unknown) => { const n = v as number; return [formatY ? formatY(n) : n.toLocaleString(), label]; }}
          />
          <Area
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={2}
            fill="url(#tl-grad)"
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── Dual-series line chart (plan vs actual) ───────────────────────────────────

interface DualLineProps {
  planned: TrendPoint[];
  actual: TrendPoint[];
  height?: number;
  formatY?: (v: number) => string;
}

export function PlanVsActualChart({ planned, actual, height = 220, formatY }: DualLineProps) {
  const merged = planned.map((p, i) => ({
    date: p.date,
    Planned: p.value,
    Actual: actual[i]?.value ?? 0,
  }));
  return (
    <div style={{ height }} className="w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={merged} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="rgba(255,255,255,0.05)" vertical={false} />
          <XAxis
            dataKey="date"
            tick={{ fill: "#475569", fontSize: 10 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v: string) => v.slice(5)}
            interval="preserveStartEnd"
          />
          <YAxis tick={{ fill: "#475569", fontSize: 10 }} tickLine={false} axisLine={false} width={50} tickFormatter={formatY} />
          <Tooltip contentStyle={tipStyle} />
          <Legend wrapperStyle={{ fontSize: 11, color: "#64748b" }} />
          <Line type="monotone" dataKey="Planned" stroke="#475569" strokeWidth={1.5} dot={false} strokeDasharray="4 3" />
          <Line type="monotone" dataKey="Actual" stroke="#6366f1" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── Bar chart ─────────────────────────────────────────────────────────────────

interface BarChartProps {
  data: { label: string; value: number; count?: number }[];
  color?: string;
  height?: number;
  valueKey?: string;
  formatY?: (v: number) => string;
}

export function HBarChart({ data, color = "#6366f1", height = 220, valueKey = "value", formatY }: BarChartProps) {
  const mapped = data.map(d => ({ name: d.label, [valueKey]: d.value }));
  return (
    <div style={{ height }} className="w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={mapped} margin={{ top: 5, right: 10, left: 0, bottom: 30 }}>
          <CartesianGrid stroke="rgba(255,255,255,0.05)" vertical={false} />
          <XAxis
            dataKey="name"
            tick={{ fill: "#475569", fontSize: 10 }}
            tickLine={false}
            axisLine={false}
            angle={-30}
            textAnchor="end"
          />
          <YAxis tick={{ fill: "#475569", fontSize: 10 }} tickLine={false} axisLine={false} width={55} tickFormatter={formatY} />
          <Tooltip contentStyle={tipStyle} formatter={(v: unknown) => { const n = v as number; return [formatY ? formatY(n) : n.toLocaleString()]; }} />
          <Bar dataKey={valueKey} fill={color} radius={[3, 3, 0, 0]} maxBarSize={40} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── Stacked multi-series bar ──────────────────────────────────────────────────

export function MultiBarChart({
  data,
  series,
  height = 220,
  formatY,
}: {
  data: Record<string, number | string>[];
  series: { key: string; color: string }[];
  height?: number;
  formatY?: (v: number) => string;
}) {
  return (
    <div style={{ height }} className="w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="rgba(255,255,255,0.05)" vertical={false} />
          <XAxis
            dataKey="date"
            tick={{ fill: "#475569", fontSize: 10 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v: string) => v.slice(5)}
            interval="preserveStartEnd"
          />
          <YAxis tick={{ fill: "#475569", fontSize: 10 }} tickLine={false} axisLine={false} width={50} tickFormatter={formatY} />
          <Tooltip contentStyle={tipStyle} formatter={(v: unknown) => { const n = v as number; return [formatY ? formatY(n) : n.toLocaleString()]; }} />
          <Legend wrapperStyle={{ fontSize: 11, color: "#64748b" }} />
          {series.map(s => (
            <Bar key={s.key} dataKey={s.key} fill={s.color} radius={[2, 2, 0, 0]} maxBarSize={20} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
