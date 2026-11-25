import json

import httpx
import pytest
from app.services.test_plan_sync import TestPlanSync


@pytest.mark.asyncio
async def test_fetch_paginates_and_preserves_shared_cases():
    def respond(request):
        path = request.url.path
        if path.endswith("/suites"):
            if request.url.params.get("continuationToken"):
                return httpx.Response(
                    200, json={"value": [{"id": 20, "name": "Non IVOC TWC"}]}
                )
            return httpx.Response(
                200,
                headers={"x-ms-continuationtoken": "next"},
                json={"value": [{"id": 10, "name": "Non IVOC CBL"}]},
            )
        if path.endswith("/TestCase"):
            assert request.url.params["isRecursive"] == "true"
            return httpx.Response(200, json={"value": [{"workItem": {"id": 42}}]})
        if path.endswith("/workitemsbatch"):
            assert json.loads(request.content)["ids"] == [42]
            return httpx.Response(
                200,
                json={
                    "value": [{"id": 42, "rev": 3, "fields": {"System.Title": "Test"}}]
                },
            )
        raise AssertionError(path)

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        result = await TestPlanSync(
            "https://dev.azure.com/org", "project", "pat"
        ).fetch(client)
    assert result["plan_id"] == 536901
    assert result["cases"][0]["products"] == ["CBL", "TWC"]
    assert result["cases"][0]["work_item"]["rev"] == 3


@pytest.mark.asyncio
async def test_missing_suite_does_not_replace_existing_snapshot(tmp_path, monkeypatch):
    destination = tmp_path / "snapshot.json"
    destination.write_text("previous", encoding="utf-8")

    async def fail(self, client):
        raise ValueError("missing suite")

    monkeypatch.setattr(TestPlanSync, "fetch", fail)
    with pytest.raises(ValueError, match="missing suite"):
        await TestPlanSync("https://example.com", "project", "pat").sync(destination)
    assert destination.read_text(encoding="utf-8") == "previous"
