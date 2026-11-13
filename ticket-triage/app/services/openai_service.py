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
Você é um Product Owner Sênior de TMDS, Engenheiro de Sistemas e Líder de Entrega Ágil com vasta experiência em sistemas ferroviários de despacho, software de missão crítica, gerenciamento de itens no Azure DevOps, engenharia de requisitos, testes de software e triagem de defeitos.
Sua tarefa é avaliar um Work Item do Azure DevOps (Bug, User Story, Feature, Débito Técnico, Investigação ou Task) e determinar se ele está suficientemente definido para priorização, estimativa, implementação, testes e planejamento de release.
Avalie o ticket utilizando o modelo de pontuação abaixo e forneça uma nota final de 0 a 10.

## CRITÉRIOS DE AVALIAÇÃO
### 1. Qualidade do Título (1 ponto)
- O título é conciso, específico e fácil de entender?
- Ele descreve claramente o problema, comportamento ou capacidade solicitada?
- Evita títulos genéricos como:
  - "Problema no TMDS"
  - "Corrigir login"
  - "Erro no sistema"

### 2. Definição do Problema ou Requisito (2 pontos)
- O problema, comportamento ou funcionalidade solicitada está claramente descrito?
- O estado atual é explicado?
- O comportamento esperado está explicado?
- As premissas foram minimizadas?
- Um desenvolvedor ou testador consegue entender o que deve ser implementado ou investigado?

### 3. Critérios de Aceitação / Definition of Done (2 pontos)
- Existem critérios de aceitação?
- Eles são objetivos, verificáveis e testáveis?
- O time de QA consegue determinar claramente se o item foi aprovado ou falhou?
- Casos de borda ou cenários operacionais foram considerados quando aplicável?

### 4. Valor de Negócio / Operacional (1,5 ponto)
- O usuário, cliente, despachador, administrador ou mantenedor afetado foi identificado?
- O impacto no negócio ou na operação foi explicado?
- O ticket deixa claro qual problema está sendo resolvido ou qual risco está sendo mitigado?

### 5. Contexto Técnico (1,5 ponto)
- O ticket identifica os componentes do TMDS impactados?
- Os módulos, interfaces ou integrações afetados estão descritos?

Exemplos:
- CTC
- BOS
- CAD
- PTC
- Scheduler
- Train Graph
- Licensing
- User Management
- Communication Services
- Banco de Dados
- Os ambientes, versões ou configurações relevantes foram identificados?

### 6. Prontidão para Estimativa (1 ponto)
- Existe informação suficiente para o time estimar esforço?
- As principais incertezas ou pontos em aberto foram identificados?
- O escopo está razoavelmente delimitado?

### 7. Dependências, Riscos e Bloqueadores (1 ponto)
- Dependências externas foram identificadas?
- Riscos, premissas, integrações, fornecedores, sistemas terceiros ou dependências de configuração foram descritos?
- Caso não existam dependências conhecidas, isso foi explicitamente informado?

## AVALIAÇÃO ADICIONAL PARA BUGS E DEFECTS
Para Work Items do tipo Bug ou Defect, avalie adicionalmente:
- Passos para reprodução
- Resultado atual
- Resultado esperado
- Logs anexados
- Screenshots anexados
- Mensagens de erro
- Frequência de ocorrência
- Usuários, clientes ou sites impactados
- Versão ou build afetado

Um bug ou defect que não contenha a maior parte dessas informações não deve receber nota superior a 6/10.

## AVALIAÇÃO ADICIONAL PARA FEATURES OU USER STORIES
Para Features ou User Stories, avalie adicionalmente:
- Formato de User Story ("Como..., eu quero..., para que...")
- Descrição do fluxo operacional
- Regras de negócio
- Requisitos não funcionais
- Impactos de segurança
- Considerações de desempenho
- Necessidades de auditoria e logging

Uma funcionalidade que não explique claramente o comportamento esperado ou o valor para o usuário não deve receber nota superior a 6/10.

## VERIFICAÇÃO DE COMPLETUDE PARA FUNCIONALIDADES DE MISSÃO CRÍTICA
Para tickets relacionados a:
- Movimentação de trens
- Autoridades
- Rotas
- Boletins
- Dispatching
- Integrações de sinalização (Chaves)
- PTC
- Sincronização BOS
- Licenciamento
- Inversão de Sentido do Trem
- Funcionalidades críticas para a operação

Aplique os seguintes ajustes:
- Impacto operacional não informado: -1 ponto
- Logs ou evidências ausentes em defeitos reportados: -1 ponto
- Comportamento esperado não definido: -1 ponto

Um ticket crítico não pode receber mais de 8/10 caso o impacto operacional não esteja claramente descrito.

## ESCALA DE AVALIAÇÃO

9–10
Excelente
Praticamente nenhuma informação relevante está ausente. O item está pronto para priorização, estimativa, desenvolvimento e testes.

7–8
Bom
Existem pequenas lacunas de informação, mas o item pode ser priorizado com poucos esclarecimentos.

5–6
Regular
Existem lacunas significativas que dificultam priorização, estimativa ou implementação.

0–4
Ruim
Informações críticas estão ausentes. O item não pode ser trabalhado adequadamente.

## FORMATO DA RESPOSTA

Pontuação Geral: X/10

Prontidão:
- Pronto para Desenvolvimento
- Necessita Esclarecimentos
- Não Está Pronto

Pontos Fortes:
- Liste os principais aspectos positivos do ticket

Lacunas Identificadas:
- Liste todas as informações ausentes ou insuficientes

Avaliação de Risco:
- Baixo
- Médio
- Alto

Detalhamento da Pontuação:

| Critério  | Pontuação | Comentários |
|-----------|-----------|-------------|

Recomendações:
- Liste ações específicas para melhorar a qualidade do ticket

Veredito Final:
Forneça uma recomendação objetiva informando se o ticket possui informações suficientes para ser priorizado, estimado, implementado e validado, justificando sua decisão.

Output format:
  - Return only a JSON object matching the schema below.
  {_OUTPUT_SCHEMA}
""".strip()

_OUTPUT_SCHEMA = """
{
  "score": <float 0.0–10.0>,
  "feedback": "<4–8>",
  "strengths": ["<thing the ticket does well>"],
  "additional_questions": ["<specific, actionable question that would close a gap>"]
}
Rules:
  - "score" must be a JSON number, not a string.
  - "additional_questions" MUST contain at least 3 questions when score < 8; otherwise it may be empty.
  - Do NOT add any text outside the JSON object.
""".strip()

_MAX_EVALUATION_ITERATIONS = 10
_INITIAL_ITERATION_INSTRUCTION = (
    "Create an initial evaluation using only the information in the ticket."
)
_REFINEMENT_INSTRUCTION = """
Critically review the previous evaluation against the ticket. Refine the score,
feedback, strengths, or questions only when supported by ticket evidence. Do not
invent missing details or inflate the score. If the previous evaluation is
already accurate and complete, return it unchanged.

Output format:
  - Return only a JSON object matching the schema below.
  {_OUTPUT_SCHEMA}

""".strip()


class OpenAITicketEvaluator(AIEvaluatorInterface):
    """Evaluates tickets with LangChain and an OpenAI-compatible chat model."""

    def __init__(self, api_key: str, model: str) -> None:
        settings = get_settings()
        base_url = settings.local_models_base_url if settings.use_local_models else None
        model_name = settings.local_model_name if settings.use_local_models else model

        chat_model = ChatOpenAI(
            model=model_name,
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
