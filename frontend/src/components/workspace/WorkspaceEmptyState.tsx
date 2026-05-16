interface WorkspaceEmptyStateProps {
  title?: string;
  message?: string;
  action?: { label: string; onClick: () => void };
}

export function WorkspaceEmptyState({
  title = "No items yet",
  message,
  action,
}: WorkspaceEmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-20 px-6 text-center">
      <div className="rounded-full bg-gray-100 p-4 mb-4">
        <svg className="h-8 w-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
        </svg>
      </div>
      <p className="text-sm font-medium text-gray-700">{title}</p>
      {message && <p className="mt-1 text-sm text-gray-500 max-w-xs">{message}</p>}
      {action && (
        <button onClick={action.onClick} className="mt-4 glow-button text-sm">
          {action.label}
        </button>
      )}
    </div>
  );
}
