# FRED-Macro-Dashboard — Implementation Schedule

> **Task tracking and milestone roadmap for FRED-Macro-Dashboard project.**

**Status Legend:** ☐ Not Started · ▶ In Progress · ✅ Done · ⚠ Risk/Blocked

---

## Overview

**Project:** FRED-Macro-Dashboard
**Type:** Personal Infrastructure + Learning Project
**Duration:** 2-3 weeks (MVP), ongoing expansion
**Owner:** Connor Kitchings
**Dependencies:** Python 3.10+, MotherDuck, FRED API

---

## Current Status

**Phase:** 5 Complete; Tier 2 Expansion Complete
**Progress:** ✅ Tier 2 Batch 7 (Census Bureau) complete; ✅ Tier 2 Batch 6 (Treasury Direct) complete; ✅ Tier 2 Batch 5 (BLS Expansion via FRED) complete; ✅ mixed-source runtime validation succeeded.
**Next Milestone:** Multi-source verification and Direct BLS evaluation

---

## Phase 1: Documentation ✅ COMPLETE

**Goal**: Complete comprehensive documentation before implementation

**Timeline**: Week 1 (2026-02-12 to 2026-02-16)

| Task | Status | Owner | Deliverable | Notes |
|------|--------|-------|-------------|-------|
| Project charter | ✅ Done | Connor | `docs/project_charter.md` | PRD-style scope |
| MVP definition | ✅ Done | Connor | `docs/mvp_definition.md` | Clear success criteria |
| Technical requirements | ✅ Done | Connor | `docs/technical_requirements.md` | System specs |
| Data dictionary | ✅ Done | Connor | `docs/data/dictionary.md` | Tier 1 + placeholders |
| FRED API documentation | ✅ Done | Connor | `docs/data/sources/fred_api.md` | Data source guide |
| System architecture | ✅ Done | Connor | `docs/architecture/system_overview.md` | Architecture diagram |
| ADR-0002: MotherDuck | ✅ Done | Connor | `docs/architecture/adr/adr-0002-motherduck.md` | Why cloud storage |
| ADR-0003: Upsert Strategy | ✅ Done | Connor | `docs/architecture/adr/adr-0003-upsert-strategy.md` | Why MERGE INTO |
| ADR-0004: Indicator Tiers | ✅ Done | Connor | `docs/architecture/adr/adr-0004-indicator-tiers.md` | Why 3 tiers |
| README update | ✅ Done | Connor | `README.md` | Project overview |
| Implementation schedule | ✅ Done | Connor | `docs/implementation_schedule.md` | This file |
| .agent/CONTEXT.md update | ✅ Done | Connor | `.agent/CONTEXT.md` | AI context |

**Success Criteria**:
- [x] All documentation files created
- [x] Architecture decisions documented
- [x] MVP scope clearly defined
- [x] Tier 1 indicators cataloged

---

## Phase 2: Foundation ✅ COMPLETE

**Goal**: Set up environment, database connection, and schema

**Timeline**: Week 1-2 (2026-02-12 to 2026-02-19)

| Task | Status | Owner | Deliverable | Notes |
|------|--------|-------|-------------|-------|
| Environment setup | ✅ Done | Connor | `pyproject.toml` dependencies | Add duckdb, fredapi, pyyaml |
| Environment variables | ✅ Done | Connor | `.env.example` template | Document required vars |
| MotherDuck connection utility | ✅ Done | Connor | `src/fred_macro/db.py` | Connection helper |
| Schema creation script | ✅ Done | Connor | `src/fred_macro/setup.py` | CREATE TABLE scripts |
| Series catalog config | ✅ Done | Connor | `config/series_catalog.yaml` | Tier 1 indicators |
| Logging configuration | ✅ Done | Connor | `src/fred_macro/logging_config.py` | Structured logging |
| Unit tests: Database | ✅ Done | Connor | `tests/test_db.py` | Connection and schema tests |

**Success Criteria**:
- [x] Dependencies installed via `uv sync`
- [x] Can connect to MotherDuck from Python
- [x] Schema creates successfully
- [x] Tier 1 indicators in catalog config
- [x] Tests pass

**Estimated Duration**: 2-3 days

---

## Phase 3: Core Pipeline ✅ COMPLETE

**Goal**: Build FRED API client and ingestion engine

**Timeline**: Week 2-3 (2026-02-19 to 2026-02-26)

