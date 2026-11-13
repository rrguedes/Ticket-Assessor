"""
Ticket evaluator — concrete implementation of AIEvaluatorInterface.
Single Responsibility: only evaluates tickets through a LangChain chat model.
"""

from __future__ import annotations

from app.config import get_settings

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.schemas.ticket import AIEvaluationResult, TicketData
from app.services.interfaces import AIEvaluatorInterface

_SYSTEM_PROMPT = """
Você é um Product Owner Sênior de TMDS, Engenheiro de Sistemas e Líder de Entrega Ágil com experiência em sistemas ferroviários de missão crítica, Azure DevOps, engenharia de requisitos, testes e triagem de defeitos.

Sua tarefa é avaliar um Work Item do Azure DevOps (Bug, User Story, Feature, Investigação, Débito Técnico ou Task) e determinar sua qualidade e prontidão para priorização, estimativa, desenvolvimento e testes.

Atribua uma nota de 0 a 10 utilizando os critérios abaixo.

CRITÉRIOS DE AVALIAÇÃO

1. Clareza do Problema/Requisito (3 pontos)
- O problema ou necessidade está claramente descrito?
- O comportamento atual e o esperado estão definidos?
- É possível entender o que deve ser desenvolvido ou investigado?

2. Critérios de Aceitação (2 pontos)
- Existem critérios de aceitação claros?
- São objetivos, verificáveis e testáveis?

3. Contexto de Negócio e Operação (2 pontos)
- O impacto para usuários, clientes ou operação está explicado?
- O valor da correção ou funcionalidade está justificado?

4. Contexto Técnico (2 pontos)
- Componentes, módulos, integrações, versões, ambientes ou sistemas impactados foram identificados?
- Há informações suficientes para análise técnica e estimativa?

5. Dependências e Evidências (1 ponto)
- Dependências, riscos ou bloqueadores foram identificados?
- Para bugs, há evidências como logs, screenshots, mensagens de erro ou passos de reprodução?

REGRAS ESPECIAIS

Para Bugs:
- Verifique se existem passos de reprodução, resultado atual, resultado esperado e evidências.
- Um bug sem evidências ou comportamento esperado claramente definido não deve receber mais de 6/10.

Para Funcionalidades Críticas TMDS:
- Verifique se o impacto operacional está descrito.
- Um item relacionado a despacho, rotas, autoridades, BOS, CAD, PTC, licenciamento ou comunicação que não informe o impacto operacional não deve receber mais de 8/10.

ESCALA

9-10: Excelente
Pronto para priorização e desenvolvimento.

7-8: Bom
Necessita apenas pequenos esclarecimentos.

5-6: Regular
Existem lacunas significativas.

0-4: Ruim
Faltam informações críticas.

Veredito Final:
Explique se o item pode ser priorizado, estimado, implementado e testado com segurança.

  {_OUTPUT_SCHEMA}
""".strip()

_OUTPUT_SCHEMA = """
Formato da resposta:
  - Retorne apenas um objeto JSON correspondente ao esquema abaixo.
{
  "score": <float 0.0–10.0>,
  "feedback": "<3–4 parágrafos>",
  "strengths": ["<coisa que o ticket faz bem>"],
  "additional_questions": ["<pergunta específica e acionável que fecharia uma lacuna>"],
  "verdict": "<explicação do veredito final>"
}
Regras:
  - "score" deve ser um número JSON, não uma string.
  - "additional_questions" DEVE conter pelo menos 4 perguntas quando score < 8; caso contrário, pode estar vazia.
  - NÃO adicione nenhum texto fora do objeto JSON.
""".strip()

_MAX_EVALUATION_ITERATIONS = 10
_INITIAL_ITERATION_INSTRUCTION = (
    "Crie uma avaliação inicial usando apenas as informações do ticket."
)
_REFINEMENT_INSTRUCTION = """
Revise criticamente a avaliação anterior em relação ao ticket. Refine a pontuação,
o feedback, os pontos fortes ou as perguntas apenas quando houver evidências no ticket.
Não invente detalhes ausentes nem inflacione a pontuação. Se a avaliação anterior já
estiver precisa e completa, retorne-a sem alterações.

{_OUTPUT_SCHEMA}

""".strip()


class OpenAITicketEvaluator(AIEvaluatorInterface):
    """Evaluates tickets with LangChain and an OpenAI-compatible chat model."""

    def __init__(self, api_key: str, model: str) -> None:
        settings = get_settings()
        base_url = settings.local_models_base_url if settings.use_local_models else None
        self._model_name = settings.local_model_name if settings.use_local_models else model

        chat_model = ChatOpenAI(
            model=self._model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=0,
        )
        parser = PydanticOutputParser(pydantic_object=AIEvaluationResult)
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "{system_prompt}\n\n{format_instructions}"),
                (
                    "human",
                    "Please evaluate this Azure DevOps ticket:\n\n{ticket}\n\n"
                    "Previous evaluation:\n{previous_evaluation}\n\n"
                    "Iteration instruction:\n{iteration_instruction}",
                ),
            ]
        )
        self._chain = prompt | chat_model | parser
        self._format_instructions = parser.get_format_instructions()

    async def evaluate_ticket(self, ticket: TicketData) -> AIEvaluationResult:
        ticket_text = self._format_ticket(ticket)
        previous_result: AIEvaluationResult | None = None
        for iteration in range(_MAX_EVALUATION_ITERATIONS):
            print(f"Interação {iteration + 1} de {_MAX_EVALUATION_ITERATIONS}")
            result = await self._chain.ainvoke(
                {
                    "system_prompt": _SYSTEM_PROMPT,
                    "format_instructions": self._format_instructions,
                    "ticket": ticket_text,
                    "previous_evaluation": (
                        previous_result.model_dump_json()
                        if previous_result is not None
                        else "(No previous evaluation; this is the initial assessment.)"
                    ),
                    "iteration_instruction": (
                        _INITIAL_ITERATION_INSTRUCTION
                        if previous_result is None
                        else _REFINEMENT_INSTRUCTION
                    ),
                }
            )
            current_result = AIEvaluationResult.model_validate(result)
            current_result.model = self._model_name

            if previous_result is not None and current_result == previous_result:
                return current_result

            previous_result = current_result

        assert previous_result is not None
        return previous_result

    # ── helpers ──────────────────────────────────────────────────────────────

    def _format_ticket(self, ticket: TicketData) -> str:
        _new_line = "\n"
        lines = [
            f"ID: {ticket.ticket_id}",
            f"Type: {ticket.ticket_type or 'N/A'}",
            f"Title: {ticket.title}",
            f"State: {ticket.state or 'N/A'}",
            f"Priority: {ticket.priority or 'N/A'}",
            f"Assigned To: {ticket.assigned_to or 'Unassigned'}",
            f"Story Points: {ticket.story_points if ticket.story_points is not None else 'N/A'}",
            f"Tags: {ticket.tags or 'None'}",
            f"Reproduction Steps: {ticket.repro_steps or '(No reproduction steps provided)'}",
            f"Fix Description: {ticket.fix_description or '(No fix description provided)'}",
            f"Description: {ticket.description or '(No description provided)'}",
            f"Acceptance Criteria: {ticket.acceptance_criteria or '(No acceptance criteria provided)'}",
            f"Comments: {_new_line.join(ticket.comments) or '(No comments provided)'}"
        ]
        return _new_line.join(lines)
