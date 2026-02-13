# FRED-Macro-Dashboard — AI Agent Context Brief

> **Entry point for all AI sessions.** Read this first, then load relevant skills.

---

## Project Snapshot

**FRED-Macro-Dashboard**: Personal macroeconomic data infrastructure
**Stack**: Python 3.10+ · DuckDB/MotherDuck · FRED API · UV
**Status**: 🟢 Phase 5 Expansion & Hardening In Progress

### Current State

- **Version**: 0.1.0 (MVP complete)
- **Current Focus**: Phase 5 expansion hardening (DQ monitoring, automation reliability, and next-batch prioritization)
- **Next Milestone**: Finalize Tier 2 Batch 4 shortlist and stale-series warning response plan
- **Previous**: Project initiated from Vibe-Coding template; Phase 1-4 delivered

## Recent Activity

- **2026-02-13**: Tier 2 Batch 3 catalog update applied
  - Added 6 Tier 2 indicators to `config/series_catalog.yaml`: `AHETPI`, `U6RATE`, `CPILFESL`, `SP500`, `DEXUSEU`, `BUSLOANS`
  - Added catalog guardrail test coverage for Batch 3 presence
  - Updated data dictionary and implementation schedule to reflect Batch 3 rollout state
  - Ran catalog seed + incremental ingestion validation (`4ca8ef27-d3ba-4336-9b76-6947e55bae81`) with success status and no critical DQ findings
- **2026-02-13**: Automation health reporting integrated
  - Added `run-health` CLI command for run-level status + DQ summaries with automation-friendly exit codes
  - Updated GitHub Actions workflow to run health gate checks and upload `run-health.json` artifacts
  - Updated runbook guidance for local/CI health triage
- **2026-02-13**: Template retirement Phases 2-3 completed
  - Removed legacy `src/vibe_coding` code path and template-specific tests
  - Finalized transition docs/schedule to mark retirement task complete
  - Kept active `fred_macro` quality gates green after retirement changes
- **2026-02-13**: Template retirement Phase 1 completed
  - Segmented test suite into active `fred_macro` path and legacy `vibe_coding` path
  - Added explicit `pytest` legacy opt-in (`--include-legacy-template`)
  - Updated `Makefile` test targets for active-only, legacy-only, and full-suite execution
- **2026-02-13**: Template retirement Phase 0 initiated
  - Added execution plan for retiring legacy `src/vibe_coding` modules
  - Added guardrail test preventing new `vibe_coding` imports in `src/fred_macro`
  - Updated schedule/state tracking to reflect transition execution in progress
- **2026-02-13**: Tier 2 Batch 2 + automation delivered
  - Added and validated Tier 2 Batch 2 indicators; removed failing series from ingestion path
  - Implemented analytical views (`view_yoy_change`, `view_rolling_avg`) in setup workflow
  - Added scheduled daily incremental ingestion via GitHub Actions + runbook guidance
  - Completed stabilization pass to reconcile schedule/context drift and catalog metadata consistency
- **2026-02-12**: Core pipeline implemented and MVP validation completed
  - Built `fred_client.py`, `ingest.py`, `setup.py`, `seed_catalog.py`, and CLI entrypoints
  - Completed acceptance scenarios for backfill, idempotency, incremental updates, and revisions
  - Added structured logging and updated implementation schedule to MVP complete
  - Identified post-MVP cleanup: align docs/tests/config with current shipped state
- **2026-02-12**: Tier 2 kickoff started
  - Added initial 5-series Tier 2 bundle to `config/series_catalog.yaml`
  - Added series catalog validation tests for tier presence and config integrity
  - Documented dual-stack transition and Tier 2 kickoff references
  - Validated incremental ingestion run with FK-safe catalog seeding
  - Validated full 9-series backfill and integrated DQ checks into ingestion
  - Added operational DQ reporting (`dq_report` table + `dq-report` CLI command)

### Architecture

**System Overview**:
```
FRED API → Python Ingestion Engine → MotherDuck (Cloud DuckDB)
```

**Key Components**:
- **Data Source**: FRED API (Federal Reserve Economic Data)
- **Ingestion**: Python-based ETL with backfill and incremental modes
- **Storage**: MotherDuck cloud database (free tier)
- **Data Model**: 3 tables (series_catalog, observations, ingestion_log)
- **Organization**: 3-tier indicator system (Core, Extended, Deep Dive)

**Architectural Decisions**:
- [ADR-0002](../docs/architecture/adr/adr-0002-motherduck.md): Use MotherDuck for cloud accessibility
- [ADR-0003](../docs/architecture/adr/adr-0003-upsert-strategy.md): Use MERGE INTO for data revisions
- [ADR-0004](../docs/architecture/adr/adr-0004-indicator-tiers.md): Three-tier indicator organization

---

## ⚠️ Critical Rules

1. **NEVER work on `main`**. Check branch: `git branch`. Create feature branch immediately if on main.
2. **Scope Discipline**. Keep Tier 1 as the baseline and stabilize quality before Tier 2 expansion.
3. **Documentation-Driven**. All documentation exists — read before implementing.
4. **Learning Project**. Document insights about DuckDB, ETL patterns, and API integration.
5. **No secrets in code**. Use environment variables (MOTHERDUCK_TOKEN, FRED_API_KEY).

