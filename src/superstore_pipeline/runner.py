"""Pipeline orchestration: ordered steps, structured run log, fail-fast with downstream skipping."""
from __future__ import annotations

import json
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import pandas as pd

from . import extract, mask, validate, warehouse
from .config import Config


@dataclass
class Context:
    """State passed between steps."""
    cfg: Config
    strict_masking: bool = False
    export: bool = True
    raw: pd.DataFrame | None = None
    masked: pd.DataFrame | None = None
    con: duckdb.DuckDBPyConnection | None = None
    quality: validate.QualityReport | None = None
    lineage: dict = field(default_factory=dict)
    masking_report: dict = field(default_factory=dict)


@dataclass
class Step:
    name: str
    fn: Callable[[Context], dict]
    depends_on: tuple[str, ...] = ()


# ---------------------------------------------------------------------------------------------- steps
def step_extract(ctx: Context) -> dict:
    ctx.raw, ctx.lineage = extract.extract_orders(ctx.cfg.orders_csv)
    return {"rows": len(ctx.raw), **ctx.lineage}


def step_validate(ctx: Context) -> dict:
    ctx.quality = validate.run_checks(ctx.raw)
    ctx.cfg.dq_report.parent.mkdir(parents=True, exist_ok=True)
    ctx.cfg.dq_report.write_text(json.dumps(ctx.quality.to_dict(), indent=2))
    if not ctx.quality.ok:
        raise validate.DataQualityError(ctx.quality)
    return {"summary": ctx.quality.summary(),
            "warnings": [f"{c.name}: {c.failed_rows} rows" for c in ctx.quality.warnings]}


def step_mask(ctx: Context) -> dict:
    key = mask.get_key(ctx.cfg.masking_key_env, strict=ctx.strict_masking)
    ctx.masked, ctx.masking_report = mask.mask_orders(ctx.raw, key, ctx.cfg.postal_prefix_len)
    return {"rows": len(ctx.masked), **ctx.masking_report}


def step_load_staging(ctx: Context) -> dict:
    if ctx.cfg.duckdb_path.exists():
        ctx.cfg.duckdb_path.unlink()            # rebuild from scratch: runs are idempotent
    ctx.con = warehouse.connect(ctx.cfg.duckdb_path)
    return {"rows": warehouse.load_staging(ctx.con, ctx.masked), "table": "stg_orders"}


def step_build_models(ctx: Context) -> dict:
    results = warehouse.run_models(ctx.con, ctx.cfg.models_dir)
    return {"models": results}


def step_reconcile(ctx: Context) -> dict:
    actual = warehouse.control_totals(ctx.con)
    problems = validate.reconcile(actual, ctx.cfg.control_totals)
    orphans = warehouse.referential_integrity(ctx.con)
    orphan_total = sum(orphans.values())
    if problems or orphan_total:
        raise RuntimeError(f"reconciliation failed: {problems}; orphan foreign keys: {orphans}")
    return {"control_totals": actual, "orphan_foreign_keys": orphans}


def step_publish(ctx: Context) -> dict:
    # persist run artefacts inside the warehouse too
    ctx.con.register("dq_df", pd.DataFrame([vars(c) for c in ctx.quality.checks]))
    ctx.con.execute("CREATE OR REPLACE TABLE dq_results AS SELECT * FROM dq_df")
    ctx.con.unregister("dq_df")
    marts = warehouse.export_marts(ctx.con, ctx.cfg.marts_dir) if ctx.export else []
    return {"marts_exported": marts}


STEPS: list[Step] = [
    Step("extract", step_extract),
    Step("validate", step_validate, ("extract",)),
    Step("mask", step_mask, ("validate",)),
    Step("load_staging", step_load_staging, ("mask",)),
    Step("build_models", step_build_models, ("load_staging",)),
    Step("reconcile", step_reconcile, ("build_models",)),
    Step("publish", step_publish, ("reconcile",)),
]


# ------------------------------------------------------------------------------------------- runner
def run_pipeline(cfg: Config, *, strict_masking: bool = False, export: bool = True,
                 steps: list[Step] | None = None) -> dict:
    """Run all steps in order. A failed step marks every step that depends on it as `skipped`.

    Every step is appended to a JSONL run log and, on success, to the warehouse `pipeline_runs` table.
    """
    steps = steps or STEPS
    ctx = Context(cfg=cfg, strict_masking=strict_masking, export=export)
    run_id = uuid.uuid4().hex[:12]
    started = datetime.now(UTC)
    log: list[dict] = []
    failed: set[str] = set()

    for step in steps:
        record = {"run_id": run_id, "step": step.name, "started_at": datetime.now(UTC).isoformat()}
        if any(dep in failed for dep in step.depends_on):
            record.update(status="skipped", duration_s=0.0, detail={"reason": "upstream step failed"})
            failed.add(step.name)
        else:
            t0 = time.perf_counter()
            try:
                record["detail"] = step.fn(ctx)
                record["status"] = "success"
            except Exception as exc:                    # noqa: BLE001 - the runner must catch everything
                record.update(status="failed", detail={"error_type": type(exc).__name__, "error": str(exc)})
                failed.add(step.name)
            record["duration_s"] = round(time.perf_counter() - t0, 3)
        log.append(record)

    status = "failed" if failed else "success"
    summary = {"run_id": run_id, "status": status, "started_at": started.isoformat(),
               "duration_s": round(sum(r["duration_s"] for r in log), 3), "steps": log}
    _write_log(cfg.run_log, log)
    _persist_runs(ctx, log)
    if ctx.con is not None:
        ctx.con.close()
    return summary


def _write_log(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, default=str) + "\n")


def _persist_runs(ctx: Context, log: list[dict]) -> None:
    """Best effort: store the run log in the warehouse when it exists (i.e. the load step ran)."""
    if ctx.con is None:
        return
    try:
        df = pd.DataFrame([{
            "run_id": r["run_id"], "step": r["step"], "status": r["status"],
            "started_at": r["started_at"], "duration_s": r["duration_s"],
            "detail": json.dumps(r.get("detail", {}), default=str),
        } for r in log])
        ctx.con.register("runs_df", df)
        ctx.con.execute("CREATE OR REPLACE TABLE pipeline_runs AS SELECT * FROM runs_df")
        ctx.con.unregister("runs_df")
    except duckdb.Error:
        pass
