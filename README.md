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
- AI-powered evaluation using an OpenAI-compatible client
- PostgreSQL persistence for evaluation history
- Simple static frontend for submitting tickets and reviewing results
- Docker Compose support for local development and deployment

## Tech stack

- Python 3.11
- FastAPI
- SQLAlchemy
- Pydantic and Pydantic Settings
- PostgreSQL
- OpenAI Python SDK
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
```

### Notes on AI model configuration

The current implementation uses an OpenAI-compatible client. This means it can work with:

- OpenAI hosted models
- local models served through Ollama

When using Ollama locally, the client can be pointed to http://localhost:11434/v1.

## Running locally

### 1. Install Python dependencies

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
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
