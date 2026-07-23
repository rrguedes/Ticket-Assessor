"""
Ticket API routes.
Single Responsibility: only maps HTTP requests to service calls and formats responses.
"""
from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.connection import get_db
from app.schemas.ticket import (
    EvaluateTicketRequest,
    EvaluationListResponse,
    EvaluationResponse,
)
from app.services.azure_devops import AzureDevOpsTicketFetcher
from app.services.evaluation_repository import PostgreSQLEvaluationRepository
from app.services.openai_service import OpenAITicketEvaluator
from app.services.ticket_service import TicketTriageService

router = APIRouter(prefix="/tickets", tags=["tickets"])


# ── Dependency factory ────────────────────────────────────────────────────────

def _get_service(db: Session = Depends(get_db)) -> TicketTriageService:
    """Compose the service with its concrete dependencies (DI via FastAPI)."""
    cfg = get_settings()
    return TicketTriageService(
        ticket_fetcher=AzureDevOpsTicketFetcher(
            org_url=cfg.azure_devops_org_url,
            project=cfg.azure_devops_project,
            pat=cfg.azure_devops_pat,
        ),
        ai_evaluator=OpenAITicketEvaluator(
            api_key=cfg.openai_api_key,
            model=cfg.openai_model,
        ),
        evaluation_repo=PostgreSQLEvaluationRepository(db=db),
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/evaluate", response_model=EvaluationResponse, status_code=200)
async def evaluate_ticket(
    body: EvaluateTicketRequest,
    service: TicketTriageService = Depends(_get_service),
) -> EvaluationResponse:
    """Fetch an Azure DevOps ticket by ID, evaluate it with AI, and persist the result."""
    try:
        return await service.evaluate_ticket(body.ticket_id)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail=f"Ticket #{body.ticket_id} not found in Azure DevOps.",
            )
        raise HTTPException(
            status_code=502,
            detail=f"Azure DevOps returned an error: {exc.response.status_code}.",
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Could not reach Azure DevOps: {exc}",
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/evaluations", response_model=EvaluationListResponse)
def list_evaluations(
    limit: int = 20,
    offset: int = 0,
    service: TicketTriageService = Depends(_get_service),
) -> EvaluationListResponse:
    """Return a paginated list of all stored evaluations."""
    evaluations, total = service.get_all_evaluations(limit=limit, offset=offset)
    return EvaluationListResponse(evaluations=evaluations, total=total)


@router.get("/evaluations/{ticket_id}", response_model=list[EvaluationResponse])
def get_ticket_evaluations(
    ticket_id: str,
    service: TicketTriageService = Depends(_get_service),
) -> list[EvaluationResponse]:
    """Return all evaluations ever produced for a specific ticket ID."""
    return service.get_evaluations_by_ticket(ticket_id)
