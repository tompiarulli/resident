# Resident: plan

## Goal

A private, self-hosted health platform that does what Function Health and Superpower do in
software (one dashboard, trends, optimal ranges, a plan, an AI to ask questions) while you bring
your own labs and keep all data on your own hardware.

## Architecture

```
 Apple Watch ─► HealthKit ─► iOS app ──HTTPS──┐
 Apple Health export.xml ─────────────────────┤
 Lab PDFs / scans ──► extraction + review ────┼─► FastAPI server ─► Postgres
 FHIR bundles / Health Records ───────────────┘        │            (TimescaleDB, pgvector)
                                                       ├─► REST API ─► web dashboard
                                                       └─► MCP (/mcp) ─► Claude / local LLMs
```

- **Storage:** one `observations` hypertable (FHIR Observation-like) with metric key, value,
  canonical unit, time, source and optional document. Originals of uploaded files are kept.
- **Metric catalog** (`packages/core`) maps HealthKit identifiers and LOINC codes to canonical
  metrics and units.
- **Contract:** the FastAPI OpenAPI spec generates the TypeScript client (and later a Swift
  client via swift-openapi-generator).

## Roadmap

### Phase 1: MVP
- [x] Monorepo scaffold, metric catalog, derived markers (HOMA-IR, TG/HDL, eGFR)
- [x] Apple Health export parser (streaming)
- [x] HealthKit ingest endpoint + iOS anchored-query sync with background delivery
- [x] MCP tools: `list_metrics`, `query_observations`
- [ ] Apple Health export upload endpoint and background import job (Procrastinate)
- [ ] Lab PDF pipeline: Docling text/table extraction, LLM structured extraction, LOINC
      mapping, review queue in the dashboard
- [ ] Device pairing with per-device tokens

### Phase 2: Continuous
- [ ] Personal baselines and drift detection for resting HR, HRV, VO2 max, sleep
- [ ] Alerts and a weekly digest
- [ ] Sleep stages and workouts from HealthKit

### Phase 3: Insights
- [ ] Reference and optimal ranges with citations
- [ ] PhenoAge biological age, correlations between wearables and labs
- [ ] Document search (pgvector) and local LLM support for extraction and chat

### Phase 4: Breadth
- [ ] FHIR bundle and HealthKit Health Records import
- [ ] Other wearables (possibly via Open Wearables)
- [ ] Multi-user households, one-command self-hosting

## Decisions

| Decision | Choice | Why |
|---|---|---|
| License | AGPL-3.0 | Hosted forks must stay open |
| Server | Python, FastAPI, SQLAlchemy 2, Alembic | Best PDF/ML ecosystem, official MCP SDK |
| Database | Postgres 17 + TimescaleDB + pgvector | Time series and embeddings in one DB |
| Web | React + Vite, TanStack Router/Query, Tailwind, ECharts | Contributor pool; ECharts handles dense series |
| iOS | SwiftUI, HealthKit, XcodeGen | Native background delivery; no project-file merge conflicts |
| TypeScript | v6, not v7 | openapi-typescript needs the JS compiler API that v7 removed |