| Task | Status | Owner | Deliverable | Notes |
|------|--------|-------|-------------|-------|
| FRED API client | ✅ Done | Connor | `src/fred_macro/fred_client.py` | Wrapper with rate limiting |
| Data transformation | ✅ Done | Connor | `src/fred_macro/ingest.py` | API response → DataFrame |
| Upsert implementation | ✅ Done | Connor | `src/fred_macro/ingest.py` (inline) | MERGE INTO logic |
| Backfill mode | ✅ Done | Connor | `src/fred_macro/ingest.py` | 10-year historical load |
| Incremental mode | ✅ Done | Connor | `src/fred_macro/ingest.py` | 60-day update logic |
| Ingestion logging | ✅ Done | Connor | `src/fred_macro/ingest.py` | Record run details |
| Error handling | ✅ Done | Connor | All modules | Retry logic, graceful failures |
| CLI interface | ✅ Done | Connor | `src/fred_macro/cli.py` | Command-line interface |
| Unit tests: FRED client | ✅ Done | Connor | `tests/test_fred_client.py` | Mock API responses |
| Unit tests: Ingestion | ☐ Not Started | Connor | `tests/test_ingest.py` | Mock dependencies |

**Success Criteria**:
- [x] Can fetch series from FRED API
- [x] Backfill mode loads 10 years of data
- [x] Incremental mode loads last 60 days
- [x] Upsert prevents duplicates
- [x] Ingestion runs logged
- [x] CLI commands work
- [x] Unit tests pass

**Estimated Duration**: 5-7 days

---

## Phase 4: Testing & Validation ✅ COMPLETE

**Goal**: Validate MVP against acceptance criteria

**Timeline**: Week 3 (2026-02-26 to 2026-03-02)

| Task | Status | Owner | Deliverable | Notes |
|------|--------|-------|-------------|-------|
| Integration test: Fresh database | ✅ Done | Connor | Manual testing | Test 1 from MVP definition |
| Integration test: Re-run (idempotency) | ✅ Done | Connor | Manual testing | Test 2 from MVP definition |
| Integration test: Incremental update | ✅ Done | Connor | Manual testing | Test 3 from MVP definition |
| Integration test: Data revision | ✅ Done | Connor | Manual testing | Test 4 from MVP definition |
| Data validation queries | ✅ Done | Connor | SQL validation | Row count checks |
| Performance benchmarking | ✅ Done | Connor | Timing logs | Backfill ~4.4s, Incremental ~6s |
| Documentation accuracy check | ✅ Done | Connor | README review | Instructions validated |
| Code review | ✅ Done | Connor | All source files | Ruff clean, architecture aligned |
| Final testing on fresh environment | ✅ Done | Connor | Current environment | All tests pass |

**Success Criteria**:
- [x] All 4 acceptance tests pass
- [x] Data validation queries show expected row counts
- [x] No duplicate observations
- [x] Backfill completes in < 2 minutes
- [x] Incremental completes in < 30 seconds
- [x] README instructions work for fresh setup

**Estimated Duration**: 2-3 days

---

## Phase 4.5: Post-MVP Stabilization ✅ COMPLETE

**Goal**: Reconcile repository state before Tier 2 expansion.

**Timeline**: Week of 2026-02-12

| Task | Status | Owner | Deliverable | Notes |
|------|--------|-------|-------------|-------|
| Status/documentation reconciliation | ✅ Done | Connor | Updated `README.md` and `.agent/CONTEXT.md` | Remove pre-MVP drift |
| Dependency/test alignment | ✅ Done | Connor | Passing test suite in project venv | Keep baseline green |
| Dual-stack transition note | ✅ Done | Connor | `docs/architecture/dual_stack_transition.md` | Temporary coexistence plan |
| Backlog prep for Phase 5 kickoff | ✅ Done | Connor | Updated schedule + next tasks | Ready for first Tier 2 work item |

**Success Criteria**:
- [x] Docs and context reflect MVP-complete status
- [x] `uv run --python .venv/bin/python python -m pytest` passes in current environment
- [x] Legacy/template deprecation path documented
- [x] Tier 2 kickoff task selected

---

## Phase 5: Expansion (Post-MVP) ✅ COMPLETE

**Goal**: Extend beyond Big Four indicators

**Timeline**: Week 4+ (After MVP completion)

### Tier 2 Indicators

