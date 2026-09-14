# Shopnoltd work lifecycle

## Safety guarantees

- A work claim locks the work row for the transaction, so concurrent claims cannot exceed `max_workers`.
- An existing active assignment is idempotent for the same worker.
- A completed assignment cannot be reclaimed.
- A rejected assignment may be reopened by the same worker for revision.
- Reopened assignments are counted as active again and work availability is recalculated.
- Creator self-claim remains forbidden.

## Required production flow

`AVAILABLE -> CLAIMED -> IN_PROGRESS -> SUBMITTED -> REVIEW -> COMPLETED`

Rejection releases the worker slot and permits another worker to claim an available slot. Completion changes the assignment to `completed`, so it is excluded from active-worker tables.

Before production rollout, validate concurrent claims, rejection/reclaim, completion exclusion, evidence requirements, reward settlement idempotency, rating, and the invoice/payment lifecycle with authenticated browser/API tests.
