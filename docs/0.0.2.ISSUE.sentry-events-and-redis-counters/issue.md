# Sentry Envelope Handling — Counter Mismatch Bug

## Feature leading to bug

Hawk supports **migration from Sentry** by allowing users to switch only the ingestion endpoint in their Sentry SDK configuration. Hawk Collector accepts Sentry envelopes through a Sentry-compatible endpoint and routes them into the Hawk processing pipeline.

Sentry SDKs could send multiple envelope item types (such as `event`, `transaction`, `log`, etc.). Hawk currently accepts the full envelope at the Collector level and treats it as a valid event for usage accounting and rate limiting purposes.

However, downstream processing does not persist all envelope item types. Only `error` events are stored. Other envelope item types are dismissed later in the worker stage.

The bug arises because **project usage counters and rate limits are updated at Collector ingestion time**, while **actual persistence decisions are made later by the workers after envelope parsing and filtering**.

This creates a mismatch between:
- what is counted as an event
- what is actually stored as an event

---

## Architectural context

### Relevant services

The bug is caused by interaction between two microservices:

- **Collector (Go)** — ingestion, authentication, rate limiting, counter updates
- **Sentry Worker (Node.js/TypeScript)** — envelope parsing and event filtering

---

### Current Sentry envelope processing flow

1. **Sentry SDK → Collector**
   - Client sends a Sentry envelope to Hawk using Sentry-compatible endpoint.
   - Collector receives the envelope as a single message payload.

2. **Collector processing**
   - Validates JWT and project identity.
   - Applies Redis-based rate limiting.
   - Updates project usage counters:
     - rate limit counters
     - minutely counters
     - hourly counters
     - daily counters (used for project charts)
   - Treats the entire envelope as a countable event.
   - Publishes the envelope message to RabbitMQ (`errors/sentry` queue).

3. **RabbitMQ → Sentry Worker**
   - Sentry worker consumes the envelope message.
   - Parses envelope structure and extracts items.

4. **Sentry Worker filtering**
   - Processes and persists only envelope items of type:
     - `event` (error events)
   - Explicitly dismisses other envelope item types:
     - `transaction`
     - `log`
     - other non-error items
   - Dismissed items are:
     - not stored in MongoDB
     - not visible in UI
     - not counted as events in database-backed views

---

### Architectural mismatch

There is a **layering mismatch** in responsibilities:

- **Collector** updates usage and rate counters *before parsing and filtering*
- **Sentry Worker** decides which envelope items are actually valid and storable

The system incorrectly assumes that:
> every accepted envelope at Collector level results in a stored event

In reality:
> only a subset of envelope items are persisted after worker-side filtering

Counters and limits are therefore updated at the wrong architectural layer.

---

## User consequences

### Phantom events in charts

Project minutely/hourly/weekly counters are incremented in Collector for all received envelopes, including those whose items are later dismissed by the Sentry worker.

Result:
- Charts display events that do not exist in storage
- Event counts in charts do not match event lists
- Analytical views become inconsistent

---

### Rate limit exceeded with zero stored events

Rate limiting is enforced in Collector using counters incremented for every received envelope.

If envelopes contain only unsupported item types (for example transactions or logs), they are later dismissed by the Sentry worker and never stored.

Result:
- User may hit rate limits
- System returns rate-limit-exceeded responses
- Project shows zero stored events

This appears contradictory and confusing from the user perspective.

---

### Summary

The root issue is that **usage counting and rate limiting occur at ingestion time**, while **event validity is decided later during envelope parsing and filtering**. This leads to counter, quota, and chart inconsistencies and user-visible confusion.
