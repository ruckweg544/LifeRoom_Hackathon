import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "../components/common/ui";
import { Input } from "../components/common/ui";
import { useHousehold } from "../context/HouseholdContext";
import { ApiError } from "../services/api";
import { householdService } from "../services/householdService";
import { AuthLayout } from "./AuthLayout";

export function JoinHouseholdPage({ embedded = false }: { embedded?: boolean }) {
  const navigate = useNavigate();
  const { applySession } = useHousehold();

  const [displayName, setDisplayName] = useState("");
  const [roomCode, setRoomCode] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState<{ displayName?: string; roomCode?: string; form?: string }>({});

  const validate = () => {
    const next: typeof errors = {};
    if (!displayName.trim()) next.displayName = "Your display name is required";
    if (!roomCode.trim()) next.roomCode = "Room code is required";
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setIsSubmitting(true);
    setErrors({});
    try {
      const session = await householdService.join({
        display_name: displayName,
        room_code: roomCode,
        password: password || null,
      });
      applySession(session);
      navigate("/app");
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Something went wrong. Please try again.";
      setErrors({ form: message });
    } finally {
      setIsSubmitting(false);
    }
  };

  const form = (
      <form className="auth-form" onSubmit={handleSubmit} noValidate>
        {errors.form && <p className="auth-form__error">{errors.form}</p>}

        <Input
          label="Your display name"
          placeholder="e.g. Alex"
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          error={errors.displayName}
          maxLength={60}
          autoFocus={!embedded}
        />

        <Input
          label="Room code"
          placeholder="e.g. FRX482"
          value={roomCode}
          onChange={(e) => setRoomCode(e.target.value.toUpperCase())}
          error={errors.roomCode}
          maxLength={12}
          style={{ textTransform: "uppercase", letterSpacing: "0.05em" }}
        />

        <Input
          label="Password"
          type="password"
          placeholder="Only if the household set one"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        <Button type="submit" isLoading={isSubmitting} fullWidth>
          Join room
        </Button>

        {!embedded && <p className="auth-form__footer">
          Don't have a room yet? <Link to="/create">Create one</Link>
        </p>}
      </form>
  );

  return embedded ? form : <AuthLayout title="Join a household" subtitle="Enter the room code your roommate shared with you.">{form}</AuthLayout>;
}
