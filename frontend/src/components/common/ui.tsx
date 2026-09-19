import { useId, type ButtonHTMLAttributes, type HTMLAttributes, type InputHTMLAttributes, type ReactNode } from "react";

export function Button({ isLoading, fullWidth, size, variant, disabled, className = "", ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { isLoading?: boolean; fullWidth?: boolean; size?: string; variant?: string }) {
  return <button type="button" {...props} disabled={disabled || isLoading} aria-busy={isLoading} className={`button ${fullWidth ? "button--full" : ""} ${variant === "danger" ? "button--danger" : ""} ${className}`} />;
}
export function Input({ label, error, hint, id, ...props }: InputHTMLAttributes<HTMLInputElement> & { label?: string; error?: string; hint?: string }) {
  const generated = useId(); const inputId = id || generated;
  return <div className="field"><label htmlFor={inputId}>{label || <span className="visually-hidden">{props.placeholder || "Input"}</span>}</label><input {...props} id={inputId} aria-invalid={!!error} aria-describedby={error || hint ? `${inputId}-help` : undefined} />{(error || hint) && <small id={`${inputId}-help`} role={error ? "alert" : undefined}>{error || hint}</small>}</div>;
}
export function Card({ className = "", ...props }: HTMLAttributes<HTMLDivElement>) { return <div {...props} className={`card ${className}`} />; }
export function PageHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: ReactNode }) { return <header className="page-header"><div><h1>{title}</h1>{subtitle && <p>{subtitle}</p>}</div>{action}</header>; }
export function EmptyState({ title, description, action }: { title: string; description?: string; action?: ReactNode }) { return <div className="empty-state"><h3>{title}</h3><p>{description}</p>{action}</div>; }
export function ErrorState({ description, onRetry }: { description: string; onRetry?: () => void }) { return <div role="alert"><p>{description}</p>{onRetry && <Button onClick={onRetry}>Retry</Button>}</div>; }
export function LoadingState({ label = "Loading…" }: { label?: string }) { return <p role="status">{label}</p>; }
export function Badge({ children, variant }: { children: ReactNode; variant?: string }) { return <span className={`badge badge--${variant || "default"}`}>{children}</span>; }
export function Avatar({ name, initials, online }: { name: string; initials: string; size?: string; online?: boolean }) { return <span className="avatar" title={`${name}${online ? " (online)" : ""}`}>{initials}</span>; }