| Task | Status | Owner | Deliverable | Notes |
|------|--------|-------|-------------|-------|
| Define Tier 2 catalog | ✅ Done | Connor | Updated `config/series_catalog.yaml` | 13 new series added (Batch 2) |
| Add Tier 2 Batch 3 catalog set | ✅ Done | Connor | Updated catalog + tests + docs | Added AHETPI, U6RATE, CPILFESL, SP500, DEXUSEU, BUSLOANS |
| Add Tier 2 Batch 4 catalog set | ✅ Done | Connor | Updated catalog + tests + docs | Added T5YIE, DCOILWTICO, DTWEXBGS, NFCI, WALCL, SOFR |
| Add Tier 2 Batch 5 catalog set (BLS Expansion) | ✅ Done | Connor | Updated catalog + tests + docs | Added 15 BLS series via FRED: JOLTS flows, sectoral employment, wages/comp, unemployment detail, PPI, CPI components |
| Test Tier 2 ingestion | ✅ Done | Connor | Validation scripts | Backfill validation complete (partial status with valid warnings) |
| Validate Batch 3 incremental ingest | ✅ Done | Connor | `ingest --mode incremental` + `run-health` | Run `4ca8ef27-d3ba-4336-9b76-6947e55bae81`: status success, critical=0, warning=7 |
| Validate Batch 4 incremental ingest | ✅ Done | Connor | `ingest --mode incremental` + `run-health` | Run `cb667b1a-e74a-4f0b-b627-1667df74d306`: status success, critical=0, warning=7 |
| Validate Batch 5 backfill | ✅ Done | Connor | `ingest --mode backfill` + `run-health` | Run `7ba696c2-f721-41f5-bb0c-9fe6425937f6`: status success, 56 series, critical=0, warning=8 |
| Add Tier 2 Batch 6 catalog set (Treasury Direct) | ✅ Done | Connor | Updated catalog + tests + docs | Added 8 Treasury series: Avg rates (Bills, Notes, Bonds, TIPS) + Auctions (2Y, 10Y, 30Y) |
| Add Tier 2 Batch 7 catalog set (Census Bureau) | ✅ Done | Connor | Updated catalog + tests + docs | Added 15 Census series: Trade (8) and Business Inventories (7) |
| Documentation update | ✅ Done | Connor | Update data dictionary | Batch 2-7 documented in catalog |

### Data Quality

| Task | Status | Owner | Deliverable | Notes |
|------|--------|-------|-------------|-------|
| Missing value checks | ✅ Done | Connor | `src/fred_macro/validation.py` | Critical on missing backfill data for required series |
| Anomaly detection | ✅ Done | Connor | `src/fred_macro/validation.py` | Tuned to 100% threshold with min-value gate |
| Freshness monitoring | ✅ Done | Connor | `src/fred_macro/validation.py` | Validated via `dq-report` |
| Operational DQ reporting | ✅ Done | Connor | `dq_report` table + `dq-report` CLI | Structured findings persisted for each ingestion run |

### Query Views

| Task | Status | Owner | Deliverable | Notes |
|------|--------|-------|-------------|-------|
| Latest values view | ✅ Done | Connor | SQL CREATE VIEW | `dq_report_latest_runs` covers operational needs |
| Year-over-year change view | ✅ Done | Connor | SQL CREATE VIEW | `view_yoy_change` implemented |
| Rolling averages view | ✅ Done | Connor | SQL CREATE VIEW | `view_rolling_avg` implemented |

### Automation

| Task | Status | Owner | Deliverable | Notes |
|------|--------|-------|-------------|-------|
| Scheduling setup | ✅ Done | Connor | GitHub Actions | Daily incremental runs + catalog sync configured via `.github/workflows/daily_ingest.yml` |
| Error notifications | ✅ Done | Connor | GitHub Actions | Native failure notifications from Actions tab |
| Automated health gate + artifact | ✅ Done | Connor | `run-health` CLI + workflow artifact | Fails on non-success/critical and uploads `run-health.json` |

### Transition Backlog (Pre-Expansion)

| Task | Status | Owner | Deliverable | Notes |
|------|--------|-------|-------------|-------|
| Deprecate/retire template modules (`src/vibe_coding`) | ✅ Done | Connor | Full retirement executed | Phases 0-3 complete; src/vibe_coding removed |
| Tier 2 expansion kickoff (first 5 indicators) | ✅ Done | Connor | Prioritized Tier 2 starter list | HOUST, PERMIT, CSUSHPISA, RSXFS, INDPRO |

