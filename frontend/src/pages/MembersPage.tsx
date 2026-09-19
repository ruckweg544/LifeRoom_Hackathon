import { useState } from "react";
import { Avatar } from "../components/common/ui";
import { Badge } from "../components/common/ui";
import { Card } from "../components/common/ui";
import { ErrorState } from "../components/common/ui";
import { LoadingState } from "../components/common/ui";
import { PageHeader } from "../components/common/ui";
import { CopyIcon } from "../components/layout/icons";
import { useHousehold } from "../context/HouseholdContext";
import { useToast } from "../context/ToastContext";
import { useApiData } from "../hooks/useApiData";
import { memberService } from "../services/memberService";
import "./MembersPage.css";

export function MembersPage() {
  const { household, currentMember } = useHousehold();
  const { showToast } = useToast();
  const { data: members, isLoading, error, reload } = useApiData(() => memberService.list());
  const [copied, setCopied] = useState(false);

  const handleCopyCode = async () => {
    if (!household) return;
    try {
      await navigator.clipboard.writeText(household.room_code);
      setCopied(true);
      showToast("Room code copied");
      setTimeout(() => setCopied(false), 1800);
    } catch {
      showToast("Couldn't copy - copy it manually instead.", "error");
    }
  };

  return (
    <div>
      <PageHeader title="Members" subtitle={household?.name} />

      <Card className="room-code-card">
        <div>
          <p className="room-code-card__label">Room code</p>
          <p className="room-code-card__code">{household?.room_code}</p>
        </div>
        <button className="room-code-card__copy" onClick={handleCopyCode} type="button">
          <CopyIcon width={16} height={16} />
          {copied ? "Copied!" : "Copy code"}
        </button>
      </Card>

      {isLoading && <LoadingState label="Loading members..." />}
      {error && !isLoading && <ErrorState description={error} onRetry={reload} />}

      {!isLoading && !error && members && (
        <div className="item-list" style={{ marginTop: "var(--space-5)" }}>
          {members.map((m) => (
            <Card key={m.id} className="member-card">
              <Avatar name={m.display_name} initials={m.initials} size="lg" online={m.online} />
              <div className="member-card__body">
                <p className="member-card__name">
                  {m.display_name} {m.id === currentMember?.id && <span className="member-card__you">(you)</span>}
                </p>
                <p className="member-card__meta">
                  {m.online ? "Online now" : "Offline"} &middot; Joined{" "}
                  {new Date(m.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
                </p>
              </div>
              <div className="member-card__badges">{m.is_owner && <Badge variant="blue">Owner</Badge>}</div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
