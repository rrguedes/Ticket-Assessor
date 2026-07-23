"""
Shared pytest fixtures.
"""
from datetime import datetime, timezone
import pytest

from app.schemas.ticket import AIEvaluationResult, EvaluationResponse, TicketData


@pytest.fixture
def sample_ticket() -> TicketData:
    return TicketData(
        ticket_id="12345",
        title="Implementar autenticação de usuários",
        description=(
            "Adicionar autenticação baseada em JWT para proteger os endpoints da API. "
            "O sistema deve permitir login, logout e renovação de token."
        ),
        acceptance_criteria=(
            "Dado um usuário válido, quando ele fizer login, receberá um token JWT. "
            "O token expira em 1 hora. Endpoints protegidos retornam 401 sem token."
        ),
        ticket_type="User Story",
        state="Active",
        priority="High",
        assigned_to="João Silva",
        tags="auth; security",
        story_points=5.0,
    )


@pytest.fixture
def minimal_ticket() -> TicketData:
    return TicketData(
        ticket_id="99999",
        title="Corrigir bug",
    )


@pytest.fixture
def good_evaluation() -> AIEvaluationResult:
    return AIEvaluationResult(
        score=8.5,
        feedback=(
            "Ticket bem estruturado com critérios de aceitação claros e valor de negócio definido. "
            "Pequenos detalhes sobre dependências poderiam ser adicionados."
        ),
        strengths=["Título descritivo", "Critérios de aceitação testáveis", "Esforço estimado"],
        additional_questions=[],
    )


@pytest.fixture
def poor_evaluation() -> AIEvaluationResult:
    return AIEvaluationResult(
        score=3.0,
        feedback=(
            "O ticket carece de informações essenciais. A descrição é vaga e não há critérios de aceitação. "
            "Não é possível priorizar ou implementar este ticket no estado atual."
        ),
        strengths=["Título presente"],
        additional_questions=[
            "Qual é o objetivo de negócio desta correção?",
            "Quais são os critérios de aceitação esperados?",
            "Quais usuários são afetados?",
        ],
    )


@pytest.fixture
def saved_evaluation() -> EvaluationResponse:
    return EvaluationResponse(
        id=1,
        ticket_id="12345",
        ticket_title="Implementar autenticação de usuários",
        ticket_type="User Story",
        ticket_state="Active",
        score=8.5,
        feedback="Ticket bem estruturado.",
        strengths=["Título descritivo"],
        additional_questions=[],
        evaluated_at=datetime(2024, 6, 1, 10, 0, tzinfo=timezone.utc),
    )
