import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { MessageChoreSuggestion } from "../components/chat/MessageChoreSuggestion";
import { ConnectionBadge } from "../components/chat/ConnectionBadge";
import { MessageBubble } from "../components/chat/MessageBubble";
import { EmptyState } from "../components/common/ui";
import { ErrorState } from "../components/common/ui";
import { LoadingState } from "../components/common/ui";
import { PageHeader } from "../components/common/ui";
import { SendIcon } from "../components/layout/icons";
import { useHousehold } from "../context/HouseholdContext";
import { useToast } from "../context/ToastContext";
import { useApiData } from "../hooks/useApiData";
import { messageService } from "../services/messageService";
import { ApiError } from "../services/api";

import "./ChatPage.css";

export function ChatPage() {
  const { household, currentMember, connectionState } = useHousehold();
  const { showToast } = useToast();

  const { data, isLoading, error, reload } = useApiData(() => messageService.list());
  const messages = data || [];
  const [draft, setDraft] = useState("");
  const [sentIds, setSentIds] = useState<Set<string>>(() => new Set());
  const [sending, setSending] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
  }, [data]);

  const handleSend = async () => {
    const content = draft.trim();
    if (!content || sending) return;
    setSending(true);
    try {
      const saved = await messageService.create(content);
      setSentIds(previous => new Set(previous).add(saved.id));
      setDraft(previous => previous.trim() === content ? "" : previous);
      reload();
    } catch (error) {
      showToast(error instanceof ApiError ? error.message : "Message not sent. Please retry.", "error");
    } finally { setSending(false); }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-page">
      <PageHeader title="Chat" subtitle={household?.name} action={<ConnectionBadge state={connectionState} />} />

      <div className="chat-panel">
        <div className="chat-panel__messages" ref={listRef}>
          {isLoading && <LoadingState label="Loading messages..." />}
          {error && !isLoading && <ErrorState description={error} />}
          {!isLoading && !error && messages.length === 0 && (
            <EmptyState title="Start the conversation." description="Send the first message to your household." />
          )}
          {!isLoading &&
            !error &&
            messages.map((m, i) => {
              const prev = messages[i - 1];
              const showSender = !prev || prev.member_id !== m.member_id;
              return <div key={m.id}>
                <MessageBubble message={m} isOwn={m.member_id === currentMember?.id} showSender={showSender} />
                {m.member_id === currentMember?.id && <MessageChoreSuggestion messageId={m.id} autoAnalyze={sentIds.has(m.id)} />}
              </div>;
            })}
        </div>

        <div className="chat-panel__composer">
          <textarea
            className="chat-panel__input"
            placeholder="Message your household..."
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            maxLength={2000}
            aria-label="Message"
          />
          <button
            type="button"
            className="chat-panel__send"
            onClick={handleSend}
            disabled={!draft.trim() || sending}
            aria-label="Send message"
          >
            <SendIcon width={18} height={18} />
          </button>
        </div>
      </div>
    </div>
  );
}
