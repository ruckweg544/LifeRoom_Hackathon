import { useEffect, useState } from "react";
import { AddChoreModal } from "../chores/AddChoreModal";
import { type MessageAnalysis } from "../../services/messageService";
import { choreService, type CreateChorePayload } from "../../services/choreService";
import { ApiError } from "../../services/api";
import { useToast } from "../../context/ToastContext";

export function MessageChoreSuggestion({ messageId, analysis, onRetry }: {
  messageId: string;
  analysis: Promise<MessageAnalysis>;
  onRetry: () => void;
}) {
  const [status, setStatus] = useState<"loading" | "done" | "error" | "saved">("loading");
  const [suggestion, setSuggestion] = useState<MessageAnalysis["suggestion"]>(null);
  const [error, setError] = useState("");
  const [retryable, setRetryable] = useState(true);
  const [open, setOpen] = useState(false);
  const { showToast } = useToast();

  useEffect(() => {
    let active = true;
    setStatus("loading");
    // Observe the send handler's request; mounting never starts an analysis.
    void analysis.then(result => {
      if (!active) return;
      setSuggestion(result.suggestion);
      setStatus("done");
    }, error => {
      if (!active) return;
      setRetryable(!(error instanceof ApiError) || (error.retryable !== false && error.code !== "AI_PROVIDER_RATE_LIMITED"));
      setError(error instanceof ApiError && error.code === "AI_PROVIDER_RATE_LIMITED"
        ? "Gemini's request or quota limit has been reached. Your message is saved. Add the chore manually; this message will not be analyzed again."
        : error instanceof ApiError && error.code === "AI_NOT_CONFIGURED"
        ? "AI is not configured on the server. Your message is saved."
        : error instanceof ApiError && error.status === 429
        ? "Too many analyses. Wait a minute and retry."
        : "Analysis unavailable. Your message is already sent.");
      setStatus("error");
    });
    return () => { active = false; };
  }, [analysis]);

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
    {status === "loading" && <span>Checking for a chore…</span>}
    {status === "error" && <><span>{error} </span>{retryable && <button type="button" onClick={onRetry}>Retry analysis</button>}</>}
    {status === "saved" && <span>Chore added — see Chores.</span>}
    {status === "done" && !suggestion && <span>No chore suggested.</span>}
    {suggestion && <><span>Suggested chore: {suggestion.title} </span>
      <button type="button" onClick={() => setOpen(true)}>Review &amp; add</button>
      <button type="button" onClick={() => setSuggestion(null)}>Dismiss</button></>}
    {open && suggestion && <AddChoreModal isOpen onClose={() => setOpen(false)} onSubmit={save} initialValues={suggestion} />}
  </div>;
}
