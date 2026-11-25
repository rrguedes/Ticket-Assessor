"""Run from ticket-triage: python -m scripts.sync_test_plan."""

import asyncio
from pathlib import Path

from app.config import get_settings
from app.services.test_plan_sync import TestPlanSync
from app.services.agent.rag.test_case_index import create_test_case_index
from scripts.test_case_index import MANIFEST


async def main():
    settings = get_settings()
    service = TestPlanSync(
        settings.azure_devops_org_url,
        settings.azure_devops_project,
        settings.azure_devops_pat,
    )
    destination = Path("app/vector_store/test_cases/plan_536901.json")
    snapshot = await service.sync(destination)
    print(f"Sincronizados {len(snapshot['cases'])} casos em {destination}")
    index = create_test_case_index(settings, MANIFEST)
    manifest = await asyncio.to_thread(index.rebuild, snapshot)
    print(f"Indexados {manifest['count']} casos na coleção {manifest['collection']}")


if __name__ == "__main__":
    asyncio.run(main())
