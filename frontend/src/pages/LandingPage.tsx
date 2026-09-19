import { Link } from "react-router-dom";
import { Card } from "../components/common/ui";
import { BillIcon, ChatIcon, ChoreIcon, GroceryIcon } from "../components/layout/icons";
import "./LandingPage.css";

const FEATURES = [
  { icon: ChatIcon, title: "Chat", description: "One thread for the household - no more scattered group texts." },
  { icon: ChoreIcon, title: "Chores", description: "Assign, track, and clear chores together." },
  { icon: BillIcon, title: "Bills", description: "Split shared expenses fairly, down to the cent." },
  { icon: GroceryIcon, title: "Groceries", description: "A shared list everyone can add to and check off." },
];

export function LandingPage() {
  return (
    <div className="landing">
      <header className="landing__header">
        <div className="landing__brand">
          <span className="landing__logo-mark" aria-hidden="true">
            LR
          </span>
          <span className="landing__logo-text">LifeRoom</span>
        </div>
      </header>

      <main className="landing__hero">
        <h1 className="landing__title">Everything your roommates need, in one room.</h1>
        <p className="landing__subtitle">
          Manage chores, expenses, groceries, and conversations with the people you live with.
        </p>

        <div className="landing__actions">
          <Link to="/create" className="btn btn--primary btn--lg">
            Create a Room
          </Link>
          <Link to="/join" className="btn btn--secondary btn--lg">
            Join a Room
          </Link>
        </div>
      </main>

      <section className="landing__features" aria-label="Features">
        {FEATURES.map(({ icon: Icon, title, description }) => (
          <Card key={title} className="landing__feature-card">
            <div className="landing__feature-icon">
              <Icon width={20} height={20} />
            </div>
            <p className="landing__feature-title">{title}</p>
            <p className="landing__feature-description">{description}</p>
          </Card>
        ))}
      </section>

      <footer className="landing__footer">Built for roommates who want less chaos, together.</footer>
    </div>
  );
}
