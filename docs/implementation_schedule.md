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

**Phase:** 1 - Documentation
**Progress:** 🟡 In Progress
**Next Milestone:** MVP — Big Four Indicators Ingestion

---

## Phase 1: Documentation ▶ IN PROGRESS

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

## Phase 2: Foundation ▶ IN PROGRESS

**Goal**: Set up environment, database connection, and schema

**Timeline**: Week 1-2 (2026-02-12 to 2026-02-19)

| Task | Status | Owner | Deliverable | Notes |
|------|--------|-------|-------------|-------|
| Environment setup | ✅ Done | Connor | `pyproject.toml` dependencies | Add duckdb, fredapi, pyyaml |
| Environment variables | ✅ Done | Connor | `.env.example` template | Document required vars |
| MotherDuck connection utility | ✅ Done | Connor | `src/fred_macro/db.py` | Connection helper |
| Schema creation script | ✅ Done | Connor | `src/fred_macro/setup.py` | CREATE TABLE scripts |
| Series catalog config | ✅ Done | Connor | `config/series_catalog.yaml` | Tier 1 indicators |
| Logging configuration | ☐ Not Started | Connor | `src/fred_macro/logging.py` | Structured logging |
| Unit tests: Database | ☐ Not Started | Connor | `tests/test_db.py` | Connection and schema tests |

**Success Criteria**:
- [ ] Dependencies installed via `uv sync`
- [ ] Can connect to MotherDuck from Python
- [ ] Schema creates successfully
- [ ] Tier 1 indicators in catalog config
- [ ] Tests pass

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

## Phase 4: Testing & Validation ▶ NEXT UP

**Goal**: Validate MVP against acceptance criteria

**Timeline**: Week 3 (2026-02-26 to 2026-03-02)

| Task | Status | Owner | Deliverable | Notes |
|------|--------|-------|-------------|-------|
| Integration test: Fresh database | ☐ Not Started | Connor | `tests/integration/test_backfill.py` | Test 1 from MVP definition |
| Integration test: Re-run (idempotency) | ☐ Not Started | Connor | `tests/integration/test_idempotency.py` | Test 2 from MVP definition |
| Integration test: Incremental update | ☐ Not Started | Connor | `tests/integration/test_incremental.py` | Test 3 from MVP definition |
| Integration test: Data revision | ☐ Not Started | Connor | `tests/integration/test_revision.py` | Test 4 from MVP definition |
| Data validation queries | ☐ Not Started | Connor | SQL scripts in docs | Row count checks |
| Performance benchmarking | ☐ Not Started | Connor | Timing logs | Verify < 2 min backfill |
| Documentation accuracy check | ☐ Not Started | Connor | README instructions | Can a new user follow setup? |
| Code review | ☐ Not Started | Connor | All source files | Self-review against standards |
| Final testing on fresh environment | ☐ Not Started | Connor | Clean virtual env | Ensure dependencies correct |

**Success Criteria**:
- [ ] All 4 acceptance tests pass
- [ ] Data validation queries show expected row counts
- [ ] No duplicate observations
- [ ] Backfill completes in < 2 minutes
- [ ] Incremental completes in < 30 seconds
- [ ] README instructions work for fresh setup

**Estimated Duration**: 2-3 days

---

## Phase 5: Expansion (Post-MVP) ☐ NOT STARTED

**Goal**: Extend beyond Big Four indicators

**Timeline**: Week 4+ (After MVP completion)

### Tier 2 Indicators

| Task | Status | Owner | Deliverable | Notes |
|------|--------|-------|-------------|-------|
| Define Tier 2 catalog | ☐ Not Started | Connor | Updated `config/series_catalog.yaml` | 20-30 series |
| Test Tier 2 ingestion | ☐ Not Started | Connor | Validation scripts | Verify data quality |
| Documentation update | ☐ Not Started | Connor | Update data dictionary | Full Tier 2 details |

### Data Quality

| Task | Status | Owner | Deliverable | Notes |
|------|--------|-------|-------------|-------|
| Missing value checks | ☐ Not Started | Connor | `src/fred_macro/validation.py` | Alert on missing data |
| Anomaly detection | ☐ Not Started | Connor | `src/fred_macro/validation.py` | Flag outliers |
| Freshness monitoring | ☐ Not Started | Connor | Dashboard or logs | Alert if data stale |

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

**Success Criteria**: TBD after MVP completion

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

### M2: Foundation Ready ☐

**Status**: ☐ Not Started
**Target Date**: 2026-02-19

**Deliverables**:
- [ ] Environment setup complete
- [ ] MotherDuck connection works
- [ ] Schema created
- [ ] Series catalog configured
- [ ] Foundation tests pass

---

### M3: MVP Complete ☐

**Status**: ☐ Not Started
**Target Date**: 2026-03-02

**Deliverables**:
- [ ] All 4 acceptance tests pass
- [ ] Big Four indicators ingested
- [ ] 10 years historical data
- [ ] Zero duplicates
- [ ] Ingestion logs created
- [ ] Documentation accurate

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
- [ ] Start environment setup
- [ ] Create database connection utility

**Expected Progress**: Phase 1 complete, Phase 2 started

---

### Week 2: Core Pipeline Development

**Goals**:
- [ ] Complete foundation setup
- [ ] Build FRED API client
- [ ] Implement ingestion engine
- [ ] Create CLI interface

**Expected Progress**: Phase 2 complete, Phase 3 majority complete

---

### Week 3: Testing & MVP Sign-Off

**Goals**:
- [ ] Run all acceptance tests
- [ ] Validate data quality
- [ ] Performance benchmarking
- [ ] Documentation accuracy check

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
| 2026-02-12 | Phase 1 (Documentation) completed | All docs written | Ready for implementation |

---

## Roll-up Kanban

### Done ✅

**Phase 1: Documentation**
- Project charter
- MVP definition
- Technical requirements
- Data dictionary
- FRED API docs
- System overview
- 3 ADRs
- README
- Implementation schedule
- .agent/CONTEXT.md

### In Progress ▶

(None currently)

### Next Up 📋

**Phase 2: Foundation**
- Environment setup
- Database connection
- Schema creation
- Series catalog config

### Backlog 📦

**Phase 3: Core Pipeline**
- FRED API client
- Ingestion engine
- Backfill/incremental modes

**Phase 4: Testing**
- Integration tests
- Data validation
- Performance benchmarks

**Phase 5: Expansion**
- Tier 2 indicators
- Data quality checks
- Query views
- Automation

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
**Next Review**: After Phase 2 completion
**Status**: Phase 1 complete, ready to start Phase 2
