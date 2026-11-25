# CivicPulse — Smart Civic Issue Detection, Prioritization and Resolution Management System

An AI-assisted platform for citizens to report civic problems (potholes,
garbage, broken streetlights, drainage, waterlogging, etc.), have them
automatically categorized and prioritized, and have them routed to the
right municipal department and field staff for resolution.

> **Status: Phase 8 of 13 complete.** This README, the database schema, and
> the folder structure reflect what actually exists today. Features listed
> under "Planned" are not yet implemented — see the Roadmap section.

---

## 1. Project Overview

Citizens report issues with a photo and location. An AI service classifies
the issue and estimates severity (the citizen can always override). A
priority engine scores the issue using severity, report frequency,
proximity to sensitive locations (schools, hospitals, major roads), and
complaint age. A duplicate-detection service (Phase 7) will group repeated
reports of the same problem. Department admins verify, assign, and track
resolution; field staff execute the work; citizens track status and rate
the outcome.

## 2. Architecture

```
Frontend (React/TS)          Backend (FastAPI)              AI Module
Pages → Components            API routes                     API
  → Hooks → Services            → Schemas                      → AI Service
  → API client                    → Services                     → AI Provider
                                     → Repositories                 → Mock / YOLO
                                       → Models → MySQL
```

> **Honesty notes on what's real vs. not yet wired up:**
> - Category and severity are citizen-selected at report time, pre-filled
>   by an AI suggestion the citizen can override. AI_PROVIDER=mock by
>   default — `MockAIProvider` is a real, deterministic, documented
>   stand-in (same image bytes always produce the same result), not a
>   trained model. `YOLOProvider` is a genuine integration point that
>   raises a clear error rather than fabricating results, since no
>   trained weights exist yet.
> - Every new issue's `priority_score`/`priority_level` are computed by a
>   real, tested priority engine (Phase 6) — severity score + report
>   frequency + location risk + complaint age, normalized to 0-100. The
>   frequency term is driven by Phase 7's duplicate grouping, and the location-risk term is 0 until Phase 12
>   seeds the `risk_zones` table — both are correct current behavior,
>   not bugs. Complaint age is recomputed whenever an issue is created
>   or its severity/category is edited; there's no scheduled background
>   job yet to age it up over time on its own (a Phase 13 concern).
> - Department auto-routing via `issue_categories` only takes effect
>   once that table has rows, which Phase 9 seed data provides — until
>   then `department_name` is `null` on every issue, which is expected.

## 3. Technology Stack

| Layer     | Technology |
|-----------|------------|
| Frontend  | React 18, TypeScript, Vite, Tailwind CSS, React Router, Axios, Recharts, Leaflet |
| Backend   | Python 3.12, FastAPI, SQLAlchemy 2.0, Pydantic v2, python-jose (JWT), passlib/bcrypt |
| Database  | MySQL 8 |
| AI        | Python, Pillow-based preprocessing, pluggable YOLO integration point |
| Infra     | Docker, docker-compose |

## 4. Folder Structure

```
civic-ai-platform/
├── frontend/
│   ├── public/
│   └── src/
│       ├── assets/
│       ├── components/{common,forms,maps,charts,issues}/
│       ├── layouts/            # AuthLayout, CitizenLayout (StaffLayout/AdminLayout arrive with their phases)
│       ├── pages/{auth,citizen,staff,admin}/
│       ├── services/           # authService, profileService, issueService, aiService
│       ├── hooks/
│       ├── context/            # AuthContext
│       ├── types/               domain.ts — mirrors backend enums
│       ├── utils/               issueDisplay.ts — category/status/severity labels and colors
│       ├── routes/             # ProtectedRoute, roleHomePath
│       ├── App.tsx
│       └── main.tsx
│
├── backend/
│   ├── app/
│   │   ├── api/                 auth, citizens, issues, ai routers
│   │   ├── core/                 config.py, database.py, security.py, enums.py, exceptions.py, rate_limit.py
│   │   ├── models/               SQLAlchemy ORM models (complete — 21 tables)
│   │   ├── schemas/              Pydantic request/response models
│   │   ├── services/             auth, profile, issue, ai, priority, audit, notification
│   │   ├── repositories/         data-access layer
│   │   ├── utils/                file_upload.py, geo.py, export_schema.py
│   │   ├── middleware/           auth dependencies (get_current_user, require_roles)
│   │   └── main.py               FastAPI app, CORS, global error handling, router wiring
│   ├── ai/
│   │   ├── models/               trained model weights go here (gitignored)
│   │   ├── inference/            AIProvider abstraction, MockAIProvider, YOLOProvider
│   │   ├── preprocessing/        image_utils.py — decode/resize shared by providers
│   │   └── training/             training scripts/notebooks (future)
│   ├── tests/                    68 passing tests across 5 modules
│   ├── requirements.txt
│   └── Dockerfile
│
├── database/
│   ├── migrations/               Alembic migrations (future)
│   ├── seeds/                    seed data scripts (Phase 9+)
│   └── schema.sql                generated MySQL DDL — regenerate via `python -m app.utils.export_schema`
│
├── docs/
├── uploads/                      runtime file storage (gitignored)
├── docker-compose.yml
├── .env.example
└── README.md
```

