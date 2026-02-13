# Dual-Stack Transition Note

## Purpose

This repository currently contains two code paths:

- `src/fred_macro`: active FRED ingestion implementation (MVP delivered on 2026-02-12)
- `src/vibe_coding`: legacy template modules retained for compatibility and existing tests

This note defines the temporary coexistence strategy so we can keep delivery velocity without breaking test safety.

## Current Policy (Stabilization Phase)

1. Keep both module trees importable and testable.
2. Treat failing tests in either tree as blockers during stabilization.
3. Avoid introducing new features in `src/vibe_coding`.
4. Add new macro functionality only under `src/fred_macro`.

## Risks

- Dependency drift between active and legacy paths.
- Confusion in docs/status if project state is not updated consistently.
- Increased maintenance overhead while both stacks coexist.

## Exit Criteria for Legacy Path

We can retire `src/vibe_coding` only after all of the following:

1. FRED-focused test coverage is in place for key ingestion and CLI paths.
2. Tooling and docs no longer reference `vibe_coding` as the primary package.
3. Migration PR explicitly removes or archives legacy modules and updates pytest coverage config.
4. A final baseline run confirms green lint/tests after retirement.

## Planned Follow-up Work

1. [x] Create a dedicated deprecation issue/PR plan for `src/vibe_coding`.
2. [x] Add guardrail to block `vibe_coding` imports from `src/fred_macro`.
3. [ ] Segment legacy/template tests from active FRED tests.
4. [ ] Remove/retarget docs and tooling that still treat `vibe_coding` as primary.
5. [ ] Execute final retirement PR and validate full baseline.

See detailed execution plan: `docs/architecture/vibe_coding_retirement_plan.md`.
