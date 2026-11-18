# Car Passport — Project Conventions

## What this project is
A FastAPI + PostgreSQL app that centralizes a vehicle's full service history (records,
receipts, garages) so owners have one source of truth instead of scattered paper
receipts. Learning-focused: prioritize clean, understandable architecture over clever
abstraction.

## Stack
- FastAPI (async)
- PostgreSQL + SQLAlchemy 2.0 (async engine/session — never mix sync and async DB calls)
- Alembic for migrations
- Pydantic v2 for schemas
- Docker Compose for local dev (Postgres + API + MinIO)
- MinIO locally / S3-compatible storage in prod for receipt files
- JWT auth (access + refresh tokens)

## Architecture: vertical slice modules
This project is organized by **domain**, not by technical layer. Each business domain
lives in its own folder under `app/modules/<domain>/` and is self-contained:

```
app/modules/<domain>/
  models.py      # SQLAlchemy ORM models for this domain only
  schemas.py     # Pydantic request/response models (Create, Update, Read variants)
  repository.py  # ALL direct DB access (queries, commits) for this domain lives here
  service.py     # Business logic. Calls repository. Routers never call repository directly.
  router.py      # FastAPI route definitions only. Thin — calls service, returns response.
```

Rules:
- `router.py` must never import `repository.py` directly. Always go through `service.py`.
- `service.py` must never build raw SQLAlchemy queries. That belongs in `repository.py`.
- `service.py` must never touch `repository.db`. To persist changes to a loaded entity,
  mutate it and call `repository.save(entity)`.
- Cross-domain logic (e.g. dashboard aggregating vehicles + service_records) goes in its
  own module, not bolted onto an existing domain.
- Shared code used by 2+ modules (base repository class, custom exceptions, pagination
  helpers) goes in `app/shared/`, not duplicated per module.

### The 404 pattern
`service.get(id)` fetches **or raises** `NotFoundException`. Routers call it and return —
they never re-check for `None`. This is why routers are 3 lines each.

### What lives in `app/shared/`
| File | Purpose |
|---|---|
| `exceptions.py` | `AppException` + `NotFound` / `Conflict` / `Unauthorized` / `Forbidden` / `Validation` / `Storage` |
| `handlers.py` | The one global exception handler. Registered in `main.py`. |
| `repository.py` | `BaseRepository[T]` — `create` / `save` / `get_by_id` / `list` / `count` / `find_one` / `delete` |
| `pagination.py` | `PageParams`, `Page[T]`, `get_page_params` dependency |
| `security.py` | Password hashing (bcrypt) + JWT encode/decode. Model-free by design. |
| `storage.py` | `Storage` ABC + `S3Storage`. All uploads go through `get_storage()`; `ensure_upload_allowed()` checks type and size. |
| `slug.py` | `generate_slug()` |
| `email.py` | `EmailSender` ABC + `SmtpEmailSender`. All email goes through `get_email_sender()`. |
| `due.py` | `due_status()` → `overdue` / `due_soon` / `ok`. Used by documents, reminders, dashboard. |
| `rate_limit.py` | `rate_limit(scope, max, window)` dependency → `TooManyRequestsException` (429). |

### Error response shape
Every error, from any endpoint, comes back as:
```json
{"error": {"code": "not_found", "message": "Make not found"}}
```
Validation errors add `"details": [{"field": "year", "message": "..."}]`.

## Naming conventions
- Python idiomatic: `snake_case` for functions/variables/files, `PascalCase` for classes.
  (Note: this differs from the camelCase convention used in the PHP/Laravel codebase —
  intentional, since mixing conventions across languages causes more confusion than it
  saves.)
- SQLAlchemy models: singular PascalCase (`ServiceRecord`, not `ServiceRecords`).
- Pydantic schemas: `<Entity>Create`, `<Entity>Update`, `<Entity>Response`.
- **Module folder names are plural and snake_case**: `makes/`, `vehicle_models/`,
  `vehicles/`, `service_records/`. The folder holding `VehicleModel` is `vehicle_models/`,
  not `models/`, so `models.py` inside it stays unambiguous.
- **Route paths use kebab-case**: `/service-records`, `/mileage-logs`. Decided once, here.
- Every module's ORM classes must be re-exported from `app/db/models.py`, or Alembic
  autogenerate will silently skip its tables.

## Error handling
- Use custom exceptions from `app/shared/exceptions.py` (e.g. `NotFoundException`,
  `UnauthorizedException`) raised from `service.py`.
- Exception → HTTP status mapping is handled by a single global exception handler
  registered in `main.py`. Routers should not contain try/except blocks for domain errors.

## Testing
- Every new module gets at least a happy-path test under `tests/<domain>/`.
- Use pytest + httpx `AsyncClient` against the FastAPI app with a test database.
- When generating a new module, always generate its test alongside it — don't leave this
  for later.

## What NOT to do
- Don't store uploaded files in Postgres — always through the storage abstraction in
  `app/shared/storage.py`.
- Don't add business logic to `router.py` "just this once."
- Don't skip Alembic migrations by hand-editing the DB schema.
- Don't auto-accept large multi-file generations without showing a plan first — this is a
  learning project; the human reviews architecture-level decisions, the agent handles
  boilerplate.  