## 5. Database Design

21 tables, all confirmed to generate valid MySQL DDL from the SQLAlchemy
models (not hand-written):

`users`, `roles`, `permissions`, `user_roles`, `citizen_profiles`,
`staff_profiles`, `departments`, `issue_categories` (category→department
routing config), `locations`, `risk_zones` (priority-engine reference
data: schools/hospitals/roads/transit/population zones), `civic_issues`,
`issue_images`, `ai_predictions`, `issue_assignments`,
`issue_status_history`, `issue_comments`, `issue_duplicates`,
`issue_feedback`, `notifications`, `audit_logs`.

Regenerate `database/schema.sql` after any model change:
```bash
cd backend && python -m app.utils.export_schema
```

## 6. API Documentation

```
GET  /api/health

POST /api/auth/register          — create a citizen account, returns JWT pair
POST /api/auth/login              — email + password, returns JWT pair
POST /api/auth/refresh            — exchange a refresh token for a new pair
POST /api/auth/forgot-password    — request a reset token (generic response either way)
POST /api/auth/reset-password     — consume a reset token, set new password
GET  /api/auth/me                 — current authenticated user

GET  /api/citizens/me              — citizen's full profile
PUT  /api/citizens/me              — partial update of profile fields
POST /api/citizens/me/profile-image — upload/replace profile photo

POST /api/issues                    — report a new issue (multipart: fields + images[] + optional video)
GET  /api/issues                    — list/filter/search issues
GET  /api/issues/nearby             — issues within a radius of a lat/lng
GET  /api/my/issues                 — the current citizen's own reports
GET  /api/issues/{id}               — full issue detail: images, timeline, AI prediction, priority, comments, feedback
PUT  /api/issues/{id}                — edit title/description/category/severity (owner only, before verification)
POST /api/issues/{id}/comments       — add a comment
POST /api/issues/{id}/feedback       — rate a resolved/closed issue (reporter only, once)

POST /api/ai/analyze-image           — AI category/severity preview for the report wizard (not persisted)

GET  /api/admin/issues/{id}/duplicates   — (admin) reports grouped under master {id}
POST /api/admin/issues/{id}/merge        — (admin) merge {"duplicate_ids": [...]} into master {id}
POST /api/admin/issues/{id}/not-duplicate — (admin) reject an automatic duplicate flag on {id}
PUT  /api/admin/issues/{id}/verify       — (admin) REPORTED/AI_ANALYZED -> VERIFIED
PUT  /api/admin/issues/{id}/assign       — (admin) assign / reassign to a field staff member
GET  /api/admin/staff                    — (admin) staff directory with workload

GET  /api/staff/me                       — my profile + workload stats
GET  /api/staff/issues                   — my active assignments, most urgent first (?priority=&status=)
GET  /api/staff/history                  — completed / handed-over work
GET  /api/staff/issues/{id}              — issue detail incl. internal notes + my assignment state
PUT  /api/staff/issues/{id}/accept       — ASSIGNED -> ACCEPTED
PUT  /api/staff/issues/{id}/start        — ACCEPTED -> IN_PROGRESS
POST /api/staff/issues/{id}/notes        — internal (default) or citizen-visible note
PUT  /api/staff/issues/{id}/progress     — 0-99% + note (visible to the citizen)
POST /api/staff/issues/{id}/photos       — BEFORE_WORK / AFTER_WORK photos (multipart)
PUT  /api/staff/issues/{id}/resolve      — IN_PROGRESS -> RESOLVED; needs >= 1 AFTER_WORK photo
```