### Project-Specific Rules

- **Read ADRs before architectural decisions**. Key decisions already made and documented.
- **Consult MVP definition for acceptance criteria**. Clear test cases defined.
- **Use series catalog config for all indicators**. No hardcoded series IDs.
- **Test upsert logic thoroughly**. Data revisions are critical (see ADR-0003).

---

## 5 Essential Commands

```bash
# Check branch (CRITICAL - never work on main)
git branch

# Setup (first time)
uv sync

# Development loop
uv run ruff format . && uv run ruff check .
uv run --python .venv/bin/python python -m pytest

# Verify and run ingestion
uv run python -m src.fred_macro.cli verify
uv run python -m src.fred_macro.cli ingest --mode backfill
uv run python -m src.fred_macro.cli ingest --mode incremental
```

---

## Entry Points by Task

### Starting a Session
→ **Read**: `.agent/CONTEXT.md` (this file)
→ **Check**: `docs/implementation_schedule.md` for current priorities
→ **Then**: Load skill `.agent/skills/start-session/SKILL.md`

### During Development
→ **Skills**: `.agent/skills/CATALOG.md` for repeatable patterns
→ **Status**: Check `docs/implementation_schedule.md`
→ **Reference**: Architecture and ADRs in `docs/architecture/`

### Closing a Session
→ **Load skill**: `.agent/skills/end-session/SKILL.md`
→ **Required**: Update implementation schedule with progress
→ **Handoff**: Document context for next session

---

## Key Files (When You Need Them)

### Project Definition
| Need | File |
|------|------|
| Vision and scope | `docs/project_charter.md` |
| MVP success criteria | `docs/mvp_definition.md` |
| Technical specs | `docs/technical_requirements.md` |
| Current priorities | `docs/implementation_schedule.md` |

### Data & Architecture
| Need | File |
|------|------|
| Database schema | `docs/data/dictionary.md` |
| Indicator catalog | `docs/data/dictionary.md` (Tier 1 defined) |
| FRED API guide | `docs/data/sources/fred_api.md` |
| System architecture | `docs/architecture/system_overview.md` |
| Why MotherDuck | `docs/architecture/adr/adr-0002-motherduck.md` |
| Why upsert | `docs/architecture/adr/adr-0003-upsert-strategy.md` |
| Why 3 tiers | `docs/architecture/adr/adr-0004-indicator-tiers.md` |
| Dual-stack transition | `docs/architecture/dual_stack_transition.md` |

### Development
| Need | File |
|------|------|
| Development standards | `docs/development_standards.md` |
| Testing guide | `docs/template_testing_guide.md` |
| Session logs | `session_logs/` (create for each session) |

### Quick Reference
| Need | File |
|------|------|
| Project overview | `README.md` |
| Essential commands | `.codex/QUICKSTART.md` |
| Project map | `.codex/MAP.md` |

---

## MVP Scope (Phase 3 Goal)

### The "Big Four" Indicators (Tier 1)

1. **FEDFUNDS** — Federal Funds Rate (monetary policy)
2. **UNRATE** — Unemployment Rate (labor market)
3. **CPIAUCSL** — Consumer Price Index (inflation)
4. **GDPC1** — Real GDP (economic output)

### Success Criteria

- ✅ Backfill 10 years of historical data
- ✅ Incremental updates (last 60 days)
- ✅ Upsert logic prevents duplicates
- ✅ Handle data revisions automatically
- ✅ Log all ingestion runs
- ✅ Zero duplicates in database
- ✅ Backfill completes in < 2 minutes
- ✅ Incremental completes in < 30 seconds

**See**: `docs/mvp_definition.md` for full acceptance tests

---

## Current Phase: Expansion & Hardening (Phase 5)

**Status**: ▶ In Progress

**Next Tasks**:
1. Prioritize Tier 2 Batch 4 candidate set with the same constrained-validation workflow used for Batch 3
2. Expand operational reporting views/runbook guidance for DQ trend monitoring
3. Keep full test suite green while transition work lands
4. Monitor stale-series warnings from daily workflow artifacts and tune thresholds/remediation playbook

**See**: `docs/implementation_schedule.md` for complete task list

---

## Technology Stack

| Category | Technology | Purpose |
|----------|------------|---------|
| Language | Python 3.10+ | Primary programming language |
| Database | DuckDB/MotherDuck | Cloud analytics database |
| Data Source | FRED API | Federal Reserve Economic Data |
| API Client | fredapi | Python wrapper for FRED |
| Config | PyYAML | Series catalog parsing |
| Package Mgmt | uv | Fast Python package manager |
| Testing | pytest | Unit and integration tests |
| Linting | Ruff | Code quality |

---

## Directory Structure

