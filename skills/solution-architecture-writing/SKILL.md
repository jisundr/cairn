---
name: solution-architecture-writing
description: Discovery dimensions, artifact formats, ADR Mode, and technical standards (DB, API, GraphQL) for the 3 architecture documents (architecture-spec, db-schema, api-spec) plus ADRs. Loaded by solution-architect alongside writer-shared.
---

# Solution Architecture Writing

Loaded by `solution-architect` for all 3 technical document types plus ADR Mode, alongside `writer-shared` (general discovery/draft/update mechanics).

---

## Dependency Chain

| Document | Required Upstream |
|---|---|
| `architecture-spec.md` | `docs/requirements/prd.md` AND `docs/requirements/user-flows.md` |
| `db-schema.md` | `docs/architecture/architecture-spec.md` |
| `api-spec.md` | `docs/architecture/architecture-spec.md` |

**Recommended upstream (read but not required):** `architecture-spec.md` benefits from `docs/design/ux-spec.md`/`docs/design/ui-layout-spec.md` if they exist; `db-schema.md`/`api-spec.md` benefit from `docs/requirements/prd.md`/`docs/requirements/user-flows.md` if they exist. Read these during Upstream Existence Check if present — their absence is never a blocker.

`db-schema.md` and `api-spec.md` don't depend on each other, so either may be produced first — but not concurrently (both run a live interview against the same human).

ADRs are standalone — no upstream required, may be produced at any point.

Every component, table, and endpoint MUST be traceable to a requirement or user flow.

---

## `architecture-spec.md`

**Scope:** System structure, components, integration points, and non-functional decisions ONLY. No schema definitions, no API endpoint contracts.

**Output path:** `docs/architecture/architecture-spec.md`

**Requires Mermaid** — invoke `Skill(skill: "mermaid-diagrams")` during Draft Phase (Architecture Diagram, Component Interactions, and Deployment Model sections — 3 separate diagrams).

**Discovery Dimensions** (ask ONE at a time, cover all 7 before drafting):
1. What are the major system components or services? (e.g., web app, API server, background workers, third-party integrations)
2. How do components communicate? (e.g., REST, GraphQL, message queues, WebSockets)
3. What are the data stores and their roles? (e.g., primary database, cache, object storage, search index)
4. What are the key non-functional requirements to address? (e.g., scalability targets, availability SLA, latency budgets, security constraints)
5. What deployment model is expected? (e.g., cloud-native, containerized, serverless, monolith)
6. What are the external integrations and third-party dependencies?
7. What are the main technical risks or unknowns?

**Artifact format:**

```markdown
# Architecture Specification: [Project Name]

## Metadata
- Architecture Specification Version: v0.1
- Last Updated: YYYY-MM-DD
- Derived From: docs/requirements/prd.md, docs/requirements/user-flows.md
- Author:
  - AI Tool: Claude Code
  - LLM Model: <exact_model_name>
- Reviewed By:

---

## System Overview
[1-3 paragraph description of the system: what it does, who uses it, and the key architectural approach]

---

## Architecture Diagram
[Mermaid C4 context or component diagram showing system boundaries and major components]

---

## Components
| ID | Component | Responsibility | Technology |
|----|-----------|---------------|------------|
| C-01 | [Name] | [What it does] | [Stack/runtime] |

---

## Component Interactions
[Mermaid sequence or flowchart diagram showing key interaction patterns between components]

| From | To | Protocol | Description |
|------|----|----------|-------------|

---

## Data Stores
| ID | Store | Type | Purpose | Component Owner |
|----|-------|------|---------|-----------------|
| DS-01 | [Name] | [PostgreSQL / Redis / S3 / etc.] | [What is stored here] | [Which component owns it] |

---

## External Integrations
| ID | Integration | Direction | Purpose | Auth Method |
|----|-------------|-----------|---------|-------------|
| EXT-01 | [Service name] | Inbound / Outbound / Both | [Why this integration exists] | [How auth works] |

---

## Non-Functional Requirements
| ID | Category | Requirement | Design Decision |
|----|----------|-------------|-----------------|
| NFR-01 | [Performance / Security / Availability / Scalability] | [Stated requirement] | [How the architecture addresses it] |

---

## Deployment Model
[Description of the deployment topology — cloud provider, containerization, CI/CD, environments]

[Mermaid deployment diagram if applicable]

---

## Security Considerations
- [Authentication and authorization approach]
- [Data protection at rest and in transit]
- [Network boundary controls]
- [Secrets management]

---

## Technical Risks
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|

---

## Assumptions & Open Questions
**Assumptions:**
- [Each assumption made during discovery]

**Open Questions:**
- [Unresolved technical items, if any — omit section if none]
```