**Success Criteria**: Kickoff bundle defined, documented, ingestion-validated, and DQ gate integrated

**Estimated Duration**: Ongoing (weeks to months)

---

## Milestones

### M1: Documentation Complete ✅

**Status**: ✅ Complete
**Date**: 2026-02-12

**Deliverables**:
- ✅ Project charter
- ✅ MVP definition
- ✅ Technical requirements
- ✅ Data dictionary (Tier 1)
- ✅ Architecture overview
- ✅ ADRs (3 decisions documented)

---

### M2: Foundation Ready ✅

**Status**: ✅ Complete
**Target Date**: 2026-02-12

**Deliverables**:
- [x] Environment setup complete
- [x] MotherDuck connection works
- [x] Schema created
- [x] Series catalog configured
- [x] Foundation tests pass

---

### M3: MVP Complete ✅

**Status**: ✅ Complete
**Target Date**: 2026-02-12

**Deliverables**:
- [x] All 4 acceptance tests pass
- [x] Big Four indicators ingested
- [x] 10 years historical data
- [x] Zero duplicates
- [x] Ingestion logs created
- [x] Documentation accurate

**Definition of Done**: See [`docs/mvp_definition.md`](mvp_definition.md)

---

### M4: Tier 2 Expansion ✅

**Status**: ✅ Complete
**Target Date**: 2026-02-13

**Deliverables**:
- [x] 20-30 additional indicators
- [x] Data quality checks
- [x] Query views
- [x] Automated scheduling

---

## Risk Management

| Risk | Likelihood | Impact | Mitigation | Status |
|------|------------|--------|------------|--------|
| FRED API rate limits hit | Medium | Medium | Implement throttling (1 req/sec), exponential backoff | ☐ To Implement |
| MotherDuck free tier limits | Low | High | Monitor storage usage, optimize schema if needed | ☐ Monitor |
| Data schema changes in FRED | Low | Medium | Validate API responses, version control configs | ☐ To Implement |
| Scope creep (adding Tier 2 too early) | Medium | Medium | Stick to MVP definition, defer Tier 2 until M3 complete | ☐ Ongoing |
| Underestimating complexity of upsert | Low | Medium | Extensive testing, reference ADR-0003 | ☐ To Validate |
| Time constraints (2-3 weeks) | Medium | Low | Focus on MVP only, accept Tier 2 delay | ☐ Ongoing |

---

## Dependencies

### External Dependencies

| Dependency | Type | Status | Notes |
|------------|------|--------|-------|
| FRED API Key | API Access | ✅ Available | Free registration |
| MotherDuck Account | Cloud Service | ✅ Available | Free tier active |
| Python 3.10+ | Runtime | ✅ Available | Installed locally |
| uv Package Manager | Tooling | ✅ Available | Installed locally |

### Internal Dependencies

| Task | Depends On | Blocker? |
|------|------------|----------|
| Core Pipeline (Phase 3) | Foundation (Phase 2) | Yes |
| Testing (Phase 4) | Core Pipeline (Phase 3) | Yes |
| Tier 2 Expansion (Phase 5) | MVP Complete (M3) | Yes |

---

## Weekly Breakdown

### Week 1: Documentation + Foundation Start

**Goals**:
- ✅ Complete all documentation
- ✅ Start environment setup
- ✅ Create database connection utility

**Expected Progress**: Phase 1 complete, Phase 2 complete

---

### Week 2: Core Pipeline Development

**Goals**:
- ✅ Complete foundation setup
- ✅ Build FRED API client
- ✅ Implement ingestion engine
- ✅ Create CLI interface

**Expected Progress**: Phase 3 complete

---

### Week 3: Testing & MVP Sign-Off

**Goals**:
- ✅ Run all acceptance tests
- ✅ Validate data quality
- ✅ Performance benchmarking
- ✅ Documentation accuracy check

**Expected Progress**: Phase 3 and 4 complete, MVP achieved

---

### Week 4+: Tier 2 Expansion (Optional)

**Goals**:
- [x] Expand indicator catalog
- [x] Add data quality checks
- [x] Create query views
- [x] Set up automation

**Expected Progress**: M4 complete; move focus to hardening and transition cleanup

---

### Current Week: Phase 5 Stabilization Pass

**Goals**:
- [x] Eliminate status drift across docs and context
- [x] Ensure test/dependency baseline is green
- [x] Finalize transition path for legacy template modules
- [x] Complete catalog metadata integrity checks