All error responses follow `{success: false, message, error_code}`.
Interactive docs at `/api/docs` (Swagger) and `/api/redoc`.

The remaining route surface (the rest of admin, departments, users, notifications,
analytics) is implemented phase by phase, starting with Phase 9.

## 7. Setup Instructions

### Prerequisites
- Python 3.12+, Node.js 20+, MySQL 8 (or Docker)

### Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Database
```bash
mysql -u root -p < database/schema.sql
```

## 8. Environment Configuration

See [`.env.example`](./.env.example) for the full list. Key variables:
`DATABASE_URL`, `JWT_SECRET`, `JWT_EXPIRE_MINUTES`, `UPLOAD_DIRECTORY`,
`MAX_UPLOAD_SIZE`, `AI_PROVIDER` (`mock` or `yolo`), `AI_MODEL_PATH`,
`CORS_ORIGINS`.

## 9. Docker
```bash
docker-compose up --build
```
Spins up MySQL (with `database/schema.sql` auto-loaded), FastAPI on
`:8000`, and the Vite dev server on `:5173`.

## 10. Tests

```bash
cd backend
pip install -r requirements.txt
DATABASE_URL="sqlite:///:memory:" pytest tests/ -v
```

**142 passing tests** across 8 modules:
- `test_auth.py` (13) — registration, login, token refresh, password reset
- `test_profile.py` (8) — profile CRUD, image upload security (content-type allow-list, size limits, Pillow-based spoofed-content-type rejection)
- `test_issues.py` (21) — creation, filtering, nearby search, citizen-side editing rules, comments, feedback, AI wiring (status transition, prediction persistence, override-flag detection, graceful degradation on AI outage)
- `test_ai.py` (11) — MockAIProvider determinism and output validity, YOLOProvider's honest failure mode, provider selection, analyze-image endpoint
- `test_otp.py` (21) — separate email/SMS codes, hashed storage, code never in responses, expiry, single-use, attempt lockout, resend cooldown, delivery-failure handling, provider safety checks
- `test_duplicates.py` (27) — radius/category/time-window/status rules, nearest-master choice, no chaining, priority escalation, image-hash similarity (recorded, never a veto), admin merge (confirm, manual group, idempotent, validation, all-or-nothing, re-homing) and dismiss
- `test_staff.py` (26) — verify/assign (incl. department, availability and activity checks), reassignment before and during work, the full accept→start→photos→notes→progress→resolve chain end to end, step-skipping refusals, evidence requirement, photo-stage rules, assignee-only access, worklist ordering/filtering, work history, staff statistics, notifications and audit entries, the internal-note visibility regression, and the `create_user` helper
- `test_priority.py` (15) — pure scoring logic (severity scores, frequency/location/age capping, level thresholds at every boundary), risk-zone distance querying, and integration with issue creation/editing

## 11. AI Setup

`app.services.ai_service.get_ai_provider()` selects a provider via the
`AI_PROVIDER` environment variable:

- **`mock`** (default): `ai/inference/mock_provider.py`. Deterministic —
  the same image bytes always produce the same category, severity,
  confidence, and detected objects (seeded from a hash of the image).
  Category/severity weightings loosely mirror realistic civic-issue
  frequency purely for demo plausibility.
- **`yolo`**: `ai/inference/yolo_provider.py`. Validates and preprocesses
  the image, then raises a clear `AIProviderError` if no model file
  exists at `AI_MODEL_PATH`, rather than fabricating a result. The
  module docstring lists the exact steps to wire in a trained model.

`POST /api/issues` runs analysis server-side on the first image — the
authoritative, stored prediction — advances the issue to `AI_ANALYZED`,
and flags `is_citizen_edited_category` when the citizen's final choice
differs from the AI's. If the provider is unavailable, issue creation
still succeeds, staying at `REPORTED` without a stored prediction.

## 12. Priority Engine

`app/services/priority_service.py` implements:

```
Priority Score = Severity Score + Report Frequency + Location Risk + Complaint Age
  (normalized / clamped to 0-100)

Severity:  LOW=20, MEDIUM=40, HIGH=70, CRITICAL=100
Frequency: 3 points per duplicate report, capped at 15
Location:  sum of nearby active RiskZone weights, capped at 15
Age:       1 point per day since reported, capped at 10

Levels: 0-30 LOW · 31-60 MEDIUM · 61-80 HIGH · 81-100 CRITICAL
```

