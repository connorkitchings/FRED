# Dual-Stack Transition Note

## Purpose

Capture the retirement status of the legacy template code path and document the single-stack baseline going forward.

## Current State (as of 2026-02-13)

This repository now operates on a single active code path:

- `src/fred_macro`: active FRED ingestion implementation

The legacy template path has been retired:

- `src/vibe_coding`: removed
- legacy template test suite: removed

## Outcome

The dual-stack transition is complete. Development and testing should target `src/fred_macro` only.

## What Was Completed

1. Retirement execution plan created.
2. Guardrail test added to prevent new `vibe_coding` imports in `src/fred_macro`.
3. Test suite segmented during transition.
4. Docs/tooling references retargeted for active package usage.
5. Legacy code and template-specific tests removed with baseline verification.

## Operational Guidance

1. Use `make test` for the active test suite.
2. Treat any new `vibe_coding` reference in active code as a regression.
3. Keep schedule/context docs aligned with the single-stack architecture.

## Historical Reference

Detailed phase-by-phase execution notes remain in:

- `docs/architecture/vibe_coding_retirement_plan.md`
