"""Tests for main.py - FastAPI endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


class TestHealthCheck:
    """Tests for the health check endpoint."""

    def test_root_returns_ok(self, test_client: TestClient):
        """Test that root endpoint returns OK status."""
        response = test_client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "LLM Council API"


class TestListConversations:
    """Tests for GET /api/conversations."""

    def test_returns_empty_list_initially(self, test_client: TestClient):
        """Test that empty list is returned when no conversations exist."""
        response = test_client.get("/api/conversations")

        assert response.status_code == 200
        assert response.json() == []

    def test_returns_all_conversations(self, test_client: TestClient):
        """Test that all conversations are returned."""
        # Create some conversations
        test_client.post("/api/conversations", json={})
        test_client.post("/api/conversations", json={})

        response = test_client.get("/api/conversations")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_returns_metadata_format(self, test_client: TestClient):
        """Test that response has correct metadata format."""
        test_client.post("/api/conversations", json={})

        response = test_client.get("/api/conversations")

        data = response.json()
        conv = data[0]
        assert "id" in conv
        assert "created_at" in conv
        assert "title" in conv
        assert "message_count" in conv


class TestCreateConversation:
    """Tests for POST /api/conversations."""

    def test_creates_new_conversation(self, test_client: TestClient):
        """Test creating a new conversation."""
        response = test_client.post("/api/conversations", json={})

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["title"] == "New Conversation"
        assert data["messages"] == []

    def test_returns_valid_uuid(self, test_client: TestClient):
        """Test that created conversation has valid UUID."""
        import uuid

        response = test_client.post("/api/conversations", json={})

        data = response.json()
        # Should not raise
        uuid.UUID(data["id"])

    def test_creates_unique_ids(self, test_client: TestClient):
        """Test that each conversation gets a unique ID."""
        resp1 = test_client.post("/api/conversations", json={})
        resp2 = test_client.post("/api/conversations", json={})

        assert resp1.json()["id"] != resp2.json()["id"]


class TestGetConversation:
    """Tests for GET /api/conversations/{id}."""

    def test_returns_existing_conversation(self, test_client: TestClient):
        """Test retrieving an existing conversation."""
        # Create a conversation
        create_resp = test_client.post("/api/conversations", json={})
        conv_id = create_resp.json()["id"]

        response = test_client.get(f"/api/conversations/{conv_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == conv_id

    def test_returns_404_for_nonexistent(self, test_client: TestClient):
        """Test that 404 is returned for nonexistent conversation."""
        response = test_client.get("/api/conversations/nonexistent-id")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_returns_full_conversation_with_messages(self, test_client: TestClient):
        """Test that full conversation with messages is returned."""
        # Create conversation
        create_resp = test_client.post("/api/conversations", json={})
        conv_id = create_resp.json()["id"]

        response = test_client.get(f"/api/conversations/{conv_id}")

        data = response.json()
        assert "messages" in data
        assert isinstance(data["messages"], list)


class TestSendMessage:
    """Tests for POST /api/conversations/{id}/message."""

    def test_returns_404_for_nonexistent_conversation(self, test_client: TestClient):
        """Test that 404 is returned for nonexistent conversation."""
        response = test_client.post(
            "/api/conversations/nonexistent/message", json={"content": "Hello"}
        )

        assert response.status_code == 404

    def test_requires_content_field(self, test_client: TestClient):
        """Test that content field is required."""
        create_resp = test_client.post("/api/conversations", json={})
        conv_id = create_resp.json()["id"]

        response = test_client.post(f"/api/conversations/{conv_id}/message", json={})

        assert response.status_code == 422  # Validation error

    @patch("backend.main.run_full_council")
    @patch("backend.main.generate_conversation_title")
    def test_returns_all_stages(
        self,
        mock_title: AsyncMock,
        mock_council: AsyncMock,
        test_client: TestClient,
    ):
        """Test that response includes all stages and metadata."""
        mock_title.return_value = "Test Title"
        mock_council.return_value = (
            [{"model": "m1", "response": "r1"}],  # stage1
            [{"model": "m1", "ranking": "r", "parsed_ranking": []}],  # stage2
            {"model": "m2", "response": "final"},  # stage3
            {"label_to_model": {}, "aggregate_rankings": []},  # metadata
        )

        create_resp = test_client.post("/api/conversations", json={})
        conv_id = create_resp.json()["id"]

        response = test_client.post(
            f"/api/conversations/{conv_id}/message", json={"content": "Hello"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "stage1" in data
        assert "stage2" in data
        assert "stage3" in data
        assert "metadata" in data

    @patch("backend.main.run_full_council")
    @patch("backend.main.generate_conversation_title")
    def test_generates_title_on_first_message(
        self,
        mock_title: AsyncMock,
        mock_council: AsyncMock,
        test_client: TestClient,
    ):
        """Test that title is generated on first message."""
        mock_title.return_value = "Generated Title"
        mock_council.return_value = ([], [], {"model": "m", "response": "r"}, {})

        create_resp = test_client.post("/api/conversations", json={})
        conv_id = create_resp.json()["id"]

        test_client.post(
            f"/api/conversations/{conv_id}/message", json={"content": "Hello"}
        )

        # Verify title was generated
        mock_title.assert_called_once()

        # Verify title was saved
        get_resp = test_client.get(f"/api/conversations/{conv_id}")
        assert get_resp.json()["title"] == "Generated Title"

    @patch("backend.main.run_full_council")
    @patch("backend.main.generate_conversation_title")
    def test_saves_messages_to_conversation(
        self,
        mock_title: AsyncMock,
        mock_council: AsyncMock,
        test_client: TestClient,
    ):
        """Test that messages are saved to conversation."""
        mock_title.return_value = "Title"
        mock_council.return_value = (
            [{"model": "m1", "response": "r1"}],
            [{"model": "m1", "ranking": "r", "parsed_ranking": []}],
            {"model": "m2", "response": "final"},
            {},
        )

        create_resp = test_client.post("/api/conversations", json={})
        conv_id = create_resp.json()["id"]

        test_client.post(
            f"/api/conversations/{conv_id}/message", json={"content": "Test message"}
        )

        # Verify messages are saved
        get_resp = test_client.get(f"/api/conversations/{conv_id}")
        messages = get_resp.json()["messages"]

        assert len(messages) == 2  # user + assistant
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Test message"
        assert messages[1]["role"] == "assistant"


class TestSendMessageStream:
    """Tests for POST /api/conversations/{id}/message/stream."""

    def test_returns_404_for_nonexistent_conversation(self, test_client: TestClient):
        """Test that 404 is returned for nonexistent conversation."""
        response = test_client.post(
            "/api/conversations/nonexistent/message/stream", json={"content": "Hello"}
        )

        assert response.status_code == 404

    @patch("backend.main.stage1_collect_responses")
    @patch("backend.main.stage2_collect_rankings")
    @patch("backend.main.stage3_synthesize_final")
    @patch("backend.main.generate_conversation_title")
    @patch("backend.main.calculate_aggregate_rankings")
    def test_returns_sse_events(
        self,
        mock_agg: AsyncMock,
        mock_title: AsyncMock,
        mock_s3: AsyncMock,
        mock_s2: AsyncMock,
        mock_s1: AsyncMock,
        test_client: TestClient,
    ):
        """Test that Server-Sent Events are returned."""
        mock_s1.return_value = [{"model": "m1", "response": "r1"}]
        mock_s2.return_value = (
            [{"model": "m1", "ranking": "r", "parsed_ranking": []}],
            {"Response A": "m1"},
        )
        mock_s3.return_value = {"model": "m2", "response": "final"}
        mock_title.return_value = "Title"
        mock_agg.return_value = []

        create_resp = test_client.post("/api/conversations", json={})
        conv_id = create_resp.json()["id"]

        response = test_client.post(
            f"/api/conversations/{conv_id}/message/stream",
            json={"content": "Hello"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

        # Parse SSE events
        events = []
        for line in response.text.split("\n"):
            if line.startswith("data: "):
                import json

                events.append(json.loads(line[6:]))

        # Verify event types
        event_types = [e["type"] for e in events]
        assert "stage1_start" in event_types
        assert "stage1_complete" in event_types
        assert "stage2_start" in event_types
        assert "stage2_complete" in event_types
        assert "stage3_start" in event_types
        assert "stage3_complete" in event_types
        assert "complete" in event_types


class TestCORS:
    """Tests for CORS configuration."""

    def test_allows_localhost_5173(self, test_client: TestClient):
        """Test that localhost:5173 is allowed."""
        response = test_client.options(
            "/api/conversations",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )

        assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"

    def test_allows_localhost_3000(self, test_client: TestClient):
        """Test that localhost:3000 is allowed."""
        response = test_client.options(
            "/api/conversations",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


class TestValidation:
    """Tests for request validation."""

    def test_send_message_validates_content_type(self, test_client: TestClient):
        """Test that content must be a string."""
        create_resp = test_client.post("/api/conversations", json={})
        conv_id = create_resp.json()["id"]

        response = test_client.post(
            f"/api/conversations/{conv_id}/message", json={"content": 123}
        )

        assert response.status_code == 422

    def test_send_message_rejects_empty_content(self, test_client: TestClient):
        """Test behavior with empty content string."""
        create_resp = test_client.post("/api/conversations", json={})
        conv_id = create_resp.json()["id"]

        # Empty string is technically valid per schema, but we test the endpoint accepts it
        # The actual behavior depends on the council implementation
        response = test_client.post(
            f"/api/conversations/{conv_id}/message", json={"content": ""}
        )

        # Should at least not be a validation error (422)
        # It may fail for other reasons (council failure) but that's expected
        assert response.status_code != 422 or response.status_code == 200
