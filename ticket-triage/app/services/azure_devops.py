"""
Azure DevOps ticket fetcher — concrete implementation of TicketFetcherInterface.
Single Responsibility: only interacts with the Azure DevOps REST API.
Open/Closed: extend by subclassing or swapping; no changes needed here for other providers.
"""

from __future__ import annotations
import base64
import re

import httpx

from app.schemas.ticket import TicketData
from app.services.interfaces import TicketFetcherInterface

# Azure DevOps numeric priority → human-readable label
_PRIORITY_MAP: dict[int, str] = {
    1: "Critical",
    2: "High",
    3: "Medium",
    4: "Low",
}


def _strip_html(text: str | None) -> str | None:
    """Remove HTML tags from Azure DevOps rich-text fields."""
    if not text:
        return text
    return re.sub(r"<[^>]+>", " ", text).strip() or None


class AzureDevOpsTicketFetcher(TicketFetcherInterface):
    """Fetches Azure DevOps work items using Personal Access Token auth."""

    def __init__(self, org_url: str, project: str, pat: str) -> None:
        self._base_url = org_url.rstrip("/")
        self._project = project
        encoded = base64.b64encode(f":{pat}".encode()).decode()
        self._headers = {
            "Authorization": f"Basic {encoded}",
            "Accept": "application/json",
        }

    async def fetch_ticket(self, ticket_id: str) -> TicketData:
        url = f"{self._base_url}/{self._project}" f"/_apis/wit/workitems/{ticket_id}"
        params = {"api-version": "7.0", "$expand": "all"}

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, headers=self._headers, params=params)
            print(response)
            response.raise_for_status()
            data = response.json()

        fields: dict = data.get("fields", {})

        priority_raw = fields.get("Microsoft.VSTS.Common.Priority")
        priority = (
            _PRIORITY_MAP.get(priority_raw, str(priority_raw)) if priority_raw else None
        )

        assigned_to_raw = fields.get("System.AssignedTo")
        if isinstance(assigned_to_raw, dict):
            assigned_to = assigned_to_raw.get("displayName")
        else:
            assigned_to = str(assigned_to_raw) if assigned_to_raw else None

        return TicketData(
            ticket_id=str(ticket_id),
            title=fields.get("System.Title", ""),
            description=_strip_html(fields.get("System.Description")),
            acceptance_criteria=_strip_html(
                fields.get("Microsoft.VSTS.Common.AcceptanceCriteria")
            ),
            ticket_type=fields.get("System.WorkItemType"),
            state=fields.get("System.State"),
            priority=priority,
            assigned_to=assigned_to,
            tags=fields.get("System.Tags"),
            story_points=fields.get("Microsoft.VSTS.Scheduling.StoryPoints"),
            repro_steps=fields.get("Microsoft.VSTS.TCM.ReproSteps"),
        )
