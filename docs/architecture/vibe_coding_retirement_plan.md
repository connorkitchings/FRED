# Legacy Template Retirement Plan (`src/vibe_coding`)

## Purpose

Define a low-risk, execution-ready path to retire legacy template modules while keeping the active FRED ingestion system (`src/fred_macro`) stable.

## Current Baseline (as of 2026-02-13)

- `src/vibe_coding` files: 36
- Repository references to `vibe_coding`: 64
- References by area:
  - `src/`: 15
  - `tests/`: 28
  - `docs/`: 20
  - `Makefile`/`pyproject.toml`: 1
- Coverage is already targeted at `src/fred_macro`.

## Non-Goals

- No new feature work in `src/vibe_coding`.
- No expansion of legacy template APIs.
- No changes to ingestion behavior during retirement planning.

## Migration Principles

1. Keep `main` green at every step (tests and CLI smoke checks).
2. Remove references before removing code.
3. Land small, reversible slices.
4. Prefer `fred_macro`-first docs, tooling, and tests.

## Execution Phases

### Phase 0: Guardrails and Plan (Completed in this step)

- Add a guardrail test that fails if `src/fred_macro` imports `vibe_coding`.
- Publish this retirement plan and link it from transition docs.
- Mark retirement backlog item as in progress in the implementation schedule.

**Acceptance checks**
- `uv run --python .venv/bin/python python -m pytest`

### Phase 1: Test Suite Segmentation (Completed in this step)

- Split template-legacy tests from active FRED tests using markers or folder conventions.
- Ensure required CI/local default focuses on `fred_macro` contract tests.
- Keep an explicit optional legacy test job while transition is active.
- Added `--include-legacy-template` pytest flag with automatic per-test classification.
- Updated `Makefile` targets:
  - `make test` -> active `fred_macro` tests
  - `make test-legacy` -> legacy template tests (temporary, removed after Phase 3 retirement)
  - `make test-all` -> full suite

**Acceptance checks**
- Default test command passes.
- Legacy test command is runnable during transition window.

### Phase 2: Docs and Tooling De-primary Legacy Package (✅ COMPLETED)

- Update docs that currently instruct `vibe_coding` imports as primary usage.
- Update helper commands and troubleshooting steps to default to `src.fred_macro`.
- Keep one explicit legacy section documenting temporary compatibility status.

**Acceptance checks**
- Documentation search has no `vibe_coding` references in primary setup paths.
- Transition note and runbook remain internally consistent.

**Completed Actions**:
- Updated `docs/troubleshooting.md` - Removed vibe_coding.config reference
- Updated `pyproject.toml` - Removed legacy_template pytest marker
- Updated `tests/conftest.py` - Removed legacy template test markers and imports

### Phase 3: Code Retirement PR (✅ COMPLETED)

- Remove or archive `src/vibe_coding` and template-only test modules.
- Remove packaging artifacts and stale references tied to legacy template layout.
- Re-run full quality gate and CLI smoke checks.

**Acceptance checks**
- `uv run --python .venv/bin/python python -m pytest` passes.
- `uv run python -m src.fred_macro.cli verify` passes.
- `uv run python -m src.fred_macro.setup` passes.
- `rg -n "vibe_coding" src tests docs` shows only intentional archival references.

**Completed Actions**:
- Deleted `src/vibe_coding/` directory (36 files)
- Deleted 14 legacy template test files
- Removed empty test subdirectories
- Updated `Makefile` legacy targets to reflect retired test path
- Updated implementation_schedule.md - Marked task complete
- Updated dual_stack_transition.md - Marked exit criteria complete

## Rollback Strategy

- Each phase is independent and merged separately.
- If a phase regresses test stability, revert only that phase commit.
- Do not partially remove runtime modules in the same commit as broad doc/test rewrites.

## Owners and Tracking

- Owner: Connor Kitchings
- Execution branch pattern: `chore-vibe-coding-retirement-*`
- Status source of truth: `docs/implementation_schedule.md`
