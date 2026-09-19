import { useState, type FormEvent } from "react";
import { useHousehold } from "../../context/HouseholdContext";
import { choreService } from "../../services/choreService";
import { Modal } from "../common/Modal";
export function AddChoreModal({ isOpen, onClose, onSubmit, initialValues }: { initialValues?: { title: string; assigned_to_id: string | null; due_date: string | null }; isOpen: boolean; onClose: () => void; onSubmit: (p: Parameters<typeof choreService.create>[0]) => Promise<void> }) {
  const { members } = useHousehold(); const [error,setError]=useState(""); const [busy,setBusy]=useState(false);
  async function submit(e: FormEvent<HTMLFormElement>) { e.preventDefault(); const form=e.currentTarget; const data=new FormData(form); setBusy(true); setError("");
    try { await onSubmit({ title:String(data.get("title")).trim(), assigned_to_id:String(data.get("assignee")) || null, due_date:data.get("due") ? new Date(String(data.get("due"))).toISOString() : null }); form.reset(); onClose(); }
    catch(e) { setError(e instanceof Error ? e.message : "Could not save chore"); } finally { setBusy(false); }
  }
  return <Modal title="Add chore" isOpen={isOpen} onClose={onClose}><form onSubmit={submit} className="auth-form">{error && <p role="alert">{error}</p>}<label>Title<input name="title" defaultValue={initialValues?.title} required maxLength={120} /></label><label>Assign to<select name="assignee" defaultValue={initialValues?.assigned_to_id || ""}><option value="">Unassigned</option>{members.map(m=><option key={m.id} value={m.id}>{m.display_name}</option>)}</select></label><label>Due date<input name="due" type="datetime-local" defaultValue={initialValues?.due_date ? `${initialValues.due_date}T18:00` : ""} /><small>Time is in your device’s local timezone. Adjust before saving.</small></label><button className="button" disabled={busy}>Save chore</button></form></Modal>;
}
