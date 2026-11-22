"""
Pydantic request/response schemas.
Single Responsibility: Only describes data shapes for the API layer.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

# ── Inbound ──────────────────────────────────────────────────────────────────


class EvaluateTicketRequest(BaseModel):
    ticket_id: str = Field(
        ..., description="Azure DevOps work item ID", examples=["12345"]
    )
    consultar_documentos: bool = Field(
        default=False,
        description="Consultar os documentos de requisitos de modos de operação",
    )


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
    repro_steps: Optional[str] = None
    fix_description: Optional[str] = None
    comments: List[str] = Field(
        default_factory=list,
        description="Comments associated with the ticket",
    )


class AIEvaluationResult(BaseModel):
    """Structured result returned by the AI evaluator."""

    score: float = Field(
        ...,
        ge=0,
        le=10,
        description="Qualidade do ticket de 0 a 10",
    )
    feedback: str = Field(
        ...,
        description="Feedback resumindo a qualidade do ticket e as principais lacunas",
    )
    strengths: List[str] = Field(
        default_factory=list,
        description="Pontos fortes do ticket",
    )
    additional_questions: List[str] = Field(
        default_factory=list,
        description="Perguntas adicionais para esclarecer lacunas do ticket",
    )
    verdict: str = Field(
        ...,
        description="Veredito final explicando se o ticket pode ser priorizado, estimado, implementado e testado",
    )
    model: Optional[str] = None


# ── Outbound ──────────────────────────────────────────────────────────────────


class RequirementExcerpt(BaseModel):
    content: str
    collection: str
    page: Optional[int] = None
    similarity_score: Optional[float] = None


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
    verdict: str
    model: Optional[str] = None
    consulted_requirements: List[RequirementExcerpt] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class EvaluationListResponse(BaseModel):
    evaluations: List[EvaluationResponse]
    total: int
