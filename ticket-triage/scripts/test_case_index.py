"""Index a synchronized plan or search it: python -m scripts.test_case_index --help."""
import argparse
import json
from pathlib import Path

from app.config import get_settings
from app.services.agent.rag.test_case_index import create_test_case_index

SNAPSHOT = Path('app/vector_store/test_cases/plan_536901.json')
MANIFEST = Path('app/vector_store/test_cases/index_manifest.json')


def main():
    parser = argparse.ArgumentParser(description='Indexar ou consultar os casos de teste')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('index')
    search = commands.add_parser('search')
    search.add_argument('query')
    search.add_argument('-k', type=int, default=5)
    args = parser.parse_args()
    index = create_test_case_index(get_settings(), MANIFEST)
    if args.command == 'index':
        with SNAPSHOT.open(encoding='utf-8') as file:
            result = index.rebuild(json.load(file))
    else:
        result = index.search(args.query, args.k)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
