# Implementation Plan

[Overview]
Complete the retirement of legacy `src/vibe_coding` template modules from the FRED-Macro-Dashboard project. This involves two phases: (1) removing docs/tooling references to vibe_coding as the primary package, and (2) executing the final retirement PR to remove legacy code and validate the baseline. The goal is to eliminate the legacy template while keeping the active FRED ingestion system stable.

This retirement is the final step in the Phase 5 transition outlined in `docs/architecture/dual_stack_transition.md` and `docs/architecture/vibe_coding_retirement_plan.md`. After completion, the project will have a single, clear code path under `src/fred_macro`.

[Types]
This implementation does not introduce new types. It focuses on:
- Removing legacy template code and tests
- Updating documentation references
- Cleaning up pytest configuration

[Files]

**New files to be created:**
- None required for this implementation.

**Existing files to be modified:**

1. `docs/troubleshooting.md` - Remove the `vibe_coding.config` import reference from troubleshooting commands

2. `pyproject.toml` - Remove the `legacy_template` pytest marker since legacy tests will be removed

3. `tests/conftest.py` - Remove:
   - `legacy_template` marker definition
   - `vibe_coding.config` import and cleanup code in fixtures

4. `docs/implementation_schedule.md` - Update the "Retire/deprecate template modules" task status to complete

5. `docs/architecture/dual_stack_transition.md` - Update exit criteria checkboxes to mark items complete

6. `docs/architecture/vibe_coding_retirement_plan.md` - Mark Phase 2 and Phase 3 as complete

**Files to be deleted:**

1. `src/vibe_coding/` - Entire directory (36 files) containing:
   - `__init__.py`
   - `config.py`
   - `api/` (main.py, endpoints/)
   - `core/` (config.py)
   - `data/` (make_dataset.py, process_features.py)
   - `models/` (train_model.py, evaluate_model.py, predict_model.py)
   - `pipelines/` (training_pipeline.py, prediction_pipeline.py)
   - `utils/` (logging.py)

2. Legacy template tests that import vibe_coding (to be removed):
   - `tests/test_config.py` (imports vibe_coding.config)
   - `tests/api/test_endpoints.py` (imports vibe_coding.api.main)
   - `tests/core/test_config.py` (imports vibe_coding.core.config)
   - `tests/data/test_make_dataset.py` (imports vibe_coding.data.make_dataset)
   - `tests/data/test_process_features.py` (imports vibe_coding.data.process_features)
   - `tests/models/test_train_model.py` (imports vibe_coding.models.train_model)
   - `tests/models/test_evaluate_model.py` (imports vibe_coding.models.evaluate_model)
   - `tests/models/test_predict_model.py` (imports vibe_coding.models.predict_model)
   - `tests/pipelines/test_training_pipeline.py` (imports vibe_coding.pipelines.training_pipeline)
   - `tests/pipelines/test_prediction_pipeline.py` (imports vibe_coding.pipelines.prediction_pipeline)
   - `tests/utils/test_logging.py` (imports vibe_coding.utils.logging)
   - `tests/integration/test_config_integration.py` (imports vibe_coding.config)
   - `tests/integration/test_logging_integration.py` (imports vibe_coding.utils.logging)
   - `tests/integration/test_workflow_integration.py` (contains test_import_vibe_coding_works)

**Configuration file updates:**
- No new configuration required.

[Functions]

**New functions:**
- None required.

**Modified functions:**
- None (this is a cleanup task).

**Removed functions:**
- All functions in the deleted `src/vibe_coding/` modules (these are legacy template code)
- All test functions in deleted legacy test files

[Classes]

**New classes:**
- None required.

**Modified classes:**
- None.

**Removed classes:**
- All classes from deleted `src/vibe_coding/` modules:
  - `vibe_coding.config.Config`
  - `vibe_coding.core.config.settings`
  - `vibe_coding.data.make_dataset.main`
  - `vibe_coding.data.process_features.main`
  - `vibe_coding.models.train_model.main`
  - `vibe_coding.models.evaluate_model.main`
  - `vibe_coding.models.predict_model.main`
  - `vibe_coding.pipelines.training_pipeline.main`
  - `vibe_coding.pipelines.prediction_pipeline.main`
  - `vibe_coding.utils.logging.logger`
  - `vibe_coding.api.main.app`

[Dependencies]

**Dependency modifications:**
- None (no new packages required)
- After removal, project will have cleaner dependency graph with only `src/fred_macro` as active package

[Testing]

**Test file requirements:**
- All FRED-focused tests in `tests/` should continue to pass:
  - `tests/test_db.py`
  - `tests/test_fred_client.py`
  - `tests/test_fred_ingest_dq.py`
  - `tests/test_fred_validation.py`
  - `tests/test_fred_dq_report_persistence.py`
  - `tests/test_cli_dq_report.py`
  - `tests/test_series_catalog_config.py`
  - `tests/test_fred_transition_guardrails.py` (guardrail test)

**Existing test modifications:**
- Remove legacy template tests that import vibe_coding (listed in Files section above)
- Remove legacy_template marker from conftest.py

**Validation strategies:**
- Run `uv run --python .venv/bin/python python -m pytest` - should pass with only FRED-focused tests
- Run `uv run python -m src.fred_macro.cli verify` - should pass
- Run `uv run python -m src.fred_macro.setup` - should pass
- Run `grep -r "vibe_coding" src tests docs` - should show only archival references (session_logs, retirement plan docs)

[Implementation Order]

1. **Phase 2: Docs and Tooling De-primary Legacy Package**
   - Step 2.1: Update `docs/troubleshooting.md` - Remove vibe_coding reference
   - Step 2.2: Update `pyproject.toml` - Remove legacy_template marker
   - Step 2.3: Update `tests/conftest.py` - Remove legacy template test markers and imports
   - Step 2.4: Verify documentation has no vibe_coding references in primary setup paths

2. **Phase 3: Code Retirement PR**
   - Step 3.1: Delete `src/vibe_coding/` directory
   - Step 3.2: Delete legacy template test files (14 files listed above)
   - Step 3.3: Update `docs/implementation_schedule.md` - Mark retirement task complete
   - Step 3.4: Update `docs/architecture/dual_stack_transition.md` - Mark exit criteria complete
   - Step 3.5: Update `docs/architecture/vibe_coding_retirement_plan.md` - Mark phases complete

3. **Validation**
   - Step 3.6: Run full quality gate (pytest, ruff, verify CLI)
   - Step 3.7: Confirm only archival references to vibe_coding remain

**Rollback strategy:**
- Each phase is designed to be reversible
- If tests fail after deletion, the `src/vibe_coding` directory can be restored from git
- Document any issues in session log for next session
