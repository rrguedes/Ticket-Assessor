"""
Unit tests for OpenAITicketEvaluator.
The LangChain model is fully mocked — no real API calls.
"""
import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.runnables import RunnableLambda

from app.schemas.ticket import TicketData
from app.services.openai_service import OpenAITicketEvaluator


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def evaluator() -> OpenAITicketEvaluator:
    return OpenAITicketEvaluator(api_key="test-key-not-real", model="gpt-4o-mini")


def test_local_model_configuration_is_used():
    settings = SimpleNamespace(
        use_local_models=True,
        local_models_base_url="http://localhost:11434/v1",
        local_model_name="llama3.2",
    )
    fake_model = RunnableLambda(lambda value: value)

    with patch("app.services.openai_service.get_settings", return_value=settings):
        with patch(
            "app.services.openai_service.ChatOpenAI", return_value=fake_model
        ) as chat_model:
            OpenAITicketEvaluator(api_key="local-key", model="gpt-4o-mini")

    chat_model.assert_called_once_with(
        model="llama3.2",
        api_key="local-key",
        base_url="http://localhost:11434/v1",
        temperature=0.2,
    )


# ── evaluate_ticket ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_evaluate_ticket_parses_score(evaluator, sample_ticket):
    response = {
        "score": 7.5,
        "feedback": "Good ticket.",
        "strengths": ["Clear title"],
        "additional_questions": ["What are the ACs?"],
    }
    with patch.object(
        evaluator,
        "_chain",
        MagicMock(ainvoke=AsyncMock(return_value=response)),
    ):
        result = await evaluator.evaluate_ticket(sample_ticket)

    assert result.score == 7.5


@pytest.mark.asyncio
async def test_evaluate_ticket_parses_feedback(evaluator, sample_ticket):
    response = {
        "score": 5.0,
        "feedback": "Missing acceptance criteria.",
        "strengths": [],
        "additional_questions": ["AC?", "Priority?", "Who is affected?"],
    }
    with patch.object(
        evaluator,
        "_chain",
        MagicMock(ainvoke=AsyncMock(return_value=response)),
    ):
        result = await evaluator.evaluate_ticket(sample_ticket)

    assert "acceptance criteria" in result.feedback.lower()


@pytest.mark.asyncio
async def test_evaluate_ticket_returns_questions_for_low_score(evaluator, minimal_ticket):
    response = {
        "score": 2.0,
        "feedback": "Ticket is too vague.",
        "strengths": [],
        "additional_questions": ["What is the goal?", "Who is affected?", "What are the ACs?"],
    }
    with patch.object(
        evaluator,
        "_chain",
        MagicMock(ainvoke=AsyncMock(return_value=response)),
    ):
        result = await evaluator.evaluate_ticket(minimal_ticket)

    assert result.score < 8
    assert len(result.additional_questions) >= 3


@pytest.mark.asyncio
async def test_evaluate_ticket_empty_questions_for_high_score(evaluator, sample_ticket):
    response = {
        "score": 9.5,
        "feedback": "Excellent ticket.",
        "strengths": ["Clear title", "Full ACs", "Business value"],
        "additional_questions": [],
    }
    with patch.object(
        evaluator,
        "_chain",
        MagicMock(ainvoke=AsyncMock(return_value=response)),
    ):
        result = await evaluator.evaluate_ticket(sample_ticket)

    assert result.score >= 8
    assert result.additional_questions == []


@pytest.mark.asyncio
async def test_evaluate_ticket_handles_missing_optional_keys(evaluator, sample_ticket):
    """OpenAI may omit optional keys; the service must handle gracefully."""
    response = {
        "score": 6.0,
        "feedback": "Partial ticket.",
    }
    with patch.object(
        evaluator,
        "_chain",
        MagicMock(ainvoke=AsyncMock(return_value=response)),
    ):
        result = await evaluator.evaluate_ticket(sample_ticket)

    assert result.strengths == []
    assert result.additional_questions == []


@pytest.mark.asyncio
async def test_evaluate_ticket_refines_until_result_stabilizes(evaluator, sample_ticket):
    response = {
        "score": 7.5,
        "feedback": "Good ticket.",
        "strengths": ["Clear title"],
        "additional_questions": ["What are the acceptance criteria?"],
    }
    chain = MagicMock(ainvoke=AsyncMock(return_value=response))
    with patch.object(evaluator, "_chain", chain):
        result = await evaluator.evaluate_ticket(sample_ticket)

    assert result.score == 7.5
    assert chain.ainvoke.await_count == 2
    refinement_input = chain.ainvoke.await_args_list[1].args[0]
    assert '"score":7.5' in refinement_input["previous_evaluation"]
    assert "Critically review" in refinement_input["iteration_instruction"]


@pytest.mark.asyncio
async def test_evaluate_ticket_stops_at_maximum_iterations(evaluator, sample_ticket):
    responses = [
        {
            "score": float(iteration),
            "feedback": f"Iteration {iteration}.",
            "strengths": [],
            "additional_questions": [],
        }
        for iteration in range(10)
    ]
    chain = MagicMock(ainvoke=AsyncMock(side_effect=responses))
    with patch.object(evaluator, "_chain", chain):
        result = await evaluator.evaluate_ticket(sample_ticket)

    assert result.feedback == "Iteration 9."
    assert chain.ainvoke.await_count == 10


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
