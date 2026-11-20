from dataclasses import replace

import duckdb
import pytest

from superstore_pipeline import extract
from superstore_pipeline.config import Config
from superstore_pipeline.runner import run_pipeline


@pytest.fixture(scope="session")
def base_cfg() -> Config:
    return Config.load()


@pytest.fixture(scope="session")
def raw_df(base_cfg):
    df, _ = extract.extract_orders(base_cfg.orders_csv)
    return df


@pytest.fixture()
def tmp_cfg(base_cfg, tmp_path) -> Config:
    """A config that writes every output under a temporary directory."""
    return replace(
        base_cfg,
        duckdb_path=tmp_path / "wh.duckdb",
        marts_dir=tmp_path / "marts",
        run_log=tmp_path / "runs.jsonl",
        dq_report=tmp_path / "dq.json",
    )


@pytest.fixture(scope="session")
def built(base_cfg, tmp_path_factory):
    """Run the whole pipeline once and share the resulting warehouse between tests."""
    tmp = tmp_path_factory.mktemp("built")
    cfg = replace(
        base_cfg,
        duckdb_path=tmp / "wh.duckdb",
        marts_dir=tmp / "marts",
        run_log=tmp / "runs.jsonl",
        dq_report=tmp / "dq.json",
    )
    summary = run_pipeline(cfg)
    assert summary["status"] == "success", summary
    con = duckdb.connect(str(cfg.duckdb_path), read_only=True)
    yield cfg, summary, con
    con.close()
