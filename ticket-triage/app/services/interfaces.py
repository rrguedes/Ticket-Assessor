"""
Abstract interfaces for every major capability.

Dependency Inversion Principle: high-level modules depend on these abstractions,
not on concrete implementations.  Liskov Substitution: every concrete class that
implements an interface must be transparently replaceable.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Tuple

from app.schemas.ticket import AIEvaluationResult, EvaluationResponse, TicketData


class TicketFetcherInterface(ABC):
    """Fetches a single ticket from an external system."""

    @abstractmethod
    async def fetch_ticket(self, ticket_id: str) -> TicketData:
        """Retrieve ticket data by its identifier."""
        ...


class AIEvaluatorInterface(ABC):
    """Evaluates a ticket using an AI model."""

    @abstractmethod
    async def evaluate_ticket(self, ticket: TicketData) -> AIEvaluationResult:
        """Return a structured AI evaluation for the given ticket."""
        ...


class EvaluationRepositoryInterface(ABC):
    """Persists and retrieves ticket evaluations."""

    @abstractmethod
    def save_evaluation(
        self, ticket_data: TicketData, evaluation: AIEvaluationResult
    ) -> EvaluationResponse:
        """Persist a new evaluation and return the saved record."""
        ...

    @abstractmethod
    def get_evaluations(
        self, limit: int = 20, offset: int = 0
    ) -> Tuple[List[EvaluationResponse], int]:
        """Return a paginated list of evaluations and the total count."""
        ...

    @abstractmethod
    def get_evaluations_by_ticket_id(
        self, ticket_id: str
    ) -> List[EvaluationResponse]:
        """Return all evaluations for a given ticket ID."""
        ...
