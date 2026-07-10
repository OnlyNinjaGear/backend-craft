// Pretend durable audit sink. record() is genuinely async (returns a Promise),
// so calling it without await/void/catch is a real floating promise.

export const auditLog = {
  async record(event: string, details: Record<string, unknown>): Promise<void> {
    // simulate an async append to a durable sink
    await new Promise<void>((resolve) => setImmediate(resolve));
    void event;
    void details;
  },
};
