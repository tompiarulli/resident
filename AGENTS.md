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

### Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/) with a **required scope**:

```
<type>(<scope>): <summary>

[optional body explaining why]

[optional footer, e.g. BREAKING CHANGE: ..., Refs #12]
```

- **Types:** `feat`, `fix`, `docs`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.
- **Scopes:** `server`, `web`, `ios`, `core`, `ingest`, `mcp`, `db`, `deploy`, `docs`, `repo`.
  Use the most specific one that fits; if a change truly spans areas, split it into separate
  commits, or use `repo` for repo-wide tooling.
- **Summary:** imperative mood ("add", not "added"), lowercase, no trailing period, at most 72
  characters.
- **Body:** wrap at 72 characters; explain what changed and why, not how.
- **Breaking changes:** add `!` after the scope (`feat(server)!: ...`) and a `BREAKING CHANGE:`
  footer.

Examples:

```
feat(ingest): parse sleep stages from Apple Health exports
fix(ios): save query anchor only after a successful upload
build(web): pin typescript to v6 for openapi-typescript
```

### Practices

- Never commit directly to `main`. Work on a branch named `<type>/<short-description>`, e.g.
  `feat/lab-pdf-extraction`, and merge through a pull request.
- Group changes into logical commits whenever possible: one coherent change per commit, not one
  commit per session or per file. When a piece of work touches several concerns (say, a model
  change, its migration, the API route that uses it, and a docs update), stage and commit them
  as separate commits in an order where each builds on the last. Use `git add -p` to split
  unrelated edits within a file.
- Every commit should build and pass tests on its own, so history stays bisectable.
- Run `just lint` and `just test` before committing.
- Rebase on `main` to stay current; don't merge `main` into feature branches. Squash or tidy
  fixup commits before merging.
- Never commit secrets, `.env` files, real health data, or exports. Test fixtures must be
  synthetic.
- Don't rewrite history on `main` or on branches others have pulled.
- PR titles follow the same Conventional Commits format, since they become squash commit messages.
