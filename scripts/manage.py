"""Small CLI that shares the exact services used by the dashboard."""
import argparse
import json
from pathlib import Path
from services.storage import initialize
from services.analysis import reserve_run, run_pipeline, latest_run
from services.imports import parse_csv, import_rows


def main():
    parser = argparse.ArgumentParser(description='Feedback review tools. Start the web app with start.ps1.')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('init')
    run = sub.add_parser('analyze')
    run.add_argument('--engine', choices=['semantic', 'lexical'], default='semantic')
    ingest = sub.add_parser('import')
    ingest.add_argument('file', type=Path)
    ingest.add_argument('--replace', action='store_true', help='Replace current feedback; saved reports remain. Default appends.')
    args = parser.parse_args()
    initialize()
    if args.command == 'analyze':
        run_pipeline(reserve_run(args.engine))
        result = latest_run()
        print(json.dumps(result, indent=2))
        if result['status'] != 'completed':
            raise SystemExit(1)
    elif args.command == 'import':
        print(json.dumps(import_rows(parse_csv(args.file.read_bytes()), args.file.name, 'replace' if args.replace else 'append'), indent=2))

if __name__ == '__main__':
    main()