Severity dominates (CRITICAL alone hits 100), while the other three
factors let a LOW-severity issue escalate into MEDIUM/HIGH territory
under enough duplicate reports, risk-zone proximity, or age — but never
let a pile of duplicates alone outrank a genuinely CRITICAL report.
Recomputed on issue creation and whenever a citizen edits severity or
category; not yet on a schedule (see the honesty note in §2).

## 12b. Email + Mobile OTP Verification

```
POST /api/auth/send-otp          {"email": "...", "mobile": "+91..."}   (either or both)
POST /api/auth/resend-otp        same body, subject to the cooldown
POST /api/auth/verify-email-otp  {"email": "...", "otp": "123456"}
POST /api/auth/verify-mobile-otp {"mobile": "+91...", "otp": "123456"}
```

Email and SMS get **separate** random codes. Codes are generated with
`secrets`, stored only as an HMAC (never plaintext), expire after 5
minutes, are single-use, lock after 5 wrong attempts, and can only be
re-sent every 60 seconds. The code is never returned by the API.
Verifying marks `users.is_email_verified` / `users.is_phone_verified`
for the matching account. React page: `/verify-contact`.

**Providers** (chosen by env var, so no code changes to switch):

| Setting | `console` (default) | real delivery |
|---|---|---|
| `EMAIL_PROVIDER` | prints the email to the backend terminal | `smtp` (Gmail App Password or any SMTP) |
| `SMS_PROVIDER` | prints the SMS to the backend terminal | `twilio` |

`console` works with no accounts and only runs when `APP_ENV=development`.
Real delivery needs the `SMTP_*` / `TWILIO_*` values in `backend/.env`
(see `.env.example`). Not yet wired: registration does not *require* a
verified contact yet, and MSG91/2Factor (cheaper for India) would be
one more small provider class alongside `twilio_sms.py`.

## 12c. Duplicate Detection

`app/services/duplicate_service.py`. On issue creation a report is flagged
`POTENTIAL_DUPLICATE` of an existing **master** when all of these hold:

- same category;
- within `DUPLICATE_RADIUS_METERS` (default 75 m);
- the master was reported within `DUPLICATE_TIME_WINDOW_HOURS` (default 7 days);
- the master is still open — a new report at a spot already RESOLVED/CLOSED/REJECTED is a recurrence, not a duplicate;
- the master is itself a master (no chains); if several qualify, the nearest wins.

**Image similarity** (a perceptual dHash of the first photo) is recorded on the
match when both reports have a photo, but it is *deliberately not a veto*: the
same pothole photographed from another angle can look very different.

**Grouping.** Each flagged report is linked to its master and counted in
`master.duplicate_count`, which feeds the priority engine's frequency term
(3 points per duplicate, capped at 15). "Reports: N" = 1 + `duplicate_count`.

**Admin correction.** An admin can *merge* duplicates into a master (works on
auto-flagged reports and on reports the detector missed; the merged report is
closed with a timeline note; all-or-nothing) or mark a flag *not a duplicate*
(the report returns to the normal workflow and the master's count and
priority roll back). Merging and dismissing write audit-log entries.

Known limits: a flagged duplicate counts toward the master's priority
*immediately*, before an admin confirms it (dismissing rolls it back); the
detector compares against open masters only, so two reports that were each
fine when filed can't be re-grouped automatically later (an admin can still
merge them); image similarity uses a simple 64-bit hash, not a learned model;
and admin/duplicate-queue notifications arrive in Phase 11.

## 12d. Field Staff Workflow (Phase 8)

```
REPORTED/AI_ANALYZED --verify--> VERIFIED --assign--> ASSIGNED --accept--> ACCEPTED
        --start--> IN_PROGRESS --resolve (needs an AFTER photo)--> RESOLVED
```

- **State machine.** `app/services/workflow.py` holds the only table of allowed
  status moves; every move is validated there and written to the issue timeline,
  so a status can't skip a step (ASSIGNED straight to RESOLVED is refused).
- **Only the assignee can act** (business rule 3). An issue has at most one active
  assignment; everything staff do is checked against it server-side.
- **Resolving needs evidence** (business rule 4): at least one `AFTER_WORK` photo.
  A `BEFORE_WORK` photo doesn't count. Photos are only accepted at the right stage
  (before: after accepting; after: once work has started) and go through the same
  content-type, size and real-image checks as every other upload.
- **Reassigning** (even mid-work) hands the issue to the new person, sends it back to
  ASSIGNED so they must accept it, rolls both people's workload counters, and notifies
  the previous owner. The old assignment appears in their work history.
