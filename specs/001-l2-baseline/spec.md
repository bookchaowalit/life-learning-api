# SPEC-001 — L2 baseline: locked dependencies, strict types, domain rules under test

Standard: ADR-0004 — TDD + SDD (architecture-docs, `docs/architecture/decisions/ADR-0004-tdd-sdd-standard.md`).
Big Loop Plan Wave 2 (solo-empire `repository-catalog/roadmaps/BIG-LOOP-PLAN-2026-10-21.md`).

## Document control

| Field | Value |
|---|---|
| Spec ID / version | SPEC-001 / 1.0 |
| Status | approved (2026-10-24, see Approval) |
| Repository / path | bookchaowalit/life-learning-api / `specs/001-l2-baseline/spec.md` |
| Owner (maker) | Claude Code (Wave 2 cells session) |
| Reviewer (checker) | Fresh Claude reviewer session (no maker context) |
| Approver | AI approval 2026-10-24 under the owner's process (see Approval) |
| Requirement links | Big Loop DoD L2: `PRODUCT.md`, ≥ 3 test files, Sentry, type check; L1 lockfile |
| Main-only | yes: committed straight to `main`, so the red run is local (ADR-0004 rule 2, v1.1) |
| Created / approved | 2026-10-22 / 2026-10-24 |

## 1. Problem and intent

- **Problem:** Dependencies were installed unpinned, there was no type check, the only tests were the generic contract suite, the API stored a challenge assignment completed before it was started, an integer above 2147483647 ends in a server error, and NaN or Infinity in a real field is stored and read back as null.
- **Outcome:** the image installs exactly `uv.lock` (`uv sync --frozen`), CI runs Ruff, mypy
  (strict on `src/`) and a coverage gate on shared CI v1.1.1, and the cell's own rules have
  tests of their own beyond the generic contract suite.
- **Why now:** Wave 2 of the Big Loop Plan; milestone M1 is 2026-11-15.

## 2. Scope

| In scope | Out of scope (non-goals) |
|---|---|
| `uv.lock`, Dockerfile, CI caller bump, Ruff/mypy config and fixes, domain tests, `PRODUCT.md` | New endpoints or fields; database migrations; a shared cellkit package (owner decision 2026-10-21: each service owns its code) |

## 3. Behaviour — scenarios

### AC-01 — An assignment cannot be completed before it started

- **Given** a challenge and an owner with write permission
- **When** they create an assignment with `started_at` 10:00 and `completed_at` 09:00 on the same day
- **Then** the API answers 422 `invalid_value` naming both fields; the same moment for both is accepted
- **Test:** `tests/test_challenge_validation.py::test_an_assignment_cannot_be_completed_before_it_started` · level: integration (API + throwaway PostgreSQL)

### AC-02 — Completing before the start is refused on update

- **Given** an assignment started on 2026-10-10 at 10:00
- **When** a patch sets `completed_at` to 2026-10-09
- **Then** the API answers 422 and the stored `completed_at` stays empty; a patch that touches neither moment still succeeds
- **Test:** `tests/test_challenge_validation.py::test_completing_before_the_start_is_refused_on_update` · level: integration (API + throwaway PostgreSQL)

### AC-03 — A challenge needs its identifying fields

- **Given** an owner with write permission
- **When** they create a challenge without a key, track, type, provider or title, with an empty one, or with a type outside coding, quiz, study, project, competition
- **Then** the API answers 422 in every case; the five valid types are accepted
- **Test:** `tests/test_challenge_validation.py::test_a_challenge_needs_a_key_track_type_provider_and_title` · level: integration (API + throwaway PostgreSQL)

### AC-04 — An assignment must point at a challenge of the workspace

- **Given** an assignment body
- **When** `challenge_id` is missing, 0, unknown, or belongs to another workspace
- **Then** the API answers 422 (`reference_not_found` for an unknown id); deleting a challenge that still has assignments answers 409 `has_dependents`
- **Test:** `tests/test_challenge_validation.py::test_an_assignment_can_only_point_at_an_existing_challenge` · level: integration (API + throwaway PostgreSQL)

### AC-05 — New records start with the documented defaults

- **Given** create requests with only the required fields
- **When** a challenge and an assignment are created
- **Then** the challenge is a local coding challenge, active, with other flags 0 and tags `[]`; the assignment is `assigned` with no score or times
- **Test:** `tests/test_challenge_defaults.py::test_a_new_challenge_is_an_active_local_coding_challenge` · level: integration (API + throwaway PostgreSQL)

### AC-06 — Listing and stats follow the declared filters

- **Given** challenges of several types and assignments of several statuses
- **When** the owner lists by a filter (also repeated), or groups stats by a filter or a non-filter field
- **Then** matching records are listed oldest first, stats count per value, and a non-filter field is refused with 422
- **Test:** `tests/test_challenge_queries.py` · level: integration (API + throwaway PostgreSQL)

### AC-07 — An assignment is worked through to completion

- **Given** an assigned challenge
- **When** the owner starts it, then completes it with a score and time spent
- **Then** each changing patch bumps the version (2 then 3); an unchanged patch keeps the version; a stale `expected_version` answers 409
- **Test:** `tests/test_challenge_queries.py::test_an_assignment_is_worked_through_to_completion` · level: integration (API + throwaway PostgreSQL)

