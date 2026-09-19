import { Link } from "react-router-dom";
import { ActivityFeed } from "../components/dashboard/ActivityFeed";
import { SummaryCard } from "../components/dashboard/SummaryCard";
import { Card } from "../components/common/ui";
import { EmptyState } from "../components/common/ui";
import { ErrorState } from "../components/common/ui";
import { LoadingState } from "../components/common/ui";
import { PriorityBadge } from "../components/chores/PriorityBadge";
import { BillIcon, ChoreIcon, GroceryIcon, MembersIcon } from "../components/layout/icons";
import { useHousehold } from "../context/HouseholdContext";
import { useApiData } from "../hooks/useApiData";
import { dashboardService } from "../services/dashboardService";
import { formatCents } from "../utils/money";
import { formatDueDate, formatRelativeTime } from "../utils/date";
import "./DashboardPage.css";

export function DashboardPage() {
  const { currentMember, household } = useHousehold();
  const { data, isLoading, error, reload } = useApiData(() => dashboardService.get());

  const firstName = currentMember?.display_name.split(" ")[0] || "there";
  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";

  return (
    <div>
      <div>
        <h1 className="dashboard-greeting">
          {greeting}, {firstName}
        </h1>
        <p className="dashboard-household">{household?.name}</p>
        <p className="dashboard-subtitle">Here's what's happening at home.</p>
      </div>

      {isLoading && <LoadingState label="Loading your dashboard..." />}
      {error && !isLoading && <ErrorState description={error} onRetry={reload} />}

      {data && !isLoading && !error && (
        <>
          <div className="summary-grid">
            <SummaryCard
              label="Chores Due"
              value={String(data.summary.chores_due)}
              icon={<ChoreIcon width={18} height={18} />}
              to="/app/chores"
            />
            <SummaryCard
              label="You Owe"
              value={formatCents(data.summary.you_owe_cents)}
              icon={<BillIcon width={18} height={18} />}
              to="/app/bills"
            />
            <SummaryCard
              label="Groceries"
              value={`${data.summary.groceries_needed} item${data.summary.groceries_needed === 1 ? "" : "s"}`}
              icon={<GroceryIcon width={18} height={18} />}
              to="/app/groceries"
            />
            <SummaryCard
              label="Roommates Online"
              value={`${data.summary.members_online} / ${data.summary.members_total}`}
              icon={<MembersIcon width={18} height={18} />}
              to="/app/members"
            />
          </div>

          <div className="dashboard-grid">
            <div className="dashboard-column">
              <Card>
                <div className="panel__header">
                  <h2 className="panel__title">Today's Chores</h2>
                  <Link to="/app/chores" className="panel__link">
                    View all
                  </Link>
                </div>
                {data.todays_chores.length === 0 ? (
                  <EmptyState title="You're all caught up." description="No chores due today." />
                ) : (
                  <ul className="mini-chore-list">
                    {data.todays_chores.map((chore) => (
                      <li key={chore.id} className="mini-chore-item">
                        <span
                          className="mini-chore-item__dot"
                          style={{
                            background:
                              chore.priority === "high"
                                ? "var(--color-priority-high)"
                                : chore.priority === "medium"
                                ? "var(--color-priority-medium)"
                                : "var(--color-priority-low)",
                          }}
                        />
                        <div className="mini-chore-item__body">
                          <p className="mini-chore-item__title">{chore.title}</p>
                          <p className="mini-chore-item__meta">
                            {chore.assigned_to_name ? `${chore.assigned_to_name} · ` : ""}
                            {formatDueDate(chore.due_date)}
                          </p>
                        </div>
                        <PriorityBadge priority={chore.priority} />
                      </li>
                    ))}
                  </ul>
                )}
              </Card>

              <Card>
                <div className="panel__header">
                  <h2 className="panel__title">Recent Messages</h2>
                  <Link to="/app/chat" className="panel__link">
                    Open chat
                  </Link>
                </div>
                {data.recent_messages.length === 0 ? (
                  <EmptyState title="Start the conversation." description="No messages yet in this household." />
                ) : (
                  <ul className="mini-message-list">
                    {data.recent_messages.map((m) => (
                      <li key={m.id} className="mini-message-item">
                        <div className="mini-message-item__body">
                          <div className="mini-message-item__top">
                            <span className="mini-message-item__sender">{m.sender_name}</span>
                            <span className="mini-message-item__time">{formatRelativeTime(m.created_at)}</span>
                          </div>
                          <p className="mini-message-item__content">{m.content}</p>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </Card>
            </div>

            <div className="dashboard-column">
              <Card>
                <div className="panel__header">
                  <h2 className="panel__title">Upcoming Bills</h2>
                  <Link to="/app/bills" className="panel__link">
                    View all
                  </Link>
                </div>
                {data.upcoming_bills.length === 0 ? (
                  <EmptyState title="No shared expenses yet." />
                ) : (
                  <ul className="mini-bill-list">
                    {data.upcoming_bills.map((bill) => (
                      <li key={bill.id} className="mini-bill-item">
                        <div>
                          <p className="mini-bill-item__title">{bill.title}</p>
                          <p className="mini-bill-item__meta">Paid by {bill.paid_by_name}</p>
                        </div>
                        <span className="mini-bill-item__amount">{formatCents(bill.amount_cents)}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </Card>

              <Card>
                <div className="panel__header">
                  <h2 className="panel__title">Grocery List</h2>
                  <Link to="/app/groceries" className="panel__link">
                    View all
                  </Link>
                </div>
                {data.grocery_preview.length === 0 ? (
                  <EmptyState title="Your grocery list is empty." />
                ) : (
                  <ul className="mini-grocery-list">
                    {data.grocery_preview.map((item) => (
                      <li key={item.id} className="mini-grocery-item">
                        <span className="mini-grocery-item__name">{item.name}</span>
                        <span className="mini-grocery-item__meta">Qty {item.quantity}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </Card>

              <Card>
                <div className="panel__header">
                  <h2 className="panel__title">Recent Activity</h2>
                </div>
                <ActivityFeed activities={data.recent_activity} />
              </Card>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
