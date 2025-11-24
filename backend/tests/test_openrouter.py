"""Tests for openrouter.py - OpenRouter API client."""

import pytest
import respx
from httpx import Response

from backend.openrouter import query_model, query_models_parallel

# Test API URL
API_URL = "https://openrouter.ai/api/v1/chat/completions"


class TestQueryModel:
    """Tests for query_model function."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_successful_query(self):
        """Test successful API query."""
        respx.post(API_URL).mock(
            return_value=Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "content": "This is the model response",
                                "reasoning_details": None,
                            }
                        }
                    ]
                },
            )
        )

        result = await query_model(
            "openai/gpt-4o", [{"role": "user", "content": "Hello"}]
        )

        assert result is not None
        assert result["content"] == "This is the model response"

    @respx.mock
    @pytest.mark.asyncio
    async def test_includes_reasoning_details(self):
        """Test that reasoning_details is included when present."""
        respx.post(API_URL).mock(
            return_value=Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "content": "Response with reasoning",
                                "reasoning_details": {"steps": ["step1", "step2"]},
                            }
                        }
                    ]
                },
            )
        )

        result = await query_model("openai/o1", [{"role": "user", "content": "Think"}])

        assert result is not None
        assert result["reasoning_details"] == {"steps": ["step1", "step2"]}

    @respx.mock
    @pytest.mark.asyncio
    async def test_returns_none_on_http_error(self):
        """Test that None is returned on HTTP errors."""
        respx.post(API_URL).mock(return_value=Response(500, text="Internal Server Error"))

        result = await query_model(
            "openai/gpt-4o", [{"role": "user", "content": "Hello"}]
        )

        assert result is None

    @respx.mock
    @pytest.mark.asyncio
    async def test_returns_none_on_rate_limit(self):
        """Test that None is returned on rate limit (429)."""
        respx.post(API_URL).mock(
            return_value=Response(429, json={"error": "Rate limit exceeded"})
        )

        result = await query_model(
            "openai/gpt-4o", [{"role": "user", "content": "Hello"}]
        )

        assert result is None

    @respx.mock
    @pytest.mark.asyncio
    async def test_returns_none_on_auth_error(self):
        """Test that None is returned on authentication error."""
        respx.post(API_URL).mock(
            return_value=Response(401, json={"error": "Invalid API key"})
        )

        result = await query_model(
            "openai/gpt-4o", [{"role": "user", "content": "Hello"}]
        )

        assert result is None

    @respx.mock
    @pytest.mark.asyncio
    async def test_returns_none_on_timeout(self):
        """Test that None is returned on timeout."""
        import httpx

        respx.post(API_URL).mock(side_effect=httpx.TimeoutException("Timeout"))

        result = await query_model(
            "openai/gpt-4o", [{"role": "user", "content": "Hello"}], timeout=1.0
        )

        assert result is None

    @respx.mock
    @pytest.mark.asyncio
    async def test_returns_none_on_connection_error(self):
        """Test that None is returned on connection error."""
        import httpx

        respx.post(API_URL).mock(side_effect=httpx.ConnectError("Connection failed"))

        result = await query_model(
            "openai/gpt-4o", [{"role": "user", "content": "Hello"}]
        )

        assert result is None

    @respx.mock
    @pytest.mark.asyncio
    async def test_returns_none_on_malformed_response(self):
        """Test that None is returned on malformed JSON response."""
        respx.post(API_URL).mock(
            return_value=Response(200, json={"unexpected": "format"})
        )

        result = await query_model(
            "openai/gpt-4o", [{"role": "user", "content": "Hello"}]
        )

        assert result is None

    @respx.mock
    @pytest.mark.asyncio
    async def test_sends_correct_headers(self):
        """Test that correct headers are sent."""
        route = respx.post(API_URL).mock(
            return_value=Response(
                200,
                json={"choices": [{"message": {"content": "ok"}}]},
            )
        )

        await query_model("openai/gpt-4o", [{"role": "user", "content": "Hello"}])

        assert route.called
        request = route.calls[0].request
        assert "Bearer" in request.headers["Authorization"]
        assert request.headers["Content-Type"] == "application/json"

    @respx.mock
    @pytest.mark.asyncio
    async def test_sends_correct_payload(self):
        """Test that correct payload is sent."""
        import json

        route = respx.post(API_URL).mock(
            return_value=Response(
                200,
                json={"choices": [{"message": {"content": "ok"}}]},
            )
        )

        messages = [{"role": "user", "content": "Test message"}]
        await query_model("openai/gpt-4o", messages)

        request = route.calls[0].request
        body = json.loads(request.content)
        assert body["model"] == "openai/gpt-4o"
        assert body["messages"] == messages

    @respx.mock
    @pytest.mark.asyncio
    async def test_handles_empty_content(self):
        """Test handling of empty content in response."""
        respx.post(API_URL).mock(
            return_value=Response(
                200,
                json={"choices": [{"message": {"content": None}}]},
            )
        )

        result = await query_model(
            "openai/gpt-4o", [{"role": "user", "content": "Hello"}]
        )

        assert result is not None
        assert result["content"] is None


class TestQueryModelsParallel:
    """Tests for query_models_parallel function."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_queries_all_models(self):
        """Test that all models are queried."""
        respx.post(API_URL).mock(
            return_value=Response(
                200,
                json={"choices": [{"message": {"content": "Response"}}]},
            )
        )

        models = ["openai/gpt-4o", "anthropic/claude-3-opus", "google/gemini-pro"]
        messages = [{"role": "user", "content": "Hello"}]

        result = await query_models_parallel(models, messages)

        assert len(result) == 3
        assert all(model in result for model in models)

    @respx.mock
    @pytest.mark.asyncio
    async def test_returns_dict_mapping_models_to_responses(self):
        """Test that result maps models to their responses."""
        respx.post(API_URL).mock(
            return_value=Response(
                200,
                json={"choices": [{"message": {"content": "Test response"}}]},
            )
        )

        models = ["model-a", "model-b"]
        result = await query_models_parallel(models, [{"role": "user", "content": "Hi"}])

        assert "model-a" in result
        assert "model-b" in result
        assert result["model-a"]["content"] == "Test response"
        assert result["model-b"]["content"] == "Test response"

    @respx.mock
    @pytest.mark.asyncio
    async def test_handles_partial_failures(self):
        """Test handling when some models fail."""
        call_count = 0

        def response_callback(request):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                return Response(500, text="Error")
            return Response(
                200,
                json={"choices": [{"message": {"content": f"Response {call_count}"}}]},
            )

        respx.post(API_URL).mock(side_effect=response_callback)

        models = ["model-1", "model-2", "model-3"]
        result = await query_models_parallel(models, [{"role": "user", "content": "Hi"}])

        # All models should be in result
        assert len(result) == 3
        # One should be None (the failed one)
        none_count = sum(1 for v in result.values() if v is None)
        assert none_count == 1

    @respx.mock
    @pytest.mark.asyncio
    async def test_handles_all_failures(self):
        """Test handling when all models fail."""
        respx.post(API_URL).mock(return_value=Response(500, text="Error"))

        models = ["model-1", "model-2"]
        result = await query_models_parallel(models, [{"role": "user", "content": "Hi"}])

        assert all(v is None for v in result.values())

    @respx.mock
    @pytest.mark.asyncio
    async def test_empty_models_list(self):
        """Test with empty models list."""
        result = await query_models_parallel([], [{"role": "user", "content": "Hi"}])
        assert result == {}

    @respx.mock
    @pytest.mark.asyncio
    async def test_single_model(self):
        """Test with single model."""
        respx.post(API_URL).mock(
            return_value=Response(
                200,
                json={"choices": [{"message": {"content": "Single response"}}]},
            )
        )

        result = await query_models_parallel(
            ["single-model"], [{"role": "user", "content": "Hi"}]
        )

        assert len(result) == 1
        assert result["single-model"]["content"] == "Single response"

    @respx.mock
    @pytest.mark.asyncio
    async def test_preserves_model_order_in_dict(self):
        """Test that model order is preserved in result dict."""
        respx.post(API_URL).mock(
            return_value=Response(
                200,
                json={"choices": [{"message": {"content": "Response"}}]},
            )
        )

        models = ["z-model", "a-model", "m-model"]
        result = await query_models_parallel(models, [{"role": "user", "content": "Hi"}])

        # Python 3.7+ dicts maintain insertion order
        assert list(result.keys()) == models
