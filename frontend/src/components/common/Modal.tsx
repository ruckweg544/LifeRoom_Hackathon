import { useEffect, useRef, type ReactNode } from "react";
export function Modal({ title, isOpen, onClose, children }: { title: string; isOpen: boolean; onClose: () => void; children: ReactNode }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => { if (isOpen) ref.current?.showModal(); else ref.current?.close(); }, [isOpen]);
  return <dialog ref={ref} aria-label={title} onCancel={onClose} onClose={onClose}><header className="page-header"><h2>{title}</h2><button type="button" onClick={onClose} aria-label="Close dialog">×</button></header>{children}</dialog>;
}