- **Notes.** Staff notes are internal by default; tick "visible to the citizen" to
  share one. Progress updates are always citizen-visible. **Internal notes are filtered
  out on the server** for citizens (earlier versions returned them and relied on the UI
  to hide them — fixed in this phase, with a regression test).
- **Staff statistics** (workload, resolved count, average resolution hours) update with
  each assignment change.
- **Notifications** are written to the `notifications` table for: issue verified,
  assigned (staff + citizen), assignment changed, work started, resolved. They aren't
  shown in an in-app notification centre until Phase 11.

**Creating staff/admin accounts** (self-registration only makes citizens; the admin UI
is Phase 9):
```bash
cd backend
python -m app.utils.create_user --role FIELD_STAFF --email ravi@city.gov.in --name "Ravi Kumar" --department ROADS
python -m app.utils.create_user --role DEPARTMENT_ADMIN --email admin@city.gov.in --name "Asha Menon"
```
(the password is prompted for; `--department` needs an existing department code).

React pages: `/staff/dashboard`, `/staff/issues` (Active / Work history, priority filter),
`/staff/issues/:id` (context-sensitive actions), `/staff/profile`.

Known limits: `/staff/map` is a disabled nav item until the Phase 10 maps work; the admin
verify/assign/staff-list endpoints are the minimal slice the staff flow needs (rejecting,
reopening, category/severity overrides, department and staff management are Phase 9);
department admins aren't yet restricted to their own department's issues; staff are not
yet notified when an assigned issue's priority rises (Phase 11).

## 13. Demo Accounts

No seed data yet. A citizen can register via `POST /api/auth/register`, and staff/admin
accounts can be created with the `create_user` command in §12d. Bulk realistic seed data
(20 citizens, 10 staff, 4 department admins, 1 super admin, 8 departments, 100+ issues)
arrives in Phase 12.

## 14. Roadmap (Phases 9–13)

| Phase | Scope |
|---|---|
| 9 | Admin dashboard, departments, staff management |
| 10 | Maps and analytics |
| 11 | Notifications |
| 12 | Testing & seed data |
| 13 | Docker hardening & deployment |

## 15. Screenshots

Not applicable yet — see the Roadmap for when each dashboard is built.

---

**What exists right now, verified working:**
- All 21 SQLAlchemy models import cleanly; `database/schema.sql` is real, generated MySQL DDL.
- Full authentication flow (JWT, bcrypt, rate limiting, audit logging, role-based authorization dependencies).
- Citizen profile module with secure image upload (content-type allow-list, size limits, Pillow-based spoofed-file rejection).
- Full issue reporting flow: multi-step wizard, multipart image/video upload, listing/filtering/nearby-search, citizen-side editing rules, comments, feedback — all enforced server-side.
- AI integration: real provider abstraction, deterministic mock provider, honestly-unimplemented YOLO stub, wired into issue creation with graceful degradation.
- **Field staff module (Phase 8)**: assignment, a validated status state machine, the full accept→resolve workflow with evidence photos, staff statistics, and the React staff pages — verified live over HTTP with accounts created by the new CLI. The tests also caught (and the phase fixed) a leak of staff-only notes to citizens through the API.
- **Duplicate detection (Phase 7)**: automatic flagging, grouping under a master, and admin merge/dismiss — verified live with the spec's three-reports-one-pothole scenario (Master CIV-1001, Reports: 3, priority 70 → 76). Tests were mutation-checked: with detection disabled, 8 of them fail.
- **Priority engine (Phase 6)**: a dedicated, pure, unit-tested scoring service wired into issue creation and editing, verified with a **live HTTP smoke test** confirming exact expected math (e.g. 70 HIGH-severity + 8 school risk-zone = 78, HIGH priority) against a real seeded risk zone.
- **68 backend tests pass** against a clean install of the pinned `requirements.txt` (verified in a fresh virtualenv).
- Frontend type-checks and builds cleanly with the full dependency set installed.
- Docker Compose file defined for all three services (not run end-to-end in this environment — no Docker daemon available here).

**A note on earlier deliveries:** this session's sandbox environment reset
twice during development, wiping all files each time. Everything above
was rebuilt from scratch after each reset and re-verified (tests re-run,
builds re-checked) rather than assumed to still work — so what's
described here reflects the actual state of the code in this zip, not
a carried-over claim from before a reset.
