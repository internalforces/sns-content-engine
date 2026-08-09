#!/usr/bin/env python3
"""Export one reproducible operations-metrics snapshot as JSON and CSV."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.analytics import append_metrics_csv, collect_operation_metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--days", type=int, default=28, choices=range(1, 91), metavar="1..90")
    parser.add_argument("--output", type=Path, default=Path("operations/metrics-history.csv"))
    args = parser.parse_args()

    metrics = collect_operation_metrics(database_url=args.database_url, days=args.days)
    append_metrics_csv(args.output, metrics)
    print(json.dumps(metrics.as_serializable_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
