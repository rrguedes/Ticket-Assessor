"""
PostgreSQL-backed evaluation repository.
Single Responsibility: only handles persistence of TicketEvaluation records.
Open/Closed: swap for a different database by providing another implementation
             of EvaluationRepositoryInterface without touching business logic.
"""

from __future__ import annotations
from typing import List, Tuple

from sqlalchemy.orm import Session

from app.database.models import TicketEvaluation
from app.schemas.ticket import AIEvaluationResult, EvaluationResponse, TicketData
from app.services.interfaces import EvaluationRepositoryInterface


class PostgreSQLEvaluationRepository(EvaluationRepositoryInterface):
    """Stores and retrieves ticket evaluations in PostgreSQL via SQLAlchemy."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def save_evaluation(
        self, ticket_data: TicketData, evaluation: AIEvaluationResult
    ) -> EvaluationResponse:
        record = TicketEvaluation(
            ticket_id=ticket_data.ticket_id,
            ticket_title=ticket_data.title,
            ticket_description=ticket_data.description,
            ticket_type=ticket_data.ticket_type,
            ticket_state=ticket_data.state,
            score=evaluation.score,
            feedback=evaluation.feedback,
            strengths=evaluation.strengths,
            additional_questions=evaluation.additional_questions,
        )
        self._db.add(record)
        self._db.commit()
        self._db.refresh(record)
        return EvaluationResponse.model_validate(record)

    def get_evaluations(
        self, limit: int = 20, offset: int = 0
    ) -> Tuple[List[EvaluationResponse], int]:
        total = self._db.query(TicketEvaluation).count()
        rows = (
            self._db.query(TicketEvaluation)
            .order_by(TicketEvaluation.evaluated_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [EvaluationResponse.model_validate(r) for r in rows], total

    def get_evaluations_by_ticket_id(self, ticket_id: str) -> List[EvaluationResponse]:
        rows = (
            self._db.query(TicketEvaluation)
            .filter(TicketEvaluation.ticket_id == ticket_id)
            .order_by(TicketEvaluation.evaluated_at.desc())
            .all()
        )
        return [EvaluationResponse.model_validate(r) for r in rows]
