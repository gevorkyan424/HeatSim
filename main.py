import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont, QIcon

from interface import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet("QGroupBox { font-weight: 700; }")
    # Set application icon if available
    icon_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "assets", "icon.ico"
    )
    if os.path.exists(icon_path):
        try:
            app.setWindowIcon(QIcon(icon_path))
        except Exception:
            pass
    window = MainWindow()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
