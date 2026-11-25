"""Download a complete, replaceable snapshot of the standard test suites."""

from __future__ import annotations

import base64
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import httpx
from app.services.test_case_text import normalize_test_case


class TestPlanSync:
    def __init__(self, org_url: str, project: str, pat: str, plan_id: int = 536901):
        self.base = f"{org_url.rstrip('/')}/{quote(project, safe='')}"
        self.org_url = org_url.rstrip("/")
        self.project = project
        self.plan_id = plan_id
        token = base64.b64encode(f":{pat}".encode()).decode()
        self.headers = {"Authorization": f"Basic {token}", "Accept": "application/json"}

    async def _pages(
        self, client: httpx.AsyncClient, path: str, params: dict | None = None
    ) -> list[dict]:
        items = []
        params = {**(params or {}), "api-version": "7.1"}
        seen = set()

        while True:
            response = await client.get(
                f"{self.base}{path}", headers=self.headers, params=params
            )
            response.raise_for_status()
            items.extend(response.json().get("value", []))
            token = response.headers.get("x-ms-continuationtoken")
            if not token:
                return items
            if token in seen:
                raise ValueError("Azure DevOps returned a repeated continuation token")
            seen.add(token)
            params["continuationToken"] = token

    async def fetch(self, client: httpx.AsyncClient) -> dict:
        prefix = f"/_apis/testplan/Plans/{self.plan_id}"
        suites = await self._pages(client, f"{prefix}/suites")
        cases: dict[int, dict] = {}

        for product, name in (("CBL", "Non IVOC CBL"), ("TWC", "Non IVOC TWC")):
            matches = [
                suite
                for suite in suites
                if suite.get("name", "").casefold() == name.casefold()
            ]
            if len(matches) != 1:
                raise ValueError(
                    f"Expected exactly one suite named {name}; found {len(matches)}"
                )
            suite_id = matches[0]["id"]
            entries = await self._pages(
                client, f"{prefix}/Suites/{suite_id}/TestCase", {"isRecursive": "true"}
            )

            for entry in entries:
                work_item = entry.get("workItem") or {}
                case_id = int(work_item["id"])
                case = cases.setdefault(
                    case_id, {"id": case_id, "products": [], "suite_ids": []}
                )
                if product not in case["products"]:
                    case["products"].append(product)
                if suite_id not in case["suite_ids"]:
                    case["suite_ids"].append(suite_id)
        ids = sorted(cases)

        for offset in range(0, len(ids), 200):
            batch = ids[offset : offset + 200]
            response = await client.post(
                f"{self.base}/_apis/wit/workitemsbatch",
                headers=self.headers,
                params={"api-version": "7.1"},
                json={"ids": batch},
            )
            response.raise_for_status()
            items = response.json().get("value", [])
            if {item["id"] for item in items} != set(batch):
                raise ValueError(
                    "Azure DevOps did not return every requested test case"
                )
            for item in items:
                cases[item["id"]]["work_item"] = item
                cases[item["id"]]["normalized"] = normalize_test_case(item)

        return {
            "plan_id": self.plan_id,
            "synced_at": datetime.now(timezone.utc).isoformat(),
            "cases": [cases[case_id] for case_id in ids],
        }

    async def sync(self, destination: Path) -> dict:
        async with httpx.AsyncClient(timeout=60) as client:
            snapshot = await self.fetch(client)
        destination.parent.mkdir(parents=True, exist_ok=True)

        temp_name = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=destination.parent, delete=False
            ) as file:
                temp_name = file.name
                json.dump(snapshot, file, ensure_ascii=False)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temp_name, destination)
        finally:
            if temp_name and os.path.exists(temp_name):
                os.unlink(temp_name)
        return snapshot
