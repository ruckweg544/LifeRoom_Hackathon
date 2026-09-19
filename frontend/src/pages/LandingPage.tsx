import { useState } from "react";
import { ChatIcon, ChoreIcon, CopyIcon } from "../components/layout/icons";
import { CreateHouseholdPage } from "./CreateHouseholdPage";
import { JoinHouseholdPage } from "./JoinHouseholdPage";
import "./LandingPage.css";

export function LandingPage() {
  const [mode, setMode] = useState<"create" | "join">("create");
  return (
    <div className="landing">
      <header className="landing__header">
        <a className="landing__brand" href="/">LifeRoom</a>
        <a className="landing__header-action" href="#room-form">Get started</a>
      </header>
      <main className="landing__main">
        <section className="landing__hero">
          <div className="landing__intro">
            <p className="landing__eyebrow">Private household rooms</p>
            <h1 className="landing__title">Everything your roommates need, in one room.</h1>
            <p className="landing__subtitle">Manage chores, expenses, groceries, and conversations with the people you live with.</p>
            <ul className="landing__features" aria-label="Features">
              <li><ChatIcon width={20} height={20} />Real-time chat</li>
              <li><ChoreIcon width={20} height={20} />Shared chores</li>
              <li><CopyIcon width={20} height={20} />Room codes</li>
            </ul>
          </div>
          <section className="landing__room" id="room-form" aria-label="Create or join a room">
            <div className="landing__tabs" role="group" aria-label="Room action">
              <button type="button" aria-pressed={mode === "create"} onClick={() => setMode("create")}>Create a Room</button>
              <button type="button" aria-pressed={mode === "join"} onClick={() => setMode("join")}>Join a Room</button>
            </div>
            {mode === "create" ? <CreateHouseholdPage embedded /> : <JoinHouseholdPage embedded />}
          </section>
        </section>
        <section className="landing__preview" aria-label="Example household summary">
          <div className="landing__summary"><h2>Chores Due</h2><p>3</p></div>
          <div className="landing__summary"><h2>You Owe</h2><p>$24.50</p></div>
          <div className="landing__summary"><h2>Groceries</h2><p>7 items</p></div>
          <div className="landing__summary"><h2>Online</h2><p>3 / 4</p></div>
        </section>
        <p className="landing__preview-note">Example room activity</p>
      </main>
    </div>
  );
}
