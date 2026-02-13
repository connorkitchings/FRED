"""Test fixtures and utilities for the project.

This module provides pytest fixtures and utilities for testing.
"""

import tempfile
from pathlib import Path

import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "fred_macro: Active tests for src/fred_macro functionality."
    )


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