---

## `db-schema.md`

**Scope:** PostgreSQL schema design ONLY. No API contracts, no application logic.

**Output path:** `docs/backend/db-schema.md`

**Requires Mermaid** — invoke `Skill(skill: "mermaid-diagrams")` during Draft Phase (Entity Relationship Diagram section).

Apply the Database Standards below while drafting.

**Discovery Dimensions** (ask ONE at a time, cover all 6 before drafting):
1. What are the core data entities? (e.g., users, orders, products — from the architecture spec)
2. What are the relationships between entities? (one-to-many, many-to-many, etc.)
3. What are the access patterns? (read-heavy, write-heavy, real-time, batch)
4. Are there soft-delete or audit requirements?
5. Are there multi-tenancy requirements that affect schema design?
6. What is the expected data volume and growth trajectory?

**Artifact format:**

````markdown
# Database Schema: [Project Name]

## Metadata
- Database Schema Version: v0.1
- Last Updated: YYYY-MM-DD
- Derived From: docs/architecture/architecture-spec.md
- Author:
  - AI Tool: Claude Code
  - LLM Model: <exact_model_name>
- Reviewed By:

---

## Overview
[Brief description of the data model — number of entities, key relationships, storage strategy]

---

## Entity Relationship Diagram
[Mermaid ER diagram showing all tables and their relationships]

---

## Tables

For each table:

### `[table_name]`
**Purpose:** [What this table represents]

```sql
CREATE TABLE [table_name] (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    -- [columns with types, constraints, defaults]
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**Columns:**
| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|

**Indexes:**
```sql
CREATE INDEX CONCURRENTLY idx_[table]_[columns] ON [table]([columns]);
```

**Constraints:**
- [List all constraints — FK, UNIQUE, CHECK — with ON DELETE behavior for FKs]

---

## Migrations
| # | Description | Reversible | Notes |
|---|-------------|-----------|-------|
| 001 | Initial schema — create [tables] | Yes | — |

---

## Assumptions & Open Questions
**Assumptions:**
- [Each schema assumption made during discovery]

**Open Questions:**
- [Unresolved schema items, if any — omit section if none]
````

---

## `api-spec.md`

**Scope:** REST API endpoint contracts ONLY (or GraphQL SDL — see GraphQL Design Standards below when the API surface is GraphQL). No schema definitions, no UI logic.

**Output path:** `docs/backend/api-spec.md`

**No Mermaid** — verified directly, no diagram references anywhere in this template. Do not load `skills/mermaid-diagrams/SKILL.md` for this document type.

Apply the API Standards below while drafting (and GraphQL Design Standards additionally, when the API surface is GraphQL).

**Discovery Dimensions** (ask ONE at a time, cover all 6 before drafting):
1. What are the main API resources? (derived from the architecture and data model)
2. Who are the API consumers? (web frontend, mobile app, third-party, internal services)
3. What authentication mechanism is used? (e.g., JWT, OAuth 2.0, API keys)
4. Are there rate limiting or throttling requirements?
5. What is the initial API version? (default: v1)
6. Are there any existing endpoints or contracts to preserve backward compatibility with?

**Artifact format (REST):**

````markdown
# API Specification: [Project Name]

## Metadata
- API Specification Version: v0.1
- Last Updated: YYYY-MM-DD
- Derived From: docs/architecture/architecture-spec.md
- Author:
  - AI Tool: Claude Code
  - LLM Model: <exact_model_name>
- Reviewed By:

---

## Overview
[Brief description of the API — base URL, version, authentication method, primary consumers]

**Base URL:** `https://api.[project].com/v1`
**Authentication:** [JWT Bearer / OAuth 2.0 / API Key — describe scheme]
**Format:** JSON (`Content-Type: application/json`)

---

## Authentication
[Description of the authentication flow and token lifecycle]

---

## Endpoints

For each resource group:

### [Resource Group] (e.g., Users, Orders)

#### `GET /[resources]`
**Summary:** [One-line description]
**Auth required:** Yes / No

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|

**Response `200 OK`:**
```json
{
  "data": [...],
  "pagination": { "nextCursor": "...", "pageSize": 20, "hasMore": true }
}
```

#### `POST /[resources]`
**Summary:** [One-line description]
**Auth required:** Yes / No

**Request Body:**
```json
{
  "field": "value"
}
```

**Response `201 Created`:**
```json
{
  "id": "...",
  "field": "value",
  "createdAt": "2024-01-15T10:30:00Z"
}
```

