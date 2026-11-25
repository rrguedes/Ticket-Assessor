import json
from types import SimpleNamespace
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app.services.agent.rag.test_case_index import TestCaseDocumentBuilder, TestCaseIndex


def case(case_id, title):
    return {'id': case_id, 'products': ['TWC'], 'suite_ids': [7],
            'work_item': {'rev': 2},
            'normalized': {'title': title, 'preconditions': 'Trem parado',
                           'steps': [{'action': 'Enviar comando', 'expected_result': 'Aceito'}]}}


class FakeStore:
    def __init__(self, fail=False):
        self.rows = {}
        self.fail = fail

    def add_texts(self, texts, metadatas, ids):
        if self.fail:
            raise RuntimeError('embedding failed')
        for text, metadata, case_id in zip(texts, metadatas, ids):
            self.rows[case_id] = (text, metadata)

    def similarity_search_with_score(self, query, k):
        return [(SimpleNamespace(page_content=text, metadata=metadata), 0.25)
                for text, metadata in list(self.rows.values())[:k]]


class TestIndex(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.manifest = Path(self.tmp.name) / 'manifest.json'
        self.stores = {}
        self.fail = False
        def factory(name):
            if name not in self.stores:
                self.stores[name] = FakeStore(self.fail)
            return self.stores[name]
        self.index = TestCaseIndex(factory, self.manifest, TestCaseDocumentBuilder('https://example.org/org', 'My Project'))
        self.snapshot = {'plan_id': 536901, 'synced_at': '2026-01-01', 'cases': [case(42, 'Cenário')]}

    def test_index_search_and_replace(self):
        self.index.rebuild(self.snapshot)
        found = self.index.search('comando')
        self.assertEqual(found[0]['case_id'], 42)
        self.assertIn('Resultado esperado: Aceito', found[0]['content'])
        self.assertIn('My%20Project/_workitems/edit/42', found[0]['url'])
        self.snapshot['cases'] = [case(99, 'Outro')]
        self.index.rebuild(self.snapshot)
        self.assertEqual([r['case_id'] for r in self.index.search('outro')], [99])

    def test_failed_rebuild_keeps_previous_index(self):
        original = self.index.rebuild(self.snapshot)
        self.fail = True
        with self.assertRaises(RuntimeError):
            self.index.rebuild(self.snapshot)
        self.assertEqual(json.loads(self.manifest.read_text())['collection'], original['collection'])
        self.assertEqual(self.index.search('comando')[0]['case_id'], 42)

    def test_invalid_snapshot_does_not_publish(self):
        self.snapshot['cases'][0]['normalized']['steps_error'] = 'invalid'
        with self.assertRaises(ValueError):
            self.index.rebuild(self.snapshot)
        self.assertFalse(self.manifest.exists())


if __name__ == '__main__':
    unittest.main()
