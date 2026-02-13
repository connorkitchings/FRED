"""Test fixtures and utilities for the project.

This module provides pytest fixtures and utilities for testing.
"""

import tempfile
from pathlib import Path

import pytest

TESTS_ROOT = Path(__file__).parent.resolve()
ACTIVE_FRED_TEST_FILES = {
    "test_cli_dq_report.py",
    "test_db.py",
    "test_fred_client.py",
    "test_fred_dq_report_persistence.py",
    "test_fred_ingest_dq.py",
    "test_fred_transition_guardrails.py",
    "test_fred_validation.py",
    "test_series_catalog_config.py",
}
LEGACY_TEMPLATE_TEST_DIRS = {
    "api",
    "core",
    "data",
    "integration",
    "models",
    "pipelines",
    "utils",
}


def _is_legacy_template_test(item_path: Path) -> bool:
    rel_path = item_path.resolve().relative_to(TESTS_ROOT).as_posix()
    top_level = rel_path.split("/", 1)[0]

    if rel_path == "test_config.py":
        return True
    if top_level in LEGACY_TEMPLATE_TEST_DIRS:
        return True
    if rel_path in ACTIVE_FRED_TEST_FILES or rel_path.startswith("test_fred_"):
        return False
    return False


def pytest_addoption(parser):
    parser.addoption(
        "--include-legacy-template",
        action="store_true",
        default=False,
        help="Include legacy template tests that target src/vibe_coding.",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "fred_macro: Active tests for src/fred_macro functionality."
    )
    config.addinivalue_line(
        "markers", "legacy_template: Legacy tests targeting src/vibe_coding."
    )


def pytest_collection_modifyitems(config, items):
    include_legacy = config.getoption("--include-legacy-template")
    requested_markexpr = config.option.markexpr or ""
    keep_legacy_for_markexpr = "legacy_template" in requested_markexpr

    retained_items = []
    deselected_items = []

    for item in items:
        item_path = Path(str(item.path))
        if _is_legacy_template_test(item_path):
            item.add_marker(pytest.mark.legacy_template)
            if include_legacy or keep_legacy_for_markexpr:
                retained_items.append(item)
            else:
                deselected_items.append(item)
        else:
            item.add_marker(pytest.mark.fred_macro)
            retained_items.append(item)

    if deselected_items:
        config.hook.pytest_deselected(items=deselected_items)
        items[:] = retained_items


@pytest.fixture
def temp_dir():
    """Provide a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_env_file(temp_dir):
    """Create a sample .env file for testing."""
    env_path = temp_dir / ".env"
    env_path.write_text("""
# Test configuration
DATABASE_URL=postgresql://localhost/test
API_KEY=test-api-key-12345
DEBUG=true
PORT=8080
""")
    return env_path


@pytest.fixture
def empty_env_file(temp_dir):
    """Create an empty .env file for testing."""
    env_path = temp_dir / ".env"
    env_path.write_text("")
    return env_path


@pytest.fixture
def clean_config():
    """Provide a fresh Config instance for testing.

    This fixture clears any cached configuration to ensure
    tests don't interfere with each other.
    """
    # Clear any cached config
    import vibe_coding.config

    vibe_coding.config._config_instance = None
    yield
    # Clean up after test
    vibe_coding.config._config_instance = None
