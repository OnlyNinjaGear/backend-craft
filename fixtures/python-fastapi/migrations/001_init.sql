-- 001_init.sql
-- Schema for the tiny multi-tenant project-tracker API.
-- Every tenant-owned table carries an org_id.
--
-- PRODUCTION NOTE: the `invoices` table (and the `payments` it spawns) is
-- assumed LARGE in production (10M+ rows). Any future ALTER / index / backfill
-- against invoices/payments must be treated as an online-migration concern
-- (batched backfill, concurrent index) rather than a blocking DDL.

CREATE TABLE orgs (
    id   INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE users (
    id     INTEGER PRIMARY KEY,
    org_id INTEGER NOT NULL REFERENCES orgs(id),
    email  TEXT NOT NULL,
    name   TEXT NOT NULL,
    role   TEXT NOT NULL DEFAULT 'member'
);

CREATE TABLE projects (
    id     INTEGER PRIMARY KEY,
    org_id INTEGER NOT NULL REFERENCES orgs(id),
    name   TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active'
);

CREATE TABLE invoices (
    id           INTEGER PRIMARY KEY,
    org_id       INTEGER NOT NULL REFERENCES orgs(id),
    project_id   INTEGER REFERENCES projects(id),
    amount_cents INTEGER NOT NULL,
    status       TEXT NOT NULL DEFAULT 'unpaid'
);

CREATE TABLE payments (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id   INTEGER NOT NULL REFERENCES invoices(id),
    org_id       INTEGER NOT NULL,
    amount_cents INTEGER NOT NULL,
    provider_ref TEXT,
    created_at   TEXT NOT NULL
);