**Expected Progress**: Stable baseline for next expansion and template retirement work

---

## Success Metrics

### MVP Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Indicators tracked | 4 (Tier 1) | Count in series_catalog |
| Historical data | 10 years | Date range in observations |
| Total observations | ~400 | Row count in observations |
| Duplicate rate | 0% | No duplicate (series_id, date) |
| Backfill time | < 2 minutes | Ingestion log duration |
| Incremental time | < 30 seconds | Ingestion log duration |
| Test coverage | ≥ 80% | pytest-cov report |

### Post-MVP Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Indicators tracked | 30-50 | Tier 1 + Tier 2 |
| Ingestion success rate | ≥ 99% | ingestion_log status |
| Data freshness | < 1 day lag | Max observation_date |

---

## Change Log

| Date | Change | Reason | Impact |
|------|--------|--------|--------|
| 2026-02-12 | Initial schedule created | Project kickoff | Baseline plan established |
| 2026-02-12 | MVP completed (Phases 1-4) | Pipeline + validation shipped | Entered post-MVP planning |
| 2026-02-12 | Added Phase 4.5 stabilization track | Align docs/tests before expansion | Reduced state drift risk |
| 2026-02-12 | Tier 2 kickoff bundle selected | Start Phase 5 with constrained scope | First 5 Tier 2 indicators added to catalog |
| 2026-02-12 | Tier 2 kickoff ingestion validation run | Confirm catalog + FK + ingestion compatibility | Seed flow fixed; incremental run succeeded |
| 2026-02-12 | Tier 2 backfill + DQ gate completed | Validate scale and quality controls | 9-series backfill successful, DQ fail-on-critical integrated |
| 2026-02-12 | Operational DQ report added | Improve run-level observability | Findings now persisted per run and accessible by CLI |
| 2026-02-13 | Tier 2 Batch 2 and analytical views merged | Expand macro coverage and analyst-ready outputs | Catalog expanded and YOY/Rolling views operational |
| 2026-02-13 | Daily ingestion automation configured | Improve operational reliability | GitHub Actions schedule + runbook guidance in place |
| 2026-02-13 | Stabilization pass applied | Remove status drift and metadata inconsistency | Catalog integrity restored and schedule/context aligned |
| 2026-02-13 | Template retirement Phase 0 started | Prepare low-risk legacy removal path | Retirement plan published and import guardrail added |
| 2026-02-13 | Template retirement Phase 1 completed | Separate active vs legacy test paths | Default tests now run FRED-only; legacy suite remains opt-in |
| 2026-02-13 | Template retirement Phases 2-3 completed | De-primary legacy references and remove retired code path | `src/vibe_coding` and legacy tests removed; schedule marks retirement done |
| 2026-02-13 | Automation health reporting added | Improve post-run observability and CI failure signal | Added `run-health` CLI command, workflow health gate, and artifact upload |
| 2026-02-13 | Tier 2 Batch 3 catalog updates applied | Continue phased indicator expansion with constrained scope | Added 6 validated series and aligned tests/documentation |
| 2026-02-13 | Tier 2 Batch 3 incremental validation completed | Confirm new indicators ingest cleanly in production path | Incremental run succeeded for all Batch 3 series; only non-critical DQ warnings observed |
| 2026-02-13 | Tier 2 Batch 4 catalog updates applied | Extend market/liquidity/inflation-expectations coverage with high-frequency signals | Added 6 validated series and aligned tests/documentation |
| 2026-02-13 | Tier 2 Batch 4 incremental validation completed | Confirm Batch 4 indicators ingest cleanly in production path | Incremental run succeeded for all Batch 4 series; only non-critical DQ warnings observed |
| 2026-02-14 | Tier 2 Batch 5 (BLS Expansion) completed | Comprehensive BLS coverage via FRED API using existing infrastructure | Added 15 BLS series: JOLTS flows (3), sectoral employment (3), wages/comp (3), unemployment detail (2), PPI (2), CPI components (2). Total: 56 series |
| 2026-02-14 | Tier 2 Batch 5 backfill validation completed | Confirm Phase 1 BLS expansion approach successful | Backfill run succeeded for all 56 series; catalog seeding workflow verified |
| 2026-02-14 | Multi-source ingestion baseline hardening applied | Close known blockers before broader Phase 2 rollout | Ingestion now routes series by `source` via `ClientFactory`, BLS retry/warning test blockers resolved, and source-routing tests added |
| 2026-02-14 | Mixed-source merge-readiness validation completed | Validate runtime FRED+BLS routing path before merge | Fixed BLS date filter type mismatch (`Timestamp` vs `str`), full test suite passed (55), verify passed, mixed-source incremental run succeeded with run-health clean (`critical=0`, `warning=0`) |
| 2026-02-14 | Test suite restoration completed | Fix broken tests after architecture refactor | Fixed 9 failing tests in CLI, ingestion, and persistence modules; refactored mocks to match new service-oriented architecture |
| 2026-02-14 | Multi-source integration tests added | Expand test coverage for FRED+BLS scenarios | Added 8 new integration tests covering mixed catalog processing, error paths, client routing, and singleton patterns |
| 2026-02-15 | Tier 2 Batch 6 (Treasury Direct) completed | Expand coverage to direct Treasury source | Added 8 series: Average rates and Auction results. Validated with live API verification. |
| 2026-02-15 | Tier 2 Batch 7 (Census Bureau) completed | Expand coverage to direct Census source | Added 15 series: International Trade (8) and Business Inventories (7). Code complete; pending API key for live verification. |

