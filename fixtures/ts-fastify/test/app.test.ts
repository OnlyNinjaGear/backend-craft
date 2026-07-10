import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import type { FastifyInstance } from 'fastify';
import { buildApp } from '../src/app.js';

// Happy-path only. These prove the app runs and the routes behave; the planted
// production-safety flaws do not break the happy path (that is the point).
describe('ts-fastify fixture', () => {
  let app: FastifyInstance;

  beforeAll(async () => {
    app = buildApp();
    await app.ready();
  });

  afterAll(async () => {
    await app.close();
  });

  it('lists only the caller org users', async () => {
    const res = await app.inject({ method: 'GET', url: '/users', headers: { 'x-user-id': 'u1' } });
    expect(res.statusCode).toBe(200);
    const ids = res.json().users.map((u: { id: string }) => u.id);
    expect(ids).toEqual(['u1', 'u2']); // org1 only, u3 (org2) excluded
  });

  it('rejects unauthenticated requests', async () => {
    const res = await app.inject({ method: 'GET', url: '/users' });
    expect(res.statusCode).toBe(401);
  });

  it('fetches a project by id within the tenant boundary', async () => {
    const ok = await app.inject({ method: 'GET', url: '/projects/p1', headers: { 'x-user-id': 'u1' } });
    expect(ok.statusCode).toBe(200);
    expect(ok.json().project.name).toBe('Apollo');

    const crossTenant = await app.inject({ method: 'GET', url: '/projects/p3', headers: { 'x-user-id': 'u1' } });
    expect(crossTenant.statusCode).toBe(404); // clean route does not leak org2's project
  });

  it('searches projects by name', async () => {
    const res = await app.inject({ method: 'GET', url: '/projects/search?q=Apol', headers: { 'x-user-id': 'u1' } });
    expect(res.statusCode).toBe(200);
    expect(res.json().projects.map((p: { name: string }) => p.name)).toContain('Apollo');
  });

  it('creates a project', async () => {
    const res = await app.inject({
      method: 'POST',
      url: '/projects',
      headers: { 'x-user-id': 'u1' },
      payload: { name: 'Delta' },
    });
    expect(res.statusCode).toBe(201);
    expect(res.json().project.name).toBe('Delta');
  });

  it('creates a transaction with schema validation and rejects invalid bodies', async () => {
    const ok = await app.inject({
      method: 'POST',
      url: '/transactions',
      headers: { 'x-user-id': 'u1' },
      payload: { projectId: 'p1', amount: 4200, currency: 'USD' },
    });
    expect(ok.statusCode).toBe(201);
    expect(ok.json().transaction.amount).toBe(4200);

    const bad = await app.inject({
      method: 'POST',
      url: '/transactions',
      headers: { 'x-user-id': 'u1' },
      payload: { projectId: 'p1', amount: 4200, currency: 'GBP' }, // not in enum
    });
    expect(bad.statusCode).toBe(400);
  });

  it('exports transactions for the caller org only', async () => {
    const res = await app.inject({ method: 'GET', url: '/transactions/export', headers: { 'x-user-id': 'u1' } });
    expect(res.statusCode).toBe(200);
    expect(res.headers['content-type']).toContain('text/csv');
    expect(res.body).toContain('t1'); // org1 row present
    expect(res.body).not.toContain('t3'); // org2 row absent
  });
});
