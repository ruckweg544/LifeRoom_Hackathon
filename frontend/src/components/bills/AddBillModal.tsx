import { useState, type FormEvent } from "react";
import { useHousehold } from "../../context/HouseholdContext";
import { billService } from "../../services/billService";
import { Modal } from "../common/Modal";
export function AddBillModal({ isOpen, onClose, onSubmit }: { isOpen: boolean; onClose: () => void; onSubmit: (p: Parameters<typeof billService.create>[0]) => Promise<void> }) {
  const { members,currentMember }=useHousehold(); const [error,setError]=useState(""); const [busy,setBusy]=useState(false);
  async function submit(e: FormEvent<HTMLFormElement>) { e.preventDefault(); const form=e.currentTarget; const data=new FormData(form); const participants=data.getAll("participants").map(String); if (!participants.length) { setError("Select at least one participant"); return; } setBusy(true); setError("");
    try { await onSubmit({title:String(data.get("title")).trim(),amount:Number(data.get("amount")),paid_by_id:String(data.get("payer")),participant_ids:participants}); form.reset(); onClose(); }
    catch(e) { setError(e instanceof Error ? e.message : "Could not save expense"); } finally { setBusy(false); }
  }
  return <Modal title="Add expense" isOpen={isOpen} onClose={onClose}><form className="auth-form" onSubmit={submit}>{error && <p role="alert">{error}</p>}<label>Title<input name="title" required maxLength={120} /></label><label>Amount (USD)<input name="amount" type="number" min="0.01" max="10000000" step="0.01" required /></label><label>Paid by<select name="payer" defaultValue={currentMember?.id}>{members.map(m=><option key={m.id} value={m.id}>{m.display_name}</option>)}</select></label><fieldset><legend>Split equally between</legend>{members.map(m=><label key={m.id}><input type="checkbox" name="participants" value={m.id} defaultChecked /> {m.display_name}</label>)}</fieldset><button className="button" disabled={busy}>Save expense</button></form></Modal>;
}
