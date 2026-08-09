#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEMO_DB="$PROJECT_DIR/demo/demo.db"

cd "$PROJECT_DIR"
python scripts/create_demo_db.py --output "$DEMO_DB" --force
export DATABASE_URL="sqlite+pysqlite:///$DEMO_DB"
exec uvicorn app.api:create_app --factory --host 127.0.0.1 --port "${PORT:-8000}"
