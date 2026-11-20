"""Command line interface:  python -m superstore_pipeline run | validate"""
from __future__ import annotations

import argparse
import json
import sys

from . import extract, validate
from .config import Config
from .runner import run_pipeline


def _print_run(summary: dict) -> None:
    icons = {"success": "OK  ", "failed": "FAIL", "skipped": "SKIP"}
    print(f"run {summary['run_id']}  status={summary['status']}  {summary['duration_s']}s")
    for r in summary["steps"]:
        extra = ""
        d = r.get("detail", {})
        if r["status"] == "failed":
            extra = f"  {d.get('error_type')}: {d.get('error')}"
        elif r["step"] == "validate":
            extra = f"  {d.get('summary', '')}"
        elif r["step"] in ("extract", "mask", "load_staging"):
            extra = f"  rows={d.get('rows')}"
        elif r["step"] == "reconcile":
            extra = f"  sales={d['control_totals']['sales']:,.2f} profit={d['control_totals']['profit']:,.2f}"
        elif r["step"] == "publish":
            extra = f"  marts={len(d.get('marts_exported', []))}"
        print(f"  [{icons[r['status']]}] {r['step']:<13}{r['duration_s']:>7.2f}s{extra}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="superstore-pipeline", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="run the full pipeline")
    run.add_argument("--config", help="path to a pipeline.yml (default: config/pipeline.yml)")
    run.add_argument("--strict-masking", action="store_true",
                     help="fail if MASKING_KEY is not set (recommended outside local development)")
    run.add_argument("--no-export", action="store_true", help="do not write mart CSV exports")
    run.add_argument("--json", action="store_true", help="print the run summary as JSON")

    val = sub.add_parser("validate", help="run only the data-quality checks")
    val.add_argument("--config")

    args = parser.parse_args(argv)
    cfg = Config.load(args.config)

    if args.command == "validate":
        df, _ = extract.extract_orders(cfg.orders_csv)
        report = validate.run_checks(df)
        for c in report.checks:
            flag = "PASS" if c.passed else ("WARN" if c.severity == "warn" else "FAIL")
            print(f"[{flag}] {c.name:<36} {c.failed_rows:>5} rows  {c.description}")
        print(report.summary())
        return 0 if report.ok else 1

    summary = run_pipeline(cfg, strict_masking=args.strict_masking, export=not args.no_export)
    print(json.dumps(summary, indent=2, default=str)) if args.json else _print_run(summary)
    return 0 if summary["status"] == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
