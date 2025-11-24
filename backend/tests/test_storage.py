"""Tests for storage.py - JSON-based conversation persistence."""

import json
import os

import pytest

from backend import storage


class TestCreateConversation:
    """Tests for create_conversation function."""

    def test_creates_conversation_file(self, mock_data_dir: str):
        """Test that a conversation file is created."""
        conv_id = "test-conv-123"
        result = storage.create_conversation(conv_id)

        # Verify file exists
        expected_path = os.path.join(mock_data_dir, f"{conv_id}.json")
        assert os.path.exists(expected_path)

        # Verify returned data
        assert result["id"] == conv_id
        assert result["title"] == "New Conversation"
        assert result["messages"] == []
        assert "created_at" in result

    def test_creates_data_directory_if_missing(self, temp_data_dir: str):
        """Test that data directory is created if it doesn't exist."""
        nested_dir = os.path.join(temp_data_dir, "nested", "data")

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("backend.storage.DATA_DIR", nested_dir)
            storage.create_conversation("test-id")

        assert os.path.exists(nested_dir)

    def test_conversation_content_is_valid_json(self, mock_data_dir: str):
        """Test that saved conversation is valid JSON."""
        conv_id = "json-test"
        storage.create_conversation(conv_id)

        path = os.path.join(mock_data_dir, f"{conv_id}.json")
        with open(path) as f:
            data = json.load(f)

        assert data["id"] == conv_id
        assert isinstance(data["messages"], list)


class TestGetConversation:
    """Tests for get_conversation function."""

    def test_returns_existing_conversation(self, mock_data_dir: str):
        """Test retrieving an existing conversation."""
        conv_id = "existing-conv"
        storage.create_conversation(conv_id)

        result = storage.get_conversation(conv_id)

        assert result is not None
        assert result["id"] == conv_id

    def test_returns_none_for_nonexistent(self, mock_data_dir: str):
        """Test that None is returned for nonexistent conversation."""
        result = storage.get_conversation("nonexistent-id")
        assert result is None

    def test_loads_messages_correctly(self, mock_data_dir: str):
        """Test that messages are loaded correctly."""
        conv_id = "msg-test"
        storage.create_conversation(conv_id)
        storage.add_user_message(conv_id, "Hello")

        result = storage.get_conversation(conv_id)

        assert len(result["messages"]) == 1
        assert result["messages"][0]["content"] == "Hello"


class TestSaveConversation:
    """Tests for save_conversation function."""

    def test_saves_conversation_data(self, mock_data_dir: str):
        """Test saving conversation data."""
        conversation = {
            "id": "save-test",
            "created_at": "2024-01-01T00:00:00",
            "title": "Test Title",
            "messages": [{"role": "user", "content": "test"}],
        }

        storage.save_conversation(conversation)

        # Verify by reading back
        result = storage.get_conversation("save-test")
        assert result["title"] == "Test Title"
        assert len(result["messages"]) == 1

    def test_overwrites_existing(self, mock_data_dir: str):
        """Test that saving overwrites existing data."""
        conv_id = "overwrite-test"
        storage.create_conversation(conv_id)

        # Modify and save
        conversation = storage.get_conversation(conv_id)
        conversation["title"] = "Updated Title"
        storage.save_conversation(conversation)

        # Verify update
        result = storage.get_conversation(conv_id)
        assert result["title"] == "Updated Title"


class TestListConversations:
    """Tests for list_conversations function."""

    def test_returns_empty_list_when_no_conversations(self, mock_data_dir: str):
        """Test empty list when no conversations exist."""
        result = storage.list_conversations()
        assert result == []

    def test_returns_all_conversations(self, mock_data_dir: str):
        """Test that all conversations are returned."""
        storage.create_conversation("conv-1")
        storage.create_conversation("conv-2")
        storage.create_conversation("conv-3")

        result = storage.list_conversations()

        assert len(result) == 3
        ids = {c["id"] for c in result}
        assert ids == {"conv-1", "conv-2", "conv-3"}

    def test_returns_metadata_only(self, mock_data_dir: str):
        """Test that only metadata is returned, not full messages."""
        conv_id = "metadata-test"
        storage.create_conversation(conv_id)
        storage.add_user_message(conv_id, "Hello world")

        result = storage.list_conversations()

        conv = next(c for c in result if c["id"] == conv_id)
        assert "messages" not in conv
        assert "message_count" in conv
        assert conv["message_count"] == 1

    def test_sorted_by_creation_time_newest_first(self, mock_data_dir: str):
        """Test that conversations are sorted newest first."""
        import time

        storage.create_conversation("old")
        time.sleep(0.01)  # Small delay to ensure different timestamps
        storage.create_conversation("new")

        result = storage.list_conversations()

        assert result[0]["id"] == "new"
        assert result[1]["id"] == "old"

    def test_includes_title(self, mock_data_dir: str):
        """Test that title is included in metadata."""
        conv_id = "title-test"
        storage.create_conversation(conv_id)
        storage.update_conversation_title(conv_id, "My Custom Title")

        result = storage.list_conversations()

        conv = next(c for c in result if c["id"] == conv_id)
        assert conv["title"] == "My Custom Title"


