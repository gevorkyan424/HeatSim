import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtCore import QSettings, QCoreApplication, QTranslator

from interface import MainWindow


def main() -> int:
    # Идентификаторы приложения для QSettings
    QCoreApplication.setOrganizationName("HeatSim")
    QCoreApplication.setApplicationName("HeatSim")
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
    # Чтение последних настроек темы и языка
    settings = QSettings()
    theme = settings.value("ui/theme", "system")
    lang = settings.value("ui/language", "ru")
    # Нормализация значения языка (только ru/en); по умолчанию ru
    try:
        lang_str = str(lang or "ru").lower()
        if lang_str not in ("ru", "en"):
            lang_str = "ru"
            settings.setValue("ui/language", "ru")
        lang = lang_str
    except Exception:
        lang = "ru"
    # Подключение переводчика при наличии .qm
    try:
        tr = QTranslator()
        base_dir = os.path.dirname(os.path.abspath(__file__))
        qm_path = os.path.join(base_dir, "i18n", f"HeatSim_{str(lang)}.qm")
        if os.path.exists(qm_path) and tr.load(qm_path):
            app.installTranslator(tr)
            setattr(app, "_app_translator", tr)
            setattr(app, "_app_translator_lang", str(lang))
        else:
            setattr(app, "_app_translator", None)
            setattr(app, "_app_translator_lang", "")
        # Даже если .qm не найден, оставляем выбранный язык — интерфейс подстроит меню/диалоги фолбэками
    except Exception:
        pass
    window = MainWindow(initial_theme=str(theme), initial_language=str(lang))
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
