"""
Pydantic request/response schemas.
Single Responsibility: Only describes data shapes for the API layer.
"""
from __future__ import annotations
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


# ── Inbound ──────────────────────────────────────────────────────────────────

class EvaluateTicketRequest(BaseModel):
    ticket_id: str = Field(..., description="Azure DevOps work item ID", examples=["12345"])


# ── Domain objects (internal) ─────────────────────────────────────────────────

class TicketData(BaseModel):
    """Raw ticket data fetched from Azure DevOps."""
    ticket_id: str
    title: str
    description: Optional[str] = None
    acceptance_criteria: Optional[str] = None
    ticket_type: Optional[str] = None
    state: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[str] = None
    tags: Optional[str] = None
    story_points: Optional[float] = None


class AIEvaluationResult(BaseModel):
    """Structured result returned by the AI evaluator."""
    score: float = Field(..., ge=0, le=10)
    feedback: str
    strengths: List[str] = []
    additional_questions: List[str] = []


# ── Outbound ──────────────────────────────────────────────────────────────────

class EvaluationResponse(BaseModel):
    id: int
    ticket_id: str
    ticket_title: Optional[str]
    ticket_type: Optional[str]
    ticket_state: Optional[str]
    score: float
    feedback: str
    strengths: List[str]
    additional_questions: List[str]
    evaluated_at: datetime

    model_config = {"from_attributes": True}


class EvaluationListResponse(BaseModel):
    evaluations: List[EvaluationResponse]
    total: int
