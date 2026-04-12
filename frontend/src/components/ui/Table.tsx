import { ReactNode } from "react";

interface Column<T> {
  header: string;
  accessor: keyof T | ((row: T) => ReactNode);
  className?: string;
}

interface TableProps<T> {
  columns: Column<T>[];
  data: T[];
  keyField: keyof T | ((row: T) => string);
  emptyMessage?: string;
}

export function Table<T>({ columns, data, keyField, emptyMessage = "No records found." }: TableProps<T>) {
  const getKey = (row: T) =>
    typeof keyField === "function" ? keyField(row) : String(row[keyField]);
  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            {columns.map((col) => (
              <th key={String(col.header)} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-4 py-8 text-center text-gray-400">{emptyMessage}</td>
            </tr>
          ) : (
            data.map((row) => (
              <tr key={getKey(row)} className="hover:bg-gray-50">
                {columns.map((col) => (
                  <td key={String(col.header)} className={`px-4 py-3 ${col.className ?? ""}`}>
                    {typeof col.accessor === "function"
                      ? col.accessor(row)
                      : String(row[col.accessor] ?? "")}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
