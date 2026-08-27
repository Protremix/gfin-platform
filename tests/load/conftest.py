"""Shared fixtures for load testing."""

from __future__ import annotations

import sys

sys.path.insert(0, ".")
sys.path.insert(0, "packages")

import pytest


@pytest.fixture
def large_dataset():
    """Generate a large dataset for capacity testing."""
    return [
        {"id": f"ENT-{i:05d}", "type": "Person", "name": f"Person {i}"}
        for i in range(10000)
    ]
