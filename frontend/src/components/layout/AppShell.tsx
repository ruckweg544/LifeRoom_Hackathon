import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { useHousehold } from "../../context/HouseholdContext";
export function AppShell({ children }: { children: ReactNode }) {
  const { household } = useHousehold();
  return <div className="app-shell"><aside><strong>LifeRoom</strong><p>{household?.name}</p><nav aria-label="Main navigation">{["", "chat", "chores", "bills", "groceries", "members", "settings"].map(page => <NavLink key={page} end to={`/app${page ? `/${page}` : ""}`}>{page ? page[0].toUpperCase()+page.slice(1) : "Dashboard"}</NavLink>)}</nav></aside><main>{children}</main></div>;
}
