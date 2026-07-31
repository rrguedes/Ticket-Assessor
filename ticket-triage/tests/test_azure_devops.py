"""
Unit tests for AzureDevOpsTicketFetcher.
HTTP calls are mocked with unittest.mock — no real network traffic.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from app.services.azure_devops import AzureDevOpsTicketFetcher, _strip_html

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def fetcher() -> AzureDevOpsTicketFetcher:
    return AzureDevOpsTicketFetcher(
        org_url="https://dev.azure.com/test-org",
        project="TestProject",
        pat="super-secret-pat",
    )


def _make_http_response(json_data: dict) -> MagicMock:
    """Build a mock that looks like an httpx.Response."""
    resp = MagicMock()
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    return resp


def _full_fields(**overrides) -> dict:
    base = {
        "System.Title": "Adicionar página de login",
        "System.Description": "<p>Precisamos de uma página de login.</p>",
        "Microsoft.VSTS.Common.AcceptanceCriteria": "<p>Usuário pode fazer login.</p>",
        "System.WorkItemType": "User Story",
        "System.State": "Active",
        "Microsoft.VSTS.Common.Priority": 2,
        "System.AssignedTo": {"displayName": "Maria Souza"},
        "System.Tags": "auth; frontend",
        "Microsoft.VSTS.Scheduling.StoryPoints": 3.0,
    }
    base.update(overrides)
    return base


# ── fetch_ticket: field mapping ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_fetch_ticket_maps_title(fetcher):
    resp = _make_http_response({"id": 1, "fields": _full_fields()})
    with patch("httpx.AsyncClient") as mc:
        mc.return_value.__aenter__.return_value.get = AsyncMock(return_value=resp)
        ticket = await fetcher.fetch_ticket("1")
    assert ticket.title == "Adicionar página de login"


@pytest.mark.asyncio
async def test_fetch_ticket_maps_ticket_type(fetcher):
    resp = _make_http_response({"id": 1, "fields": _full_fields()})
    with patch("httpx.AsyncClient") as mc:
        mc.return_value.__aenter__.return_value.get = AsyncMock(return_value=resp)
        ticket = await fetcher.fetch_ticket("1")
    assert ticket.ticket_type == "User Story"


@pytest.mark.asyncio
async def test_fetch_ticket_maps_priority_2_to_high(fetcher):
    resp = _make_http_response(
        {"id": 1, "fields": _full_fields(**{"Microsoft.VSTS.Common.Priority": 2})}
    )
    with patch("httpx.AsyncClient") as mc:
        mc.return_value.__aenter__.return_value.get = AsyncMock(return_value=resp)
        ticket = await fetcher.fetch_ticket("1")
    assert ticket.priority == "High"


@pytest.mark.asyncio
async def test_fetch_ticket_maps_priority_1_to_critical(fetcher):
    resp = _make_http_response(
        {"id": 1, "fields": _full_fields(**{"Microsoft.VSTS.Common.Priority": 1})}
    )
    with patch("httpx.AsyncClient") as mc:
        mc.return_value.__aenter__.return_value.get = AsyncMock(return_value=resp)
        ticket = await fetcher.fetch_ticket("1")
    assert ticket.priority == "Critical"


@pytest.mark.asyncio
async def test_fetch_ticket_maps_assigned_to_displayname(fetcher):
    resp = _make_http_response({"id": 1, "fields": _full_fields()})
    with patch("httpx.AsyncClient") as mc:
        mc.return_value.__aenter__.return_value.get = AsyncMock(return_value=resp)
        ticket = await fetcher.fetch_ticket("1")
    assert ticket.assigned_to == "Maria Souza"


@pytest.mark.asyncio
async def test_fetch_ticket_strips_html_from_description(fetcher):
    fields = _full_fields(**{"System.Description": "<p>Plain <b>text</b> here.</p>"})
    resp = _make_http_response({"id": 1, "fields": fields})
    with patch("httpx.AsyncClient") as mc:
        mc.return_value.__aenter__.return_value.get = AsyncMock(return_value=resp)
        ticket = await fetcher.fetch_ticket("1")
    assert "<p>" not in (ticket.description or "")
    assert "Plain" in (ticket.description or "")


@pytest.mark.asyncio
async def test_fetch_ticket_maps_story_points(fetcher):
    resp = _make_http_response({"id": 1, "fields": _full_fields()})
    with patch("httpx.AsyncClient") as mc:
        mc.return_value.__aenter__.return_value.get = AsyncMock(return_value=resp)
        ticket = await fetcher.fetch_ticket("1")
    assert ticket.story_points == 3.0


# ── fetch_ticket: missing / optional fields ───────────────────────────────────


@pytest.mark.asyncio
async def test_fetch_ticket_handles_missing_optional_fields(fetcher):
    resp = _make_http_response({"id": 99, "fields": {"System.Title": "Minimal"}})
    with patch("httpx.AsyncClient") as mc:
        mc.return_value.__aenter__.return_value.get = AsyncMock(return_value=resp)
        ticket = await fetcher.fetch_ticket("99")
    assert ticket.title == "Minimal"
    assert ticket.description is None
    assert ticket.acceptance_criteria is None
    assert ticket.assigned_to is None
    assert ticket.priority is None
    assert ticket.story_points is None
    assert ticket.repro_steps is None


@pytest.mark.asyncio
async def test_fetch_ticket_handles_string_assigned_to(fetcher):
    fields = _full_fields(**{"System.AssignedTo": "João Silva"})
    resp = _make_http_response({"id": 1, "fields": fields})
    with patch("httpx.AsyncClient") as mc:
        mc.return_value.__aenter__.return_value.get = AsyncMock(return_value=resp)
        ticket = await fetcher.fetch_ticket("1")
    assert ticket.assigned_to == "João Silva"


# ── fetch_ticket: HTTP errors ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_fetch_ticket_raises_on_404(fetcher):
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "404 Not Found", request=MagicMock(), response=mock_resp
    )
    with patch("httpx.AsyncClient") as mc:
        mc.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)
        with pytest.raises(httpx.HTTPStatusError):
            await fetcher.fetch_ticket("99999")


# ── _strip_html helper ────────────────────────────────────────────────────────


def test_strip_html_removes_tags():
    assert _strip_html("<p>Hello <b>world</b></p>") == "Hello  world"


def test_strip_html_returns_none_for_none():
    assert _strip_html(None) is None


def test_strip_html_returns_none_for_blank():
    assert _strip_html("   ") is None


def test_strip_html_returns_none_for_tags_only():
    assert _strip_html("<p></p>") is None
