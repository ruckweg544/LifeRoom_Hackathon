import { useCallback, useEffect, useRef, useState } from "react";
import { AddChoreModal } from "../chores/AddChoreModal";
import { messageService, type MessageAnalysis } from "../../services/messageService";
import { choreService, type CreateChorePayload } from "../../services/choreService";
import { ApiError } from "../../services/api";
import { useToast } from "../../context/ToastContext";

export function MessageChoreSuggestion({ messageId, autoAnalyze }: { messageId: string; autoAnalyze: boolean }) {
  const [status, setStatus] = useState<"idle" | "loading" | "done" | "error" | "saved">("idle");
  const [suggestion, setSuggestion] = useState<MessageAnalysis["suggestion"]>(null);
  const [error, setError] = useState("");
  const [open, setOpen] = useState(false);
  const started = useRef(false);
  const pending = useRef(false);
  const { showToast } = useToast();

  const analyze = useCallback(async () => {
    if (pending.current) return;
    pending.current = true;
    setStatus("loading");
    try {
      const result = await messageService.analyze(messageId);
      setSuggestion(result.suggestion);
      setStatus("done");
    } catch (error) {
      setError(error instanceof ApiError && error.status === 429
        ? "Too many analyses. Wait a minute and retry."
        : "Analysis unavailable. Your message is already sent.");
      setStatus("error");
    } finally { pending.current = false; }
  }, [messageId]);

  useEffect(() => {
    if (autoAnalyze && !started.current) {
      started.current = true;
      void analyze();
    }
  }, [autoAnalyze, analyze]);

  async function save(payload: CreateChorePayload) {
    try {
      await choreService.create({ ...payload, source_message_id: messageId });
      showToast("Chore added.", "success");
    } catch (error) {
      if (!(error instanceof ApiError) || error.status !== 409) throw error;
      showToast("This message already has a chore.", "success");
    }
    setStatus("saved");
    setSuggestion(null);
  }

  return <div className="chat-chore-suggestion" aria-live="polite">
    {status === "idle" && <button type="button" onClick={() => void analyze()}>Find a chore</button>}
    {status === "loading" && <span>Checking for a chore…</span>}
    {status === "error" && <><span>{error} </span><button type="button" onClick={() => void analyze()}>Retry analysis</button></>}
    {status === "saved" && <span>Chore added — see Chores.</span>}
    {status === "done" && !suggestion && <span>No chore suggested.</span>}
    {suggestion && <><span>Suggested chore: {suggestion.title} </span>
      <button type="button" onClick={() => setOpen(true)}>Review &amp; add</button>
      <button type="button" onClick={() => setSuggestion(null)}>Dismiss</button></>}
    {open && suggestion && <AddChoreModal isOpen onClose={() => setOpen(false)} onSubmit={save} initialValues={suggestion} />}
  </div>;
}
