"""Shared fixtures for backend tests."""

import os
import tempfile
from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

# Set up test environment before importing app
os.environ["OPENROUTER_API_KEY"] = "test-api-key"


@pytest.fixture
def temp_data_dir() -> Generator[str, None, None]:
    """Create a temporary directory for test data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_data_dir(temp_data_dir: str) -> Generator[str, None, None]:
    """Patch the DATA_DIR config to use a temp directory."""
    with patch("backend.storage.DATA_DIR", temp_data_dir):
        with patch("backend.config.DATA_DIR", temp_data_dir):
            yield temp_data_dir


@pytest.fixture
def test_client(mock_data_dir: str) -> TestClient:
    """Create a test client for the FastAPI app."""
    from backend.main import app

    return TestClient(app)


@pytest.fixture
def sample_stage1_results() -> list[dict]:
    """Sample Stage 1 results for testing."""
    return [
        {"model": "openai/gpt-4o", "response": "This is GPT-4o's response about the topic."},
        {"model": "anthropic/claude-3-opus", "response": "This is Claude's detailed analysis."},
        {"model": "google/gemini-pro", "response": "Gemini provides this perspective."},
    ]


@pytest.fixture
def sample_label_to_model() -> dict[str, str]:
    """Sample label mapping for testing."""
    return {
        "Response A": "openai/gpt-4o",
        "Response B": "anthropic/claude-3-opus",
        "Response C": "google/gemini-pro",
    }


@pytest.fixture
def sample_stage2_results() -> list[dict]:
    """Sample Stage 2 results with rankings."""
    return [
        {
            "model": "openai/gpt-4o",
            "ranking": """Response A provides good detail but lacks depth.
Response B has excellent analysis with clear reasoning.
Response C offers a unique perspective.

FINAL RANKING:
1. Response B
2. Response C
3. Response A""",
            "parsed_ranking": ["Response B", "Response C", "Response A"],
        },
        {
            "model": "anthropic/claude-3-opus",
            "ranking": """All responses show merit. Response A is comprehensive.
Response B is thorough. Response C is concise.

FINAL RANKING:
1. Response A
2. Response B
3. Response C""",
            "parsed_ranking": ["Response A", "Response B", "Response C"],
        },
        {
            "model": "google/gemini-pro",
            "ranking": """Evaluating the responses:
Response A - Good
Response B - Better
Response C - Best

FINAL RANKING:
1. Response C
2. Response B
3. Response A""",
            "parsed_ranking": ["Response C", "Response B", "Response A"],
        },
    ]


@pytest.fixture
def mock_query_model() -> Generator[AsyncMock, None, None]:
    """Mock the query_model function."""
    with patch("backend.council.query_model") as mock:
        mock.return_value = {"content": "Mocked response"}
        yield mock


@pytest.fixture
def mock_query_models_parallel() -> Generator[AsyncMock, None, None]:
    """Mock the query_models_parallel function."""
    with patch("backend.council.query_models_parallel") as mock:
        mock.return_value = {
            "openai/gpt-4o": {"content": "GPT-4o response"},
            "anthropic/claude-3-opus": {"content": "Claude response"},
            "google/gemini-pro": {"content": "Gemini response"},
        }
        yield mock
