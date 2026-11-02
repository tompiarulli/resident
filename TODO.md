# TODO

Near-term focus: **a private, secure Resident that's useful for one person.**

1. **Privacy and security first.** Data never leaves hardware I control. The server is reachable
   only inside my tailnet, every access is authenticated and logged, and nothing calls out to
   the internet.
2. **Every Apple Watch / Apple Health metric syncs automatically** to that server.
3. **A local AI agent** answers questions about my health, using a local model and Resident's
   MCP tools. Cloud models (Claude etc.) are a later, explicit opt-in.

Labs, PDFs, FHIR and dashboard polish wait until these work end to end.
The longer roadmap is in [docs/PLAN.md](docs/PLAN.md).

---

## 1. Security foundation

Do these before any real health data goes in.

**Threat model**
- [x] Write `docs/SECURITY.md`: assets, threats, mitigations, trust boundaries, out of scope
- [x] State the core guarantees: no public exposure, no outbound network calls, no telemetry,
      all access authenticated and audited

**Network: tailnet only**
- [x] No published ports: a Tailscale sidecar serves HTTPS on the MagicDNS name and proxies to
      the server (`deploy/compose.yaml`)
- [ ] Apply the Tailscale ACLs from `deploy/README.md` so only my devices reach `tag:resident`
- [x] Server and database on an internal Docker network with no egress (verified: DNS and
      raw-IP connections both fail)
- [x] Postgres is only reachable from the server container
- [ ] Test the Tailscale sidecar end to end with a real auth key

**Authentication and authorization**
- [x] Per-device tokens: SHA-256 hashed, named, scoped, revocable, last-used time
      (`resident devices add|list|revoke`)
- [x] Scopes: `ingest` (write only), `read` (read only), `admin`
- [x] Dashboard auth via the `Tailscale-User-Login` header, only for allowlisted logins
- [x] MCP endpoint requires a `read` token; Host header allowlist blocks DNS rebinding
- [ ] Pairing flow: QR code in the dashboard instead of copying tokens by hand
- [ ] Least-privilege database roles: the MCP/agent path uses a read-only role

**Data protection**
- [ ] Full-disk encryption on the host (FileVault / LUKS)
- [ ] Encrypted, versioned backups (`pg_dump` + restic or age) to a second location I control;
      test a restore
- [x] Unexpected errors are logged with type and stack frames only, never the message
- [ ] "Export everything" and "delete everything" commands

**Audit log**
- [x] Record every REST and MCP access: actor, action, metric, date range, result count. Never
      values. Admin tokens read it from `GET /api/audit`
- [ ] View the audit log in the dashboard

**Supply chain and hardening**
- [x] GitHub secret scanning, push protection and Dependabot security updates (enabled)
- [ ] CI: Dependabot version updates, `pip-audit`, `pnpm audit` and CodeQL
- [ ] CI: run `just lint` and `just test` on pull requests and require them in the `main` ruleset
- [x] Server container runs as non-root with a read-only filesystem, no capabilities and
      `no-new-privileges`; images pinned by version
- [ ] Pin images by digest
- [x] Request body size limit (413), including chunked uploads
- [ ] Basic rate limiting
- [x] iOS token in the Keychain with `AfterFirstUnlockThisDeviceOnly`
- [ ] iOS: remove `NSAllowsLocalNetworking` once the server is reached over HTTPS

## 2. Run it for real

- [ ] Choose the host (home server / Unraid box / Mac mini) and deploy the hardened compose stack
- [ ] Migrations run automatically on start; health check and restart policy
- [ ] Publish the server image to GHCR from CI, signed, so the host pulls a verified image
- [ ] iPhone: Tailscale app with VPN On Demand so background syncs reach the server

## 3. Apple Watch sync on a real device

- [ ] Install the iOS platform in Xcode; build and run on a simulator
- [ ] Enroll in the Apple Developer Program (needed for HealthKit on device)
- [ ] Pair the app with the server (scan a QR code from the dashboard instead of typing a token)
- [ ] First manual sync succeeds; settings screen shows last sync time and counts per type
- [ ] Handle the phone being locked (HealthKit data is unavailable then; retry later)
- [ ] Verify background delivery after workouts and overnight; `BGProcessingTask` fallback

