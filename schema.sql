PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    token_hash TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS households (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    invite_hash TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS members (
    household_id TEXT NOT NULL REFERENCES households(id),
    user_id TEXT NOT NULL REFERENCES users(id),
    PRIMARY KEY (household_id, user_id)
);
CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL,
    sender_id TEXT NOT NULL,
    content TEXT NOT NULL CHECK(length(trim(content)) BETWEEN 1 AND 4000),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    FOREIGN KEY (household_id, sender_id) REFERENCES members(household_id, user_id)
);
CREATE INDEX IF NOT EXISTS messages_room ON messages(household_id);
CREATE TABLE IF NOT EXISTS chores (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL,
    created_by TEXT NOT NULL,
    title TEXT NOT NULL CHECK(length(trim(title)) BETWEEN 1 AND 200),
    assignee_id TEXT,
    due_date TEXT,
    completed INTEGER NOT NULL DEFAULT 0 CHECK(completed IN (0, 1)),
    FOREIGN KEY (household_id, created_by) REFERENCES members(household_id, user_id),
    FOREIGN KEY (household_id, assignee_id) REFERENCES members(household_id, user_id)
);
CREATE INDEX IF NOT EXISTS chores_room ON chores(household_id);
CREATE TABLE IF NOT EXISTS bills (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL,
    created_by TEXT NOT NULL,
    payer_id TEXT NOT NULL,
    title TEXT NOT NULL,
    amount_cents INTEGER NOT NULL CHECK(amount_cents > 0),
    UNIQUE(id, household_id),
    FOREIGN KEY (household_id, created_by) REFERENCES members(household_id, user_id),
    FOREIGN KEY (household_id, payer_id) REFERENCES members(household_id, user_id)
);
CREATE INDEX IF NOT EXISTS bills_room ON bills(household_id);
CREATE TABLE IF NOT EXISTS bill_shares (
    bill_id TEXT NOT NULL,
    household_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    amount_cents INTEGER NOT NULL CHECK(amount_cents >= 0),
    PRIMARY KEY (bill_id, user_id),
    FOREIGN KEY (bill_id, household_id) REFERENCES bills(id, household_id),
    FOREIGN KEY (household_id, user_id) REFERENCES members(household_id, user_id)
);
