"use client";

const OPTIONS = [7, 14, 30, 60, 90] as const;

interface DaysSelectorProps {
  value: number;
  onChange: (d: number) => void;
}

export function DaysSelector({ value, onChange }: DaysSelectorProps) {
  return (
    <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-0.5">
      {OPTIONS.map((d) => (
        <button
          key={d}
          onClick={() => onChange(d)}
          className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
            value === d
              ? "bg-white text-indigo-700 shadow-sm"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          {d}d
        </button>
      ))}
    </div>
  );
}
