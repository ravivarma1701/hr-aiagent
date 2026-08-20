#!/bin/sh
set -e

mkdir -p storage

echo "Running database migrations..."
alembic upgrade head

# scripts/seed.py has no built-in guard against re-seeding an
# already-populated database (it would hit unique-constraint errors on
# employee emails, etc.), so we only run it once, the first time the
# "employees" table is empty -- e.g. a brand-new persistent volume. On
# every later boot against the same volume, this is skipped and whatever
# data already exists (including anything created live during a demo) is
# left alone.
EMPTY=$(python -c "
import sqlite3
try:
    conn = sqlite3.connect('storage/hrms.db')
    count = conn.execute('SELECT COUNT(*) FROM employees').fetchone()[0]
    print(1 if count == 0 else 0)
except sqlite3.OperationalError:
    print(1)
")

if [ "$EMPTY" = "1" ]; then
  echo "Empty database detected -- seeding demo data (accounts, departments, HR policies, ...)..."
  python scripts/seed.py
else
  echo "Existing data found -- skipping seed."
fi

# A single worker: the SQLite file + the in-process ChromaDB client and
# sentence-transformers model are not safely shared across multiple worker
# processes, and this app's traffic level doesn't need more than one.
echo "Starting server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
