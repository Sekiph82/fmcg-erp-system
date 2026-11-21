import { clsx } from "clsx";
import { InputHTMLAttributes, useId } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export function Input({ label, error, className, id, ...props }: InputProps) {
  const auto = useId();
  const fieldId = id ?? auto;   // the label is always tied to its control (screen readers, getByLabel)
  return (
    <div className="flex flex-col gap-1">
      {label && <label htmlFor={fieldId} className="text-sm font-medium text-gray-700">{label}</label>}
      <input
        id={fieldId}
        className={clsx(
          "block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm neon-focus",
          "placeholder:text-gray-400",
          error && "border-red-500 focus:border-red-500",
          className
        )}
        {...props}
      />
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}
