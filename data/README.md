# Data Boundary

This directory is reserved for local ingestion adapters and source snapshots.
Raw daily ingestion is intentionally ignored by Git.

Production evidence must retain:

- source identity and URL or filing identifier;
- access and observation timestamps;
- market, currency, unit, period, and version metadata;
- licensing and redistribution status;
- transformation and normalization history.

Do not commit confidential records, API credentials, licensed market feeds, or
unlabeled synthetic data. Public examples belong in `examples/` and must state
their classification explicitly.
