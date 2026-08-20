# Car Passport

A FastAPI + PostgreSQL API that centralizes a vehicle's full service history —
records, receipts, garages — so an owner has one source of truth instead of a
shoebox of paper receipts.

This is a learning-focused project: the codebase prioritizes clean,
understandable architecture over clever abstraction. See
[`CLAUDE.md`](./CLAUDE.md) for the full set of conventions this repo follows.

## Stack

- **FastAPI** (async) + **Pydantic v2** for request/response schemas
- **PostgreSQL** + **SQLAlchemy 2.0** (async engine/session throughout)
- **Alembic** for migrations
- **JWT** auth (access + refresh tokens), **bcrypt** password hashing
- **MinIO** locally / **S3-compatible** storage in prod, for receipt files
- **Docker Compose** for local dev (API + Postgres + MinIO)
- **pytest** + **httpx** for tests, run against a real Postgres + MinIO — no mocking

## Architecture

The app is organized by **domain**, not by technical layer. Each business
domain is a self-contained "vertical slice" under `app/modules/<domain>/`:

```
app/modules/<domain>/
  models.py      # SQLAlchemy ORM models for this domain only
  schemas.py     # Pydantic Create / Update / Response variants
  repository.py  # ALL direct DB access for this domain
  service.py     # Business logic — routers never call repository directly
  router.py      # FastAPI routes only. Thin — calls service, returns response.
```

Shared infrastructure used by more than one domain lives in `app/shared/`
instead of being duplicated:

| File | Purpose |
|---|---|
| `exceptions.py` / `handlers.py` | Domain exceptions + the one global handler that turns them into HTTP responses |
| `repository.py` | `BaseRepository[T]` — create / save / get_by_id / list / count / find_one / delete |
| `pagination.py` | `PageParams`, `Page[T]` for endpoints that can grow unbounded |
| `security.py` | Password hashing + JWT encode/decode — model-free by design |
| `storage.py` | `Storage` ABC + `S3Storage` — every file upload goes through this |
| `slug.py` | `generate_slug()` |

Every error, from any endpoint, comes back the same shape:

```json
{"error": {"code": "not_found", "message": "Vehicle not found"}}
```

## Project structure

```
app/
  core/config.py            # Settings (env-driven)
  db/                        # engine/session, declarative Base, the model registry
  modules/
    users/                   # accounts + JWT auth (register/login/refresh/me)
    makes/                   # vehicle manufacturers (Toyota, Honda, ...)
    vehicle_models/          # models under a make (Corolla, Civic, ...)
    vehicles/                # a specific owned vehicle
    garages/                 # shared directory of service garages
    service_records/         # the actual history entries against a vehicle
    receipts/                # files attached to a service record
  shared/                    # cross-domain infrastructure (see above)
alembic/versions/             # migrations
tests/<domain>/                # one test module per domain, mirrors app/modules
scripts/seed.py                # demo data generator (see below)
```

## Getting started

```bash
cp .env.example .env          # adjust secrets if you care; local defaults work as-is
docker compose up -d          # Postgres + MinIO + API
docker compose exec api alembic upgrade head
```

The API is now at `http://localhost:8000`, interactive docs at
`http://localhost:8000/docs`, MinIO console at `http://localhost:9001`
(`minioadmin` / `minioadmin`).

### Seed some demo data

```bash
docker compose exec api python -m scripts.seed
```

Creates 5 makes with real models, 5 garages, two demo users, and a batch of
vehicles/service records/receipts spread across them. Prints the demo logins
when it finishes:

```
alice@example.com / password123
bob@example.com   / password123
```

Log in via `POST /api/v1/auth/login` in `/docs`, copy the `access_token`,
click **Authorize**, and every protected endpoint has real data behind it.
Re-running the script is safe — makes, models, garages and the demo users are
reused; vehicles/records/receipts get a fresh batch added each time.

### Run the tests

```bash
docker compose exec api python -m pytest
```

Tests run against a real Postgres (`car_passport_test`, created automatically
on first `docker compose up`) and real MinIO — no mocked DB or storage layer.

## API overview

All routes are prefixed with `/api/v1`. 🔒 = requires `Authorization: Bearer
<token>`.

| Domain | Routes |
|---|---|
| **Auth** | `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh` |
| **Users** | 🔒 `GET /users/me` |
| **Makes** | `POST/GET /makes`, `GET/PUT/DELETE /makes/{id}` — public catalog |
| **Vehicle models** | `POST /models/make/{make_id}`, `GET /models?make_id=`, `GET/PUT/DELETE /models/{id}` — public catalog |
| **Vehicles** | 🔒 `POST/GET /vehicles` (paginated), 🔒 `GET/PUT/DELETE /vehicles/{id}` — scoped to your own |
| **Garages** | `POST/GET /garages`, `GET/PUT/DELETE /garages/{id}` — public directory |
| **Service records** | 🔒 `POST/GET /service-records/vehicle/{vehicle_id}` (paginated), 🔒 `GET/PUT/DELETE /service-records/{id}` |
| **Receipts** | 🔒 `POST/GET /receipts/service-record/{id}`, 🔒 `GET /receipts/{id}/download-url`, 🔒 `DELETE /receipts/{id}` |

`GET /health` (no prefix) is a plain liveness probe.

Ownership is enforced with a 404, not a 403: touching a vehicle (or a service
record, or a receipt) that belongs to someone else looks identical to it not
existing at all — the API never confirms that someone else's resource is
there.

## Current status

**Built:** the full vehicle catalog (makes → models → vehicles), JWT auth
with per-user vehicle ownership, garages, service records, receipt uploads
through the storage abstraction, and a demo-data seed script. 49 tests, all
green.

**Not built yet:**
- Password reset / email verification
- Refresh-token rotation or revocation (tokens just expire — no blacklist)
- Content-type/extension allowlisting on receipt uploads
- A dashboard/aggregation endpoint (e.g. "upcoming service across all your vehicles")
- Rate limiting, structured logging, CI

See recent commit history / conversation notes for the reasoning behind
specific architectural choices (ownership via 404 vs 403, CASCADE vs RESTRICT
per relationship, why `garages` is a shared directory rather than per-user).
