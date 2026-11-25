# Ticket Triage

Ticket Triage is a FastAPI-based application designed to evaluate Azure DevOps work items for quality, completeness, and readiness for implementation. It helps teams quickly identify tickets that are well-defined and actionable, while also surfacing missing information that could block prioritization or delivery.

## What the project does

The application performs the following workflow:

1. Fetches a ticket from Azure DevOps using its REST API.
2. Sends the ticket content to an AI evaluator.
3. Returns a structured assessment with:
   - a score from 0 to 10
   - written feedback
   - identified strengths
   - suggested follow-up questions
4. Stores the evaluation in PostgreSQL for later review.

This makes it useful for improving backlog hygiene and supporting ticket refinement processes.

## Why it exists

The project is intended to help product owners, developers, and project managers reduce ambiguity in work items before implementation begins. Instead of manually reviewing every ticket, the system provides a fast, repeatable evaluation that highlights gaps in description, acceptance criteria, context, or business value.

## Main features

- FastAPI REST API with interactive Swagger documentation
- Azure DevOps integration for retrieving work items
- AI-powered evaluation using LangChain with OpenAI-compatible chat models
- PostgreSQL persistence for evaluation history
- Simple static frontend for submitting tickets and reviewing results
- Docker Compose support for local development and deployment

## Tech stack

- Python 3.11
- FastAPI
- SQLAlchemy
- Pydantic and Pydantic Settings
- PostgreSQL
- LangChain and LangChain OpenAI integration
- HTTPX
- Docker and Docker Compose
- pytest

## Project structure

- app/main.py: FastAPI application entry point
- app/api/routes/tickets.py: API routes for evaluation and history
- app/services/: business logic, Azure DevOps integration, and AI evaluation
- app/database/: database models and connection setup
- app/schemas/: request and response schemas
- frontend/: lightweight static web UI
- tests/: unit and integration tests

## Configuration

The application reads configuration from a .env file.

### Required environment variables

Create a .env file in the project root with the following values:

```env
DATABASE_URL=postgresql://triage:triagepass@localhost:5432/ticket_triage
OPENAI_API_KEY=your-openai-or-ollama-key
AZURE_DEVOPS_PAT=your-azure-devops-pat
AZURE_DEVOPS_ORG_URL=https://dev.azure.com/your-organization
AZURE_DEVOPS_PROJECT=your-project-name
OPENAI_MODEL=llama3.2
USE_LOCAL_MODELS=true|false
LOCAL_MODELS_BASE_URL=http://yourlocalurl:11434/v1
LOCAL_MODEL_NAME=llama3.2
```

### Notes on AI model configuration

The evaluator uses LangChain with an OpenAI-compatible chat model. This means it can work with:

- OpenAI hosted models
- local models served through Ollama

When `USE_LOCAL_MODELS=true`, the evaluator uses `LOCAL_MODEL_NAME` and points to `LOCAL_MODELS_BASE_URL`, such as `http://localhost:11434/v1` for Ollama's OpenAI-compatible API.

## Running locally

### 1. Install Python dependencies

```bash
uv sync
```

### 2. Start PostgreSQL

You can either run PostgreSQL manually or use Docker Compose:

```bash
docker compose up -d db
```

### 3. Start the API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Then open:

- http://localhost:8000/
- http://localhost:8000/triage/docs for the API documentation

### 4. Start the Web UI

```bash
```

## Running with Docker Compose

The repository includes a Docker Compose configuration that starts both the application and PostgreSQL.

```bash
docker compose up --build
```

The app will be exposed on port 8000.

## API endpoints

The main API routes are mounted under the /triage prefix:

- GET /triage/healthz: health check endpoint
- POST /triage/tickets/evaluate: evaluate a given ticket ID
- GET /triage/tickets/evaluations: list stored evaluations
- GET /triage/tickets/evaluations/{ticket_id}: list evaluations for a specific ticket

## Testing

Run the test suite with:

```bash
pytest
```

## Important considerations

- The system currently assumes access to Azure DevOps and a valid personal access token.
- The AI output is structured and validated with Pydantic models.
- The app is designed as a functional prototype and may need additional hardening for production use, such as authentication, rate limiting, and better error handling.
- The project does not currently declare a license file.

### Sincronização dos casos de teste

A partir de `ticket-triage/`, execute `python -m scripts.sync_test_plan` para baixar os casos das suítes **Non IVOC CBL** e **Non IVOC TWC**, incluindo suas subsuítes, do plano 536901. São usadas as mesmas configurações `AZURE_DEVOPS_ORG_URL`, `AZURE_DEVOPS_PROJECT` e `AZURE_DEVOPS_PAT` da aplicação. O PAT precisa ter acesso de leitura aos planos e work items.

O comando grava `app/vector_store/test_cases/plan_536901.json` com os campos originais dos work items, os produtos associados e a data da sincronização. Uma falha durante a coleta preserva o arquivo anterior. Execute novamente para atualizar o retrato completo. Após salvar o arquivo, o comando também reconstrói o índice de busca; a avaliação de tickets ainda não consulta os casos automaticamente.

Cada caso também contém `normalized`, com texto legível para título, descrição, pré-condições e outros campos textuais disponíveis. Os passos são mantidos em ordem, com ação e resultado esperado separados; referências a passos compartilhados permanecem como referências e ainda não são expandidas. Os campos originais permanecem em `work_item.fields`, inclusive XML e HTML, para preservar os dados de origem. As próximas sincronizações geram essa representação automaticamente.


Para indexar o retrato já baixado, execute `python -m scripts.test_case_index index` a partir de `ticket-triage/`. Consulte com `python -m scripts.test_case_index search "descrição do cenário" -k 5`. A busca retorna os candidatos, seus metadados e a distância vetorial (quanto menor, mais próximo); isso não comprova cobertura. O Ollama e o modelo configurado em `EMBEDDING_MODEL` devem estar disponíveis, e `CHROMA_PERSIST_DIRECTORY` deve permanecer igual entre indexação e consulta.

A publicação do índice ocorre após a indexação completa. Se ela falhar, o JSON pode estar mais recente que o índice anterior, cuja data de sincronização é apresentada na busca. Cada reconstrução cria uma nova coleção; coleções anteriores permanecem no Chroma e podem ocupar espaço. Para validar a qualidade da busca, compare os resultados com casos conhecidos antes de usá-los na avaliação de cobertura.
