# Ticket Triage System

Sistema de triagem de tickets do Azure DevOps com avaliação por IA (OpenAI ChatGPT), pontuação 0–10, e perguntas complementares quando nota < 8.

## Run & Operate

- **Ticket Triage App** — `cd ticket-triage && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
- **Testes** — `cd ticket-triage && python3 -m pytest tests/ -v`
- **Docker** — `cd ticket-triage && docker compose up --build`

## Stack

- Backend: Python 3.11, FastAPI, SQLAlchemy 2, psycopg2
- Frontend: HTML5 + CSS3 puro (servido pelo FastAPI como arquivos estáticos)
- IA: OpenAI gpt-4o-mini via API
- Integração: Azure DevOps REST API v7.0 (PAT auth)
- Banco: PostgreSQL (Replit DB via `DATABASE_URL`)
- Testes: pytest + pytest-asyncio + pytest-mock (30 testes)
- Docker: Dockerfile multi-stage + docker-compose.yml

## Where things live

```
ticket-triage/
├── app/
│   ├── main.py                      # Entry point FastAPI; monta rotas e estáticos
│   ├── config.py                    # Pydantic Settings (env vars)
│   ├── database/
│   │   ├── connection.py            # Engine SQLAlchemy + get_db()
│   │   └── models.py                # Modelo TicketEvaluation
│   ├── schemas/ticket.py            # Pydantic schemas (request/response)
│   ├── services/
│   │   ├── interfaces.py            # ABCs: TicketFetcherInterface, AIEvaluatorInterface, EvaluationRepositoryInterface
│   │   ├── azure_devops.py          # Implementação: busca ticket no Azure DevOps
│   │   ├── openai_service.py        # Implementação: avalia ticket via OpenAI
│   │   ├── evaluation_repository.py # Implementação: persiste no PostgreSQL
│   │   └── ticket_service.py        # Orquestrador (DI, SOLID)
│   └── api/routes/tickets.py        # Endpoints FastAPI
├── frontend/
│   ├── index.html
│   ├── css/style.css
│   └── js/app.js
├── tests/                           # 30 testes unitários (sem chamadas reais)
├── Dockerfile                       # Multi-stage build
├── docker-compose.yml               # App + PostgreSQL
└── requirements.txt
```

## Architecture decisions

- **SOLID**: cada serviço implementa uma interface ABC; `TicketTriageService` depende só de abstrações (DIP)
- **Monolito modular**: um processo, separação clara por responsabilidade
- **Frontend estático servido pelo FastAPI** via `StaticFiles` — sem servidor separado
- **HTML stripped** dos campos rich-text do Azure DevOps antes de enviar ao LLM
- **gpt-4o-mini** como modelo padrão: equilíbrio custo/qualidade para avaliação de texto

## Secrets required

| Secret | Descrição |
|---|---|
| `OPENAI_API_KEY` | Chave da API OpenAI |
| `AZURE_DEVOPS_PAT` | Personal Access Token do Azure DevOps |
| `AZURE_DEVOPS_ORG_URL` | URL da organização (ex: https://dev.azure.com/org) |
| `AZURE_DEVOPS_PROJECT` | Nome do projeto no Azure DevOps |
| `DATABASE_URL` | Gerenciado pelo Replit automaticamente |

## Gotchas

- O FastAPI cria as tabelas automaticamente no startup (`Base.metadata.create_all`)
- Para Docker: copie `.env.example` para `.env` e preencha os valores
- Testes rodam com mocks completos — não requerem conexão real com Azure/OpenAI/DB

## User preferences

_Populate as you build._