**Error Responses:**
| Status | Code | Description |
|--------|------|-------------|
| 400 | VALIDATION_FAILED | [When this occurs] |
| 401 | UNAUTHORIZED | [When this occurs] |

---

## Error Format
All error responses follow this structure:

```json
{
  "code": "ERROR_CODE",
  "message": "Human-readable description",
  "details": [
    { "field": "fieldName", "message": "Validation message" }
  ]
}
```

---

## Versioning
- **Current version:** v1
- **Strategy:** URL-based versioning (`/v1/`, `/v2/`)
- **Breaking change policy:** See API Standards below

---

## Assumptions & Open Questions
**Assumptions:**
- [Each API assumption made during discovery]

**Open Questions:**
- [Unresolved API items, if any — omit section if none]
````

---

## ADR Mode

**Trigger detection** (checked before UPSTREAM EXISTENCE CHECK, in the agent's own DOCUMENT MODE DETECTION):

- New-decision signals: "log that we decided", "document our choice", "record that we chose", "create an ADR for", "we decided to use" — no reference to an existing ADR number.
- Status-update signals: references a specific ADR by number/title ("ADR-0001", "the PostgreSQL ADR") + status-change verbs ("mark as accepted", "deprecate", "supersede", "update the status of").
- If ambiguous: ask ONE targeted question — "Are you recording a new decision, or updating the status of an existing ADR?" — then proceed immediately.

**File path convention:** `docs/adr/ADR-NNNN-<kebab-title>.md`, where `NNNN` is a zero-padded 4-digit sequential number and `<kebab-title>` is the decision title in lowercase-hyphenated form.

**Numbering rules:**
1. Use `Glob` to scan `docs/adr/ADR-*.md` for all existing ADR files.
2. Extract the numeric portion from each filename.
3. Find the highest existing number and increment by 1.
4. If no ADRs exist → start at `0001`.
5. Do not mention this check to the user.

**Mermaid** — invoke `Skill(skill: "mermaid-diagrams")` during the draft phase for ADRs; the diagram itself is optional (include only if the decision is structural/architectural — see the Decision section below).

**Discovery dimensions (5 required):** before asking any questions, extract as much as possible from the opening context; ask only for dimensions marked missing, one at a time:
1. **The decision** — What was decided? State it clearly and directly.
2. **The context** — What situation, problem, or constraint drove this decision?
3. **The alternatives** — What other options were considered? At least one required.
4. **The rationale** — Why was this option chosen over the alternatives?
5. **The consequences** — What are the positive and negative outcomes?

**ADR document template** (no `## Metadata` block — Status/Date substitute):

```markdown
# ADR-NNNN: [Decision Title — concise, imperative, e.g. "Use X as the Y"]

## Status
Proposed

## Date
YYYY-MM-DD

## Context
[What situation, problem, or constraint drove this decision?]

## Decision
[What was decided? State it clearly and directly.]

[Optional Mermaid diagram — include only if the decision is structural/architectural in nature]

## Alternatives Considered
[Bullet list of alternatives and why each was not chosen]

## Rationale
[Why was this decision made? Connect the context to the decision.]

## Consequences
### Positive
[Bullet list of benefits]

### Negative / Trade-offs
[Bullet list of downsides, risks, or constraints introduced]
```

**Immutability rule:** ADR body content is locked after the initial write. `Context`, `Decision`, `Alternatives Considered`, `Rationale`, `Consequences` MUST NOT be modified after writing. Only `## Status` may be updated (valid values: `Proposed`, `Accepted`, `Deprecated`, `Superseded`; if Superseded, include a reference to the superseding ADR).

**Status update format** (sub-mode B — status change only, never a content edit; if the user asks to edit body content, respond: "ADR content is locked after writing. Create a new ADR to record a revised or new decision."):

```markdown
## Status
Accepted

**Status updated:** YYYY-MM-DD — [reason or note explaining the change]
```

If Superseded:

```markdown
## Status
Superseded

**Status updated:** YYYY-MM-DD — Superseded by [ADR-NNNN: Title]
```

**Sub-mode A (new ADR) flow:** determine next ADR number (Numbering rules) → extract/ask the 5 discovery dimensions → draft the complete ADR, present in-session as formatted Markdown (do NOT invoke `Write` yet) → ask "Does this look right? Reply **approve** to write it, or tell me what to change." → write on approval via `Write`.

**Note — deliberate override of `writer-shared`:** presenting the drafted ADR in-session and gating the `Write` call on a plain "approve" reply overrides `writer-shared`'s standard Draft Phase step 4 (which prohibits displaying the full document as text before writing) and its Final Review Phase (`AskUserQuestion`-based review after `Write`). This is intentional and ADR-specific: ADR content is immutable once written, so review must happen before the `Write` call, not after.

**Sub-mode B (status update) flow:** confirm this is a status change only, not content edit → identify the target ADR (from context, or `Glob` + ask if ambiguous) → determine the new status (infer or ask) → gather the reason (from context or ask) → apply the update (only `## Status` field + the status-updated line + superseding reference if applicable) → present the updated content in-session → write on approval.

---

## Database Standards (db-schema.md draft phase)

Assumes PostgreSQL as the default backend.

**Naming conventions (mandatory):**
- Tables: `snake_case`, plural (`user_profiles`, `order_items`)
- Columns: `snake_case`, singular (`first_name`, `created_at`)
- Foreign keys: `<referenced_table_singular>_id` (`user_id`)
- Indexes: `idx_<table>_<columns>` (`idx_orders_user_id`)
- Unique constraints: `uq_<table>_<columns>` (`uq_users_email`)
- Check constraints: `chk_<table>_<description>` (`chk_orders_amount_positive`)
- Join tables (many-to-many): `<table_a>_<table_b>`, alphabetical order (`order_products`)

**Data type picks:**

| Data | Type | Why |
|---|---|---|
| Primary key (new tables) | `BIGINT GENERATED ALWAYS AS IDENTITY` | Preferred over `SERIAL` |
| Public-facing / distributed ID | `UUID DEFAULT gen_random_uuid()` | |
| Money / currency | `NUMERIC(19, 4)` | Never `FLOAT`/`REAL` |
| Timestamps | `TIMESTAMPTZ`, always UTC | Never bare `TIMESTAMP` unless truly timezone-invariant |
| Structured JSON | `JSONB` | Never plain `JSON` |
| Enumerations | `TEXT` + `CHECK` constraint | Easier to evolve than native `ENUM` |

**Constraints and audit columns (mandatory):** every table gets `PRIMARY KEY`, `NOT NULL` where applicable, explicit `ON DELETE` behavior on every FK (`RESTRICT` is the safest default). Standard audit columns on every entity table (not pure join tables): `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`, `updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()` (maintained via trigger/application layer, never manual). Soft-delete column, if used: `deleted_at TIMESTAMPTZ NULL`.

**Migration safety (mandatory):** every migration must be backward compatible. Expand/contract per change type: add column (nullable/default → backfill → deploy); rename column (add new → backfill → dual write/read new → deploy → drop old later); remove column (stop read/write → deploy → drop); change type (add new-typed → backfill → dual write → drop old later); add `NOT NULL` (backfill nulls → `CHECK ... NOT VALID` → `VALIDATE CONSTRAINT` → promote → drop check). Indexes: always `CREATE/DROP INDEX CONCURRENTLY` in production. Large tables (>10M rows): batch backfills 1,000–10,000 rows, `VACUUM ANALYZE` after, watch replication lag.

**Migration file conventions (mandatory):** one logical change per file; naming `YYYYMMDD_HHMMSS_<description>.sql` (or the project's migration tool equivalent). Each entry documents: description, reason, rollback procedure, whether it needs a maintenance window, whether it's irreversible. Rollback rule: document the rollback procedure for every entry; mark **`IRREVERSIBLE`** with a required manual-approval note if it can't be auto-rolled-back.

---

## API Standards (api-spec.md draft phase)

**URL design:** lowercase, hyphen-separated paths (`/user-profiles`); nouns, plural for collections (`/orders`, never `/getOrders`); nest sub-resources only for ownership (`/users/{userId}/orders`); prefer flat + filtering over deep nesting; `POST` for non-CRUD actions (`/orders/{id}/cancel`), never `GET` for state changes.

**Pagination and response envelope (mandatory):** cursor-based pagination is the default for large/frequently-changing collections; offset-based only for small, stable ones. Every list response:

```json
{
  "data": [...],
  "pagination": {
    "nextCursor": "eyJpZCI6MTIzfQ==",
    "pageSize": 20,
    "hasMore": true
  }
}
```

Empty collections return `{ "data": [] }` — never `null` or `404`.

**Filtering/sorting:** query params for filtering (`?status=active&type=order`); `sort=field:direction`, multiple supported (`?sort=status:asc,createdAt:desc`); optional sparse fieldsets (`?fields=id,name,status`).

**Request/response body conventions (mandatory):** `camelCase` field names (never snake_case); dates ISO 8601 (`"2024-01-15T10:30:00Z"`); money as `string` with explicit currency field, never floating point; booleans plain `true`/`false`; identical field names for analogous operations across resources.

**OpenAPI version and structure:** always `openapi: "3.1.0"` (never 3.0.x/Swagger 2.0). Every spec includes `info`, `servers`, `paths`, `components/schemas`, `components/securitySchemes`.

**Schema completeness rules:** every schema object declares `type`, `properties`, `required`, a one-sentence `description`; every property declares `type`, `description`, `example`, `enum` where fixed, `format` where applicable. Reusable schemas live in `components/schemas`, referenced via `$ref`, `PascalCase` names. Request bodies: every `POST`/`PUT`/`PATCH` defines `requestBody` with `required: true`, no read-only fields. Responses: every endpoint defines success + `400`/`422` error; every resource-creating `POST` defines `201`.

**Canonical error schema (mandatory)** — define exactly this in `components/schemas/Error`, used for every error response:

```yaml
Error:
  type: object
  required: [code, message]
  properties:
    code:
      type: string
      description: Machine-readable error code
      example: VALIDATION_FAILED
    message:
      type: string
      description: Human-readable error description
    details:
      type: array
      description: Optional list of field-level validation errors
      items:
        type: object
        properties:
          field: { type: string }
          message: { type: string }
```

**Parameters, security, tags:** path params `name`/`in: path`/`required: true`/`schema`; query params `name`/`in: query`/`schema`/`description`/`required` only when truly required. Every non-public endpoint declares a `security` requirement; public endpoints (health checks) set `security: []` explicitly. Every endpoint carries at least one tag.

**Versioning strategy (mandatory):** URL-based (`/v1/`, `/v2/` — major version only). Deprecation: `deprecated: true` + note ("DEPRECATED: Use [replacement] instead. Removal: [date/version]."); deprecated endpoints stay functional at least **6 months**; a migration guide accompanies every deprecation; optional `Sunset` header. Multi-version coexistence: at most **2 concurrent major versions**; begin deprecating the previous version immediately on a new major release. Version discovery: `GET /versions` or `GET /health` returns current version; `info.version` in the OpenAPI doc must match.

**Pre-finalization checklist:**
- [ ] All endpoints documented with parameters, request/response schemas via `$ref`
- [ ] `Error` schema defined and used for all error responses
- [ ] Authentication defined in `components/securitySchemes`; every endpoint has `security` or explicit `security: []`
- [ ] List endpoints use the `{data, pagination}` envelope; empty lists return `{data: []}`
- [ ] No inline complex schemas — all via `$ref`; schema names are `PascalCase`

---

## GraphQL Design Standards (api-spec.md draft phase, GraphQL surfaces only)

Load this section only when the API surface is GraphQL (co-applied alongside API Standards above for cross-cutting conventions — pagination philosophy, error vocabulary, deprecation window). **Only this section is ported** — maestro's source `graphql-guide` also carries backend-implementation and frontend-consumption sections scoped to a code-writing agent (`software-engineer`) that isn't part of this port and that `solution-architect` must never act as (it produces specifications, not code).

**Schema-first contract.** The SDL (`.graphql` schema) is the contract artifact — `api-spec.md` documents the SDL (types, queries, mutations, subscriptions) the way an OpenAPI document is the contract for REST. Do not also produce an OpenAPI document for a GraphQL surface.

**Naming (mandatory):**

```graphql
type Order {                     # PascalCase types
  id: ID!
  createdAt: DateTime!           # camelCase fields
  status: OrderStatus!
}

enum OrderStatus { PENDING SHIPPED CANCELLED }   # SCREAMING_SNAKE_CASE values

input CreateOrderInput { ... }                    # Input suffix
type CreateOrderPayload { order: Order }          # Payload suffix
```

**Nullability.** Fields are non-null (`!`) by default for data that is always present; nullable only when absence is meaningful. Every nullable field's schema description MUST state what `null` means.

**Pagination.** Relay-style cursor connection pattern for any collection that can grow:

```graphql
type OrderConnection {
  edges: [OrderEdge!]!
  pageInfo: PageInfo!
}
type OrderEdge { node: Order! cursor: String! }
type PageInfo { hasNextPage: Boolean! endCursor: String }
```

Never expose an unbounded collection as a raw list field.

**Errors.** Domain/business errors are typed result unions returned as data, not top-level GraphQL errors:

```graphql
union CreateOrderResult = Order | ValidationError

type ValidationError {
  code: String!      # aligns with the canonical Error schema above
  message: String!
  details: [FieldError!]
}
```

Top-level `errors[]` (transport-level) is reserved for auth failures, malformed queries, unhandled exceptions.

**Evolution.** No URL versioning for the schema — evolve additively (new fields/types only). Deprecate retired fields with `@deprecated(reason: "Use x instead. Removal: <date>.")` and hold the same **6-month deprecation window** as REST.
