from PyQt5.QtCore import QCoreApplication, QSettings
import sys


def main() -> int:
    lang = (sys.argv[1] if len(sys.argv) > 1 else "en").lower()
    if lang not in ("ru", "en"):
        lang = "en"
    QCoreApplication.setOrganizationName("HeatSim")
    QCoreApplication.setApplicationName("HeatSim")
    s = QSettings()
    s.setValue("ui/language", lang)
    try:
        s.sync()
    except Exception:
        pass
    print(f"Set ui/language={lang}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
