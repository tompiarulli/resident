# Resident

**Your own resident doctor's chart, running on your own hardware.**

Resident is a private, self-hosted alternative to services like Function Health and Superpower.
It pulls in your Apple Watch data, lab results and medical documents, keeps them in a database
you control, spots trends early, and lets Claude or a local LLM answer questions about your
health over MCP.

> [!WARNING]
> **Resident is in very early development and is not ready to use.** Expect missing features,
> breaking changes and data loss between versions. Don't rely on it for real health data yet.

> [!IMPORTANT]
> Resident is not medical advice. It provides decision support, not a diagnosis. Talk to a
> clinician about your results.

## Pieces

- **iOS companion app** syncs HealthKit data (heart rate, HRV, VO2 max, sleep, weight and more)
  to your server in the background.
- **Server** (FastAPI + Postgres/TimescaleDB) stores every measurement with its source, in
  canonical units.
- **MCP server** at `/mcp` lets Claude Desktop, Claude Code or local models query your data.
- **Web dashboard** (React + Vite) shows your metrics and trends.

Coming next: lab PDF extraction, FHIR import, derived markers, alerts and a weekly digest.
See [docs/PLAN.md](docs/PLAN.md).

## Quick start

Requires [uv](https://docs.astral.sh/uv/), [pnpm](https://pnpm.io/), [just](https://just.systems/),
Docker, and for the iOS app Xcode with [XcodeGen](https://github.com/yonaskolb/XcodeGen).

```bash
cp .env.example .env
just setup
just db && just migrate
just server   # API on :8000, MCP on :8000/mcp
just web      # dashboard on :5173
just ios      # opens the Xcode project
```

### Connect Claude

Add Resident as a remote MCP server pointing at `http://localhost:8000/mcp`.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) to get set up and open a pull request, and
[AGENTS.md](AGENTS.md) for conventions, commit format and git practices.

## License

[AGPL-3.0](LICENSE). If you run a modified version as a service, you must share your changes.
