import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont

from interface import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet("QGroupBox { font-weight: 700; }")
    window = MainWindow()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
