# AGENTS.md

Guidance for anyone, human or AI agent, working in this repository.

## What this is

Resident is a private, self-hosted alternative to services like Function Health and Superpower.
It collects Apple Watch data, lab results and medical documents into one database you run
yourself, surfaces trends and insights, and exposes everything to Claude or local LLMs over MCP.

See [docs/PLAN.md](docs/PLAN.md) for the architecture and roadmap.

## Layout

```
apps/server     FastAPI REST API + MCP server (Python, uv)
apps/web        React + Vite dashboard (TypeScript, pnpm)
apps/ios        SwiftUI companion app that syncs HealthKit (XcodeGen)
packages/core   SQLAlchemy models, metric catalog, derived markers
packages/ingest Importers: Apple Health export, HealthKit payloads, later PDFs and FHIR
openapi/        Exported OpenAPI spec, the contract between server, web and iOS
deploy/         Docker Compose (Postgres + TimescaleDB + pgvector)
```

## Commands

Run `just` to list recipes. The common ones:

| Task | Command |
|---|---|
| Install everything | `just setup` |
| Start local Postgres | `just db` then `just migrate` |
| Run the API + MCP server | `just server` (http://localhost:8000, MCP at `/mcp/`) |
| Manage device tokens | `just device-add <name> <scopes...>`, `just devices`, `just device-revoke <name>` |
| Run the dashboard | `just web` (http://localhost:5173) |
| Tests | `just test` |
| Lint | `just lint` |
| Regenerate the TS API client | `just openapi` |
| Open the iOS project | `just ios` |

## Security

[docs/SECURITY.md](docs/SECURITY.md) lists guarantees every change must keep: no public
exposure, no outbound network calls, authenticated and audited access, least-privilege tokens.
In practice:

- **New routes and tools** need `require(Scope...)` (REST) or run behind `RequireScope` (MCP),
  and must call `audit.record(...)` when they read or write health data.
- **No new network calls** from the server: no telemetry, update checks or third-party APIs.
- **No new published ports** in `deploy/compose.yaml`; the Tailscale sidecar is the only way in.
- **Tests:** `apps/server/tests/test_security.py` covers these guarantees and needs `just db`
  running; extend it when adding routes.

## Conventions

- **Units:** every observation is stored in the canonical unit defined in
  `packages/core/src/resident_core/catalog.py`. Convert at ingest time, never at read time.
- **Provenance:** every value keeps its source (and document, if any). Never write an observation
  without a `source_id`.
- **Idempotent imports:** importers must set a stable `external_id` so re-imports don't duplicate.
- **Cited formulas:** derived markers and reference ranges cite their source in a docstring.
- **API changes:** after changing a FastAPI route or schema, run `just openapi` and commit the
  updated `openapi/openapi.json` and `apps/web/src/api/schema.d.ts` with the change.
- **Database changes:** change models in `packages/core`, then add an Alembic migration in
  `apps/server/migrations/versions`. `observations` is a TimescaleDB hypertable, so every unique
  constraint on it must include `start_at`.
- **Privacy:** never log observation values or document contents. Never add telemetry or calls to
  third-party services without an explicit opt-in setting.
- **Not medical advice:** user-facing text frames insights as decision support, not diagnosis.

## Git

`main` has a linear history where **every commit is a squash-merged pull request**. The PR title
becomes the commit subject and the PR description becomes the commit body, so both follow the
commit message rules below. GitHub enforces this (see [Enforcement](#enforcement)).

### Commit messages and PR titles

Use [Conventional Commits](https://www.conventionalcommits.org/) with a **required scope** for
PR titles, since each one becomes a commit on `main`:

```
<type>(<scope>): <summary>

[optional body explaining why]

[optional footer, e.g. BREAKING CHANGE: ..., Refs #12]
```

- **Types:** `feat`, `fix`, `docs`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.
- **Scopes:** `server`, `web`, `ios`, `core`, `ingest`, `mcp`, `db`, `deploy`, `docs`, `repo`.
  Use the most specific one that fits, or `repo` for repo-wide tooling.
- **Summary:** imperative mood ("add", not "added"), lowercase first letter, no trailing period,
  at most 72 characters.
- **Body:** wrap at 72 characters; explain what changed and why, not how.
- **Breaking changes:** add `!` after the scope (`feat(server)!: ...`) and a `BREAKING CHANGE:`
  footer.

Examples:

```
feat(ingest): parse sleep stages from Apple Health exports
fix(ios): save query anchor only after a successful upload
build(web): pin typescript to v6 for openapi-typescript
```

### Pull requests

- **Branch** from `main` as `<type>/<short-description>`, e.g. `feat/lab-pdf-extraction`.
  Never push directly to `main`.
- **One logical change per PR.** Since a PR becomes a single commit, keep each PR focused on one
  coherent change. If work touches several concerns that make sense on their own (a model change
  and migration, then the API route that uses it), open separate PRs in order.
- **Title** is the future commit subject: Conventional Commits with a scope.
- **Description** is the future commit body: what changed and why, wrapped prose, plus any
  `BREAKING CHANGE:` or `Refs #12` footer. Keep checklists and screenshots out of it; put them
  in a PR comment instead. (There's deliberately no PR template, since its text would end up in
  the commit.)
- **Branch commits** are your working history and get squashed away, so write them however you
  like. Only the PR title and description reach `main`.
- **Merge** with "Squash and merge" (the only option enabled). The branch is deleted afterwards.
- Run `just lint` and `just test` before pushing. Every commit on `main` should build and pass
  tests, so history stays bisectable.
- Never commit secrets, `.env` files, real health data or exports. Test fixtures must be
  synthetic.

### Enforcement

| Rule | Where |
|---|---|
| Squash merge only; commit = PR title + description | Repository merge settings |
| Linear history, no force pushes or deletion of `main`, changes via PR only, squash only | `main` ruleset |
| PR title is a Conventional Commit with an allowed type and scope | `.github/workflows/pr-title.yml`, a required check |

The ruleset is versioned in `.github/rulesets/main.json`. To apply changes to it, update the
existing ruleset in the repository settings or with `gh api` (see `.github/rulesets/README.md`).

There are deliberately no local commit hooks: contributors can commit however they like, and the
squash merge produces the final commit.
