"use client";

import { useEffect } from "react";
import { useUnsavedChangesContext } from "@/context/UnsavedChangesContext";

/**
 * Mark the current page as having unsaved changes.
 *
 * Usage in any form:
 *   const [isDirty, setIsDirty] = useState(false);
 *   useUnsavedChanges(isDirty);
 *
 *   // Set dirty when user edits a field:
 *   onChange={() => setIsDirty(true)}
 *
 *   // Clear dirty after successful save:
 *   setIsDirty(false);
 */
export function useUnsavedChanges(isDirty: boolean) {
  const { setDirty } = useUnsavedChangesContext();

  useEffect(() => {
    setDirty(isDirty);
    // Always clear when the component unmounts
    return () => setDirty(false);
  }, [isDirty, setDirty]);
}