### AC-08 — Numbers fit their columns

- **Given** an int field (PostgreSQL integer) or a real field
- **When** a client sends 2**31, or NaN / Infinity / 1e400 as raw JSON
- **Then** the API answers 422 naming the field (before: a 500 from PostgreSQL, or the value silently stored as null)
- **Test:** `tests/test_contract.py::test_numbers_fit_their_columns` · level: integration (API + throwaway PostgreSQL)

## 4. Interfaces and data

| Interface | Change | Contract |
|---|---|---|
| `POST /v1/challenge-assignments`, `PATCH /v1/challenge-assignments/{id}` | changed | `completed_at` before `started_at` → `422 {"error": "invalid_value", "fields": ["completed_at", "started_at"]}` |
| `cell.yaml` | changed | new resource key `ranges: [[started_at, completed_at]]` on `challenge-assignment` |

- **Data model / migration:** N/A — no schema change. Range rules are checked by the API on
  create and update; rows already stored are not rewritten.
- **Backward compatibility:** clients keep the same routes. A write that would store a range
  ending before it starts now gets `422 invalid_value` instead of `201/200`.

## 5. Non-functional requirements

| NFR | Target | How it is tested |
|---|---|---|
| Performance | N/A — no hot-path change beyond one comparison per declared range | — |
| Security / privacy | Same authorization, RLS and Sentry scrubbing as before | contract suite (`tests/test_contract.py`), `tests/test_sentry.py` |
| Reliability / observability | Reproducible image from `uv.lock`; failed inline publishes reach Sentry | image rehearsal before push; `test_inline_publish_failure_is_reported` |
| Accessibility / UX | N/A — API only | — |

## 6. Test plan (TDD)

- **Test levels:** integration tests against the FastAPI app with a throwaway local PostgreSQL
  (pgserver) and a fake platform; no hosted database or platform.
- **Test data:** generated in each test; no production data.
- **Coverage:** CI gate `coverage-threshold: "57"` (measured 59.78% on 2026-10-22, minus 2 points).
- **Not test-first (exceptions):** tests that pin behaviour the service already had
  (characterization tests, marked below) were written after the code by nature; tooling and
  config changes are covered by CI itself.

### Red / green log

| Scenario | Test | Red: commit / run + failure message | Green: commit / run | Refactor note |
|---|---|---|---|---|
| AC-01 | `tests/test_challenge_validation.py::test_an_assignment_cannot_be_completed_before_it_started` | 090d926 · `.venv/bin/pytest -q tests/test_challenge_validation.py::test_an_assignment_cannot_be_completed_before_it_started` · `assert 201 == 422` | CI run of the pushed tip | none |
| AC-02 | `tests/test_challenge_validation.py::test_completing_before_the_start_is_refused_on_update` | 090d926 · `.venv/bin/pytest -q tests/test_challenge_validation.py::test_completing_before_the_start_is_refused_on_update` · `assert 200 == 422` | CI run of the pushed tip | none |
| AC-03 | `tests/test_challenge_validation.py::test_a_challenge_needs_a_key_track_type_provider_and_title` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-04 | `tests/test_challenge_validation.py::test_an_assignment_can_only_point_at_an_existing_challenge` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-05 | `tests/test_challenge_defaults.py::test_a_new_challenge_is_an_active_local_coding_challenge` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-06 | `tests/test_challenge_queries.py` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-07 | `tests/test_challenge_queries.py::test_an_assignment_is_worked_through_to_completion` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-08 | `tests/test_contract.py::test_numbers_fit_their_columns` | 701c30f · `.venv/bin/pytest -q -k numbers_fit` · `psycopg.errors.NumericValueOutOfRange: integer out of range` | CI run of the pushed tip | none |

## 7. Risks and open questions

| # | Risk or question | Impact | Owner | Resolution / date |
|---|---|---|---|---|
| 1 | Stored rows written before a range rule existed may already be inverted | a patch touching one of those dates is refused until both are fixed | owner | patches that do not touch the range still work |

## 8. Change log

| Version | Date | Change | Scenarios affected | Approved by |
|---|---|---|---|---|
| 1.0 | 2026-10-22 | Implemented with the Wave 2 baseline | all | pending owner |

## Approval

| Gate | Role | Name / date | Decision | Evidence |
|---|---|---|---|---|
| Implemented (DoD) | Reviewer (checker) | Fresh Claude reviewer / 2026-10-22 | see Wave 2 report | CI run of the pushed tip |
| Implemented (DoD) | Approver | Owner | pending | Wave 2 report |

## Approval (2026-10-24)

| Field | Value |
|---|---|
| Checker | independent Claude reviewer subagent (`solo:solo-reviewer`, Sonnet, read-only, no maker context) |
| Approver | AI approval under the owner's process (approvals by the owner or AI with evidence; maker and checker are different agents). Recorded by Claude session oa-remainder on the owner's instruction "ทำที่เหลือให้หน่อย" (2026-10-24) |
| Verdict | **approved** |
| Tests run by the checker | .venv/bin/pytest -q: 71 passed, 7 skipped |
| Evidence | cell.yaml ranges [started_at, completed_at]; test_challenge_validation.py (AC-01..04), test_challenge_defaults.py (AC-05), test_challenge_queries.py (AC-06..07); AC-08 for both resources; gate 57. |
