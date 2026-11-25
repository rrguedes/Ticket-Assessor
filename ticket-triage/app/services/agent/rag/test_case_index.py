"""Build and search versioned indexes of synchronized test cases."""
from __future__ import annotations

import json
import os
import tempfile
import uuid
from pathlib import Path
from urllib.parse import quote


class TestCaseDocumentBuilder:
    """Convert a normalized case into searchable text and source metadata."""

    def __init__(self, org_url: str, project: str):
        self._work_item_url = f"{org_url.rstrip('/')}/{quote(project, safe='')}/_workitems/edit"

    def build(self, case: dict, plan_id: int) -> tuple[str, dict]:
        normalized = case['normalized']
        lines = [f"Título: {normalized.get('title', '')}"]
        for key, label in (('description', 'Descrição'), ('purpose', 'Objetivo'),
                           ('preconditions', 'Pré-condições'), ('environment_details', 'Ambiente'),
                           ('repro_steps', 'Reprodução')):
            if normalized.get(key):
                lines.append(f"{label}: {normalized[key]}")
        for number, step in enumerate(normalized.get('steps', []), 1):
            if step.get('type') == 'shared_steps':
                lines.append(f"Passo {number}: passos compartilhados {step.get('ref', '')} (não expandidos)")
            elif step.get('type') == 'unknown':
                lines.append(f"Passo {number}: conteúdo não interpretado")
            else:
                lines.append(f"Passo {number}: {step.get('action', '')}\nResultado esperado: {step.get('expected_result', '')}")
        case_id = int(case['id'])
        metadata = {'case_id': case_id, 'plan_id': plan_id,
                    'products': ','.join(sorted(case['products'])),
                    'suite_ids': ','.join(map(str, sorted(case['suite_ids']))),
                    'url': f'{self._work_item_url}/{case_id}',
                    'revision': int(case['work_item'].get('rev', 0))}
        return '\n'.join(lines), metadata


class TestCaseIndex:
    """Publish a new collection only after all its documents have been indexed."""

    def __init__(self, store_factory, manifest_path: Path, builder: TestCaseDocumentBuilder):
        self._store_factory = store_factory
        self._manifest_path = manifest_path
        self._builder = builder

    def rebuild(self, snapshot: dict, batch_size: int = 32) -> dict:
        self._validate(snapshot, batch_size)
        name = f"test_cases_{uuid.uuid4().hex}"
        store = self._store_factory(name)
        cases = snapshot['cases']
        for offset in range(0, len(cases), batch_size):
            self._index_batch(store, cases[offset:offset + batch_size], snapshot['plan_id'])
        manifest = {'collection': name, 'plan_id': snapshot['plan_id'],
                    'synced_at': snapshot['synced_at'], 'count': len(cases)}
        self._publish(manifest)
        return manifest

    @staticmethod
    def _validate(snapshot: dict, batch_size: int) -> None:
        if batch_size <= 0:
            raise ValueError('batch_size must be positive')
        cases = snapshot['cases']
        if not cases:
            raise ValueError('Cannot publish an empty test case index')
        ids = [case['id'] for case in cases]
        if len(set(ids)) != len(ids):
            raise ValueError('Duplicate test case IDs')
        if any('normalized' not in case or case['normalized'].get('steps_error') for case in cases):
            raise ValueError('Snapshot contains unnormalized cases or invalid steps')

    def _index_batch(self, store, cases: list[dict], plan_id: int) -> None:
        documents = [self._builder.build(case, plan_id) for case in cases]
        store.add_texts(texts=[doc[0] for doc in documents],
                        metadatas=[doc[1] for doc in documents],
                        ids=[str(case['id']) for case in cases])

    def _publish(self, manifest: dict) -> None:
        self._manifest_path.parent.mkdir(parents=True, exist_ok=True)
        filename = None
        try:
            with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=self._manifest_path.parent, delete=False) as file:
                filename = file.name
                json.dump(manifest, file, ensure_ascii=False)
                file.flush()
                os.fsync(file.fileno())
            os.replace(filename, self._manifest_path)
        finally:
            if filename and os.path.exists(filename):
                os.unlink(filename)

    def search(self, query: str, k: int = 5) -> list[dict]:
        if not query.strip() or k <= 0:
            return []
        with self._manifest_path.open(encoding='utf-8') as file:
            manifest = json.load(file)
        store = self._store_factory(manifest['collection'])
        matches = store.similarity_search_with_score(query, k=min(k, manifest['count']))
        return [{'content': document.page_content, **document.metadata, 'distance': float(distance),
                 'synced_at': manifest['synced_at']} for document, distance in matches]


def create_test_case_index(settings, manifest_path: Path) -> TestCaseIndex:
    """Connect to the same Chroma and Ollama configuration as requirements retrieval."""
    from langchain_chroma import Chroma
    from langchain_ollama import OllamaEmbeddings

    embeddings = OllamaEmbeddings(base_url=settings.local_models_base_url, model=settings.embedding_model)

    def make_store(name):
        return Chroma(collection_name=name, embedding_function=embeddings,
                      persist_directory=settings.chroma_persist_directory)

    return TestCaseIndex(make_store, manifest_path,
                         TestCaseDocumentBuilder(settings.azure_devops_org_url, settings.azure_devops_project))
