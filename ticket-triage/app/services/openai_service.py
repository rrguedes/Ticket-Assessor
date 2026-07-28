"""
OpenAI ticket evaluator — concrete implementation of AIEvaluatorInterface.
Single Responsibility: only communicates with the OpenAI Chat Completions API.
"""

from __future__ import annotations
import json

from openai import AsyncOpenAI

from app.schemas.ticket import AIEvaluationResult, TicketData
from app.services.interfaces import AIEvaluatorInterface

_SYSTEM_PROMPT = """
You are an expert software project manager and ticket quality analyst specialised in Agile/Scrum.
Your task is to evaluate Azure DevOps work items (tickets) for completeness and readiness for prioritisation and implementation.

Score the ticket from 0 to 10 using these weighted criteria:
  1. Title Clarity        (max 1 pt): Is the title concise and descriptive?
  2. Description Quality  (max 2 pts): Is the description detailed, clear, and unambiguous?
  3. Acceptance Criteria  (max 2 pts): Are there clear, testable acceptance criteria?
  4. Business Value       (max 2 pts): Is the business value or user need explained?
  5. Priority / Effort    (max 1 pt):  Is priority and/or estimated effort provided?
  6. Dependencies         (max 1 pt):  Are dependencies or blockers identified (or confirmed as none)?
  7. Context              (max 1 pt):  For bugs: reproduction steps; for features: user story or context.

Scoring guide:
  9–10  Excellent — virtually no information is missing.
  7–8   Good — minor gaps; ticket can be prioritised with small clarifications.
  5–6   Fair — significant information gaps that hamper prioritisation.
  0–4   Poor — critical information is absent; the ticket cannot be acted on.

Respond ONLY with a valid JSON object in this exact schema (no markdown fences):
{
  "score": <float 0.0–10.0>,
  "feedback": "<2–4 sentences summarising quality, explaining deductions, and highlighting the main gaps>",
  "strengths": ["<thing the ticket does well>"],
  "additional_questions": ["<specific, actionable question that would close a gap>"]
}

Rules:
  - "score" must be a JSON number, not a string.
  - "additional_questions" MUST contain at least 3 questions when score < 8; otherwise it may be empty.
  - Do NOT add any text outside the JSON object.
""".strip()


class OpenAITicketEvaluator(AIEvaluatorInterface):
    """Evaluates a ticket by calling the OpenAI Chat Completions API. Model: gpt-4o-mini"""

    def __init__(self, api_key: str, model: str = "llama3.2") -> None:
        self._client = AsyncOpenAI(
            base_url="http://host.docker.internal:11434/v1", api_key=api_key
        )
        self._model = model

    async def evaluate_ticket(self, ticket: TicketData) -> AIEvaluationResult:
        user_message = f"Please evaluate this Azure DevOps ticket:\n\n{self._format_ticket(ticket)}"

        response = await self._client.chat.completions.create(
            model=self._model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.2,
        )

        raw = response.choices[0].message.content
        data: dict = json.loads(raw)

        return AIEvaluationResult(
            score=float(data.get("score", 0)),
            feedback=data.get("feedback", ""),
            strengths=data.get("strengths", []),
            additional_questions=data.get("additional_questions", []),
        )

    # ── helpers ──────────────────────────────────────────────────────────────

    def _format_ticket(self, ticket: TicketData) -> str:
        lines = [
            f"ID: {ticket.ticket_id}",
            f"Type: {ticket.ticket_type or 'N/A'}",
            f"Title: {ticket.title}",
            f"State: {ticket.state or 'N/A'}",
            f"Priority: {ticket.priority or 'N/A'}",
            f"Assigned To: {ticket.assigned_to or 'Unassigned'}",
            f"Story Points: {ticket.story_points if ticket.story_points is not None else 'N/A'}",
            f"Tags: {ticket.tags or 'None'}",
            "",
            "Description:",
            ticket.description or "(No description provided)",
            "",
            "Acceptance Criteria:",
            ticket.acceptance_criteria or "(No acceptance criteria provided)",
        ]
        return "\n".join(lines)
