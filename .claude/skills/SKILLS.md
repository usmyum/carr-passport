---
name: new-module
description: Scaffold a new domain module (models, schemas, repository, service, router, test) following this project's vertical-slice architecture. Use when the user asks to create/add/scaffold a new module, entity, or resource (e.g. "add a service_records module", "create a garages resource", "scaffold receipts").
---

# Scaffold a new domain module

When invoked, the user will give an entity name (e.g. `service_records`) and a rough
field list (e.g. `service_date, mileage, cost, notes, vehicle_id`). If fields aren't
given, ask for them before generating anything — do not guess a schema for a real
business entity.

## Process

1. **Read `app/modules/vehicles/` in full first.** This is the project's golden-template
   module. Match its exact style: import order, docstring conventions, how sessions are
   injected, how errors are raised. Do not invent a different style.
2. **Read `CLAUDE.md`** at the project root for naming/architecture rules and follow them
   exactly (snake_case, router→service→repository only, custom exceptions, etc).
3. **Show a short plan first** — the files you'll create/edit and a one-line description
   of each — before writing code. Wait for confirmation if not already in an approved
   plan/auto-accept flow.
4. Generate the following files under `app/modules/<entity>/`:

   - **`models.py`** — one SQLAlchemy 2.0 model (`Mapped[]` / `mapped_column()` style,
     matching `vehicles/models.py`). Include `created_at`/`updated_at` timestamps and any
     foreign keys implied by the fields (e.g. `vehicle_id` → FK to `vehicles.id`).
   - **`schemas.py`** — Pydantic v2 models: `<Entity>Base`, `<Entity>Create`,
     `<Entity>Update` (all fields optional), `<Entity>Read` (includes `id`,
     `created_at`). Use `model_config = ConfigDict(from_attributes=True)` on `Read`.
   - **`repository.py`** — async CRUD functions only (`create`, `get_by_id`, `list`,
     `update`, `delete`) using the async session pattern from `vehicles/repository.py`.
     No business logic here.
   - **`service.py`** — thin wrapper calling the repository, raising
     `NotFoundException` from `app/shared/exceptions.py` when a lookup fails, and doing
     any cross-field validation that isn't a DB constraint.
   - **`router.py`** — FastAPI `APIRouter()` with standard CRUD endpoints
     (`POST /`, `GET /`, `GET /{id}`, `PATCH /{id}`, `DELETE /{id}`), each calling
     `service.py` only, using `Depends(get_current_user)` if the entity is user-owned.

5. **Register the router** in `main.py` (`app.include_router(...)`) — check how existing
   routers are registered and match that exact pattern.
6. **Generate an Alembic migration**: run `alembic revision --autogenerate -m "add
   <entity> table"` after the model is written — don't hand-write the migration.
7. **Write a test** at `tests/<entity>/test_<entity>.py` covering create + get + list at
   minimum, using the same fixtures/pattern as `tests/vehicles/` if it exists.
8. **Summarize what was created** in a short list at the end — files touched, migration
   generated, test added — so the user can review before running anything further.

## Things to always ask about instead of assuming
- Whether the entity is user-owned (needs `user_id` + auth dependency) or global
  reference data (like `make`/`model`).
- Any foreign key relationships not obvious from the field list.
- Whether soft-delete is needed (this project doesn't use it by default — hard delete
  unless told otherwise).