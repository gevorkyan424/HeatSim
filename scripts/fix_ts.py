import re
import sys
from pathlib import Path
import xml.etree.ElementTree as ET
from typing import Any


def fix_ts_text(text: str) -> str:
    # Нормализуем пробелы внутри имён тегов: < context > -> <context>
    patterns = [
        (r"<\s*context\s*>", "<context>"),
        (r"</\s*context\s*>", "</context>"),
        (r"<\s*message\s*>", "<message>"),
        (r"</\s*message\s*>", "</message>"),
        (r"<\s*translation\s*>", "<translation>"),
        (r"</\s*translation\s*>", "</translation>"),
        (r"<\s*name\s*>", "<name>"),
        (r"</\s*name\s*>", "</name>"),
        (r"<\s*TS(\s|>)", r"<TS\1"),
        (r"</\s*TS\s*>", "</TS>"),
        (r"<!\s*DOCTYPE\s*TS\s*>", "<!DOCTYPE TS>"),
        (r"<\s*location(\s)", r"<location\1"),
    ]
    out = text
    for pat, repl in patterns:
        out = re.sub(pat, repl, out)
    # Нормализация XML-сущностей вида & gt; -> &gt; (и аналогичных)
    entity_map = {
        "gt": "&gt;",
        "lt": "&lt;",
        "amp": "&amp;",
        "quot": "&quot;",
        "apos": "&apos;",
    }

    def _ent_sub(m: Any) -> str:
        name: str = str(m.group(1))
        rep = entity_map.get(name)
        if rep is None:
            return str(m.group(0))
        return rep

    out = re.sub(r"&\s*(gt|lt|amp|quot|apos)\s*;", _ent_sub, out)
    return out


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/fix_ts.py <path-to-ts>")
        return 2
    ts_path = Path(sys.argv[1])
    if not ts_path.exists():
        print(f"File not found: {ts_path}")
        return 1
    raw = ts_path.read_text(encoding="utf-8")
    fixed = fix_ts_text(raw)
    # Сохраним резервную копию
    bak_path = ts_path.with_suffix(ts_path.suffix + ".bak")
    bak_path.write_text(raw, encoding="utf-8")
    ts_path.write_text(fixed, encoding="utf-8")
    # Валидация XML
    try:
        ET.fromstring(fixed)
        print("OK: XML parsed successfully after fix.")
        return 0
    except ET.ParseError as e:
        print(f"Warning: XML still not well-formed: {e}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
