// Tiny in-memory pretend-SQL store. No real driver.
// query(sql, params?) and execute(sql, params?) support a small SELECT/INSERT
// grammar so the app can look like it talks to a DB. This module is clean
// infrastructure; all planted flaws live in the route handlers in app.ts.

export type Row = Record<string, unknown>;

type Store = { users: Row[]; projects: Row[]; transactions: Row[] };

const store: Store = {
  users: [
    { id: 'u1', orgId: 'org1', name: 'Ava', email: 'ava@acme.test', role: 'member' },
    { id: 'u2', orgId: 'org1', name: 'Ben', email: 'ben@acme.test', role: 'admin' },
    { id: 'u3', orgId: 'org2', name: 'Cara', email: 'cara@globex.test', role: 'member' },
  ],
  projects: [
    { id: 'p1', orgId: 'org1', name: 'Apollo', status: 'active' },
    { id: 'p2', orgId: 'org1', name: 'Beacon', status: 'active' },
    { id: 'p3', orgId: 'org2', name: 'Comet', status: 'active' },
  ],
  transactions: [
    { id: 't1', orgId: 'org1', projectId: 'p1', amount: 1200, currency: 'USD' },
    { id: 't2', orgId: 'org1', projectId: 'p2', amount: 800, currency: 'USD' },
    { id: 't3', orgId: 'org2', projectId: 'p3', amount: 500, currency: 'EUR' },
  ],
};

function bind(sql: string, params: unknown[]): string {
  let i = 0;
  return sql.replace(/\?/g, () => {
    const v = params[i++];
    return typeof v === 'number' ? String(v) : `'${String(v)}'`;
  });
}

function unquote(token: string): string {
  return token.trim().replace(/^'(.*)'$/, '$1');
}

function matchClause(row: Row, clause: string): boolean {
  const like = /(\w+)\s+like\s+(.+)/i.exec(clause);
  if (like) {
    const needle = unquote(like[2]).replace(/%/g, '').toLowerCase();
    return String(row[like[1]] ?? '').toLowerCase().includes(needle);
  }
  const eq = /(\w+)\s*=\s*(.+)/.exec(clause);
  if (eq) {
    return String(row[eq[1]] ?? '') === unquote(eq[2]);
  }
  return true;
}

// Returns LIVE row references (ORM-like), so a handler that mutates a returned
// row mutates the store. Read handlers must not mutate what they read.
export function query(sql: string, params: unknown[] = []): Row[] {
  const bound = bind(sql, params);
  const table = /from\s+(\w+)/i.exec(bound)?.[1] as keyof Store | undefined;
  if (!table || !store[table]) return [];
  let rows = store[table];
  const where = /where\s+(.+?)\s*$/i.exec(bound);
  if (where) {
    const clauses = where[1].split(/\s+and\s+/i);
    rows = rows.filter((row) => clauses.every((clause) => matchClause(row, clause)));
  }
  return rows;
}

export function execute(sql: string, params: unknown[] = []): void {
  const bound = bind(sql, params);
  const insert = /insert into (\w+)\s*\(([^)]+)\)\s*values\s*\(([^)]+)\)/i.exec(bound);
  if (insert) {
    const table = insert[1] as keyof Store;
    const cols = insert[2].split(',').map((c) => c.trim());
    const vals = insert[3].split(',').map((token) => {
      const t = token.trim();
      return t.startsWith("'") ? unquote(t) : Number(t);
    });
    const row: Row = {};
    cols.forEach((col, idx) => {
      row[col] = vals[idx];
    });
    store[table].push(row);
  }
}
