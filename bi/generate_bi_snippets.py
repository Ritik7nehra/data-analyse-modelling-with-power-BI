"""Render bi/generated/metrics_reference.md from bi/metrics.yml.

    python bi/generate_bi_snippets.py
"""
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent


def build() -> str:
    spec = yaml.safe_load((HERE / "metrics.yml").read_text())
    lines = [
        "# Metric reference (generated)",
        "",
        "Generated from `bi/metrics.yml` by `bi/generate_bi_snippets.py`. Do not edit by hand.",
        "",
        f"Source table: `{spec['source_table']}` (Power BI / Fabric table name: `{spec['power_bi_table']}`).",
        "",
        "The **SQL** column is executed and tested. The DAX, Tableau and Looker Studio columns are hand-written",
        "equivalents that have **not** been run in those tools.",
        "",
        "| Metric | Format | SQL (tested) | Power BI (DAX) | Tableau | Looker Studio |",
        "|---|---|---|---|---|---|",
    ]
    for m in spec["metrics"]:
        row = [m["label"], m["format"]] + [f"`{m[k]}`" for k in ("sql", "dax", "tableau", "looker_studio")]
        lines.append("| " + " | ".join(row) + " |")
    lines += ["", "## Definitions", ""]
    lines += [f"- **{m['label']}**: {m['description']}" for m in spec["metrics"]]
    lines += ["", "## Dimensions", "", ", ".join(f"`{d['name']}` ({d['label']})" for d in spec["dimensions"]), ""]
    return "\n".join(lines)


if __name__ == "__main__":
    out = HERE / "generated" / "metrics_reference.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text(build())
    print(f"wrote {out}")
