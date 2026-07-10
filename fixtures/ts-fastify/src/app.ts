import Fastify, { type FastifyInstance, type FastifyRequest } from 'fastify';
import * as fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import * as db from './db.js';
import { auditLog } from './auditLog.js';

const DATA_DIR = fileURLToPath(new URL('../data', import.meta.url));

// Fake auth: tenant context comes from the authenticated user, never the body.
function authContext(req: FastifyRequest): { userId: string; orgId: string } | null {
  const userId = req.headers['x-user-id'];
  if (typeof userId !== 'string') return null;
  const rows = db.query('SELECT * FROM users WHERE id = ?', [userId]); // clean: parameterized
  const user = rows[0];
  if (!user) return null;
  return { userId, orgId: String(user.orgId) };
}

export function buildApp(): FastifyInstance {
  const app = Fastify();

  // CLEAN: list users scoped to the caller's org, tenant from auth, parameterized.
  app.get('/users', async (req, reply) => {
    const ctx = authContext(req);
    if (!ctx) return reply.code(401).send({ error: 'unauthenticated' });
    const users = db.query('SELECT id, orgId, name, email, role FROM users WHERE orgId = ?', [ctx.orgId]);
    return { users };
  });

  app.patch<{ Params: { id: string }; Body: Record<string, unknown> }>('/users/:id', async (req, reply) => {
    const ctx = authContext(req);
    if (!ctx) return reply.code(401).send({ error: 'unauthenticated' });
    const rows = db.query('SELECT * FROM users WHERE id = ? AND orgId = ?', [req.params.id, ctx.orgId]);
    const user = rows[0];
    if (!user) return reply.code(404).send({ error: 'not found' });
    Object.assign(user, req.body); // PLANTED: api-mass-assignment
    return { user };
  });

  // CLEAN: fetch a project by id, tenant-scoped, parameterized values.
  app.get<{ Params: { id: string } }>('/projects/:id', async (req, reply) => {
    const ctx = authContext(req);
    if (!ctx) return reply.code(401).send({ error: 'unauthenticated' });
    const rows = db.query('SELECT * FROM projects WHERE id = ? AND orgId = ?', [req.params.id, ctx.orgId]);
    if (rows.length === 0) return reply.code(404).send({ error: 'not found' });
    return { project: rows[0] };
  });

  app.get<{ Querystring: { q?: string } }>('/projects/search', async (req, reply) => {
    const ctx = authContext(req);
    if (!ctx) return reply.code(401).send({ error: 'unauthenticated' });
    const q = req.query.q ?? '';
    const projects = db.query(`SELECT * FROM projects WHERE orgId = '${ctx.orgId}' AND name LIKE '%${q}%'`); // PLANTED: sql-string-concat
    return { projects };
  });

  app.post('/projects', async (req, reply) => {
    const ctx = authContext(req);
    if (!ctx) return reply.code(401).send({ error: 'unauthenticated' });
    const body = req.body as any; // PLANTED: ts-any-at-boundary
    const id = 'p' + Math.random().toString(36).slice(2, 8);
    db.execute('INSERT INTO projects (id, orgId, name, status) VALUES (?, ?, ?, ?)', [
      id,
      ctx.orgId,
      body.name,
      body.status ?? 'active',
    ]);
    auditLog.record('project.created', { orgId: ctx.orgId, id, name: body.name }); // PLANTED: ts-floating-promise
    return reply.code(201).send({ project: { id, orgId: ctx.orgId, name: body.name, status: body.status ?? 'active' } });
  });

  app.get('/transactions/export', async (req, reply) => {
    const ctx = authContext(req);
    if (!ctx) return reply.code(401).send({ error: 'unauthenticated' });
    const raw = fs.readFileSync(`${DATA_DIR}/transactions.csv`, 'utf8'); // PLANTED: event-loop-blocking
    const lines = raw.trim().split('\n');
    const header = lines[0];
    const rows = lines.slice(1).filter((line) => line.split(',')[1] === ctx.orgId);
    const csv = [header, ...rows].join('\n');
    reply.header('content-type', 'text/csv');
    return csv;
  });

  // CLEAN: JSON schema validation + tenant/ownership check + awaited async + explicit error handling.
  const createTransactionSchema = {
    body: {
      type: 'object',
      required: ['projectId', 'amount', 'currency'],
      additionalProperties: false,
      properties: {
        projectId: { type: 'string' },
        amount: { type: 'number', minimum: 0 },
        currency: { type: 'string', enum: ['USD', 'EUR'] },
      },
    },
  } as const;

  app.post<{ Body: { projectId: string; amount: number; currency: string } }>(
    '/transactions',
    { schema: createTransactionSchema },
    async (req, reply) => {
      const ctx = authContext(req);
      if (!ctx) return reply.code(401).send({ error: 'unauthenticated' });
      const owned = db.query('SELECT * FROM projects WHERE id = ? AND orgId = ?', [req.body.projectId, ctx.orgId]);
      if (owned.length === 0) return reply.code(404).send({ error: 'project not found' });
      const id = 't' + Math.random().toString(36).slice(2, 8);
      try {
        db.execute('INSERT INTO transactions (id, orgId, projectId, amount, currency) VALUES (?, ?, ?, ?, ?)', [
          id,
          ctx.orgId,
          req.body.projectId,
          req.body.amount,
          req.body.currency,
        ]);
        await auditLog.record('transaction.created', { orgId: ctx.orgId, id }); // clean: awaited async
      } catch (err) {
        req.log.error({ err }, 'failed to create transaction'); // clean: explicit handling, no payload leak
        return reply.code(500).send({ error: 'could not create transaction' });
      }
      return reply.code(201).send({ transaction: { id, projectId: req.body.projectId, amount: req.body.amount, currency: req.body.currency } });
    },
  );

  return app;
}
