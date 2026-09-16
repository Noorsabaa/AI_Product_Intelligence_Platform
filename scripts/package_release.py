"""Build a portable ZIP with a consistent DB snapshot and no local credentials."""
import os
import sqlite3
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT.parent / 'Feedback-Review-v3.zip'
SKIP_DIRS = {'.venv', '.venv313', 'venv', 'node_modules', '__pycache__', '.pytest_cache', '.git', 'workspaces', 'account-tests'}
SKIP_FILES = {'refine.py', 'restore_runtime.py', 'cluster_probe.py', 'original-source.db', 'browser.db', 'launcher.db', 'release-reviews.db', 'feedback-export.csv'}
QA_FILES = {'browser-smoke.cjs','browser-results-v3.json','dashboard-v3-desktop.png','dashboard-v3-mobile.png',
            'trends-v3-desktop.png','priorities-v3-desktop.png','evidence-v3-desktop.png','import-v3-mobile.png',
            'report-v3-desktop.png','sign-in-v3.png','generate-report-v3.png','report-history-v3.png'}


def package():
    snapshot = ROOT / 'qa' / 'release-reviews.db'
    source = sqlite3.connect(ROOT / 'data' / 'reviews.db')
    target = sqlite3.connect(snapshot)
    source.backup(target)
    source.close()
    target.execute('PRAGMA journal_mode=DELETE')
    assert target.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    reviews = target.execute('SELECT COUNT(*) FROM reviews').fetchone()[0]
    target.close()
    with zipfile.ZipFile(OUTPUT, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for folder, dirs, files in os.walk(ROOT):
            dirs[:] = [name for name in dirs if name not in SKIP_DIRS and not name.startswith('pytest-cache-files-')]
            for filename in files:
                path = Path(folder) / filename
                relative = path.relative_to(ROOT)
                if relative.parts[0] == 'qa' and filename not in QA_FILES:
                    continue
                if filename in SKIP_FILES or path.suffix in {'.db', '.pyc'} or filename.endswith(('.db-wal', '.db-shm')):
                    continue
                if filename.startswith('.env') and filename != '.env.example':
                    continue
                archive.write(path, 'Signal/' + relative.as_posix())
        archive.write(snapshot, 'Signal/data/reviews.db')
    with zipfile.ZipFile(OUTPUT) as archive:
        assert archive.testzip() is None
        assert 'Signal/.env' not in archive.namelist()
        assert 'Signal/frontend/dist/index.html' in archive.namelist()
        assert not any('/workspaces/' in name or name.endswith('/accounts.db') for name in archive.namelist())
        count = len(archive.namelist())
    print(f'{OUTPUT}\n{OUTPUT.stat().st_size / 1024 / 1024:.2f} MB · {count} files · {reviews} reviews · integrity verified')


if __name__ == '__main__':
    package()
