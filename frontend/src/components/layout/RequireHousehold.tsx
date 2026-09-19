import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useHousehold } from "../../context/HouseholdContext";
export function RequireHousehold({ children }: { children: ReactNode }) {
  const { isLoading, isAuthenticated } = useHousehold();
  if (isLoading) return <p role="status">Restoring session…</p>;
  return isAuthenticated ? children : <Navigate to="/" replace />;
}