## 4. Sync every metric

**Server**
- [ ] Store any HealthKit type, not just catalog entries: raw type identifier as the metric key;
      the catalog only adds display names and conversions
- [ ] Generate catalog entries for all HealthKit quantity types with default units
- [ ] Sync deletions (anchored query deleted objects)
- [ ] Accept gzip-compressed batches

**iOS: types**
- [ ] All quantity types with data (heart, respiratory, activity, mobility, body, audio
      exposure, nutrition, wrist temperature)
- [ ] Sleep with stages; stand hours; mindful minutes; heart rate and AFib notifications
- [ ] Workouts (own table): type, duration, energy, distance, average and max heart rate
- [ ] Activity rings; ECG classification and average heart rate
- [ ] Characteristics: date of birth, biological sex, blood type

## 5. Backfill history

- [ ] Resumable first sync on the phone with progress, newest data first
- [ ] Or `export.xml` upload + background import with the streaming parser
- [ ] No double counting when both paths are used
- [ ] Load test with ~5M rows

## 6. Summaries the agent can use

Raw samples are too dense to hand to a model, especially a small local one.

- [ ] Timescale continuous aggregates: daily min/max/avg/count per metric
- [ ] Daily sleep and activity summaries
- [ ] Personal baselines: 30- and 90-day rolling averages for resting HR, HRV, respiratory rate,
      wrist temperature, sleep

## 7. Local AI agent

MCP stays the interface, so any client can be swapped in. Everything runs inside the tailnet.

**Model and runtime**
- [ ] Run a local model server (Ollama, LM Studio or llama.cpp) on a tailnet machine with
      enough memory; pick a model that handles tool calling well
- [ ] Measure tool-calling accuracy on a fixed set of questions before choosing a model

**Agent**
- [ ] Evaluate agent options against the same questions:
  - [ ] A built-in chat page in the dashboard, built with Mastra (TypeScript, fits the web stack,
        has an MCP client) and pointed at the local model
  - [ ] An existing MCP-capable agent such as Hermes Agent or Open WebUI, connecting to
        Resident's MCP endpoint with a read-scoped token
- [ ] Agent gets read-only tools only: no write, delete, web or shell access, which limits the
      damage from prompt injection in imported documents

**MCP tools shaped for questions**
- [ ] `health_snapshot`: latest value, baseline and trend for key metrics in one call
- [ ] `daily_summary(metric, start, end)` and `compare_periods(metric, a, b)`
- [ ] `sleep(start, end)` and `workouts(start, end)`
- [ ] `find_anomalies(start, end)`: days where metrics left their personal baseline
- [ ] `query_observations` downsamples automatically past a size limit
- [ ] Profile resource (age, sex, height) and server instructions covering units, sources and
      the not-medical-advice framing

**Check it works**
- [ ] Ask real questions ("How has my resting heart rate changed since I started running?",
      "How did I sleep this week vs my normal?", "Anything unusual this month?") and fix tools
      until answers are accurate with few calls

## Later

- Claude and other cloud models, as an explicit per-provider opt-in, through a local bridge
  that keeps the server tailnet-only
- Lab PDFs, FHIR import, dashboard insights (see [docs/PLAN.md](docs/PLAN.md))

---

## Unverified

Things built but not yet proven end to end:

- **Tailscale sidecar:** never started (needs a real auth key). Unknown whether `tailscale serve`
  forwards the original Host header or rewrites it to `server:8000`; the server accepts both.
  Also confirm `Tailscale-User-Login` arrives for dashboard requests.
- **iOS app:** only type-checked; never built or run (Xcode is missing the iOS platform).

## Open questions

- Host: Unraid box, Mac mini, or something else? It also needs to run the local model, or
  reach one on another tailnet machine.
- Apple Developer Program now ($99/yr), or simulator until sync works?
- Backfill: phone-side first sync, `export.xml` import, or both?
- Agent: built-in Mastra chat, an existing agent like Hermes Agent or Open WebUI, or try both?
