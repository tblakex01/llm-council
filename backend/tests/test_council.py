"""Tests for council.py - core orchestration logic."""

import pytest

from backend.council import (
    calculate_aggregate_rankings,
    parse_ranking_from_text,
    run_full_council,
    stage1_collect_responses,
    stage2_collect_rankings,
    stage3_synthesize_final,
)


class TestParseRankingFromText:
    """Tests for parse_ranking_from_text function."""

    def test_standard_numbered_format(self):
        """Test parsing standard numbered list format."""
        text = """Response A provides good detail but lacks depth.
Response B has excellent analysis with clear reasoning.
Response C offers a unique perspective.

FINAL RANKING:
1. Response B
2. Response C
3. Response A"""
        result = parse_ranking_from_text(text)
        assert result == ["Response B", "Response C", "Response A"]

    def test_numbered_format_no_space_after_period(self):
        """Test parsing numbered list without space after period."""
        text = """Some evaluation text here.

FINAL RANKING:
1.Response A
2.Response B
3.Response C"""
        result = parse_ranking_from_text(text)
        assert result == ["Response A", "Response B", "Response C"]

    def test_numbered_format_extra_spaces(self):
        """Test parsing with extra spaces."""
        text = """Evaluation.

FINAL RANKING:
1.   Response C
2.   Response A
3.   Response B"""
        result = parse_ranking_from_text(text)
        assert result == ["Response C", "Response A", "Response B"]

    def test_fallback_to_response_patterns(self):
        """Test fallback when numbered format not found but FINAL RANKING exists."""
        text = """Evaluation text.

FINAL RANKING:
Response B is best
Response A comes second
Response C is last"""
        result = parse_ranking_from_text(text)
        assert result == ["Response B", "Response A", "Response C"]

    def test_no_final_ranking_header(self):
        """Test fallback when no FINAL RANKING header exists."""
        text = """Here are my rankings:
Response C is the best answer.
Response A is second best.
Response B is the weakest."""
        result = parse_ranking_from_text(text)
        assert result == ["Response C", "Response A", "Response B"]

    def test_empty_text(self):
        """Test with empty text."""
        result = parse_ranking_from_text("")
        assert result == []

    def test_no_responses_mentioned(self):
        """Test text without any Response mentions."""
        text = "This is just some random text without any rankings."
        result = parse_ranking_from_text(text)
        assert result == []

    def test_multiple_response_mentions_picks_after_ranking(self):
        """Test that only responses after FINAL RANKING are extracted."""
        text = """I think Response A did well earlier in the discussion.
Response B was also mentioned.

FINAL RANKING:
1. Response C
2. Response B
3. Response A"""
        result = parse_ranking_from_text(text)
        assert result == ["Response C", "Response B", "Response A"]

    def test_lowercase_final_ranking_not_matched(self):
        """Test that lowercase 'final ranking:' is not matched."""
        text = """final ranking:
1. Response A
2. Response B"""
        # Should fall back to extracting all Response patterns
        result = parse_ranking_from_text(text)
        assert result == ["Response A", "Response B"]

    def test_four_responses(self):
        """Test parsing with four responses (A, B, C, D)."""
        text = """FINAL RANKING:
1. Response D
2. Response A
3. Response C
4. Response B"""
        result = parse_ranking_from_text(text)
        assert result == ["Response D", "Response A", "Response C", "Response B"]

    def test_single_response(self):
        """Test parsing with only one response."""
        text = """FINAL RANKING:
1. Response A"""
        result = parse_ranking_from_text(text)
        assert result == ["Response A"]

    def test_duplicate_responses_preserved(self):
        """Test that duplicate mentions are preserved (edge case)."""
        text = """FINAL RANKING:
1. Response A
2. Response A"""
        result = parse_ranking_from_text(text)
        assert result == ["Response A", "Response A"]

    def test_response_with_extra_text_after(self):
        """Test response labels with extra text after them."""
        text = """FINAL RANKING:
1. Response B - excellent
2. Response A - good
3. Response C - needs improvement"""
        result = parse_ranking_from_text(text)
        assert result == ["Response B", "Response A", "Response C"]


