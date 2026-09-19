import { useMemo, useState } from "react";
import { AddChoreModal } from "../components/chores/AddChoreModal";
import { ChoreItem } from "../components/chores/ChoreItem";
import { Button } from "../components/common/ui";
import { EmptyState } from "../components/common/ui";
import { ErrorState } from "../components/common/ui";
import { LoadingState } from "../components/common/ui";
import { PageHeader } from "../components/common/ui";
import { PlusIcon } from "../components/layout/icons";
import { useHousehold } from "../context/HouseholdContext";
import { useToast } from "../context/ToastContext";
import { useApiData } from "../hooks/useApiData";
import { choreService } from "../services/choreService";
import type { Chore } from "../types";
import "./ListPage.css";

type Filter = "all" | "mine" | "active" | "completed";

export function ChoresPage() {
  const { currentMember } = useHousehold();
  const { showToast } = useToast();
  const { data: chores, isLoading, error, reload } = useApiData(() => choreService.list());
  const [filter, setFilter] = useState<Filter>("all");
  const [isModalOpen, setIsModalOpen] = useState(false);

  const filtered = useMemo(() => {
    if (!chores) return [];
    switch (filter) {
      case "mine":
        return chores.filter((c) => c.assigned_to_id === currentMember?.id);
      case "active":
        return chores.filter((c) => !c.completed);
      case "completed":
        return chores.filter((c) => c.completed);
      default:
        return chores;
    }
  }, [chores, filter, currentMember]);

  const handleToggle = async (chore: Chore) => {
    try {
      const updated = await choreService.update(chore.id, { completed: !chore.completed });
      reload();
      showToast(updated.completed ? `Marked "${updated.title}" complete` : `Reopened "${updated.title}"`);
    } catch {
      showToast("Couldn't update that chore. Please try again.", "error");
    }
  };

  const handleDelete = async (chore: Chore) => {
    if (!window.confirm(`Delete "${chore.title}"? This can't be undone.`)) return;
    try {
      await choreService.remove(chore.id);
      reload();
      showToast("Chore deleted");
    } catch {
      showToast("Couldn't delete that chore. Please try again.", "error");
    }
  };

  const handleCreate = async (payload: Parameters<typeof choreService.create>[0]) => {
    const created = await choreService.create(payload);
    reload();
    showToast(`Added "${created.title}"`);
  };

  return (
    <div>
      <PageHeader
        title="Chores"
        subtitle="Keep the household running smoothly."
        action={
          <Button onClick={() => setIsModalOpen(true)}>
            <PlusIcon width={16} height={16} /> Add chore
          </Button>
        }
      />

      <div className="filter-tabs" role="tablist" aria-label="Filter chores">
        {(["all", "mine", "active", "completed"] as Filter[]).map((f) => (
          <button
            key={f}
            role="tab"
            aria-selected={filter === f}
            className={`filter-tabs__btn ${filter === f ? "filter-tabs__btn--active" : ""}`}
            onClick={() => setFilter(f)}
          >
            {f[0].toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>

      {isLoading && <LoadingState label="Loading chores..." />}
      {error && !isLoading && <ErrorState description={error} onRetry={reload} />}

      {!isLoading && !error && filtered.length === 0 && (
        <EmptyState
          title="You're all caught up."
          description={filter === "all" ? "No chores yet - add one to get started." : "Nothing to show for this filter."}
          action={
            filter === "all" && (
              <Button size="sm" onClick={() => setIsModalOpen(true)}>
                Add a chore
              </Button>
            )
          }
        />
      )}

      {!isLoading && !error && filtered.length > 0 && (
        <div className="item-list">
          {filtered.map((chore) => (
            <ChoreItem key={chore.id} chore={chore} onToggleComplete={handleToggle} onDelete={handleDelete} />
          ))}
        </div>
      )}

      <AddChoreModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} onSubmit={handleCreate} />
    </div>
  );
}
