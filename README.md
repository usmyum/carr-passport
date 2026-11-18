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
- **Docker Compose** for local dev (API + Postgres + MinIO + Mailpit)
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

Demo users start unverified. To try transfers, call
`POST /auth/resend-verification` and open the link from the email in
**Mailpit** at <http://localhost:8025> — every email the API sends lands
there, nothing leaves your machine.

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

### Lint

```bash
docker compose exec api ruff check .
```

CI (`.github/workflows/ci.yml`) runs the lint and the full test suite on every
push to `main` and every pull request.

## API overview

All routes are prefixed with `/api/v1`. 🔒 = requires `Authorization: Bearer
<token>`.

| Domain | Routes |
|---|---|
| **Auth** | `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh` (rotates), `POST /auth/logout`, `POST /auth/verify-email`, 🔒 `POST /auth/resend-verification`, `POST /auth/forgot-password`, `POST /auth/reset-password` |
| **Users** | 🔒 `GET /users/me` |
| **Makes** | `POST/GET /makes`, `GET/PUT/DELETE /makes/{id}` — public catalog |
| **Vehicle models** | `POST /models/make/{make_id}`, `GET /models?make_id=`, `GET/PUT/DELETE /models/{id}` — public catalog |
| **Vehicles** | 🔒 `POST/GET /vehicles` (paginated, `?include_past=true` adds cars you sold), 🔒 `GET/PUT/DELETE /vehicles/{id}` |
| **Ownership transfers** | 🔒 `POST /transfers/vehicle/{vehicle_id}`, 🔒 `GET /transfers/incoming`, 🔒 `GET /transfers/outgoing`, 🔒 `POST /transfers/{id}/accept\|decline\|cancel` |
| **Garages** | `POST/GET /garages`, `GET/PUT/DELETE /garages/{id}` — public directory |
| **Service records** | 🔒 `POST/GET /service-records/vehicle/{vehicle_id}` (paginated), 🔒 `GET/PUT/DELETE /service-records/{id}` |
| **Receipts** | 🔒 `POST/GET /receipts/service-record/{id}`, 🔒 `GET /receipts/{id}/download-url`, 🔒 `DELETE /receipts/{id}` |

`GET /health` (no prefix) is a plain liveness probe.

### Accounts & sessions

- **Email verification:** sign-up sends a link. Unverified accounts work
  normally except for ownership transfers, which are addressed by email.
- **Password reset:** `forgot-password` always answers 202 (it never reveals
  which emails have accounts); the link works once, for 60 minutes, and
  using it logs out every existing session.
- **Refresh-token rotation:** each `/auth/refresh` uses up the refresh token
  and returns a new pair. Replaying a used one means it was copied, so that
  whole login is revoked. Access tokens are short-lived and never looked up.
- Emailed tokens and refresh tokens are stored as hashes / IDs, never in a
  form that could be replayed from a database leak.
- **Rate limits** (per IP) on register, login, refresh, verification and
  password-reset endpoints → `429 rate_limited`. In-memory: fine for one API
  process; several processes would need Redis behind `app/shared/rate_limit.py`.
- **Logging:** one line per request with method, path, status and duration.
  Every response has an `X-Request-ID` header, and every log line carries it.
  Readable text locally, JSON lines elsewhere (`APP_ENV` ≠ `local`).

### Ownership: the history belongs to the car

A vehicle is identified by its VIN, and its history follows it from owner to
owner. Who may do what is decided in one place, `OwnershipService`:

| You are… | You can |
|---|---|
| **Current owner** | See the full history (including previous owners' records), add records, edit/delete the records *you* added, start a transfer |
| **Past owner** | Read-only: the vehicle, plus records dated up to the day you sold it |
| **Anyone else** | Nothing — a 404, identical to the vehicle not existing |

- A sale is a transfer: the seller offers the car to the buyer's email, the
  buyer accepts, and ownership moves over in one transaction. Offers expire
  after 14 days.
- A vehicle that has ever changed hands can't be deleted — its history belongs
  to everyone who owned it.
- Past owners get an honest 403 on writes (they already know the car exists);
  strangers always get a 404.

## Current status

**Built:** the full vehicle catalog (makes → models → vehicles), JWT auth,
VIN-based vehicles whose history transfers between owners, garages, service records, receipt uploads
through the storage abstraction, and a demo-data seed script. Receipt uploads
are checked against a content-type allowlist and the configured size limit;
presigned download URLs work from a browser, not just inside the Docker
network (`S3_PUBLIC_ENDPOINT_URL`). Email verification, password reset,
refresh-token rotation, rate limiting and structured logging. 84 tests, all
green.

**Not built yet:**
- A dashboard/aggregation endpoint (e.g. "upcoming service across all your vehicles")
- Mileage logs, service reminders, vehicle documents, shareable history
- Cleanup job for expired refresh / one-time tokens

See recent commit history / conversation notes for the reasoning behind
specific architectural choices (ownership via 404 vs 403, CASCADE vs RESTRICT
per relationship, why `garages` is a shared directory rather than per-user).