class TestCalculateAggregateRankings:
    """Tests for calculate_aggregate_rankings function."""

    def test_basic_aggregation(
        self, sample_stage2_results: list[dict], sample_label_to_model: dict[str, str]
    ):
        """Test basic aggregate ranking calculation."""
        result = calculate_aggregate_rankings(sample_stage2_results, sample_label_to_model)

        # Verify all models are represented
        models = {r["model"] for r in result}
        assert models == {"openai/gpt-4o", "anthropic/claude-3-opus", "google/gemini-pro"}

        # Verify sorted by average_rank (ascending)
        avg_ranks = [r["average_rank"] for r in result]
        assert avg_ranks == sorted(avg_ranks)

    def test_average_rank_calculation(self):
        """Test that average ranks are calculated correctly."""
        stage2_results = [
            {
                "model": "model1",
                "ranking": "FINAL RANKING:\n1. Response A\n2. Response B",
                "parsed_ranking": ["Response A", "Response B"],
            },
            {
                "model": "model2",
                "ranking": "FINAL RANKING:\n1. Response B\n2. Response A",
                "parsed_ranking": ["Response B", "Response A"],
            },
        ]
        label_to_model = {
            "Response A": "openai/gpt-4o",
            "Response B": "anthropic/claude-3-opus",
        }

        result = calculate_aggregate_rankings(stage2_results, label_to_model)

        # Both models should have average rank of 1.5 (tied)
        for r in result:
            assert r["average_rank"] == 1.5
            assert r["rankings_count"] == 2

    def test_clear_winner(self):
        """Test scenario with a clear winner."""
        stage2_results = [
            {
                "model": "judge1",
                "ranking": "FINAL RANKING:\n1. Response A\n2. Response B\n3. Response C",
                "parsed_ranking": ["Response A", "Response B", "Response C"],
            },
            {
                "model": "judge2",
                "ranking": "FINAL RANKING:\n1. Response A\n2. Response C\n3. Response B",
                "parsed_ranking": ["Response A", "Response C", "Response B"],
            },
            {
                "model": "judge3",
                "ranking": "FINAL RANKING:\n1. Response A\n2. Response B\n3. Response C",
                "parsed_ranking": ["Response A", "Response B", "Response C"],
            },
        ]
        label_to_model = {
            "Response A": "winner-model",
            "Response B": "second-model",
            "Response C": "third-model",
        }

        result = calculate_aggregate_rankings(stage2_results, label_to_model)

        # Winner should be first with average rank of 1.0
        assert result[0]["model"] == "winner-model"
        assert result[0]["average_rank"] == 1.0

    def test_empty_stage2_results(self):
        """Test with empty stage2 results."""
        result = calculate_aggregate_rankings([], {"Response A": "model1"})
        assert result == []

    def test_empty_label_mapping(self):
        """Test with empty label mapping."""
        stage2_results = [
            {
                "model": "judge1",
                "ranking": "FINAL RANKING:\n1. Response A",
                "parsed_ranking": ["Response A"],
            }
        ]
        result = calculate_aggregate_rankings(stage2_results, {})
        assert result == []

    def test_partial_rankings(self):
        """Test when some rankings don't include all responses."""
        stage2_results = [
            {
                "model": "judge1",
                "ranking": "FINAL RANKING:\n1. Response A\n2. Response B",
                "parsed_ranking": ["Response A", "Response B"],
            },
            {
                "model": "judge2",
                "ranking": "FINAL RANKING:\n1. Response A",  # Only ranked one
                "parsed_ranking": ["Response A"],
            },
        ]
        label_to_model = {
            "Response A": "model-a",
            "Response B": "model-b",
        }

        result = calculate_aggregate_rankings(stage2_results, label_to_model)

        # model-a should have 2 rankings, model-b should have 1
        model_a_result = next(r for r in result if r["model"] == "model-a")
        model_b_result = next(r for r in result if r["model"] == "model-b")

        assert model_a_result["rankings_count"] == 2
        assert model_b_result["rankings_count"] == 1

    def test_rounding(self):
        """Test that average ranks are rounded to 2 decimal places."""
        stage2_results = [
            {
                "model": "judge1",
                "ranking": "FINAL RANKING:\n1. Response A\n2. Response B\n3. Response C",
                "parsed_ranking": ["Response A", "Response B", "Response C"],
            },
            {
                "model": "judge2",
                "ranking": "FINAL RANKING:\n1. Response B\n2. Response A\n3. Response C",
                "parsed_ranking": ["Response B", "Response A", "Response C"],
            },
            {
                "model": "judge3",
                "ranking": "FINAL RANKING:\n1. Response C\n2. Response A\n3. Response B",
                "parsed_ranking": ["Response C", "Response A", "Response B"],
            },
        ]
        label_to_model = {
            "Response A": "model-a",
            "Response B": "model-b",
            "Response C": "model-c",
        }

        result = calculate_aggregate_rankings(stage2_results, label_to_model)

        # All averages should be rounded to 2 decimal places
        for r in result:
            avg_str = str(r["average_rank"])
            if "." in avg_str:
                decimal_places = len(avg_str.split(".")[1])
                assert decimal_places <= 2


