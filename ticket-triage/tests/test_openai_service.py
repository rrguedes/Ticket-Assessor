"""
Unit tests for OpenAITicketEvaluator.
The OpenAI client is fully mocked — no real API calls.
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.schemas.ticket import TicketData
from app.services.openai_service import OpenAITicketEvaluator


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def evaluator() -> OpenAITicketEvaluator:
    return OpenAITicketEvaluator(api_key="test-key-not-real", model="gpt-4o-mini")


def _make_openai_response(payload: dict) -> MagicMock:
    """Build a mock that looks like an OpenAI ChatCompletion response."""
    msg = MagicMock()
    msg.content = json.dumps(payload)
    choice = MagicMock()
    choice.message = msg
    response = MagicMock()
    response.choices = [choice]
    return response


# ── evaluate_ticket ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_evaluate_ticket_parses_score(evaluator, sample_ticket):
    mock_resp = _make_openai_response({
        "score": 7.5,
        "feedback": "Good ticket.",
        "strengths": ["Clear title"],
        "additional_questions": ["What are the ACs?"],
    })
    with patch.object(
        evaluator._client.chat.completions, "create", new=AsyncMock(return_value=mock_resp)
    ):
        result = await evaluator.evaluate_ticket(sample_ticket)

    assert result.score == 7.5


@pytest.mark.asyncio
async def test_evaluate_ticket_parses_feedback(evaluator, sample_ticket):
    mock_resp = _make_openai_response({
        "score": 5.0,
        "feedback": "Missing acceptance criteria.",
        "strengths": [],
        "additional_questions": ["AC?", "Priority?", "Who is affected?"],
    })
    with patch.object(
        evaluator._client.chat.completions, "create", new=AsyncMock(return_value=mock_resp)
    ):
        result = await evaluator.evaluate_ticket(sample_ticket)

    assert "acceptance criteria" in result.feedback.lower()


@pytest.mark.asyncio
async def test_evaluate_ticket_returns_questions_for_low_score(evaluator, minimal_ticket):
    mock_resp = _make_openai_response({
        "score": 2.0,
        "feedback": "Ticket is too vague.",
        "strengths": [],
        "additional_questions": ["What is the goal?", "Who is affected?", "What are the ACs?"],
    })
    with patch.object(
        evaluator._client.chat.completions, "create", new=AsyncMock(return_value=mock_resp)
    ):
        result = await evaluator.evaluate_ticket(minimal_ticket)

    assert result.score < 8
    assert len(result.additional_questions) >= 3


@pytest.mark.asyncio
async def test_evaluate_ticket_empty_questions_for_high_score(evaluator, sample_ticket):
    mock_resp = _make_openai_response({
        "score": 9.5,
        "feedback": "Excellent ticket.",
        "strengths": ["Clear title", "Full ACs", "Business value"],
        "additional_questions": [],
    })
    with patch.object(
        evaluator._client.chat.completions, "create", new=AsyncMock(return_value=mock_resp)
    ):
        result = await evaluator.evaluate_ticket(sample_ticket)

    assert result.score >= 8
    assert result.additional_questions == []


@pytest.mark.asyncio
async def test_evaluate_ticket_handles_missing_optional_keys(evaluator, sample_ticket):
    """OpenAI may omit optional keys; the service must handle gracefully."""
    mock_resp = _make_openai_response({
        "score": 6.0,
        "feedback": "Partial ticket.",
    })
    with patch.object(
        evaluator._client.chat.completions, "create", new=AsyncMock(return_value=mock_resp)
    ):
        result = await evaluator.evaluate_ticket(sample_ticket)

    assert result.strengths == []
    assert result.additional_questions == []


# ── _format_ticket ────────────────────────────────────────────────────────────

def test_format_ticket_includes_all_fields(evaluator):
    ticket = TicketData(
        ticket_id="999",
        title="Implementar OAuth2",
        description="Adicionar suporte a OAuth2.",
        acceptance_criteria="Usuário pode logar via Google.",
        ticket_type="Feature",
        state="New",
        priority="High",
        assigned_to="Alice",
        tags="auth",
        story_points=3.0,
    )
    formatted = evaluator._format_ticket(ticket)

    assert "999" in formatted
    assert "Implementar OAuth2" in formatted
    assert "Adicionar suporte a OAuth2" in formatted
    assert "Usuário pode logar via Google" in formatted
    assert "Alice" in formatted
    assert "High" in formatted
    assert "3.0" in formatted


def test_format_ticket_shows_placeholder_for_missing_description(evaluator, minimal_ticket):
    formatted = evaluator._format_ticket(minimal_ticket)
    assert "No description provided" in formatted


def test_format_ticket_shows_placeholder_for_missing_criteria(evaluator, minimal_ticket):
    formatted = evaluator._format_ticket(minimal_ticket)
    assert "No acceptance criteria provided" in formatted