---

## Roll-up Kanban

### Done ✅

**Phase 1-4**
- Project charter
- MVP definition
- Technical requirements
- Data dictionary
- FRED API docs
- System overview
- 3 ADRs
- Foundation setup (DB, schema, catalog)
- Core pipeline (client, ingest, CLI, logging)
- MVP validation (acceptance tests + performance checks)

**Phase 5: Expansion kickoff and hardening**
- Tier 2 kickoff bundle selected and added to catalog
- Tier 2 kickoff docs added to data dictionary
- Catalog validation test coverage added
- Backfill validation complete for all configured kickoff series
- Data-quality checks integrated into ingestion run lifecycle
- Per-run DQ report persistence and CLI inspection command implemented
- Add explicit DQ reporting views/queries for operations
- Tier 2 Batch 2 indicators and analytical views merged
- Daily GitHub Actions scheduling enabled for incremental ingest
- Tier 2 Batch 3 indicators added with catalog test coverage and docs updates
- Tier 2 Batch 3 indicators validated via incremental run and run-health summary
- Tier 2 Batch 4 indicators added with catalog test coverage and docs updates
- Tier 2 Batch 4 indicators validated via incremental run and run-health summary
- Tier 2 Batch 5 (BLS Expansion via FRED) indicators added with catalog test coverage and docs updates
- Tier 2 Batch 5 indicators validated via backfill run and run-health summary (56 total series ingested)

### Done ✅

**Phase 2 readiness hardening**
- Multi-source client routing in `IngestionEngine` with `ClientFactory` dispatch
- BLS client warning/test blockers resolved and covered by tests
- Mixed-source runtime validation succeeded
- Test suite restoration completed (all 68 tests passing)
- Multi-source integration tests added (8 new tests covering FRED+BLS scenarios)

**Direct BLS API Expansion**
- Expanded from 2 to 25 direct BLS series (23 new series added)
- Catalog now contains 80 total series (55 FRED + 25 BLS direct)
- Added BLS setup documentation
- All 68 tests passing with new catalog

**Treasury & Census Expansion**
- Treasury Direct: 8 series added (Rates & Auctions)
- Census Bureau: 15 series added (Trade & Inventories)
- Total Catalog Size: 103 series

### In Progress ▶

None - Ready for next phase

### Backlog 📦

**Future Enhancements**
- Direct BLS API feature expansion beyond current FRED-mediated BLS coverage
- Additional mixed-source integration scenarios and operational runbook updates
- New indicator expansion as specialized analysis needs arise

---

## Notes

### Learning Objectives

This project doubles as a learning exercise for:
- **DuckDB/MotherDuck**: Cloud analytics database
- **ETL Patterns**: Backfill, incremental, upsert
- **API Integration**: Rate limiting, error handling
- **Data Modeling**: Time series, revisions, catalogs

Track learning insights in session logs and knowledge base.

---

### Session Logging

Every development session should:
1. Check this implementation schedule for current priorities
2. Update task statuses as work progresses
3. Log insights and issues in session logs
4. Update this schedule at session end

---

**Last Updated**: 2026-02-14
**Next Review**: After next phase selection (Alerting or Analytics)
**Status**: M4 complete; Phase 5 Tier 2 expansion complete (103 series: 55 FRED + 25 BLS + 8 Treasury + 15 Census); Multi-source verification in progress
