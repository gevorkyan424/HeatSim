import os
import sys
from PyQt5.QtCore import QCoreApplication, QSettings, QTranslator


def main() -> int:
    QCoreApplication.setOrganizationName("HeatSim")
    QCoreApplication.setApplicationName("HeatSim")
    s = QSettings()
    lang = s.value("ui/language", "ru")
    theme = s.value("ui/theme", "system")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(base_dir)
    qm_path = os.path.join(root, "i18n", f"HeatSim_{lang}.qm")
    ok = False
    if os.path.exists(qm_path):
        tr = QTranslator()
        ok = tr.load(qm_path)
    print(f"ui/language={lang}")
    print(f"ui/theme={theme}")
    print(f"qm_path={qm_path}")
    print(f"qm_exists={os.path.exists(qm_path)}")
    print(f"qm_load_ok={ok}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
