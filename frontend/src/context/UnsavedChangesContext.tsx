"use client";

import {
  createContext,
  useCallback,
  useContext,
  useRef,
  useState,
} from "react";

interface UnsavedChangesContextValue {
  isDirty: boolean;
  setDirty: (dirty: boolean) => void;
  /** Returns true if navigation should proceed (user confirmed or no dirty state). */
  confirmLeave: () => Promise<boolean>;
}

const UnsavedChangesContext = createContext<UnsavedChangesContextValue | null>(null);

export function UnsavedChangesProvider({ children }: { children: React.ReactNode }) {
  const [isDirty, setIsDirtyState] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const resolveRef = useRef<((ok: boolean) => void) | null>(null);

  const setDirty = useCallback((dirty: boolean) => {
    setIsDirtyState(dirty);
  }, []);

  const confirmLeave = useCallback((): Promise<boolean> => {
    if (!isDirty) return Promise.resolve(true);
    return new Promise((resolve) => {
      resolveRef.current = resolve;
      setShowModal(true);
    });
  }, [isDirty]);

  const handleLeave = () => {
    setShowModal(false);
    setIsDirtyState(false);
    resolveRef.current?.(true);
  };

  const handleStay = () => {
    setShowModal(false);
    resolveRef.current?.(false);
  };

  return (
    <UnsavedChangesContext.Provider value={{ isDirty, setDirty, confirmLeave }}>
      {children}

      {/* ── Confirmation Modal ─────────────────────────────────────────────── */}
      {showModal && (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-sm mx-4 border border-gray-100">
            {/* Icon */}
            <div className="flex items-center justify-center w-12 h-12 rounded-full bg-amber-100 mx-auto mb-4">
              <svg className="w-6 h-6 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
              </svg>
            </div>

            <h3 className="text-base font-semibold text-gray-900 text-center mb-1">
              Unsaved Changes
            </h3>
            <p className="text-sm text-gray-500 text-center mb-6">
              You have unsaved changes on this page. If you leave now, your changes will be lost.
            </p>

            <div className="flex flex-col gap-2">
              <button
                onClick={handleStay}
                className="w-full px-4 py-2.5 text-sm font-semibold text-white bg-indigo-600 rounded-xl hover:bg-indigo-700 transition-colors"
              >
                Stay and Keep Editing
              </button>
              <button
                onClick={handleLeave}
                className="w-full px-4 py-2.5 text-sm font-medium text-gray-600 bg-gray-100 rounded-xl hover:bg-gray-200 transition-colors"
              >
                Leave Without Saving
              </button>
            </div>
          </div>
        </div>
      )}
    </UnsavedChangesContext.Provider>
  );
}

export function useUnsavedChangesContext() {
  const ctx = useContext(UnsavedChangesContext);
  if (!ctx) throw new Error("useUnsavedChangesContext must be inside UnsavedChangesProvider");
  return ctx;
}