class TestAddUserMessage:
    """Tests for add_user_message function."""

    def test_adds_message_to_conversation(self, mock_data_dir: str):
        """Test adding a user message."""
        conv_id = "user-msg-test"
        storage.create_conversation(conv_id)

        storage.add_user_message(conv_id, "Hello, council!")

        conv = storage.get_conversation(conv_id)
        assert len(conv["messages"]) == 1
        assert conv["messages"][0]["role"] == "user"
        assert conv["messages"][0]["content"] == "Hello, council!"

    def test_appends_multiple_messages(self, mock_data_dir: str):
        """Test appending multiple messages."""
        conv_id = "multi-msg-test"
        storage.create_conversation(conv_id)

        storage.add_user_message(conv_id, "First message")
        storage.add_user_message(conv_id, "Second message")

        conv = storage.get_conversation(conv_id)
        assert len(conv["messages"]) == 2
        assert conv["messages"][0]["content"] == "First message"
        assert conv["messages"][1]["content"] == "Second message"

    def test_raises_error_for_nonexistent_conversation(self, mock_data_dir: str):
        """Test that ValueError is raised for nonexistent conversation."""
        with pytest.raises(ValueError, match="not found"):
            storage.add_user_message("nonexistent", "Hello")

    def test_preserves_existing_messages(self, mock_data_dir: str):
        """Test that existing messages are preserved."""
        conv_id = "preserve-test"
        storage.create_conversation(conv_id)
        storage.add_user_message(conv_id, "Original")

        # Add another message
        storage.add_user_message(conv_id, "New")

        conv = storage.get_conversation(conv_id)
        assert conv["messages"][0]["content"] == "Original"


class TestAddAssistantMessage:
    """Tests for add_assistant_message function."""

    def test_adds_assistant_message_with_stages(self, mock_data_dir: str):
        """Test adding an assistant message with all stages."""
        conv_id = "assistant-msg-test"
        storage.create_conversation(conv_id)

        stage1 = [{"model": "gpt-4", "response": "GPT response"}]
        stage2 = [{"model": "gpt-4", "ranking": "1. Response A"}]
        stage3 = {"model": "gemini", "response": "Final answer"}

        storage.add_assistant_message(conv_id, stage1, stage2, stage3)

        conv = storage.get_conversation(conv_id)
        assert len(conv["messages"]) == 1
        msg = conv["messages"][0]
        assert msg["role"] == "assistant"
        assert msg["stage1"] == stage1
        assert msg["stage2"] == stage2
        assert msg["stage3"] == stage3

    def test_raises_error_for_nonexistent_conversation(self, mock_data_dir: str):
        """Test that ValueError is raised for nonexistent conversation."""
        with pytest.raises(ValueError, match="not found"):
            storage.add_assistant_message("nonexistent", [], [], {})

    def test_maintains_message_order(self, mock_data_dir: str):
        """Test that message order is maintained."""
        conv_id = "order-test"
        storage.create_conversation(conv_id)

        storage.add_user_message(conv_id, "User question")
        storage.add_assistant_message(
            conv_id,
            [{"model": "m1", "response": "r1"}],
            [{"model": "m1", "ranking": "r"}],
            {"model": "m2", "response": "final"},
        )

        conv = storage.get_conversation(conv_id)
        assert conv["messages"][0]["role"] == "user"
        assert conv["messages"][1]["role"] == "assistant"


class TestUpdateConversationTitle:
    """Tests for update_conversation_title function."""

    def test_updates_title(self, mock_data_dir: str):
        """Test updating conversation title."""
        conv_id = "title-update-test"
        storage.create_conversation(conv_id)

        storage.update_conversation_title(conv_id, "New Title")

        conv = storage.get_conversation(conv_id)
        assert conv["title"] == "New Title"

    def test_raises_error_for_nonexistent_conversation(self, mock_data_dir: str):
        """Test that ValueError is raised for nonexistent conversation."""
        with pytest.raises(ValueError, match="not found"):
            storage.update_conversation_title("nonexistent", "Title")

    def test_preserves_other_data(self, mock_data_dir: str):
        """Test that other conversation data is preserved."""
        conv_id = "preserve-data-test"
        storage.create_conversation(conv_id)
        storage.add_user_message(conv_id, "Hello")

        storage.update_conversation_title(conv_id, "Updated")

        conv = storage.get_conversation(conv_id)
        assert conv["title"] == "Updated"
        assert len(conv["messages"]) == 1
        assert conv["messages"][0]["content"] == "Hello"


class TestEnsureDataDir:
    """Tests for ensure_data_dir function."""

    def test_creates_directory_if_missing(self, temp_data_dir: str):
        """Test that directory is created if it doesn't exist."""
        new_dir = os.path.join(temp_data_dir, "new_data")

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("backend.storage.DATA_DIR", new_dir)
            storage.ensure_data_dir()

        assert os.path.exists(new_dir)

    def test_handles_existing_directory(self, mock_data_dir: str):
        """Test that existing directory doesn't cause error."""
        # Should not raise
        storage.ensure_data_dir()


class TestGetConversationPath:
    """Tests for get_conversation_path function."""

    def test_returns_correct_path(self, mock_data_dir: str):
        """Test that correct path is returned."""
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("backend.storage.DATA_DIR", "/test/data")
            path = storage.get_conversation_path("conv-123")

        assert path == "/test/data/conv-123.json"
