"""
Ticket Triage Service — the application's core orchestrator.

Dependency Inversion Principle: depends on the three abstract interfaces, never
on concrete classes.  Business logic lives here; infrastructure concerns are
pushed to the concrete implementations injected at construction time.
"""

from __future__ import annotations

from langchain_core.documents import Document

from app.schemas.ticket import (
    EvaluationResponse,
    RequirementExcerpt,
    TicketData,
)
from app.services.interfaces import (
    AIEvaluatorInterface,
    EvaluationRepositoryInterface,
    RequirementsRetrieverInterface,
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
        requirements_retriever: RequirementsRetrieverInterface | None = None,
    ) -> None:
        self._ticket_fetcher = ticket_fetcher
        self._ai_evaluator = ai_evaluator
        self._evaluation_repo = evaluation_repo
        self._requirements_retriever = requirements_retriever

    async def evaluate_ticket(
        self, ticket_id: str, consultar_documentos: bool = False
    ) -> EvaluationResponse:
        """Fetch, evaluate, persist and return the evaluation for *ticket_id*."""
        ticket_data = await self._ticket_fetcher.fetch_ticket(ticket_id)
        requirements_context = None
        requirement_documents: list[Document] = []
        if consultar_documentos and self._requirements_retriever is not None:
            requirement_documents = self._requirements_retriever.search(
                self._build_requirements_query(ticket_data)
            )
            requirements_context = self._format_requirements_context(
                requirement_documents
            )

        if requirements_context:
            ai_result = await self._ai_evaluator.evaluate_ticket(
                ticket_data,
                requirements_context=requirements_context,
            )
        else:
            ai_result = await self._ai_evaluator.evaluate_ticket(ticket_data)
        saved_evaluation = self._evaluation_repo.save_evaluation(ticket_data, ai_result)
        if requirement_documents:
            return saved_evaluation.model_copy(
                update={
                    "consulted_requirements": self._serialize_requirements(
                        requirement_documents
                    )
                }
            )
        return saved_evaluation

    @staticmethod
    def _build_requirements_query(ticket_data: TicketData) -> str:
        """Build a semantic query from the ticket's searchable fields."""
        fields = [
            ticket_data.title,
            ticket_data.description,
            ticket_data.acceptance_criteria,
            ticket_data.ticket_type,
            ticket_data.tags,
        ]
        return "\n".join(value for value in fields if value)

    @staticmethod
    def _format_requirements_context(documents: list[Document]) -> str | None:
        if not documents:
            return None

        excerpts = []
        for index, document in enumerate(documents, start=1):
            collection = document.metadata.get("collection", "unknown")
            page = document.metadata.get("page", "unknown")
            excerpts.append(
                f"[Trecho {index} | collection={collection} | página={page}]\n"
                f"{document.page_content}"
            )
        return "\n\n".join(excerpts)

    @staticmethod
    def _serialize_requirements(
        documents: list[Document],
    ) -> list[RequirementExcerpt]:
        return [
            RequirementExcerpt(
                content=document.page_content,
                collection=str(document.metadata.get("collection", "unknown")),
                page=(
                    document.metadata.get("page")
                    if isinstance(document.metadata.get("page"), int)
                    else None
                ),
                similarity_score=(
                    float(document.metadata["similarity_score"])
                    if document.metadata.get("similarity_score") is not None
                    else None
                ),
            )
            for document in documents
        ]

    def get_all_evaluations(
        self, limit: int = 20, offset: int = 0
    ) -> tuple[list[EvaluationResponse], int]:
        """Return a paginated list of all evaluations and the total count."""
        return self._evaluation_repo.get_evaluations(limit, offset)

    def get_evaluations_by_ticket(self, ticket_id: str) -> list[EvaluationResponse]:
        """Return every evaluation ever created for the given ticket."""
        return self._evaluation_repo.get_evaluations_by_ticket_id(ticket_id)
