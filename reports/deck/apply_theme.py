"""Write the deck's theme colours/name into a pptxgenjs-built .pptx and repair one chart-XML fault.

    python reports/deck/apply_theme.py reports/Superstore_Executive_Deck.pptx

pptxgenjs hard-codes Office's palette, so scheme colours (tx2, bg2, accent1 ...) used by the deck would resolve to
Office blue/orange until the real palette is written into ppt/theme/theme1.xml. The palette below must match THEME in
build_deck.js. It also replaces <c:crossesAt val="autoZero"/> (invalid, makes PowerPoint offer to repair) with the
equivalent <c:crosses val="autoZero"/>.
"""
from __future__ import annotations

import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

NAME = "Superstore Ledger"
COLORS = {
    "dk1": "1B2A2F", "lt1": "FFFFFF", "dk2": "0F4C5C", "lt2": "EAF1F0",
    "accent1": "0F4C5C", "accent2": "E36414", "accent3": "5B8E7D", "accent4": "F4A259", "accent5": "8CB369",
    "accent6": "BC4B51", "hlink": "0F4C5C", "folHlink": "5B8E7D",
}
THEME_PART = "ppt/theme/theme1.xml"


def patch_theme(xml: str) -> str:
    scheme = f'<a:clrScheme name="{NAME}">' + "".join(
        f'<a:{k}><a:srgbClr val="{v}"/></a:{k}>' for k, v in COLORS.items()) + "</a:clrScheme>"
    new, n = re.subn(r"<a:clrScheme\b[\s\S]*?</a:clrScheme>", lambda _: scheme, xml, count=1)
    if n != 1:
        raise SystemExit(f"{THEME_PART} has no <a:clrScheme>; was this deck written by pptxgenjs?")
    return re.sub(r'(<a:(?:theme|fontScheme)\b[^>]*?\bname=")[^"]*"', lambda m: f'{m.group(1)}{NAME}"', new)


def main(path: str) -> None:
    src = Path(path)
    with zipfile.ZipFile(src) as zin:
        if THEME_PART not in zin.namelist():
            raise SystemExit(f"{src} has no {THEME_PART}")
        tmp = Path(tempfile.mkdtemp()) / "out.pptx"
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                if item.is_dir():                      # folder entries are not parts
                    continue
                data = zin.read(item.filename)
                if item.filename == THEME_PART:
                    data = patch_theme(data.decode("utf-8")).encode("utf-8")
                elif item.filename.endswith(".xml") and b'<c:crossesAt val="autoZero"/>' in data:
                    data = data.replace(b'<c:crossesAt val="autoZero"/>', b'<c:crosses val="autoZero"/>')
                zout.writestr(item.filename, data)
    shutil.move(str(tmp), src)
    print(f"theme '{NAME}' applied to {src}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
