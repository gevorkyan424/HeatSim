import shutil
import sys
import site
from pathlib import Path
from typing import List, Set


def candidates() -> List[str]:
    names = [
        "lrelease.exe",
        "lrelease6.exe",
        "lrelease-qt5.exe",
        "lrelease-qt6.exe",
        "pyside6-lrelease.exe",
        "lrelease",
        "pyside6-lrelease",
    ]
    found: List[str] = []
    for n in names:
        p = shutil.which(n)
        if p:
            found.append(p)
    return found


def search_more() -> List[str]:
    roots: List[Path] = []
    # Typical Python-related locations
    for p in [sys.prefix, sys.base_prefix]:
        roots.append(Path(p) / "Scripts")
        roots.append(Path(p) / "Library" / "bin")
    # Site-packages directories
    for sp in site.getsitepackages() + [site.getusersitepackages()]:
        roots.append(Path(sp))
    # Common Qt installation root on Windows
    roots.append(Path("C:/Qt"))
    # De-dup and filter existing
    uniq: List[Path] = []
    seen: Set[Path] = set()
    for r in roots:
        rp = r.resolve()
        if rp in seen or not rp.exists():
            continue
        seen.add(rp)
        uniq.append(rp)
    hits: List[str] = []
    for root in uniq:
        try:
            # bounded depth search: scripts/bin roots direct; for site-packages search recursively but name-filtered
            patterns = ["**/*lrelease*.exe", "**/pyside6-lrelease*.exe"]
            for pat in patterns:
                for f in root.glob(pat):
                    try:
                        if f.is_file():
                            hits.append(str(f))
                    except Exception:
                        pass
        except Exception:
            continue
    return hits


def main() -> int:
    for p in candidates():
        print(p)
        return 0
    # Fallback search
    hits = search_more()
    if hits:
        print(hits[0])
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
