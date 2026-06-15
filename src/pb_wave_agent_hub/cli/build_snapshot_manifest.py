from __future__ import annotations

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Build a simple snapshot manifest for a snapshot directory.")
    parser.add_argument("--snapshot-glob", required=True, help="For example data/snapshots/month_2026_05/*.json")
    parser.add_argument("--output", required=True, help="Manifest output path.")
    args = parser.parse_args()

    project_dir = Path.cwd()
    snapshot_paths = sorted(project_dir.glob(args.snapshot_glob))
    if not snapshot_paths:
        raise SystemExit(f"no snapshots matched: {args.snapshot_glob}")

    rows = []
    for path in snapshot_paths:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            snapshot_id = raw.get("snapshot_id")
            captured_at_utc = raw.get("captured_at_utc")
            count = len(raw.get("rows") or [])
        else:
            snapshot_id = raw[0].get("snapshot_id") if raw else None
            captured_at_utc = raw[0].get("captured_at_utc") if raw else None
            count = len(raw)
        rows.append(
            {
                "snapshot_id": snapshot_id,
                "captured_at_utc": captured_at_utc,
                "row_count": count,
                "path": str(path),
            }
        )

    payload = {
        "snapshot_glob": args.snapshot_glob,
        "snapshot_count": len(rows),
        "rows": rows,
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
