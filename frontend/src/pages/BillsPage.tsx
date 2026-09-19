import { useState } from "react";
import { AddBillModal } from "../components/bills/AddBillModal";
import { BillItem } from "../components/bills/BillItem";
import { Button } from "../components/common/ui";
import { Card } from "../components/common/ui";
import { EmptyState } from "../components/common/ui";
import { ErrorState } from "../components/common/ui";
import { LoadingState } from "../components/common/ui";
import { PageHeader } from "../components/common/ui";
import { PlusIcon } from "../components/layout/icons";
import { useHousehold } from "../context/HouseholdContext";
import { useToast } from "../context/ToastContext";
import { useApiData } from "../hooks/useApiData";
import { billService } from "../services/billService";
import type { Bill } from "../types";
import { formatCents } from "../utils/money";
import "./ListPage.css";

export function BillsPage() {
  const { currentMember } = useHousehold();
  const { showToast } = useToast();
  const { data: bills, isLoading, error, reload } = useApiData(() => billService.list());
  const [isModalOpen, setIsModalOpen] = useState(false);

  const youOwe =
    bills?.reduce((sum, b) => {
      const mine = b.participants.find((p) => p.member_id === currentMember?.id && !p.settled && b.paid_by_id !== currentMember?.id);
      return sum + (mine ? mine.share_cents : 0);
    }, 0) || 0;

  const youAreOwed =
    bills?.reduce((sum, b) => {
      if (b.paid_by_id !== currentMember?.id) return sum;
      const owed = b.participants.filter((p) => p.member_id !== currentMember?.id && !p.settled).reduce((s, p) => s + p.share_cents, 0);
      return sum + owed;
    }, 0) || 0;

  const handleCreate = async (payload: Parameters<typeof billService.create>[0]) => {
    const created = await billService.create(payload);
    reload();
    showToast(`Added "${created.title}"`);
  };

  const handleToggleSettled = async (bill: Bill, participantId: string, settled: boolean) => {
    try {
      await billService.setSettled(bill.id, participantId, settled);
      reload();
      showToast(settled ? "Marked as paid" : "Marked as unpaid");
    } catch {
      showToast("Couldn't update that. Please try again.", "error");
    }
  };

  const handleDelete = async (bill: Bill) => {
    if (!window.confirm(`Delete "${bill.title}"? This can't be undone.`)) return;
    try {
      await billService.remove(bill.id);
      reload();
      showToast("Expense deleted");
    } catch {
      showToast("Couldn't delete that expense. Please try again.", "error");
    }
  };

  return (
    <div>
      <PageHeader
        title="Bills"
        subtitle="Shared household expenses, split fairly."
        action={
          <Button onClick={() => setIsModalOpen(true)}>
            <PlusIcon width={16} height={16} /> Add expense
          </Button>
        }
      />

      {bills && bills.length > 0 && (
        <div className="summary-grid" style={{ gridTemplateColumns: "repeat(2, 1fr)", marginTop: 0 }}>
          <Card>
            <p style={{ fontSize: 13, color: "var(--color-text-secondary)", fontWeight: 500 }}>You Owe</p>
            <p style={{ fontSize: 24, fontWeight: 700, color: "var(--color-text)" }}>
              {formatCents(youOwe)}
            </p>
          </Card>
          <Card>
            <p style={{ fontSize: 13, color: "var(--color-text-secondary)", fontWeight: 500 }}>You Are Owed</p>
            <p style={{ fontSize: 24, fontWeight: 700, color: "var(--color-text)" }}>
              {formatCents(youAreOwed)}
            </p>
          </Card>
        </div>
      )}

      {isLoading && <LoadingState label="Loading bills..." />}
      {error && !isLoading && <ErrorState description={error} onRetry={reload} />}

      {!isLoading && !error && (!bills || bills.length === 0) && (
        <EmptyState
          title="No shared expenses yet."
          description="Add a bill to start splitting costs with your household."
          action={
            <Button size="sm" onClick={() => setIsModalOpen(true)}>
              Add an expense
            </Button>
          }
        />
      )}

      {!isLoading && !error && bills && bills.length > 0 && (
        <div className="item-list">
          {bills.map((bill) => (
            <BillItem key={bill.id} bill={bill} onToggleSettled={handleToggleSettled} onDelete={handleDelete} />
          ))}
        </div>
      )}

      <AddBillModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} onSubmit={handleCreate} />
    </div>
  );
}