class TestStage1CollectResponses:
    """Tests for stage1_collect_responses function."""

    @pytest.mark.asyncio
    async def test_successful_collection(self, mock_query_models_parallel):
        """Test successful response collection from all models."""
        result = await stage1_collect_responses("What is Python?")

        assert len(result) == 3
        assert all("model" in r and "response" in r for r in result)
        mock_query_models_parallel.assert_called_once()

    @pytest.mark.asyncio
    async def test_partial_failure(self, mock_query_models_parallel):
        """Test graceful handling when some models fail."""
        mock_query_models_parallel.return_value = {
            "openai/gpt-4o": {"content": "GPT response"},
            "anthropic/claude-3-opus": None,  # Failed
            "google/gemini-pro": {"content": "Gemini response"},
        }

        result = await stage1_collect_responses("What is Python?")

        # Should only include successful responses
        assert len(result) == 2
        models = {r["model"] for r in result}
        assert "anthropic/claude-3-opus" not in models

    @pytest.mark.asyncio
    async def test_all_models_fail(self, mock_query_models_parallel):
        """Test handling when all models fail."""
        mock_query_models_parallel.return_value = {
            "openai/gpt-4o": None,
            "anthropic/claude-3-opus": None,
            "google/gemini-pro": None,
        }

        result = await stage1_collect_responses("What is Python?")

        assert result == []


class TestStage2CollectRankings:
    """Tests for stage2_collect_rankings function."""

    @pytest.mark.asyncio
    async def test_anonymization_mapping(
        self, sample_stage1_results: list[dict], mock_query_models_parallel
    ):
        """Test that label_to_model mapping is correctly created."""
        mock_query_models_parallel.return_value = {
            "openai/gpt-4o": {"content": "FINAL RANKING:\n1. Response A"},
            "anthropic/claude-3-opus": {"content": "FINAL RANKING:\n1. Response B"},
            "google/gemini-pro": {"content": "FINAL RANKING:\n1. Response C"},
        }

        _, label_to_model = await stage2_collect_rankings("test query", sample_stage1_results)

        # Verify mapping exists for all responses
        assert "Response A" in label_to_model
        assert "Response B" in label_to_model
        assert "Response C" in label_to_model

        # Verify mapping points to correct models
        assert label_to_model["Response A"] == "openai/gpt-4o"
        assert label_to_model["Response B"] == "anthropic/claude-3-opus"
        assert label_to_model["Response C"] == "google/gemini-pro"

    @pytest.mark.asyncio
    async def test_rankings_include_parsed(
        self, sample_stage1_results: list[dict], mock_query_models_parallel
    ):
        """Test that rankings include parsed_ranking field."""
        mock_query_models_parallel.return_value = {
            "openai/gpt-4o": {
                "content": "FINAL RANKING:\n1. Response B\n2. Response A\n3. Response C"
            },
        }

        results, _ = await stage2_collect_rankings("test query", sample_stage1_results)

        assert len(results) == 1
        assert "parsed_ranking" in results[0]
        assert results[0]["parsed_ranking"] == ["Response B", "Response A", "Response C"]


class TestStage3SynthesizeFinal:
    """Tests for stage3_synthesize_final function."""

    @pytest.mark.asyncio
    async def test_successful_synthesis(
        self,
        sample_stage1_results: list[dict],
        sample_stage2_results: list[dict],
        mock_query_model,
    ):
        """Test successful final synthesis."""
        mock_query_model.return_value = {"content": "Final synthesized answer"}

        result = await stage3_synthesize_final(
            "test query", sample_stage1_results, sample_stage2_results
        )

        assert "model" in result
        assert "response" in result
        assert result["response"] == "Final synthesized answer"

    @pytest.mark.asyncio
    async def test_chairman_failure(
        self,
        sample_stage1_results: list[dict],
        sample_stage2_results: list[dict],
        mock_query_model,
    ):
        """Test fallback when chairman fails."""
        mock_query_model.return_value = None

        result = await stage3_synthesize_final(
            "test query", sample_stage1_results, sample_stage2_results
        )

        assert "Error:" in result["response"]


class TestRunFullCouncil:
    """Tests for run_full_council function."""

    @pytest.mark.asyncio
    async def test_all_models_fail_returns_error(self, mock_query_models_parallel):
        """Test that complete failure returns error response."""
        mock_query_models_parallel.return_value = {
            "model1": None,
            "model2": None,
        }

        stage1, stage2, stage3, metadata = await run_full_council("test query")

        assert stage1 == []
        assert stage2 == []
        assert "error" in stage3["model"].lower() or "Error" in stage3["response"]
        assert metadata == {}

    @pytest.mark.asyncio
    async def test_successful_full_council(
        self, mock_query_models_parallel, mock_query_model
    ):
        """Test successful full council run."""
        # First call for stage1, second for stage2
        mock_query_models_parallel.side_effect = [
            {
                "openai/gpt-4o": {"content": "GPT response"},
                "anthropic/claude-3-opus": {"content": "Claude response"},
            },
            {
                "openai/gpt-4o": {"content": "FINAL RANKING:\n1. Response A\n2. Response B"},
                "anthropic/claude-3-opus": {
                    "content": "FINAL RANKING:\n1. Response B\n2. Response A"
                },
            },
        ]
        mock_query_model.return_value = {"content": "Final synthesis"}

        stage1, stage2, stage3, metadata = await run_full_council("test query")

        assert len(stage1) == 2
        assert len(stage2) == 2
        assert stage3["response"] == "Final synthesis"
        assert "label_to_model" in metadata
        assert "aggregate_rankings" in metadata
