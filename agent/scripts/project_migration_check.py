"""Explicit-path, read-only project preflight and additive migration verification."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.services.migration_guard import capture_baseline, compare_baseline, project_preflight  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="mode", required=True)
    preflight = commands.add_parser("preflight")
    preflight.add_argument("--erp", type=Path, required=True)
    preflight.add_argument("--brain", type=Path, required=True)
    preflight.add_argument("--output", type=Path)
    capture = commands.add_parser("capture")
    capture.add_argument("--database", type=Path, required=True)
    capture.add_argument("--output", type=Path, required=True)
    compare = commands.add_parser("compare")
    compare.add_argument("--before", type=Path, required=True)
    compare.add_argument("--database", type=Path, required=True)
    compare.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.output and (args.output.exists() or args.output.resolve() in {
            path.resolve() for path in (getattr(args, "erp", None), getattr(args, "brain", None),
                                       getattr(args, "database", None), getattr(args, "before", None)) if path}):
        parser.error("Le rapport exige un nouveau fichier distinct des données")
    if args.mode == "preflight":
        result = project_preflight(args.erp, args.brain)
    elif args.mode == "capture":
        result = capture_baseline(args.database)
    else:
        result = compare_baseline(json.loads(args.before.read_text(encoding="utf-8")), capture_baseline(args.database))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as destination:
            json.dump(result, destination, ensure_ascii=False, indent=2)
            destination.write("\n")
        summary = {"mode": args.mode, "report": str(args.output)}
        if "preserved" in result:
            summary["preserved"] = result["preserved"]
        print(json.dumps(summary, ensure_ascii=False))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("preserved", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