```
FRED/
├── .agent/              # AI agent guidance
│   ├── CONTEXT.md       # This file
│   └── skills/          # Reusable workflows
├── docs/                # Documentation
│   ├── project_charter.md
│   ├── mvp_definition.md
│   ├── technical_requirements.md
│   ├── implementation_schedule.md
│   ├── data/
│   │   ├── dictionary.md
│   │   └── sources/
│   │       └── fred_api.md
│   └── architecture/
│       ├── system_overview.md
│       └── adr/
│           ├── adr-0002-motherduck.md
│           ├── adr-0003-upsert-strategy.md
│           └── adr-0004-indicator-tiers.md
├── src/                 # Source code (to be implemented)
│   └── fred_macro/
│       ├── db.py        # Database utilities
│       ├── fred_client.py  # FRED API client
│       ├── ingest.py    # Ingestion engine
│       └── setup.py     # Schema creation
├── config/              # Configuration files
│   └── series_catalog.yaml  # Indicator catalog
├── tests/               # Test suite
├── session_logs/        # Session history
├── README.md            # Project overview
├── pyproject.toml       # Dependencies
└── .env.example         # Environment template
```

---

## Environment Variables Required

```bash
# Required for operation
MOTHERDUCK_TOKEN="your_motherduck_token_here"
FRED_API_KEY="your_fred_api_key_here"

# Optional
LOG_LEVEL="INFO"  # DEBUG, INFO, WARNING, ERROR
```

**Setup**: Copy `.env.example` to `.env` and fill in values

---

## Learning Objectives

This project is also a learning exercise. Document insights about:

1. **DuckDB/MotherDuck**
   - Cloud analytics database patterns
   - SQL MERGE INTO for upsert
   - Columnar storage benefits

2. **ETL Patterns**
   - Backfill vs. incremental modes
   - Handling data revisions
   - Idempotent operations

3. **API Integration**
   - Rate limiting strategies
   - Error handling and retries
   - Exponential backoff

4. **Data Modeling**
   - Time series schema design
   - Composite primary keys
   - Audit logging patterns

**Track**: Add insights to `docs/knowledge_base.md` as you learn

---

## Common Queries

### Check ingestion status
```sql
SELECT * FROM ingestion_log
ORDER BY run_timestamp DESC
LIMIT 10;
```

### Latest values for Tier 1 indicators
```sql
SELECT s.series_id, s.title, o.observation_date, o.value, s.units
FROM observations o
JOIN series_catalog s ON o.series_id = s.series_id
WHERE s.tier = 1
  AND o.observation_date = (
    SELECT MAX(observation_date)
    FROM observations o2
    WHERE o2.series_id = o.series_id
  );
```

### Check for duplicates (should be zero)
```sql
SELECT series_id, observation_date, COUNT(*) as duplicate_count
FROM observations
GROUP BY series_id, observation_date
HAVING COUNT(*) > 1;
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| FRED API rate limits | Throttle to 1 req/sec, exponential backoff on 429 |
| MotherDuck free tier limits | Monitor usage, optimize schema if needed |
| Scope creep (adding Tier 2 early) | Strict MVP adherence, defer Tier 2 until M3 complete |
| Data revisions complexity | Extensive testing of upsert logic, reference ADR-0003 |
| Time constraints | Focus on MVP only, accept post-MVP delays |

---

## Communication Style

When working with AI assistants:

- **Be specific about MVP scope**: "Tier 1 only" means Big Four indicators
- **Reference ADRs**: "See ADR-0002 for why MotherDuck"
- **Cite acceptance tests**: "Test 2 from mvp_definition.md"
- **Learning context**: "This is also a learning project — explain DuckDB patterns"

---

## Development Workflow

```bash
# 1. Check branch and create feature branch if needed
git branch
git checkout -b feat/database-connection

# 2. Make changes

# 3. Format and lint
uv run ruff format . && uv run ruff check .

# 4. Run tests
uv run pytest

# 5. Commit with conventional format
git commit -m "feat: add MotherDuck connection utility"

# 6. Update implementation schedule
# Mark tasks as complete in docs/implementation_schedule.md

# 7. Create session log
# Document what was done in session_logs/YYYY-MM-DD/NN.md
```

---

## What's Out of Scope

Explicitly **NOT** part of this project:

- ❌ Real-time streaming data
- ❌ Web dashboard / UI (post-MVP consideration)
- ❌ Multi-user access
- ❌ Historical vintages tracking
- ❌ Forecasting or predictive models
- ❌ Data export features (use SQL queries)
- ❌ Integration with trading systems

---

## References

### Internal Documentation
- [Project Charter](../docs/project_charter.md) — Vision and scope
- [MVP Definition](../docs/mvp_definition.md) — Success criteria
- [Technical Requirements](../docs/technical_requirements.md) — System specs
- [Implementation Schedule](../docs/implementation_schedule.md) — Task tracking

### External Resources
- [FRED Website](https://fred.stlouisfed.org)
- [FRED API Docs](https://fred.stlouisfed.org/docs/api/fred/)
- [MotherDuck Docs](https://motherduck.com/docs/)
- [DuckDB Docs](https://duckdb.org/docs/)

---

**Next**: Check `docs/implementation_schedule.md` for current priorities, then load appropriate skill from `.agent/skills/CATALOG.md`
