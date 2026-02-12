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

**Phase:** 5 - Expansion Kickoff
**Progress:** ▶ Tier 2 kickoff bundle validated (incremental + backfill) with DQ checks integrated
**Next Milestone:** Tier 2 quality tuning and expanded indicator rollout

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
| Unit tests: Database | ☐ Not Started | Connor | `tests/test_db.py` | Connection and schema tests |

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
| Unit tests: FRED client | ☐ Not Started | Connor | `tests/test_fred_client.py` | Mock API responses |
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

## Phase 5: Expansion (Post-MVP) ▶ IN PROGRESS

**Goal**: Extend beyond Big Four indicators

**Timeline**: Week 4+ (After MVP completion)

### Tier 2 Indicators

| Task | Status | Owner | Deliverable | Notes |
|------|--------|-------|-------------|-------|
| Define Tier 2 catalog | ✅ Done | Connor | Updated `config/series_catalog.yaml` | Kickoff bundle of first 5 Tier 2 indicators added |
| Test Tier 2 ingestion | ✅ Done | Connor | Validation scripts | Incremental + full backfill validation completed for all 9 configured series |
| Documentation update | ✅ Done | Connor | Update data dictionary | Kickoff bundle documented |

### Data Quality

| Task | Status | Owner | Deliverable | Notes |
|------|--------|-------|-------------|-------|
| Missing value checks | ▶ In Progress | Connor | `src/fred_macro/validation.py` | Critical on missing backfill data for required series |
| Anomaly detection | ▶ In Progress | Connor | `src/fred_macro/validation.py` | Basic rapid-change warnings implemented |
| Freshness monitoring | ▶ In Progress | Connor | `src/fred_macro/validation.py` | Frequency-aware stale data warnings implemented |
| Operational DQ reporting | ✅ Done | Connor | `dq_report` table + `dq-report` CLI | Structured findings persisted for each ingestion run |

### Query Views

| Task | Status | Owner | Deliverable | Notes |
|------|--------|-------|-------------|-------|
| Latest values view | ☐ Not Started | Connor | SQL CREATE VIEW | Quick snapshot |
| Year-over-year change view | ☐ Not Started | Connor | SQL CREATE VIEW | Inflation analysis |
| Rolling averages view | ☐ Not Started | Connor | SQL CREATE VIEW | Smooth trends |

### Automation

| Task | Status | Owner | Deliverable | Notes |
|------|--------|-------|-------------|-------|
| Scheduling setup | ☐ Not Started | Connor | Cron or Prefect | Daily incremental runs |
| Error notifications | ☐ Not Started | Connor | Email or Slack alerts | Notify on failures |

### Transition Backlog (Pre-Expansion)

| Task | Status | Owner | Deliverable | Notes |
|------|--------|-------|-------------|-------|
| Deprecate/retire template modules (`src/vibe_coding`) | ☐ Not Started | Connor | Transition plan + execution PR | Execute after stabilization criteria pass |
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

### M4: Tier 2 Expansion ☐

**Status**: ☐ Not Started
**Target Date**: TBD (Post-MVP)

**Deliverables**:
- [ ] 20-30 additional indicators
- [ ] Data quality checks
- [ ] Query views
- [ ] Automated scheduling

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
- [ ] Expand indicator catalog
- [ ] Add data quality checks
- [ ] Create query views
- [ ] Set up automation

**Expected Progress**: Post-MVP enhancements

---

### Current Week: Stabilization Baseline

**Goals**:
- [ ] Eliminate status drift across docs and context
- [x] Ensure test/dependency baseline is green
- [x] Finalize transition path for legacy template modules
- [x] Pick first Tier 2 expansion slice

**Expected Progress**: Phase 4.5 complete, Phase 5 ready to begin

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

### In Progress ▶

**Phase 5: Expansion kickoff**
- Tier 2 kickoff bundle selected and added to catalog
- Tier 2 kickoff docs added to data dictionary
- Catalog validation test coverage added
- Backfill validation complete for all configured kickoff series
- Data-quality checks integrated into ingestion run lifecycle
- Per-run DQ report persistence and CLI inspection command implemented

### Next Up 📋

**Phase 5 kickoff**
- Tune DQ thresholds and severity policy by series/frequency
- Add explicit DQ reporting views/queries for operations
- Plan next Tier 2 expansion batch and scheduling prototype

### Backlog 📦

**Phase 5: Expansion**
- Tier 2 indicators
- Data quality checks
- Query views
- Automation
- Template module deprecation/retirement

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

**Last Updated**: 2026-02-12
**Next Review**: After DQ threshold tuning and next Tier 2 batch selection
**Status**: MVP complete; Phase 5 quality hardening in progress
