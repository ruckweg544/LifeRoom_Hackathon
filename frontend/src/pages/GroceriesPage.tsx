import { useMemo, useState, type FormEvent } from "react";
import { Button } from "../components/common/ui";
import { EmptyState } from "../components/common/ui";
import { ErrorState } from "../components/common/ui";
import { Input } from "../components/common/ui";
import { LoadingState } from "../components/common/ui";
import { PageHeader } from "../components/common/ui";
import { GroceryRow } from "../components/groceries/GroceryRow";
import { useToast } from "../context/ToastContext";
import { useApiData } from "../hooks/useApiData";
import { groceryService } from "../services/groceryService";
import type { GroceryItem } from "../types";
import "./ListPage.css";
import "../components/groceries/groceries.css";

export function GroceriesPage() {
  const { showToast } = useToast();
  const { data: items, isLoading, error, reload } = useApiData(() => groceryService.list());
  const [name, setName] = useState("");
  const [isAdding, setIsAdding] = useState(false);

  const needed = useMemo(() => items?.filter((i) => !i.purchased) || [], [items]);
  const purchased = useMemo(() => items?.filter((i) => i.purchased) || [], [items]);

  const handleAdd = async (e: FormEvent) => {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) return;
    setIsAdding(true);
    try {
      const created = await groceryService.create({ name: trimmed, quantity: 1 });
      reload();
      setName("");
      showToast(`Added ${created.name}`);
    } catch {
      showToast("Couldn't add that item. Please try again.", "error");
    } finally {
      setIsAdding(false);
    }
  };

  const handleTogglePurchased = async (item: GroceryItem) => {
    try {
      await groceryService.update(item.id, { purchased: !item.purchased });
      reload();
    } catch {
      showToast("Couldn't update that item. Please try again.", "error");
    }
  };

  const handleDelete = async (item: GroceryItem) => {
    try {
      await groceryService.remove(item.id);
      reload();
    } catch {
      showToast("Couldn't delete that item. Please try again.", "error");
    }
  };

  return (
    <div>
      <PageHeader title="Groceries" subtitle="A shared list everyone can add to." />

      <form className="quick-add" onSubmit={handleAdd}>
        <div className="quick-add__input">
          <Input placeholder="Add grocery item..." value={name} onChange={(e) => setName(e.target.value)} maxLength={120} />
        </div>
        <Button type="submit" isLoading={isAdding} disabled={!name.trim()}>
          Add
        </Button>
      </form>

      {isLoading && <LoadingState label="Loading groceries..." />}
      {error && !isLoading && <ErrorState description={error} onRetry={reload} />}

      {!isLoading && !error && items && items.length === 0 && <EmptyState title="Your grocery list is empty." description="Add the first item above." />}

      {!isLoading && !error && items && items.length > 0 && (
        <>
          <p className="grocery-section-title">Need to Buy ({needed.length})</p>
          {needed.length === 0 ? (
            <EmptyState title="Nothing needed right now." />
          ) : (
            <ul className="grocery-list">
              {needed.map((item) => (
                <GroceryRow key={item.id} item={item} onTogglePurchased={handleTogglePurchased} onDelete={handleDelete} />
              ))}
            </ul>
          )}

          {purchased.length > 0 && (
            <>
              <p className="grocery-section-title">Purchased ({purchased.length})</p>
              <ul className="grocery-list">
                {purchased.map((item) => (
                  <GroceryRow key={item.id} item={item} onTogglePurchased={handleTogglePurchased} onDelete={handleDelete} />
                ))}
              </ul>
            </>
          )}
        </>
      )}
    </div>
  );
}
