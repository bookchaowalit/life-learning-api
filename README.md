# life-learning-api
The Learning cell: its own API (Railway, serverless) and its own Neon
database, described by `cell.yaml` and served by the code in `src/cellkit/`, which
this repository owns. It
reuses empire-platform for identity, authorization, executions and audit over
HTTP with the caller's token.

| | |
|---|---|
| API | Railway project `life-learning-api`, service `learning-api` (Serverless) |
| Data | Neon project `life-learning-api`, database `learning` |
| Registry | solo-empire `repository-catalog/registries/online-systems.yaml` (`learning`) |

## API

Every resource has list, stats, get, get-by-legacy-id, create, patch and delete
(see `cellkit/app.py`). Permissions are `learning.<resource>:read|write|delete`.

| Path | Resource | Filters |
|---|---|---|
| `/v1/challenges` | challenge | `challenge_type`, `category` |
| `/v1/challenge-assignments` | challenge-assignment | `challenge_id`, `status` |

## Develop and operate

```bash
uv venv .venv && uv pip install --python .venv/bin/python -e ".[dev]"
.venv/bin/pytest -q
NEON_API_KEY=... .venv/bin/learning-db provision
npm install && railway config apply   # service settings only; code deploys from GitHub (below)
railway scale --service learning-api asia-southeast1-eqsg3a=1 us-east4-eqdc4a=0   # next to Neon and the platform
```

Deploys (CD, since 2026-10-18): `learning-api` is connected to this repository's `main` with
Railway's Wait for CI (`checkSuites`). A merge to `main` deploys only after the CI and security
checks pass; a failing check leaves production on the previous deployment. Roll back by
redeploying an earlier deployment in Railway. `railway up` is no longer used.

Railway variables: `SENTRY_DSN` (error reporting; unset = off, see
`src/cellkit/_sentry.py`), `LEARNING_DB_MODE=hosted`, `LEARNING_DB_URL_API`,
`LEARNING_JWT_PUBLIC_KEY_PEM`, `LEARNING_JWT_ISSUER`, `EMPIRE_PLATFORM_URL`.
