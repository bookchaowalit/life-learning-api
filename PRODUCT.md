# Product

<!-- impeccable:product-schema 1 -->

## Platform

api

## Users

- The Solo Empire owner, through the cell's own MCP server (`learning-mcp`, tools
  `learning.<resource>.list|get|create|update|delete`) and the hosted tool hub
  (`platform-mcp-remote-worker`, which lists this cell's origin).
- Local owner tooling that reads cells through the registry client: `ops-toolkit`
  (`infra/scripts/utils/cell_store.py`) and `mcp-aggregator` (`src/cell-store.ts`, `EMPIRE_LEARNING_API`).
- Automations with an `empire-platform` token (for example `owner-mcp`), within the permissions
  `learning.challenge:read|write|delete` and `learning.challenge-assignment:read|write|delete`.
- No web page reads this cell: `life-dashboard-web` has no learning module.

## Product Purpose

A catalogue of learning challenges (coding exercises, quizzes, study tasks, projects, competitions)
from outside providers or local, with how each can be accessed, and a record of when each challenge
was assigned to the owner and how it went (status, score, time spent, solution link).

Success: each challenge the owner might practise exists once with its provider, access model and
estimated time, and every assignment keeps its outcome so progress can be reviewed later.

## Positioning

One capability, one service: its own API (Railway), its own database (Neon) with row-level
security per workspace, and authorization, executions and audit through `empire-platform`. It is
workspace-scoped, so the same service can serve other tenants without code changes.

## Operating Context

- Production: `https://learning-api-production-3cee.up.railway.app` (`/health`), deployed by
  merging to `main` after CI.
- The cell was created empty on 2026-10-11: the old SQLite challenge tables held no rows, so nothing
  was imported. The old `progress_log` stays in SQLite for now (registry note: it feeds the
  roles-skills evidence gates). Imports through the API keep the old id in `legacy_id`.
- Monitored by `platform-uptime-worker` (`learning-api`); errors go to Sentry when `SENTRY_DSN` is set.
- This cell publishes no graph events (`cell.yaml` has no `graph:`).

## Capabilities and Constraints

- `/v1/challenges`: list (filters `challenge_type`, `category`), stats, get, get-by-legacy-id,
  create (with `Idempotency-Key`), patch (with `expected_version`), delete.
- `/v1/challenge-assignments`: the same routes; filters `challenge_id`, `status`.
- Rules tested:
  - A challenge needs `challenge_key`, `track`, `challenge_type`, `provider` and `title`; none can
    be empty or cleared by a patch (422 `invalid_value`).
  - `challenge_type` is one of coding, quiz, study, project, competition; assignment `status` is
    one of assigned, in_progress, completed, skipped; `category` is free text.
  - A new challenge is a local `coding` challenge with `is_active` 1, other flags 0, rotation
    order 0 and `tags_json` `[]`; a new assignment is `assigned`.
  - `is_active`, `is_external`, `free_access` and `account_required` are integers (0 or 1 by
    convention), and `tags_json` is plain text, not validated as JSON.
  - An assignment needs `challenge_id` and `assignment_date`; the challenge must exist in the same
    workspace (422 `reference_not_found`); a challenge that still has assignments cannot be deleted
    (409 `has_dependents`).
  - `completed_at` cannot be before `started_at` (422 `invalid_value`, on create and on patch); the
    same moment is allowed.
  - `challenge_key` is not unique, and a challenge can be assigned many times, including on the same
    day.
  - `stats` groups only by a filter; any other `group_by` is a 422. List order is oldest first
    (`order=desc` reverses it).
- Gaps in the model: `score_percent` has no 0 to 100 bound and the 0/1 flags accept any integer;
  `challenge_key` uniqueness is [ต้องยืนยัน]. Two gaps in the shared service code are covered by
  expected-failure tests: an integer above 2147483647 ends in a server error instead of a 422, and a
  `NaN` or `Infinity` in `time_spent_minutes` is accepted and read back as `null`.
- Out of scope: fetching challenges from providers, grading solutions, scheduling or rotating
  assignments (`rotation_order` is stored but nothing uses it here) and the `progress_log`.

## Measures

Proposed (nothing collects them yet):

- Assignments completed per week (`GET /v1/challenge-assignments/stats?group_by=status`).
- Share of assignments `skipped` vs `completed` per month.
- 5xx rate and p95 latency on `/v1/challenges` (Sentry and uptime worker).
