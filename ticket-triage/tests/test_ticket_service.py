"""
Unit tests for TicketTriageService.
All dependencies are replaced with mocks — no real network or DB calls.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.ticket_service import TicketTriageService


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_fetcher():
    return AsyncMock()


@pytest.fixture
def mock_evaluator():
    return AsyncMock()


@pytest.fixture
def mock_repo():
    return MagicMock()


@pytest.fixture
def service(mock_fetcher, mock_evaluator, mock_repo) -> TicketTriageService:
    return TicketTriageService(
        ticket_fetcher=mock_fetcher,
        ai_evaluator=mock_evaluator,
        evaluation_repo=mock_repo,
    )


# ── evaluate_ticket ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_evaluate_ticket_calls_all_dependencies(
    service, mock_fetcher, mock_evaluator, mock_repo,
    sample_ticket, good_evaluation, saved_evaluation,
):
    mock_fetcher.fetch_ticket.return_value = sample_ticket
    mock_evaluator.evaluate_ticket.return_value = good_evaluation
    mock_repo.save_evaluation.return_value = saved_evaluation

    result = await service.evaluate_ticket("12345")

    mock_fetcher.fetch_ticket.assert_awaited_once_with("12345")
    mock_evaluator.evaluate_ticket.assert_awaited_once_with(sample_ticket)
    mock_repo.save_evaluation.assert_called_once_with(sample_ticket, good_evaluation)
    assert result == saved_evaluation


@pytest.mark.asyncio
async def test_evaluate_ticket_returns_saved_evaluation(
    service, mock_fetcher, mock_evaluator, mock_repo,
    sample_ticket, good_evaluation, saved_evaluation,
):
    mock_fetcher.fetch_ticket.return_value = sample_ticket
    mock_evaluator.evaluate_ticket.return_value = good_evaluation
    mock_repo.save_evaluation.return_value = saved_evaluation

    result = await service.evaluate_ticket("12345")

    assert result.id == 1
    assert result.score == 8.5
    assert result.ticket_id == "12345"


@pytest.mark.asyncio
async def test_evaluate_ticket_propagates_fetcher_exception(
    service, mock_fetcher, mock_evaluator, mock_repo,
):
    mock_fetcher.fetch_ticket.side_effect = ValueError("Ticket not found")

    with pytest.raises(ValueError, match="Ticket not found"):
        await service.evaluate_ticket("00000")

    mock_evaluator.evaluate_ticket.assert_not_awaited()
    mock_repo.save_evaluation.assert_not_called()


@pytest.mark.asyncio
async def test_evaluate_ticket_propagates_ai_exception(
    service, mock_fetcher, mock_evaluator, mock_repo,
    sample_ticket,
):
    mock_fetcher.fetch_ticket.return_value = sample_ticket
    mock_evaluator.evaluate_ticket.side_effect = RuntimeError("OpenAI error")

    with pytest.raises(RuntimeError, match="OpenAI error"):
        await service.evaluate_ticket("12345")

    mock_repo.save_evaluation.assert_not_called()


# ── get_all_evaluations ───────────────────────────────────────────────────────

def test_get_all_evaluations_delegates_to_repo(
    service, mock_repo, saved_evaluation,
):
    mock_repo.get_evaluations.return_value = ([saved_evaluation], 1)

    evaluations, total = service.get_all_evaluations(limit=10, offset=5)

    mock_repo.get_evaluations.assert_called_once_with(10, 5)
    assert total == 1
    assert evaluations[0] == saved_evaluation


def test_get_all_evaluations_empty(service, mock_repo):
    mock_repo.get_evaluations.return_value = ([], 0)

    evaluations, total = service.get_all_evaluations()

    assert total == 0
    assert evaluations == []


# ── get_evaluations_by_ticket ─────────────────────────────────────────────────

def test_get_evaluations_by_ticket_delegates_to_repo(
    service, mock_repo, saved_evaluation,
):
    mock_repo.get_evaluations_by_ticket_id.return_value = [saved_evaluation]

    result = service.get_evaluations_by_ticket("12345")

    mock_repo.get_evaluations_by_ticket_id.assert_called_once_with("12345")
    assert len(result) == 1
    assert result[0].ticket_id == "12345"


def test_get_evaluations_by_ticket_returns_empty_for_unknown(service, mock_repo):
    mock_repo.get_evaluations_by_ticket_id.return_value = []

    result = service.get_evaluations_by_ticket("unknown-id")

    assert result == []
