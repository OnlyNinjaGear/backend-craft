package main

import (
	"context"
	"time"
)

// InventoryClient talks to the (pretend) downstream inventory service.
type InventoryClient struct {
	// callReserve performs a single reservation attempt. Swappable so tests
	// can inject a fake that succeeds on the first try.
	callReserve func(item string) error
	// callCheck performs a single availability lookup.
	callCheck func(ctx context.Context, item string) (bool, error)
}

// NewInventoryClient returns a client with the default (pretend) transport.
func NewInventoryClient() *InventoryClient {
	return &InventoryClient{
		callReserve: func(item string) error {
			// Pretend network round trip to the inventory service.
			return nil
		},
		callCheck: func(ctx context.Context, item string) (bool, error) {
			if err := ctx.Err(); err != nil {
				return false, err
			}
			return true, nil
		},
	}
}

// Reserve reserves stock for an item, retrying until the inventory service
// accepts the reservation.
func (c *InventoryClient) Reserve(item string) error {
	for {
		err := c.callReserve(item)
		if err == nil {
			return nil
		}
		// PLANTED: retry-without-jitter-or-cap
		time.Sleep(1 * time.Second)
	}
}

// Check reports whether an item is currently in stock.
func (c *InventoryClient) Check(ctx context.Context, item string) (bool, error) {
	return c.callCheck(ctx, item)
}
