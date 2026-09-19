import { useState, type FormEvent } from "react";
import { Button } from "../components/common/ui";
import { Card } from "../components/common/ui";
import { Input } from "../components/common/ui";
import { PageHeader } from "../components/common/ui";
import { useHousehold } from "../context/HouseholdContext";
import { useToast } from "../context/ToastContext";
import { ApiError } from "../services/api";
import { memberService } from "../services/memberService";
import "./SettingsPage.css";

export function SettingsPage() {
  const { household, currentMember, updateCurrentMember, leaveHousehold } = useHousehold();
  const { showToast } = useToast();

  const [displayName, setDisplayName] = useState(currentMember?.display_name || "");
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isDirty = displayName.trim() !== currentMember?.display_name;

  const handleSave = async (e: FormEvent) => {
    e.preventDefault();
    if (!displayName.trim()) {
      setError("Display name cannot be blank");
      return;
    }
    setIsSaving(true);
    setError(null);
    try {
      const updated = await memberService.updateMyProfile(displayName.trim());
      updateCurrentMember(updated);
      showToast("Display name updated");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't save changes. Please try again.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div>
      <PageHeader title="Settings" subtitle="Manage your profile and household." />

      <div className="settings-grid">
        <Card>
          <h2 className="settings-card__title">Your profile</h2>
          <form className="auth-form" onSubmit={handleSave}>
            {error && <p className="auth-form__error">{error}</p>}
            <Input label="Display name" value={displayName} onChange={(e) => setDisplayName(e.target.value)} maxLength={60} />
            <Button type="submit" isLoading={isSaving} disabled={!isDirty} style={{ alignSelf: "flex-start" }}>
              Save changes
            </Button>
          </form>
        </Card>

        <Card>
          <h2 className="settings-card__title">Household</h2>
          <dl className="settings-list">
            <div className="settings-list__row">
              <dt>Name</dt>
              <dd>{household?.name}</dd>
            </div>
            <div className="settings-list__row">
              <dt>Room code</dt>
              <dd className="settings-list__code">{household?.room_code}</dd>
            </div>
            <div className="settings-list__row">
              <dt>Password protected</dt>
              <dd>{household?.has_password ? "Yes" : "No"}</dd>
            </div>
          </dl>
        </Card>

        <Card>
          <h2 className="settings-card__title">Danger zone</h2>
          <p className="settings-card__description">Signing out removes this session from this device. Rejoining creates a new member; the same display name cannot be reused.</p>
          <Button
            variant="danger"
            onClick={() => {
              if (window.confirm("Sign out and remove this device’s session?")) leaveHousehold();
            }}
          >
            Sign out
          </Button>
        </Card>
      </div>
    </div>
  );
}
