"""Documentation hygiene: every relative link in the markdown docs must point at a file that exists."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOCS = [
    ROOT / "README.md",
    *sorted((ROOT / "docs").glob("*.md")),
    ROOT / "bi" / "README.md",
    ROOT / "powerbi" / "README.md",
    ROOT / "powerquery" / "README.md",
    ROOT / "warehouse" / "bigquery" / "README.md",
    ROOT / "data" / "README.md",
]
LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)\)|!\[[^\]]*\]\(([^)\s]+)\)")


@pytest.mark.parametrize("doc", DOCS, ids=lambda p: str(p.relative_to(ROOT)))
def test_relative_links_resolve(doc):
    text = re.sub(r"```.*?```", "", doc.read_text(encoding="utf-8"), flags=re.S)   # ignore code blocks
    broken = []
    for m in LINK.finditer(text):
        target = (m.group(1) or m.group(2)).split("#")[0]
        if not target or target.startswith(("http://", "https://", "mailto:")):
            continue
        if not (doc.parent / target).exists():
            broken.append(target)
    assert not broken, f"{doc.name}: broken links {broken}"


def test_status_labels_are_explained_in_readme():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "✅" in text and "🟡" in text and "not run" in text
