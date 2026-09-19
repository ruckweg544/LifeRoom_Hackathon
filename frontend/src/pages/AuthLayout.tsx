import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import "./AuthLayout.css";

export function AuthLayout({ title, subtitle, children }: { title: string; subtitle: string; children: ReactNode }) {
  return (
    <div className="auth-layout">
      <Link to="/" className="auth-layout__brand">
        <span className="auth-layout__logo-mark" aria-hidden="true">
          LR
        </span>
        <span>LifeRoom</span>
      </Link>

      <div className="auth-layout__card">
        <h1 className="auth-layout__title">{title}</h1>
        <p className="auth-layout__subtitle">{subtitle}</p>
        {children}
      </div>
    </div>
  );
}
