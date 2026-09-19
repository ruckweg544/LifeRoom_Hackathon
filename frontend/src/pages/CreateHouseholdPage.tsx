import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "../components/common/ui";
import { Input } from "../components/common/ui";
import { useHousehold } from "../context/HouseholdContext";
import { ApiError } from "../services/api";
import { householdService } from "../services/householdService";
import { AuthLayout } from "./AuthLayout";

export function CreateHouseholdPage() {
  const navigate = useNavigate();
  const { applySession } = useHousehold();

  const [displayName, setDisplayName] = useState("");
  const [householdName, setHouseholdName] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState<{ displayName?: string; householdName?: string; form?: string }>({});

  const validate = () => {
    const next: typeof errors = {};
    if (!displayName.trim()) next.displayName = "Your display name is required";
    if (!householdName.trim()) next.householdName = "Household name is required";
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setIsSubmitting(true);
    setErrors({});
    try {
      const session = await householdService.create({
        display_name: displayName,
        household_name: householdName,
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

  return (
    <AuthLayout title="Create your household" subtitle="Set up a private room for you and your roommates.">
      <form className="auth-form" onSubmit={handleSubmit} noValidate>
        {errors.form && <p className="auth-form__error">{errors.form}</p>}

        <Input
          label="Your display name"
          placeholder="e.g. Sieon"
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          error={errors.displayName}
          maxLength={60}
          autoFocus
        />

        <Input
          label="Household name"
          placeholder="e.g. Foxridge House"
          value={householdName}
          onChange={(e) => setHouseholdName(e.target.value)}
          error={errors.householdName}
          maxLength={120}
        />

        <Input
          label="Room password (optional)"
          type="password"
          placeholder="Leave blank for no password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          hint="Roommates will need this password to join, in addition to the room code."
        />

        <Button type="submit" isLoading={isSubmitting} fullWidth>
          Create household
        </Button>

        <p className="auth-form__footer">
          Already have a room code? <Link to="/join">Join a room</Link>
        </p>
      </form>
    </AuthLayout>
  );
}
