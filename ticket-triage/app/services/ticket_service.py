"""
Ticket Triage Service — the application's core orchestrator.

Dependency Inversion Principle: depends on the three abstract interfaces, never
on concrete classes.  Business logic lives here; infrastructure concerns are
pushed to the concrete implementations injected at construction time.
"""
from __future__ import annotations
from typing import List, Tuple

from app.schemas.ticket import EvaluationResponse
from app.services.interfaces import (
    AIEvaluatorInterface,
    EvaluationRepositoryInterface,
    TicketFetcherInterface,
)


class TicketTriageService:
    """
    Orchestrates the end-to-end ticket triage workflow:

      1. Fetch ticket details from the external tracker.
      2. Ask the AI evaluator to score and comment on it.
      3. Persist the evaluation for future retrieval.
    """

    def __init__(
        self,
        ticket_fetcher: TicketFetcherInterface,
        ai_evaluator: AIEvaluatorInterface,
        evaluation_repo: EvaluationRepositoryInterface,
    ) -> None:
        self._ticket_fetcher = ticket_fetcher
        self._ai_evaluator = ai_evaluator
        self._evaluation_repo = evaluation_repo

    async def evaluate_ticket(self, ticket_id: str) -> EvaluationResponse:
        """Fetch, evaluate, persist and return the evaluation for *ticket_id*."""
        ticket_data = await self._ticket_fetcher.fetch_ticket(ticket_id)
        ai_result = await self._ai_evaluator.evaluate_ticket(ticket_data)
        return self._evaluation_repo.save_evaluation(ticket_data, ai_result)

    def get_all_evaluations(
        self, limit: int = 20, offset: int = 0
    ) -> Tuple[List[EvaluationResponse], int]:
        """Return a paginated list of all evaluations and the total count."""
        return self._evaluation_repo.get_evaluations(limit, offset)

    def get_evaluations_by_ticket(
        self, ticket_id: str
    ) -> List[EvaluationResponse]:
        """Return every evaluation ever created for the given ticket."""
        return self._evaluation_repo.get_evaluations_by_ticket_id(ticket_id)
