"""Pipeline configuration loaded from config/pipeline.yml."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


def find_repo_root(start: Path | None = None) -> Path:
    """Walk up from `start` until a directory containing config/pipeline.yml is found."""
    here = (start or Path(__file__)).resolve()
    for parent in [here, *here.parents]:
        if (parent / "config" / "pipeline.yml").exists():
            return parent
    raise FileNotFoundError("config/pipeline.yml not found in any parent directory")


@dataclass(frozen=True)
class Config:
    root: Path
    orders_csv: Path
    duckdb_path: Path
    models_dir: Path
    marts_dir: Path
    run_log: Path
    dq_report: Path
    masking_key_env: str
    postal_prefix_len: int
    control_totals: dict

    @classmethod
    def load(cls, path: str | Path | None = None, root: Path | None = None) -> Config:
        root = Path(root).resolve() if root else find_repo_root()
        cfg_path = Path(path) if path else root / "config" / "pipeline.yml"
        raw = yaml.safe_load(cfg_path.read_text())

        def rel(p: str) -> Path:
            return (root / p).resolve()

        return cls(
            root=root,
            orders_csv=rel(raw["source"]["orders_csv"]),
            duckdb_path=rel(raw["warehouse"]["duckdb_path"]),
            models_dir=rel(raw["warehouse"]["models_dir"]),
            marts_dir=rel(raw["outputs"]["marts_dir"]),
            run_log=rel(raw["outputs"]["run_log"]),
            dq_report=rel(raw["outputs"]["dq_report"]),
            masking_key_env=raw["masking"]["key_env"],
            postal_prefix_len=int(raw["masking"]["postal_prefix_len"]),
            control_totals=dict(raw["quality"]["control_totals"]),
        )
