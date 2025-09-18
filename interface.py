# interface.py
import os
import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Callable, TypedDict, Any, List, Dict, Optional, Sequence, cast

from PyQt5.QtGui import (
    QFont,
    QPixmap,
    QRegularExpressionValidator,
    QStandardItemModel,
    QStandardItem,
)
from PyQt5.QtCore import (
    Qt,
    QRegularExpression,
    QObject,
    QEvent,
    QModelIndex,
    QSortFilterProxyModel,
    QTimer,
)
from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QRadioButton,
    QButtonGroup,
    QMessageBox,
    QSizePolicy,
    QHeaderView,
    QTableView,
    QFrame,
    QAction,
    QFileDialog,
    QTextEdit,
    QDialog,
    QDialogButtonBox,
)

import logic  # модуль расчётов

LOG_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "app.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

try:
    import openpyxl  # type: ignore
except Exception:
    openpyxl = None
    # Workbook will be created via openpyxl.Workbook() when module is present

# ===================== БАЗА СВОЙСТВ КОМПОНЕНТОВ =====================
COMPONENT_DB = {
    "Вода": (373.0, 4.2, 2.0, 2260.0),
    "Ртуть": (629.9, 0.14, 0.146, 294.0),
    "Этанол": (351.5, 2.44, 1.42, 846.0),
    "Азот": (77.4, 2.04, 1.04, 200.0),
    "Пропан": (231.0, 2.38, 1.67, 356.0),
    "Бутан": (272.7, 2.22, 1.67, 360.0),
    "Бензин": (388.0, 2.20, 1.70, 375.0),
    "Глицерин": (563.0, 2.43, 1.95, 924.0),
    "Фенол": (454.9, 2.10, 1.7, 654.0),
    "Водород": (20.2, 9.7, 14.3, 445.0),
    "Этиловый спирт": (351.5, 2.44, 1.42, 854.0),
    "Свинец": (2022.0, 0.15, 0.13, 871.0),
    "Аммиак": (239.8, 4.70, 2.09, 1370.0),
    "Медь": (2835.0, 0.62, 0.20, 4730.0),
    "Железо": (3135.0, 0.82, 0.45, 6770.0),
    "Алюминий": (2792.0, 1.18, 0.90, 10500.0),
    "Литий": (1615.0, 3.58, 3.58, 20200.0),
    "Графит": (4473.0, float("nan"), 0.71, 35500.0),
    "Диэтиловый эфир": (307.8, 2.19, 1.84, 412.0),
    "Бериллий": (2742.0, 1.82, 1.82, 12700.0),
    "Бор": (4200.0, 2.60, 1.02, 47000.0),
    "Сера": (718.0, 1.75, 0.71, 325.0),
    "Серная кислота": (610.0, 1.38, 1.40, 787.0),
    "Натрий": (1156.0, 1.25, 0.81, 8000.0),
    "Калий": (1032.0, 0.76, 0.75, 9560.0),
    "Хлор": (239.0, 0.48, 0.50, 287.0),
    "Йод": (457.0, 0.37, 0.17, 199.0),
    "Магний": (1363.0, 1.44, 1.02, 8571.0),
    "Кальций": (1757.0, 1.10, 0.65, 6970.0),
    "Цинк": (1180.0, 0.57, 0.52, 1700.0),
    "Олово": (2543.0, 0.30, 0.24, 2960.0),
    "Платина": (4100.0, 0.51, 0.13, 6000.0),
    "Никель": (3003.0, 0.75, 0.46, 6000.0),
    "Бензол": (353.25, 1.74, 1.13, 393.0),
    "Толуол": (383.75, 1.70, 1.13, 351.0),
    "Спирт": (351.52, 2.44, 1.43, 841.0),
}


# ===================== УТИЛИТЫ =====================
def num_edit(read_only: bool = False, fixed_width: int = 150) -> QLineEdit:
    e = QLineEdit()
    e.setAlignment(Qt.AlignRight)
    # initial enabled state will be controlled via set_enabled helper
    e.setEnabled(not read_only)
    e.setPlaceholderText("0.0")
    e.setFixedWidth(fixed_width)
    if not e.isEnabled():
        e.setStyleSheet("background:#f3f3f3;")
    rx = QRegularExpression(r"^$|^[0-9]{1,10}([.,][0-9]{0,5})?$")
    e.setValidator(QRegularExpressionValidator(rx))

    def fix_number():
        t = e.text().strip()
        if not t:
            return
        if t.endswith(",") or t.endswith("."):
            t += "00"
        sep = max(t.rfind(","), t.rfind("."))
        if sep != -1:
            i, f = t[:sep], t[sep + 1 :]
            t = i[:10] + t[sep] + (f or "00")[:5]
        else:
            t = t[:10]
        e.blockSignals(True)
        e.setText(t)
        e.blockSignals(False)

    e.editingFinished.connect(fix_number)
    return e


def to_float(text: str) -> float:
    try:
        return float(text.replace(",", "."))
    except Exception:
        return 0.0


def format_num(value: float, fmt: str = ".6g") -> str:
    try:
        v = float(value)
        # special-case exact zero for clearer display
        if abs(v) < 1e-12:
            return "0.0"
        return f"{v:{fmt}}"
    except Exception:
        return "0.0"


def set_read_only(le: QLineEdit, ro: bool) -> None:
    # kept for backward-compat but delegate to new enabled semantics
    set_enabled(le, not ro)


def set_enabled(le: QLineEdit, enabled: bool) -> None:
    le.setEnabled(enabled)
    if not enabled:
        # disabled fields: gray background
        le.setStyleSheet("background:#f3f3f3;")
    else:
        # enabled fields: clear style (caller may set manual highlight)
        le.setStyleSheet("")
    # keep associated lock button in sync without triggering its signals
    btn = getattr(le, "_lock_btn", None)
    if btn is not None:
        # update text only; button click will set enabled state explicitly
        btn.setText("🔒" if not enabled else "🔓")


def lock_button_for(line_edit: QLineEdit) -> QPushButton:
    btn = QPushButton()
    btn.setFixedSize(22, 22)
    btn.setToolTip("Заблокировать/разблокировать поле")

    def on_click():
        # if the field is enabled -> lock it; otherwise unlock
        if line_edit.isEnabled():
            # lock
            set_enabled(line_edit, False)
            setattr(line_edit, "_just_unlocked", False)
            # remove any temporary handler if present
            h = getattr(line_edit, "_just_unlocked_handler", None)
            if h is not None:
                try:
                    line_edit.textEdited.disconnect(h)
                except Exception:
                    pass
                try:
                    delattr(line_edit, "_just_unlocked_handler")
                except Exception:
                    pass
        else:
            # unlock — prepare flags so that an immediate editingFinished (without user typing)
            # won't auto-disable, but a real typed edit followed by editingFinished will.
            set_enabled(line_edit, True)
            try:
                # waiting flag indicates we recently unlocked and expect possible typing
                setattr(line_edit, "_just_unlocked_waiting", True)
                # clear typed flag
                if hasattr(line_edit, "_just_unlocked_typed"):
                    delattr(line_edit, "_just_unlocked_typed")
            except Exception:
                pass

            def _on_text_edited(_text: str) -> None:
                # mark that the user actually typed
                try:
                    setattr(line_edit, "_just_unlocked_typed", True)
                finally:
                    try:
                        line_edit.textEdited.disconnect(_on_text_edited)
                    except Exception:
                        pass
                    try:
                        if hasattr(line_edit, "_just_unlocked_handler"):
                            delattr(line_edit, "_just_unlocked_handler")
                    except Exception:
                        pass

            # store handler reference for cleanup and connect
            try:
                setattr(line_edit, "_just_unlocked_handler", _on_text_edited)
                line_edit.textEdited.connect(_on_text_edited)
            except Exception:
                try:
                    if hasattr(line_edit, "_just_unlocked_handler"):
                        delattr(line_edit, "_just_unlocked_handler")
                except Exception:
                    pass

    btn.clicked.connect(on_click)
    # initial text reflects current state
    btn.setText("🔒" if not line_edit.isEnabled() else "🔓")
    # attach for external sync
    setattr(line_edit, "_lock_btn", btn)
    return btn


def auto_disable_handler(line_edit: QLineEdit) -> Callable[[], None]:
    def _handler() -> None:
        # if we just unlocked for editing, only skip auto-disable when no typing occurred
        if getattr(line_edit, "_just_unlocked_waiting", False):
            # if user typed, proceed to disable and clear flags
            if getattr(line_edit, "_just_unlocked_typed", False):
                try:
                    delattr(line_edit, "_just_unlocked_typed")
                except Exception:
                    pass
                try:
                    delattr(line_edit, "_just_unlocked_waiting")
                except Exception:
                    pass
                # allow auto-disable to proceed
            else:
                # user didn't type yet — skip disabling for now
                return
        set_enabled(line_edit, False)

    return _handler


# ===================== TYPE DEFINITIONS =====================
class FlowData(TypedDict):
    t_in: float
    t_out: float
    m: float
    p: float


class MixRow(TypedDict):
    name: str
    share: float
    tb: float
    cf: float
    cp: float
    rf: float


class CalcResult(TypedDict, total=False):
    q: float
    t_out_plus: float
    sigma: float
    k: float


# ===================== ПАНЕЛЬ ПОТОКОВ =====================
class FlowPanel:
    def __init__(self, title: str, sign: str):
        self.box = QGroupBox(title)
        grid = QGridLayout(self.box)
        self.t_in = num_edit()
        self.t_out = num_edit()
        self.m = num_edit()
        self.p = num_edit()

        # per-field lock buttons for some inputs (auto-disable after editing)
        self.t_in_lock = lock_button_for(self.t_in)
        self.t_out_lock = lock_button_for(self.t_out)
        self.m_lock = lock_button_for(self.m)
        self.p_lock = lock_button_for(self.p)

        row = 0
        grid.addWidget(
            QLabel(
                f"Температура на входе ({title.lower()}), T<sub>{sign}</sub><sup>in</sup> [ K ]"
            ),
            row,
            0,
        )
        h0 = QHBoxLayout()
        h0.setContentsMargins(0, 0, 0, 0)
        h0.addWidget(self.t_in)
        h0.addWidget(self.t_in_lock)
        grid.addLayout(h0, row, 1)

        row += 1
        grid.addWidget(
            QLabel(
                f"Температура на выходе ({title.lower()}), T<sub>{sign}</sub><sup>out</sup> [ K ]"
            ),
            row,
            0,
        )
        h1 = QHBoxLayout()
        h1.setContentsMargins(0, 0, 0, 0)
        h1.addWidget(self.t_out)
        h1.addWidget(self.t_out_lock)
        grid.addLayout(h1, row, 1)

        row += 1
        grid.addWidget(
            QLabel(f"Расход потока ({title.lower()}), g<sub>{sign}</sub> [ кг/сек ]"),
            row,
            0,
        )
        h2 = QHBoxLayout()
        h2.setContentsMargins(0, 0, 0, 0)
        h2.addWidget(self.m)
        h2.addWidget(self.m_lock)
        grid.addLayout(h2, row, 1)

        row += 1
        grid.addWidget(
            QLabel(f"Давление ({title.lower()}), P<sub>{sign}</sub> [ кг/м² ]"), row, 0
        )
        h3 = QHBoxLayout()
        h3.setContentsMargins(0, 0, 0, 0)
        h3.addWidget(self.p)
        h3.addWidget(self.p_lock)
        grid.addLayout(h3, row, 1)

        self.box.setFixedSize(700, 180)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)

        # auto-disable these fields after editingFinished (user can re-enable with lock button)
        try:
            self.t_in.editingFinished.connect(auto_disable_handler(self.t_in))
            self.t_out.editingFinished.connect(auto_disable_handler(self.t_out))
            self.m.editingFinished.connect(auto_disable_handler(self.m))
            self.p.editingFinished.connect(auto_disable_handler(self.p))
        except Exception:
            pass

    def widget(self) -> QGroupBox:
        return self.box

    def to_dict(self) -> FlowData:
        return FlowData(
            {
                "t_in": to_float(self.t_in.text()),
                "t_out": to_float(self.t_out.text()),
                "m": to_float(self.m.text()),
                "p": to_float(self.p.text()),
            }
        )


# ===================== DELETE FILTER =====================
class KeyDeleteFilter(QObject):
    def __init__(self, callback: Callable[[], None]):
        super().__init__()
        self.callback: Callable[[], None] = callback

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # type: ignore[override]
        if (
            event.type() == QEvent.KeyPress
            and getattr(event, "key", lambda: None)() == Qt.Key_Delete
        ):
            self.callback()
            return True
        return super().eventFilter(obj, event)


# ===================== МОДЕЛЬ СМЕСИ =====================
class MixModel(QStandardItemModel):
    COL_NAME, COL_SHARE, COL_TB, COL_CF, COL_CP, COL_RF = range(6)
    HEADERS = [
        "Компонент",
        "Доля",
        "Tb, K",
        "C_f, кДж/кг·K",
        "C_p, кДж/кг·K",
        "r_f, кДж/кг",
    ]
    SORT_ROLE = Qt.UserRole + 1

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(0, 6, parent)
        for i, h in enumerate(self.HEADERS):
            self.setHeaderData(i, Qt.Horizontal, h, role=Qt.DisplayRole)

    def _num_item(self, value: float) -> QStandardItem:
        it = QStandardItem(f"{value:.6g}")
        it.setEditable(False)
        it.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        it.setData(value, self.SORT_ROLE)
        return it

    def _set_num(self, row: int, col: int, value: float) -> None:
        idx = self.index(row, col)
        self.setData(idx, f"{value:.6g}", Qt.DisplayRole)
        self.setData(idx, value, self.SORT_ROLE)

    def add_or_update(
        self, name: str, share: float, tb: float, cf: float, cp: float, rf: float
    ) -> int:
        row = self._row_by_name(name)
        if row >= 0:
            idx_share = self.index(row, self.COL_SHARE)
            cur_share = float(self.data(idx_share, Qt.DisplayRole).replace(",", "."))
            new_share = cur_share + share
            self.setData(idx_share, f"{new_share:.6g}", Qt.DisplayRole)
            self.setData(idx_share, new_share, self.SORT_ROLE)
            self._set_num(row, self.COL_TB, tb)
            self._set_num(row, self.COL_CF, cf)
            self._set_num(row, self.COL_CP, cp)
            self._set_num(row, self.COL_RF, rf)
            return row
        r = self.rowCount()
        self.insertRow(r)
        name_item = QStandardItem(name)
        name_item.setEditable(False)
        name_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        self.setItem(r, self.COL_NAME, name_item)
        self.setItem(r, self.COL_SHARE, self._num_item(share))
        self.setItem(r, self.COL_TB, self._num_item(tb))
        self.setItem(r, self.COL_CF, self._num_item(cf))
        self.setItem(r, self.COL_CP, self._num_item(cp))
        self.setItem(r, self.COL_RF, self._num_item(rf))
        return r

    def _row_by_name(self, name: str) -> int:
        for r in range(self.rowCount()):
            if self.data(self.index(r, self.COL_NAME), Qt.DisplayRole) == name:
                return r
        return -1

    def remove_rows(self, rows: List[int]) -> None:
        for r in sorted(rows, reverse=True):
            self.removeRow(r)

    def rows_as_dicts(self) -> List[MixRow]:
        out: List[MixRow] = []
        for r in range(self.rowCount()):

            def v(c: int):
                txt = self.data(self.index(r, c), Qt.DisplayRole) or "0"
                return float(txt.replace(",", ".")) if c != self.COL_NAME else txt

            out.append(
                cast(
                    MixRow,
                    {
                        "name": v(self.COL_NAME),
                        "share": v(self.COL_SHARE),
                        "tb": v(self.COL_TB),
                        "cf": v(self.COL_CF),
                        "cp": v(self.COL_CP),
                        "rf": v(self.COL_RF),
                    },
                )
            )
        return out


# ===================== ПАНЕЛЬ СМЕСИ =====================
class MixPanel:
    def __init__(self, title: str, is_hot: bool, export_path: str):
        self.is_hot = is_hot
        self.export_path = export_path
        self.box = QGroupBox(f"Смесь компонентов {title.lower()}")
        self.box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        v = QVBoxLayout(self.box)

        # верхняя линия управления
        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(6)
        self.comp = QComboBox()
        self.comp.addItems(sorted(COMPONENT_DB.keys()))
        self.comp.setFixedWidth(200)
        self.comp.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.share = num_edit(fixed_width=100)
        self.share.editingFinished.connect(self.validate_share_max1)
        self.sum_field = num_edit(read_only=True, fixed_width=100)
        self.sum_field.setText("0.0")
        self.add_btn = QPushButton("Добавить")
        top.addWidget(self.comp)
        top.addStretch(1)
        top.addWidget(QLabel("Доля"))
        top.addWidget(self.share)
        top.addSpacing(8)
        # Перестановка: сначала кнопка Добавить, затем поле суммы
        top.addWidget(self.add_btn)
        top.addSpacing(8)
        top.addWidget(QLabel("Сумма"))
        top.addWidget(self.sum_field)
        v.addLayout(top)

        # источник параметров
        src = QHBoxLayout()
        src.setContentsMargins(0, 0, 0, 0)
        src.setSpacing(8)
        self.rb_group = QButtonGroup(self.box)
        self.rb_db = QRadioButton(
            "Взять параметры из справочника NIST Chemistry WebBook"
        )
        self.rb_manual = QRadioButton("Ввести параметры вручную")
        self.rb_group.addButton(self.rb_db, 0)
        self.rb_group.addButton(self.rb_manual, 1)
        self.rb_db.setChecked(True)
        src.addWidget(self.rb_db)
        src.addWidget(self.rb_manual)
        src.addStretch(1)
        v.addLayout(src)

        # параметры
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(6)
        self.tb = num_edit(read_only=True)
        self.cf = num_edit(read_only=True)
        self.cp = num_edit(read_only=True)
        self.rf = num_edit(read_only=True)
        grid.addWidget(QLabel("Температура кипения, Tb  [ K ]"), 0, 0)
        grid.addWidget(self.tb, 0, 1)
        grid.addWidget(
            QLabel("Удельная теплоёмкость жидкости, C_f  [ кДж/кг·K ]"), 1, 0
        )
        grid.addWidget(self.cf, 1, 1)
        grid.addWidget(QLabel("Удельная теплоёмкость пара, C_p  [ кДж/кг·K ]"), 2, 0)
        grid.addWidget(self.cp, 2, 1)
        grid.addWidget(
            QLabel("Скрытая теплота фазового перехода, r_f  [ кДж/кг ]"), 3, 0
        )
        grid.addWidget(self.rf, 3, 1)
        v.addLayout(grid)

        # таблица
        self.model = MixModel()
        self.proxy = QSortFilterProxyModel()
        self.proxy.setSourceModel(self.model)
        self.proxy.setSortRole(MixModel.SORT_ROLE)
        self.proxy.setDynamicSortFilter(True)
        self.view = QTableView()
        self.view.setModel(self.proxy)
        self.view.setSortingEnabled(False)
        self.view.horizontalHeader().setVisible(True)
        self.view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.view.verticalHeader().setVisible(False)
        self.view.setSelectionBehavior(QTableView.SelectRows)
        self.view.setSelectionMode(QTableView.ExtendedSelection)
        v.addWidget(self.view)

        # шрифты
        header_font = QFont("Consolas", 9, QFont.Bold)
        self.view.horizontalHeader().setFont(header_font)
        try:
            hh = self.view.horizontalHeader()
            hh_font = hh.font()
            hh_font.setBold(True)
            hh.setFont(hh_font)
        except Exception:
            pass
        table_font = QFont("Consolas", 9)
        self.view.setFont(table_font)
        self.view.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        try:
            self.view.setStyleSheet("QHeaderView::section { font-weight: 700; }")
        except Exception:
            pass

        # Delete + двойной клик
        self._del_filter = KeyDeleteFilter(self.delete_selected_rows)
        self.view.installEventFilter(self._del_filter)
        self.view.doubleClicked.connect(self.on_double_click)

        # автоэкспорт и пересчёт
        self.model.dataChanged.connect(self._on_model_changed)
        self.model.rowsInserted.connect(self._on_model_changed)
        self.model.rowsRemoved.connect(self._on_model_changed)

        # сигналы
        self.add_btn.clicked.connect(self.on_add)
        self.rb_db.toggled.connect(self.on_mode_change)
        self.comp.currentTextChanged.connect(self.fill_from_db)
        self.fill_from_db(self.comp.currentText())

        # ensure these fields don't carry stale _lock_btn attributes
        for w in (self.share, self.tb, self.cf, self.cp, self.rf, self.sum_field):
            if hasattr(w, "_lock_btn"):
                delattr(w, "_lock_btn")

        self.update_share_hint()
        self._resort()

    def widget(self) -> QGroupBox:
        return self.box

    # сортировка по Tb автоматически
    def _resort(self) -> None:
        col = MixModel.COL_TB
        order = Qt.DescendingOrder if self.is_hot else Qt.AscendingOrder
        self.proxy.sort(col, order)

    def _on_model_changed(self, *args: Any) -> None:
        self.update_share_hint()
        self._resort()
        self._auto_export_csv()

    def _auto_export_csv(self) -> None:
        try:
            with open(self.export_path, "w", newline="", encoding="utf-8-sig") as f:
                wr = csv.writer(f, delimiter=";")
                wr.writerow(
                    [
                        "Компонент",
                        "Доля",
                        "Tb, K",
                        "C_f, кДж/кг·K",
                        "C_p, кДж/кг·K",
                        "r_f, кДж/кг",
                    ]
                )
                for r in range(self.model.rowCount()):
                    row = []
                    for c in range(self.model.columnCount()):
                        txt = (
                            self.model.data(self.model.index(r, c), Qt.DisplayRole)
                            or ""
                        )
                        if c != 0:
                            txt = txt.replace(".", ",")
                        row.append(txt)
                    wr.writerow(cast(List[str], row))
        except Exception:
            pass

    def current_sum(self) -> float:
        s = 0.0
        for r in range(self.model.rowCount()):
            txt = (
                self.model.data(self.model.index(r, MixModel.COL_SHARE), Qt.DisplayRole)
                or "0"
            )
            s += float(txt.replace(",", "."))
        return s

    def update_share_hint(self) -> None:
        total = self.current_sum()
        remaining = max(0.0, 1.0 - total)
        self.share.setPlaceholderText(f"≤ {remaining:.5f}")
        self.sum_field.setText(f"{total:.5f}")
        try:
            if abs(total - 1.0) <= 1e-4:
                # зелёный при корректной сумме
                self.sum_field.setStyleSheet("QLineEdit { background:#d9f7d9; }")
            else:
                # красный пока не 1.0
                self.sum_field.setStyleSheet("QLineEdit { background:#ffd6d6; }")
        except Exception:
            pass

    def on_mode_change(self, _checked: bool) -> None:
        manual = self.rb_manual.isChecked()
        for w in (self.tb, self.cf, self.cp, self.rf):
            set_enabled(w, manual)
        if self.rb_db.isChecked():
            self.fill_from_db(self.comp.currentText())

        try:
            if manual:
                highlight_style = "QLineEdit { background: #fff7d6; }"
                for w in (self.tb, self.cf, self.cp, self.rf):
                    w.setStyleSheet(highlight_style)
            else:
                for w in (self.tb, self.cf, self.cp, self.rf):
                    if not w.isEnabled():
                        w.setStyleSheet("background:#f3f3f3;")
                    else:
                        w.setStyleSheet("")
        except Exception:
            pass

    def fill_from_db(self, name: str) -> None:
        props = COMPONENT_DB.get(name)
        if props:
            tb, cf, cp, rf = props
            self.tb.setText(f"{tb}")
            self.cf.setText(f"{cf}")
            self.cp.setText(f"{cp}")
            self.rf.setText(f"{rf}")
        else:
            for w in (self.tb, self.cf, self.cp, self.rf):
                w.setText("0.0")

    def validate_share_max1(self) -> None:
        val = to_float(self.share.text())
        if val > 1.0:
            QMessageBox.warning(
                self.box,
                "Доля",
                "Доля компонента не может превышать 1. Повторите ввод.",
            )
            self.share.clear()
            self.share.setFocus()

    def on_add(self) -> None:
        remaining = max(0.0, 1.0 - self.current_sum())
        share_val = to_float(self.share.text())
        if share_val > 1.0 + 1e-12:
            QMessageBox.warning(
                self.box,
                "Доля",
                "Доля компонента не может превышать 1. Повторите ввод.",
            )
            self.share.clear()
            self.share.setFocus()
            return
        if share_val <= 0.0:
            QMessageBox.warning(self.box, "Доля", "Введите положительную долю > 0.")
            return
        if share_val > remaining + 1e-12:
            if remaining <= 0.0:
                QMessageBox.warning(
                    self.box, "Сумма долей", "Сумма долей уже равна 1.0."
                )
                return
            share_val = remaining
            self.share.setText(f"{share_val:.5f}")

        name = self.comp.currentText()
        if self.rb_db.isChecked():
            tb, cf, cp, rf = COMPONENT_DB[name]
        else:
            tb, cf, cp, rf = (
                to_float(self.tb.text()),
                to_float(self.cf.text()),
                to_float(self.cp.text()),
                to_float(self.rf.text()),
            )
        self.model.add_or_update(name, share_val, tb, cf, cp, rf)
        self.share.clear()

    def ask_delete(self, count: int) -> bool:
        box = QMessageBox(self.box)
        box.setIcon(QMessageBox.Question)
        box.setWindowTitle("Удаление")
        box.setText(f"Удалить {count} строку(и)?")
        yes_btn = box.addButton("Да", QMessageBox.AcceptRole)
        no_btn = box.addButton("Нет", QMessageBox.RejectRole)
        box.setDefaultButton(no_btn)  # по умолчанию Нет
        box.exec_()
        return box.clickedButton() is yes_btn

    def selected_source_rows(self) -> List[int]:
        rows: List[int] = []
        for proxy_index in self.view.selectionModel().selectedRows():
            src_idx = self.proxy.mapToSource(proxy_index)
            rows.append(src_idx.row())
        return sorted(set(rows), reverse=True)

    def delete_selected_rows(self) -> None:
        rows = self.selected_source_rows()
        if not rows:
            QMessageBox.information(
                self.box, "Удаление", "Выберите строку(и) для удаления."
            )
            return
        if not self.ask_delete(len(rows)):
            return
        self.model.remove_rows(rows)

    def on_double_click(self, index: QModelIndex) -> None:
        if not index.isValid():
            return
        if not self.ask_delete(1):
            return
        self.model.removeRow(self.proxy.mapToSource(index).row())

    def mix_rows(self) -> List[MixRow]:
        return self.model.rows_as_dicts()


# ===================== ПАНЕЛЬ ГИДРОДИНАМИКИ =====================
class HydroPanel(QGroupBox):
    def __init__(
        self, title: str = "Гидродинамика потоков", parent: Optional[QWidget] = None
    ):
        super().__init__(title, parent)
        base = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "assets", "images"
        )
        self._images = {
            "mix_mix": os.path.join(base, "one.png"),
            "parallel": os.path.join(base, "two.png"),
            "mix_cold_disp_hot": os.path.join(base, "three.png"),
            "mix_hot_disp_cold": os.path.join(base, "four.png"),
            "counter": os.path.join(base, "five.png"),
        }
        root = QHBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)
        left = QVBoxLayout()
        right = QVBoxLayout()
        left.setContentsMargins(4, 4, 4, 4)
        right.setContentsMargins(4, 4, 4, 4)
        root.addLayout(left)
        root.addLayout(right)
        root.setStretch(0, 0)
        root.setStretch(1, 0)

        self.rb_mix_mix = QRadioButton("Смешение - смешение")
        self.rb_parallel = QRadioButton("Вытеснение - вытеснение (прямоток)")
        self.rb_mix_cold = QRadioButton("Смешение (хол.) - вытеснение (гор.)")
        self.rb_mix_hot = QRadioButton("Смешение (гор.) - вытеснение (хол.)")
        self.rb_counter = QRadioButton("Вытеснение - вытеснение (противоток)")
        for rb in (
            self.rb_mix_mix,
            self.rb_parallel,
            self.rb_mix_cold,
            self.rb_mix_hot,
            self.rb_counter,
        ):
            left.addWidget(rb)
        left.addStretch(1)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setFixedSize(350, 175)
        self.image_label.setFrameShape(QFrame.Box)
        self.image_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        right.addWidget(self.image_label, 0, Qt.AlignTop | Qt.AlignHCenter)

        def _on_rb_mix_mix_toggled(on: bool) -> None:
            if on:
                self._set_mode("mix_mix")

        def _on_rb_parallel_toggled(on: bool) -> None:
            if on:
                self._set_mode("parallel")

        def _on_rb_mix_cold_toggled(on: bool) -> None:
            if on:
                self._set_mode("mix_cold_disp_hot")

        def _on_rb_mix_hot_toggled(on: bool) -> None:
            if on:
                self._set_mode("mix_hot_disp_cold")

        def _on_rb_counter_toggled(on: bool) -> None:
            if on:
                self._set_mode("counter")

        self.rb_mix_mix.toggled.connect(_on_rb_mix_mix_toggled)
        self.rb_parallel.toggled.connect(_on_rb_parallel_toggled)
        self.rb_mix_cold.toggled.connect(_on_rb_mix_cold_toggled)
        self.rb_mix_hot.toggled.connect(_on_rb_mix_hot_toggled)
        self.rb_counter.toggled.connect(_on_rb_counter_toggled)

        self.rb_mix_mix.setChecked(True)
        self._set_mode("mix_mix")

    def current_schema(self) -> str:
        """Возвращает идентификатор схемы (Schema1..Schema5) согласно выбранной радиокнопке."""
        if self.rb_mix_mix.isChecked():
            return "Schema1"
        if self.rb_parallel.isChecked():
            return "Schema2"
        if self.rb_mix_cold.isChecked():
            return "Schema3"
        if self.rb_mix_hot.isChecked():
            return "Schema4"
        if self.rb_counter.isChecked():
            return "Schema5"
        return "Schema1"

    def _set_mode(self, key: str) -> None:
        pix = QPixmap(self._images.get(key, ""))
        if pix.isNull():
            self.image_label.setText("Нет изображения")
            self.image_label.setPixmap(QPixmap())
            return
        self.image_label.setPixmap(
            pix.scaled(
                self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
        )

    def resizeEvent(self, e: QEvent) -> None:  # type: ignore[override]
        super().resizeEvent(e)  # type: ignore[arg-type]
        if self.rb_mix_mix.isChecked():
            self._set_mode("mix_mix")
        elif self.rb_parallel.isChecked():
            self._set_mode("parallel")
        elif self.rb_mix_cold.isChecked():
            self._set_mode("mix_cold_disp_hot")
        elif self.rb_mix_hot.isChecked():
            self._set_mode("mix_hot_disp_cold")
        elif self.rb_counter.isChecked():
            self._set_mode("counter")


# ===================== ПАНЕЛЬ ВЫХОДНЫХ ПАРАМЕТРОВ =====================
class OutputPanel(QGroupBox):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("Параметры теплообменника", parent)
        g = QGridLayout(self)
        self.q = num_edit(read_only=False, fixed_width=120)
        self.q_lock = lock_button_for(self.q)
        self.sigma = num_edit(read_only=True, fixed_width=120)
        self.k = num_edit(read_only=True, fixed_width=120)
        # стартовые значения
        self.sigma.setText("0.0")
        set_enabled(self.sigma, False)
        self.k.setText("0.0")
        set_enabled(self.k, False)
        g.addWidget(QLabel("Тепловая нагрузка, Q [кВт]"), 0, 0)
        hq = QHBoxLayout()
        hq.setContentsMargins(0, 0, 0, 0)
        hq.addWidget(self.q)
        hq.addWidget(self.q_lock)
        g.addLayout(hq, 0, 1)
        g.addWidget(QLabel("Производство энтропии, σ [кВт/К]"), 1, 0)
        g.addWidget(self.sigma, 1, 1)
        g.addWidget(QLabel("Коэффициент теплопередачи, K [кВт/К]"), 2, 0)
        g.addWidget(self.k, 2, 1)
        # Removed schema_label (schema info now only in status bar)
        # remove stale lock attributes if any
        for w in (self.sigma, self.k):
            if hasattr(w, "_lock_btn"):
                delattr(w, "_lock_btn")
        # auto-disable Q after editingFinished
        try:
            self.q.editingFinished.connect(auto_disable_handler(self.q))
        except Exception:
            pass

    def clear_values(self) -> None:
        for w in (self.q,):
            w.clear()
        # сохранить sigma/k как read-only 0.0
        self.sigma.setText("0.0")
        set_enabled(self.sigma, False)
        self.k.setText("0.0")
        set_enabled(self.k, False)

    # schema label removed


# ===================== ГЛАВНОЕ ОКНО =====================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # flag to indicate we are currently importing data (suppress full on_calc triggers)
        self._importing = False
        # after importing, suppress full sigma/K calculation on schema toggle until user presses Calculate
        self._suppress_full_calc_after_import = False
        # track changes after import to show recalc button
        self._post_import_changed = False
        self.setWindowTitle("Двухпоточный теплообмен")
        self.setFixedSize(1600, 1050)
        # статусная строка
        self.status = self.statusBar()
        try:
            self.status.showMessage("Готово")
        except Exception:
            pass
        # флаг: было ли явное нажатие кнопки Вычислить после последнего изменения схемы/сброса
        self._explicit_calc_done = False
        self._results_stale = False

        # File menu: Import/Export inputs (JSON)
        try:
            file_menu = self.menuBar().addMenu("Файл")
            imp_act = QAction("Импорт входных данных...", self)
            exp_act = QAction("Экспорт входных данных...", self)
            imp_xlsx = QAction("Импорт из Excel (.xlsx)...", self)
            exp_xlsx = QAction("Экспорт в Excel (.xlsx)...", self)
            file_menu.addAction(imp_act)
            file_menu.addAction(exp_act)
            file_menu.addAction(imp_xlsx)
            file_menu.addAction(exp_xlsx)
            imp_act.triggered.connect(self.import_inputs)  # type: ignore[call-arg]
            exp_act.triggered.connect(self.export_inputs)  # type: ignore[call-arg]
            imp_xlsx.triggered.connect(self.import_inputs_xlsx)  # type: ignore[call-arg]
            exp_xlsx.triggered.connect(self.export_inputs_xlsx)  # type: ignore[call-arg]
            # --- Меню помощи ---
            help_menu = self.menuBar().addMenu("Помощь")
            act_help = QAction("Справка", self)
            act_logs = QAction("Логи", self)
            act_about = QAction("О программе", self)
            act_license = QAction("Лицензионное соглашение", self)
            help_menu.addAction(act_help)
            help_menu.addAction(act_logs)
            help_menu.addSeparator()
            # Add license as a submenu item under Help
            help_menu.addAction(act_license)
            help_menu.addAction(act_about)
            act_help.triggered.connect(self.show_help_dialog)
            act_logs.triggered.connect(self.show_logs_dialog)
            act_license.triggered.connect(self.show_license_dialog)
            act_about.triggered.connect(self.show_about_dialog)
        except Exception as e:
            logger.exception("Ошибка создания меню: %s", e)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout()
        central.setLayout(layout)

        # потоки
        row1 = QHBoxLayout()
        layout.addLayout(row1)
        self.cold_panel = FlowPanel("Холодный поток", sign="−")
        self.hot_panel = FlowPanel("Горячий поток", sign="+")
        row1.addWidget(self.cold_panel.widget())
        row1.addWidget(self.hot_panel.widget())

        # смеси
        row2 = QHBoxLayout()
        layout.addLayout(row2)
        self.cold_mix = MixPanel(
            "холодного потока",
            is_hot=False,
            export_path=os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "data",
                "csv",
                "cold_mix.csv",
            ),
        )
        self.hot_mix = MixPanel(
            "горячего потока",
            is_hot=True,
            export_path=os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "data", "csv", "hot_mix.csv"
            ),
        )
        row2.addWidget(self.cold_mix.widget())
        row2.addWidget(self.hot_mix.widget())

        # connect mix model changes to update button state and attempt minimal auto-calc
        try:
            self.cold_mix.model.dataChanged.connect(self._on_mix_changed)  # type: ignore[call-arg]
            self.cold_mix.model.rowsInserted.connect(self._on_mix_changed)  # type: ignore[call-arg]
            self.cold_mix.model.rowsRemoved.connect(self._on_mix_changed)  # type: ignore[call-arg]
            self.hot_mix.model.dataChanged.connect(self._on_mix_changed)  # type: ignore[call-arg]
            self.hot_mix.model.rowsInserted.connect(self._on_mix_changed)  # type: ignore[call-arg]
            self.hot_mix.model.rowsRemoved.connect(self._on_mix_changed)  # type: ignore[call-arg]
        except Exception:
            pass

        # гидродинамика + правый столбец (OutputPanel + кнопки)
        row3 = QHBoxLayout()
        row3.setSpacing(12)
        layout.addLayout(row3)
        self.hydro = HydroPanel()
        row3.addWidget(self.hydro, 1)

        # правая колонка: OutputPanel + кнопки (чуть шире)
        right_col = QVBoxLayout()
        right_col.setContentsMargins(0, 0, 0, 0)
        right_col.setSpacing(8)
        self.out_panel = OutputPanel()
        self.out_panel.setMinimumWidth(750)
        right_col.addWidget(self.out_panel)
        btns = QVBoxLayout()
        btns.setContentsMargins(0, 0, 0, 0)
        btns.setSpacing(8)
        self.calc_btn = QPushButton("Вычислить")
        self.reset_btn = QPushButton("Очистить параметры")
        self.calc_btn.setMinimumHeight(36)
        self.reset_btn.setMinimumHeight(36)
        self.analysis_btn = QPushButton("Провести анализ")
        self.analysis_btn.setToolTip("Провести анализ изменяя доли компонентов потоков")
        self.analysis_btn.setMinimumHeight(36)
        self.recalc_btn = QPushButton("Перерасчёт")
        self.recalc_btn.setToolTip("Пересчитать после изменений")
        self.recalc_btn.setMinimumHeight(36)
        self.recalc_btn.hide()
        btns.addWidget(self.calc_btn)
        btns.addWidget(self.recalc_btn)
        btns.addWidget(self.analysis_btn)
        btns.addWidget(self.reset_btn)
        right_col.addLayout(btns)
        # таймер мигания для кнопки перерасчёта
        from PyQt5.QtCore import QTimer as _QTimer

        self._recalc_blink_state = False

        def _blink_recalc():
            try:
                if not self.recalc_btn.isVisible():
                    # вернуть стандартный стиль
                    self.recalc_btn.setStyleSheet("")
                    return
                self._recalc_blink_state = not getattr(
                    self, "_recalc_blink_state", False
                )
                if self._recalc_blink_state:
                    self.recalc_btn.setStyleSheet(
                        "QPushButton { background:#ff4d4f; color:white; font-weight:bold; }"
                    )
                else:
                    self.recalc_btn.setStyleSheet(
                        "QPushButton { background:#ffcccc; color:#800; font-weight:bold; }"
                    )
            except Exception:
                pass

        self._recalc_blink_timer = _QTimer(self)
        self._recalc_blink_timer.timeout.connect(_blink_recalc)  # type: ignore
        self._recalc_blink_timer.start(700)
        right_col.addStretch(1)
        row3.addLayout(right_col, 0)

        # связи
        try:
            # Explicit user click should clear import suppression and run full calc
            self.calc_btn.clicked.connect(self._on_calc_button_clicked)
        except Exception:
            pass
        try:
            self.recalc_btn.clicked.connect(self._on_recalc_clicked)
        except Exception:
            pass
        try:
            self.reset_btn.clicked.connect(self.on_reset)
        except Exception:
            pass
        try:
            self.analysis_btn.clicked.connect(self.open_analysis_window)
        except Exception:
            pass
        # автопересчёт при смене схемы если есть пред. результат
        try:
            for rb in (
                self.hydro.rb_mix_mix,
                self.hydro.rb_parallel,
                self.hydro.rb_mix_cold,
                self.hydro.rb_mix_hot,
                self.hydro.rb_counter,
            ):
                rb.toggled.connect(self._on_schema_changed)  # type: ignore[call-arg]
        except Exception:
            pass
        # взаимная блокировка: ввод Q блокирует T+out и наоборот
        try:
            # используем editingFinished — расчёт выполняется после завершения ввода
            self.out_panel.q.editingFinished.connect(self._on_q_edit_finished)  # type: ignore[call-arg]
            self.hot_panel.t_out.editingFinished.connect(
                self._on_tplus_out_edit_finished  # type: ignore[call-arg]
            )
        except Exception:
            pass
        # Подключим auto-calc при завершении ввода основных входных полей
        try:
            for w in (
                self.cold_panel.t_in,
                self.cold_panel.t_out,
                self.cold_panel.m,
                self.hot_panel.t_in,
                self.hot_panel.t_out,
                self.hot_panel.m,
            ):
                w.editingFinished.connect(self._normalize_input)
        except Exception:
            pass
        # Also trigger auto-calc when mixtures change (components/dolya edited or rows changed)
        # Automatic recalculation on every mix change was removed to avoid noisy updates.

        # update calc button appearance when inputs change
        try:
            widgets_and_models = [
                self.cold_panel.t_in,
                self.cold_panel.t_out,
                self.cold_panel.m,
                self.hot_panel.t_in,
                self.hot_panel.t_out,
                self.hot_panel.m,
                self.out_panel.q,
            ]
            for w in widgets_and_models:
                # connect editingFinished if available
                if hasattr(w, "editingFinished"):
                    try:
                        w.editingFinished.connect(self._update_calc_button_state)  # type: ignore[call-arg]
                    except Exception:
                        pass
                # connect dataChanged if available (models)
                if hasattr(w, "dataChanged"):
                    try:
                        w.dataChanged.connect(self._update_calc_button_state)  # type: ignore[call-arg]
                    except Exception:
                        pass
        except Exception:
            pass

        # initial update of button state
        self._update_calc_button_state()

        # Подключим слежение за изменениями полей потоков для пометки устаревания результатов
        try:

            def _mark_change():
                try:
                    self._mark_stale_results()
                except Exception:
                    pass

            for w in (
                self.cold_panel.t_in,
                self.cold_panel.t_out,
                self.cold_panel.m,
                self.cold_panel.p,
                self.hot_panel.t_in,
                self.hot_panel.t_out,
                self.hot_panel.m,
                self.hot_panel.p,
                self.out_panel.q,
            ):
                try:
                    w.editingFinished.connect(_mark_change)  # type: ignore
                except Exception:
                    pass
        except Exception:
            pass

        # Снять стартовый фокус с поля T_in холодного потока (курсор не должен мигать там при запуске)
        try:
            QTimer.singleShot(0, self._remove_initial_focus)  # type: ignore[arg-type]
        except Exception:
            pass

    def _on_mix_changed(self, *args: Any) -> None:
        """Handler for mix model changes: update calc button and attempt minimal auto-calc."""
        try:
            self._update_calc_button_state()
        except Exception:
            pass
        try:
            self._auto_calc_minimal()
        except Exception:
            pass
        # Любое изменение смеси после первого явного вычисления делает результаты устаревшими
        try:
            if getattr(self, "_explicit_calc_done", False):
                self._results_stale = True
                if self._mix_valid(self.cold_mix.mix_rows()) and self._mix_valid(
                    self.hot_mix.mix_rows()
                ):
                    self.recalc_btn.show()
        except Exception:
            pass

    def _remove_initial_focus(self) -> None:
        """Убирает фокус с поля температуры на входе холодного потока при старте."""
        try:
            self.cold_panel.t_in.clearFocus()
            # Переводим фокус на главное окно (ничто не редактируется по умолчанию)
            self.setFocus(Qt.OtherFocusReason)
        except Exception:
            pass

    def _on_calc_button_clicked(self) -> None:
        """Handler for explicit user click on Calculate: clear import suppression and run full calculation."""
        try:
            self._suppress_full_calc_after_import = False
        except Exception:
            pass
        try:
            self.on_calc()
        except Exception:
            pass
        try:
            self._explicit_calc_done = True
            self._results_stale = False
            self.recalc_btn.hide()
            try:
                self.status.showMessage("Вычисления выполнены успешно", 4000)
            except Exception:
                pass
        except Exception:
            pass

    def _on_schema_changed(self, checked: bool) -> None:
        """Called when hydro schema radio buttons toggle.
        Always trigger a recalculation when the schema changes (user expects σ/K to update).
        """
        try:
            if not checked:
                return
            # Если ещё не было явного нажатия Вычислить, то ограничиваемся минимальным авторасчётом
            if (
                (not getattr(self, "_explicit_calc_done", False))
                or getattr(self, "_importing", False)
                or getattr(self, "_suppress_full_calc_after_import", False)
            ):
                try:
                    self._try_auto_calc()
                except Exception:
                    pass
                return
            # Полный пересчёт только после явного вычисления
            try:
                self.on_calc()
            except Exception:
                pass
        except Exception:
            pass

    def _gather_inputs_for_export(self) -> Dict[str, Any]:
        """Collect current inputs into a JSON-serializable dict."""
        try:
            cold = self.cold_panel.to_dict()
        except Exception:
            cold = {}
        try:
            hot = self.hot_panel.to_dict()
        except Exception:
            hot = {}
        try:
            cold_mix = self.cold_mix.mix_rows()
        except Exception:
            cold_mix = []
        try:
            hot_mix = self.hot_mix.mix_rows()
        except Exception:
            hot_mix = []
        schema = None
        try:
            schema = self.hydro.current_schema()
        except Exception:
            schema = None
        q_txt = None
        try:
            q_txt = self.out_panel.q.text().strip()
        except Exception:
            q_txt = None
        return {
            "cold": cold,
            "hot": hot,
            "cold_mix": cold_mix,
            "hot_mix": hot_mix,
            "schema": schema,
            "q": q_txt,
        }

    def export_inputs(self) -> None:
        """Export inputs to a CSV file that can be opened in Excel.
        Format: a single CSV with a leading `section` column. Sections:
        - flow_cold: columns t_in,t_out,m,p
        - flow_hot: columns t_in,t_out,m,p
        - mix_cold / mix_hot: columns name,share,tb,cf,cp,rf
        """
        try:
            path, _ = QFileDialog.getSaveFileName(
                self, "Экспорт входных данных", "", "CSV Files (*.csv);;All Files (*)"
            )
            if not path:
                return
            data = self._gather_inputs_for_export()

            # Helper to protect Excel from auto-formatting values (dates/numbers)
            def protect_for_excel(val: Any) -> str:
                s = str(val)
                if not s:
                    return ""
                # Common date-like patterns with / or - or mm/dd or dd-mm etc.
                if any(ch in s for ch in ("/", "-")) and any(c.isdigit() for c in s):
                    return "'" + s
                # Leading zeros or long numeric strings -> keep as text
                if s.startswith("0") and len(s) > 1 and s[1].isdigit():
                    return "'" + s
                return s

            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f, delimiter=";")
                # flows
                w.writerow(["section", "t_in", "t_out", "m", "p"])
                w.writerow(["type", "K", "K", "kg/s", "kg/m^2"])
                cold = cast(Dict[str, Any], data.get("cold") or {})
                hot = cast(Dict[str, Any], data.get("hot") or {})
                w.writerow(
                    [
                        "flow_cold",
                        protect_for_excel(cold.get("t_in", "")),
                        protect_for_excel(cold.get("t_out", "")),
                        protect_for_excel(cold.get("m", "")),
                        protect_for_excel(cold.get("p", "")),
                    ]
                )
                w.writerow(
                    [
                        "flow_hot",
                        protect_for_excel(hot.get("t_in", "")),
                        protect_for_excel(hot.get("t_out", "")),
                        protect_for_excel(hot.get("m", "")),
                        protect_for_excel(hot.get("p", "")),
                    ]
                )
                # mixes
                w.writerow([])
                w.writerow(["section", "name", "share", "tb", "cf", "cp", "rf"])
                w.writerow(
                    ["type", "str", "fraction", "K", "kJ/kg*K", "kJ/kg*K", "kJ/kg"]
                )

                def _nz(v: Any) -> str:
                    try:
                        if v in (None, ""):
                            return ""
                        if isinstance(v, (int, float)) and float(v) == 0.0:
                            return ""
                        s = str(v)
                        if s.replace(".", "", 1).isdigit() and float(s) == 0.0:
                            return ""
                        return protect_for_excel(v)
                    except Exception:
                        return ""

                for r in data.get("cold_mix", []):
                    w.writerow(
                        [
                            "mix_cold",
                            protect_for_excel(r.get("name", "")),
                            _nz(r.get("share", "")),
                            _nz(r.get("tb", "")),
                            _nz(r.get("cf", "")),
                            _nz(r.get("cp", "")),
                            _nz(r.get("rf", "")),
                        ]
                    )
                for r in data.get("hot_mix", []):
                    w.writerow(
                        [
                            "mix_hot",
                            protect_for_excel(r.get("name", "")),
                            _nz(r.get("share", "")),
                            _nz(r.get("tb", "")),
                            _nz(r.get("cf", "")),
                            _nz(r.get("cp", "")),
                            _nz(r.get("rf", "")),
                        ]
                    )
                # schema and q
                w.writerow([])
                w.writerow(["meta", "schema", data.get("schema", "")])
                w.writerow(["meta", "q", data.get("q", "")])
        except Exception as e:
            QMessageBox.warning(self, "Ошибка экспорта", str(e))

    def export_inputs_xlsx(self) -> None:
        """Export inputs to an .xlsx workbook with separate sheets for flows and mixes."""
        if openpyxl is None:
            QMessageBox.warning(
                self,
                "Excel экспорт",
                "Требуется пакет openpyxl. Установите его в окружение.",
            )
            return
        try:
            path, _ = QFileDialog.getSaveFileName(
                self, "Экспорт в Excel", "", "Excel Files (*.xlsx);;All Files (*)"
            )
            if not path:
                return
            data = self._gather_inputs_for_export()
            # create workbook via module to satisfy static checkers
            wb = openpyxl.Workbook()
            # Flows sheet
            ws1 = cast(Any, wb.active)
            ws1.title = "flows"
            ws1.append(["section", "t_in", "t_out", "m", "p"])
            cold = cast(Dict[str, Any], data.get("cold") or {})
            hot = cast(Dict[str, Any], data.get("hot") or {})
            ws1.append(
                [
                    "flow_cold",
                    cold.get("t_in", ""),
                    cold.get("t_out", ""),
                    cold.get("m", ""),
                    cold.get("p", ""),
                ]
            )
            ws1.append(
                [
                    "flow_hot",
                    hot.get("t_in", ""),
                    hot.get("t_out", ""),
                    hot.get("m", ""),
                    hot.get("p", ""),
                ]
            )
            # mixes
            ws2 = wb.create_sheet("mix_cold")
            ws2.append(["name", "share", "tb", "cf", "cp", "rf"])
            for r in data.get("cold_mix", []):
                ws2.append(
                    [
                        r.get("name", ""),
                        r.get("share", ""),
                        r.get("tb", ""),
                        r.get("cf", ""),
                        r.get("cp", ""),
                        r.get("rf", ""),
                    ]
                )
            ws3 = wb.create_sheet("mix_hot")
            ws3.append(["name", "share", "tb", "cf", "cp", "rf"])
            for r in data.get("hot_mix", []):
                ws3.append(
                    [
                        r.get("name", ""),
                        r.get("share", ""),
                        r.get("tb", ""),
                        r.get("cf", ""),
                        r.get("cp", ""),
                        r.get("rf", ""),
                    ]
                )
            # meta
            ws_meta = wb.create_sheet("meta")
            ws_meta.append(["schema", data.get("schema", "")])
            ws_meta.append(["q", data.get("q", "")])
            wb.save(path)
        except Exception as e:
            QMessageBox.warning(self, "Ошибка экспорта Excel", str(e))

    def import_inputs_xlsx(self) -> None:
        """Import inputs from an .xlsx workbook created by `export_inputs_xlsx`."""
        if openpyxl is None:
            QMessageBox.warning(
                self,
                "Excel импорт",
                "Требуется пакет openpyxl. Установите его в окружение.",
            )
            return
        try:
            self._importing = True
            path, _ = QFileDialog.getOpenFileName(
                self, "Импорт из Excel", "", "Excel Files (*.xlsx);;All Files (*)"
            )
            if not path:
                return
            wb = openpyxl.load_workbook(path, data_only=True)
            assert openpyxl is not None
            # flows
            if "flows" in wb.sheetnames:
                ws = cast(Any, wb["flows"])
                rows = list(ws.values)
                # expect header then two rows
                if len(rows) >= 3:
                    fc = rows[1]
                    fh = rows[2]
                    # safe extraction from tuples that may have variable length
                    from typing import Optional, Sequence

                    def safe_get(
                        cell_tuple: Optional[Sequence[Any]], idx: int, default: str = ""
                    ) -> str:
                        try:
                            if not cell_tuple or len(cell_tuple) <= idx:
                                return default
                            v = cell_tuple[idx]
                            return "" if v is None else str(v)
                        except Exception:
                            return default

                    self.cold_panel.t_in.setText(safe_get(fc, 1))
                    self.cold_panel.t_out.setText(safe_get(fc, 2))
                    self.cold_panel.m.setText(safe_get(fc, 3))
                    self.cold_panel.p.setText(safe_get(fc, 4))

                    self.hot_panel.t_in.setText(safe_get(fh, 1))
                    self.hot_panel.t_out.setText(safe_get(fh, 2))
                    self.hot_panel.m.setText(safe_get(fh, 3))
                    self.hot_panel.p.setText(safe_get(fh, 4))
            # mixes
            for name, target in (
                ("mix_cold", self.cold_mix),
                ("mix_hot", self.hot_mix),
            ):
                if name in wb.sheetnames:
                    try:
                        ws = cast(Any, wb[name])
                        rows = list(ws.values)[1:]
                        if target.model.rowCount() > 0:
                            target.model.removeRows(0, target.model.rowCount())

                        def cell_to_float(val: Any) -> float:
                            try:
                                if val is None:
                                    return 0.0
                                return float(val)
                            except Exception:
                                return 0.0

                        def cell_to_str(val: Any) -> str:
                            try:
                                if val is None:
                                    return ""
                                return str(val)
                            except Exception:
                                return ""

                        import re as _re

                        _date_res = [
                            _re.compile(r"^\d{4}[-/]\d{2}[-/]\d{2}$"),
                            _re.compile(r"^\d{2}[-./]\d{2}[-./]\d{4}$"),
                        ]

                        def _is_bad_share(raw: Any, numeric: float) -> bool:
                            try:
                                if numeric == 0.0:
                                    return True
                                if raw is None:
                                    return False
                                s = str(raw).strip()
                                if _re.search(r"[A-Za-zА-Яа-я]", s):
                                    return True
                                for rg in _date_res:
                                    if rg.match(s):
                                        return True
                                return False
                            except Exception:
                                return True

                        for row in rows:
                            try:
                                nm = cell_to_str(row[0]) if row and len(row) > 0 else ""
                                raw_share = row[1] if row and len(row) > 1 else None
                                share = cell_to_float(raw_share)
                                if _is_bad_share(raw_share, share):
                                    continue
                                tb = (
                                    cell_to_float(row[2])
                                    if row and len(row) > 2
                                    else 0.0
                                )
                                cf = (
                                    cell_to_float(row[3])
                                    if row and len(row) > 3
                                    else 0.0
                                )
                                cp = (
                                    cell_to_float(row[4])
                                    if row and len(row) > 4
                                    else 0.0
                                )
                                rf = (
                                    cell_to_float(row[5])
                                    if row and len(row) > 5
                                    else 0.0
                                )
                                target.model.add_or_update(nm, share, tb, cf, cp, rf)
                            except Exception:
                                pass
                    except Exception:
                        pass
            # meta
            if "meta" in wb.sheetnames:
                try:
                    ws = wb["meta"]
                    rows = list(ws.values)
                    for r in rows:
                        if not r or len(r) == 0:
                            continue
                        if len(r) > 0 and r[0] == "schema":
                            schema_val = r[1] if len(r) > 1 else None
                            if schema_val:
                                if schema_val == "Schema1":
                                    self.hydro.rb_mix_mix.setChecked(True)
                                elif schema_val == "Schema2":
                                    self.hydro.rb_parallel.setChecked(True)
                                elif schema_val == "Schema3":
                                    self.hydro.rb_mix_cold.setChecked(True)
                                elif schema_val == "Schema4":
                                    self.hydro.rb_mix_hot.setChecked(True)
                                elif schema_val == "Schema5":
                                    self.hydro.rb_counter.setChecked(True)
                        if len(r) > 0 and r[0] == "q":
                            try:
                                if len(r) > 1:
                                    self.out_panel.q.setText(str(r[1] or ""))
                            except Exception:
                                pass
                except Exception:
                    pass
            try:
                self._try_auto_calc()
                self._update_calc_button_state()
            except Exception:
                pass
            try:
                self._suppress_full_calc_after_import = True
            except Exception:
                pass
            try:
                self._post_import_changed = False
                self.recalc_btn.hide()
                self._lock_imported_fields()
            except Exception:
                pass
        except Exception as e:
            QMessageBox.warning(self, "Ошибка импорта Excel", str(e))
        finally:
            try:
                self._importing = False
            except Exception:
                pass

    def import_inputs(self) -> None:
        """Import inputs from a CSV file with the format written by export_inputs().
        During import only minimal auto-fill is performed (t_out or q). Full sigma/K
        calculation is not executed; user should press "Вычислить" to compute σ и K.
        """
        import re

        date_regexes = [
            re.compile(r"^\d{4}[-/]\d{2}[-/]\d{2}$"),  # YYYY-MM-DD or YYYY/MM/DD
            re.compile(
                r"^\d{2}[-./]\d{2}[-./]\d{4}$"
            ),  # DD-MM-YYYY / DD.MM.YYYY / DD/MM/YYYY
        ]

        def _is_invalid_token(tok: str) -> bool:
            t = tok.strip()
            if not t:
                return False
            # letters present
            if re.search(r"[A-Za-zА-Яа-я]", t):
                return True
            # date like patterns
            for rg in date_regexes:
                if rg.match(t):
                    return True
            return False

        flows: Dict[str, Dict[str, str]] = {"flow_cold": {}, "flow_hot": {}}
        cold_mix: List[Dict[str, Any]] = []
        hot_mix: List[Dict[str, Any]] = []
        schema_val: Optional[str] = None
        q_val: Optional[str] = None
        try:
            self._importing = True
            path, _ = QFileDialog.getOpenFileName(
                self, "Импорт входных данных", "", "CSV Files (*.csv);;All Files (*)"
            )
            if not path:
                return
            with open(path, "r", encoding="utf-8-sig") as f:
                rdr = csv.reader(f, delimiter=";")
                for row in rdr:
                    if not row:
                        continue
                    first = row[0].strip()
                    if first.lower() == "section":
                        continue
                    if first in ("flow_cold", "flow_hot"):
                        # strip leading apostrophe inserted to protect Excel-format
                        def strip_protect(x: str) -> str:
                            if x.startswith("'"):
                                return x[1:]
                            return x

                        val_t_in = strip_protect(row[1]) if len(row) > 1 else ""
                        val_t_out = strip_protect(row[2]) if len(row) > 2 else ""
                        val_m = strip_protect(row[3]) if len(row) > 3 else ""
                        val_p = strip_protect(row[4]) if len(row) > 4 else ""
                        flows[first]["t_in"] = (
                            "" if _is_invalid_token(val_t_in) else val_t_in
                        )
                        flows[first]["t_out"] = (
                            "" if _is_invalid_token(val_t_out) else val_t_out
                        )
                        flows[first]["m"] = "" if _is_invalid_token(val_m) else val_m
                        flows[first]["p"] = "" if _is_invalid_token(val_p) else val_p
                        continue
                    if first in ("mix_cold", "mix_hot"):
                        name = row[1] if len(row) > 1 else ""
                        share = row[2] if len(row) > 2 else "0"
                        tb = row[3] if len(row) > 3 else "0"
                        cf = row[4] if len(row) > 4 else "0"
                        cp = row[5] if len(row) > 5 else "0"
                        rf = row[6] if len(row) > 6 else "0"
                        # если числовые поля не валидны (слово/дата) – делаем их пустыми чтобы fallback -> 0.0
                        for var_name, raw in [
                            ("share", share),
                            ("tb", tb),
                            ("cf", cf),
                            ("cp", cp),
                            ("rf", rf),
                        ]:
                            if _is_invalid_token(raw):
                                if var_name == "share":
                                    share = ""
                                elif var_name == "tb":
                                    tb = ""
                                elif var_name == "cf":
                                    cf = ""
                                elif var_name == "cp":
                                    cp = ""
                                elif var_name == "rf":
                                    rf = ""
                        # проверка доли: если не число или 0 -> пропускаем компонент
                        share_is_valid = False
                        try:
                            share_val_tmp = (
                                float(share.replace(",", ".")) if share.strip() else 0.0
                            )
                            if share_val_tmp != 0.0:
                                share_is_valid = True
                        except Exception:
                            share_is_valid = False
                        if not share_is_valid:
                            continue
                        try:
                            share_f = float(share.replace(",", "."))
                            tb_f = float(tb.replace(",", "."))
                            cf_f = float(cf.replace(",", "."))
                            cp_f = float(cp.replace(",", "."))
                            rf_f = float(rf.replace(",", "."))
                            rec = {
                                "name": name,
                                "share": share_f,
                                "tb": tb_f,
                                "cf": cf_f,
                                "cp": cp_f,
                                "rf": rf_f,
                            }
                        except Exception:
                            # любое исключение при парсинге -> полностью пропускаем компонент
                            continue
                        if first == "mix_cold":
                            cold_mix.append(rec)
                        else:
                            hot_mix.append(rec)
                        continue
                    if first == "meta":
                        key = row[1] if len(row) > 1 else ""
                        val = row[2] if len(row) > 2 else ""
                        if key == "schema":
                            schema_val = val
                        elif key == "q":
                            q_val = val

            # populate flows
            fc = flows.get("flow_cold", {})
            if fc:
                self.cold_panel.t_in.setText(str(fc.get("t_in", "")))
                self.cold_panel.t_out.setText(str(fc.get("t_out", "")))
                self.cold_panel.m.setText(str(fc.get("m", "")))
                self.cold_panel.p.setText(str(fc.get("p", "")))
            fh = flows.get("flow_hot", {})
            if fh:
                self.hot_panel.t_in.setText(str(fh.get("t_in", "")))
                self.hot_panel.t_out.setText(str(fh.get("t_out", "")))
                self.hot_panel.m.setText(str(fh.get("m", "")))
                self.hot_panel.p.setText(str(fh.get("p", "")))

            # replace mixes
            if self.cold_mix.model.rowCount() > 0:
                self.cold_mix.model.removeRows(0, self.cold_mix.model.rowCount())
            for r in cold_mix:
                try:
                    self.cold_mix.model.add_or_update(
                        r.get("name", ""),
                        float(r.get("share", 0.0) or 0.0),
                        float(r.get("tb", 0.0) or 0.0),
                        float(r.get("cf", 0.0) or 0.0),
                        float(r.get("cp", 0.0) or 0.0),
                        float(r.get("rf", 0.0) or 0.0),
                    )
                except Exception:
                    pass
            if self.hot_mix.model.rowCount() > 0:
                self.hot_mix.model.removeRows(0, self.hot_mix.model.rowCount())
            for r in hot_mix:
                try:
                    self.hot_mix.model.add_or_update(
                        r.get("name", ""),
                        float(r.get("share", 0.0) or 0.0),
                        float(r.get("tb", 0.0) or 0.0),
                        float(r.get("cf", 0.0) or 0.0),
                        float(r.get("cp", 0.0) or 0.0),
                        float(r.get("rf", 0.0) or 0.0),
                    )
                except Exception:
                    pass

            # set schema and q if present
            if schema_val:
                if schema_val == "Schema1":
                    self.hydro.rb_mix_mix.setChecked(True)
                elif schema_val == "Schema2":
                    self.hydro.rb_parallel.setChecked(True)
                elif schema_val == "Schema3":
                    self.hydro.rb_mix_cold.setChecked(True)
                elif schema_val == "Schema4":
                    self.hydro.rb_mix_hot.setChecked(True)
                elif schema_val == "Schema5":
                    self.hydro.rb_counter.setChecked(True)
            if q_val is not None:
                self.out_panel.q.setText(str(q_val))

            # normalize and attempt minimal auto-calc
            try:
                self._try_auto_calc()
                self._update_calc_button_state()
            except Exception:
                pass
            # suppress full sigma/K calculation on subsequent schema toggles until user confirms
            try:
                self._suppress_full_calc_after_import = True
            except Exception:
                pass
            try:
                self._post_import_changed = False
                self.recalc_btn.hide()
                self._lock_imported_fields()
            except Exception:
                pass
        except Exception as e:
            QMessageBox.warning(self, "Ошибка импорта", str(e))
        finally:
            try:
                self._importing = False
            except Exception:
                pass

    def _can_compute_sigma_k(self) -> bool:
        """Return True if we have enough validated inputs to compute sigma and k."""
        try:
            cold = self.cold_panel.to_dict()
            hot = self.hot_panel.to_dict()
            cold_mix = self.cold_mix.mix_rows()
            hot_mix = self.hot_mix.mix_rows()

            # require Q present
            if not self.out_panel.q.text().strip():
                return False

            # require both streams to have t_in and t_out and m and valid mixes
            cold_ok = (
                bool(cold.get("t_in"))
                and bool(cold.get("t_out"))
                and bool(cold.get("m"))
                and self._mix_valid(cold_mix)
            )
            hot_ok = (
                bool(hot.get("t_in"))
                and bool(hot.get("t_out"))
                and bool(hot.get("m"))
                and self._mix_valid(hot_mix)
            )
            return cold_ok and hot_ok
        except Exception:
            return False

    @staticmethod
    def _mix_valid(mix: Sequence[MixRow]) -> bool:
        try:
            if not mix:
                return False
            s = sum(float(item.get("share", 0.0)) for item in mix)
            return abs(s - 1.0) <= 1e-3
        except Exception:
            return False

    def _update_calc_button_state(self) -> None:
        """Highlight `self.calc_btn` when sigma/k can be computed by pressing it."""
        try:
            ready = self._can_compute_sigma_k()
            if ready:
                # highlight: yellow background and bold
                self.calc_btn.setStyleSheet("background: #ffec8b; font-weight: 700;")
            else:
                self.calc_btn.setStyleSheet("")
        except Exception:
            pass

    # --- блокировка полей ---
    def _on_q_changed(self) -> None:
        has_q = self.out_panel.q.text().strip() != ""
        # when Q has value, disable T_out (hot)
        set_enabled(self.hot_panel.t_out, not has_q)

    def _on_tplus_out_changed(self) -> None:
        has_tout = self.hot_panel.t_out.text().strip() != ""
        # when T_out has value, disable Q
        set_enabled(self.out_panel.q, not has_tout)

    def _on_q_edit_finished(self) -> None:
        # при завершении ввода Q — блокируем T+out и попытка вычислить T_out автоматически
        try:
            has_q = self.out_panel.q.text().strip() != ""
            set_enabled(self.hot_panel.t_out, not has_q)
            if has_q:
                # вызовем calculate и если вернётся t_out_plus — заполним
                cold = self.cold_panel.to_dict()
                hot = self.hot_panel.to_dict()
                cold_mix = self.cold_mix.mix_rows()
                hot_mix = self.hot_mix.mix_rows()
                q_val = to_float(self.out_panel.q.text())
                res = getattr(logic, "calculate", None)
                if callable(res):
                    ans = res(
                        cold=cold,
                        hot=hot,
                        cold_mix=cold_mix,
                        hot_mix=hot_mix,
                        q=q_val,
                        schema=self.hydro.current_schema(),
                    )
                    ans = cast(Dict[str, Any], ans)
                    ans_dict = ans
                    if ans_dict and "t_out_plus" in ans_dict:
                        # временно блокируем сигналы при записи
                        self.hot_panel.t_out.blockSignals(True)
                        self.hot_panel.t_out.setText(f"{ans_dict['t_out_plus']:.6g}")
                        self.hot_panel.t_out.blockSignals(False)
                        try:
                            self._update_calc_button_state()
                        except Exception:
                            pass
        except Exception:
            pass

    def _on_tplus_out_edit_finished(self) -> None:
        # при завершении ввода T+out — блокируем Q и попытка вычислить Q автоматически
        try:
            has_tout = self.hot_panel.t_out.text().strip() != ""
            set_enabled(self.out_panel.q, not has_tout)
            if has_tout:
                cold = self.cold_panel.to_dict()
                hot = self.hot_panel.to_dict()
                cold_mix = self.cold_mix.mix_rows()
                hot_mix = self.hot_mix.mix_rows()
                q_val = to_float(self.out_panel.q.text())
                res = getattr(logic, "calculate", None)
                if callable(res):
                    ans = res(
                        cold=cold,
                        hot=hot,
                        cold_mix=cold_mix,
                        hot_mix=hot_mix,
                        q=q_val,
                        schema=self.hydro.current_schema(),
                    )
                    ans = cast(Dict[str, Any], ans)
                    ans_dict = ans
                    if ans_dict and "q" in ans_dict:
                        self.out_panel.q.blockSignals(True)
                        self.out_panel.q.setText(f"{ans_dict['q']:.6g}")
                        self.out_panel.q.blockSignals(False)
                        try:
                            self._update_calc_button_state()
                        except Exception:
                            pass
        except Exception:
            pass

    def on_calc(self) -> None:
        # If suppression is active (import just happened), ignore programmatic calls.
        if getattr(self, "_suppress_full_calc_after_import", False):
            return
        cold = self.cold_panel.to_dict()
        hot = self.hot_panel.to_dict()
        cold_mix = self.cold_mix.mix_rows()
        hot_mix = self.hot_mix.mix_rows()
        q_val = to_float(self.out_panel.q.text())
        schema = self.hydro.current_schema()

        try:
            res = getattr(logic, "calculate", None)
            if callable(res):
                ans = res(
                    cold=cold,
                    hot=hot,
                    cold_mix=cold_mix,
                    hot_mix=hot_mix,
                    q=q_val,
                    schema=schema,
                )
                ans = cast(Dict[str, Any], ans)
                if ans:
                    # safely extract numeric/string values from ans
                    try:
                        sigma_val = (
                            float(ans.get("sigma", 0.0))
                            if ans.get("sigma") is not None
                            else 0.0
                        )
                    except Exception:
                        sigma_val = 0.0
                    try:
                        k_val = (
                            float(ans.get("k", 0.0))
                            if ans.get("k") is not None
                            else 0.0
                        )
                    except Exception:
                        k_val = 0.0
                    if sigma_val:
                        self.out_panel.sigma.setText(format_num(sigma_val))
                        set_enabled(self.out_panel.sigma, False)
                    if k_val:
                        self.out_panel.k.setText(format_num(k_val))
                        set_enabled(self.out_panel.k, False)

                    # статус (не использовать слово "Schema" в выводе)
                    schema_display = schema
                    contact = ""
                    q_show = q_val
                    s_show = 0.0
                    try:
                        k_src = str(ans.get("k_source", ""))
                        contact = str(ans.get("contact_type", ""))
                        q_show = float(ans.get("q", q_val) or q_val)
                        k_show = k_val
                        s_show = sigma_val
                        schema_display = str(ans.get("schema", schema))
                        msg = f"{schema_display}  contact={contact or '-'}  k_source={k_src or '-'}  Q={q_show:.4g}  K={k_show:.4g}  σ={s_show:.4g}"
                        self.status.showMessage(msg)
                    except Exception:
                        pass
                    set_enabled(self.out_panel.k, False)
                    # Если σ посчитана, но K отсутствует, попробуем ещё раз выполнить расчёт (возможно
                    # теперь доступны дополнительные данные после записи t_out или q) и получить K.
                    try:
                        if ans and ("sigma" in ans) and (not ans.get("k")):
                            # reload inputs (t_out/q might have been filled above)
                            cold2 = self.cold_panel.to_dict()
                            hot2 = self.hot_panel.to_dict()
                            cold_mix2 = self.cold_mix.mix_rows()
                            hot_mix2 = self.hot_mix.mix_rows()
                            q2 = float(ans.get("q", q_val) or q_val)
                            res2 = getattr(logic, "calculate", None)
                            if callable(res2):
                                ans2 = res2(
                                    cold=cold2,
                                    hot=hot2,
                                    cold_mix=cold_mix2,
                                    hot_mix=hot_mix2,
                                    q=q2,
                                    schema=schema,
                                )
                                ans2 = cast(Dict[str, Any], ans2)
                                if ans2 and ans2.get("k"):
                                    try:
                                        k2_val = float(ans2.get("k", 0.0) or 0.0)
                                    except Exception:
                                        k2_val = 0.0
                                    if k2_val:
                                        self.out_panel.k.setText(format_num(k2_val))
                                        set_enabled(self.out_panel.k, False)
                                        # update status with new k info
                                        try:
                                            k_src2 = str(ans2.get("k_source", ""))
                                            k_show2 = k2_val
                                            msg2 = f"{schema_display}  contact={contact or '-'}  k_source={k_src2 or '-'}  Q={q_show:.4g}  K={k_show2:.4g}  σ={s_show:.4g}"
                                            self.status.showMessage(msg2)
                                        except Exception:
                                            pass
                    except Exception:
                        pass
                if ans and "q" in ans:
                    # записываем Q и делаем T+out недоступным для ввода
                    try:
                        self.out_panel.q.blockSignals(True)
                        self.out_panel.q.setText(f"{ans['q']:.6g}")
                        self.out_panel.q.blockSignals(False)
                    except Exception:
                        pass
                    set_enabled(self.hot_panel.t_out, False)
                if ans and "t_out_plus" in ans:
                    self.hot_panel.t_out.setText(f"{ans['t_out_plus']:.6g}")
                    set_enabled(self.out_panel.q, False)
                # persist schema selection (store current hydro schema id)
                try:
                    schema_path = os.path.join(
                        os.path.dirname(os.path.abspath(__file__)),
                        "data",
                        "csv",
                        "schema.txt",
                    )
                    with open(schema_path, "w", encoding="utf-8") as f:
                        f.write(self.hydro.current_schema())
                except Exception:
                    pass
            else:
                QMessageBox.information(
                    self,
                    "Расчёт",
                    "Функция расчёта в logic.py не найдена. Заполните её.",
                )
        except Exception as e:
            QMessageBox.warning(self, "Ошибка расчёта", str(e))

    def _auto_calc_minimal(self) -> None:
        """Выполнить быстрый авторасчёт, только для заполнения `q` или `t_out_plus`.
        Не обновляет `sigma` и `k` — эти величины вычисляются только по нажатию кнопки.
        """
        cold = self.cold_panel.to_dict()
        hot = self.hot_panel.to_dict()
        cold_mix = self.cold_mix.mix_rows()
        hot_mix = self.hot_mix.mix_rows()
        q_val = to_float(self.out_panel.q.text())
        schema = self.hydro.current_schema()
        try:
            res = getattr(logic, "calculate", None)
            if callable(res):
                ans = res(
                    cold=cold,
                    hot=hot,
                    cold_mix=cold_mix,
                    hot_mix=hot_mix,
                    q=q_val,
                    schema=schema,
                )
                # Only apply q or t_out_plus if provided by calculation
                ans = cast(Dict[str, Any], ans)
                ans_dict = ans
                if (
                    ans_dict
                    and "q" in ans_dict
                    and (not self.out_panel.q.text().strip())
                ):
                    try:
                        self.out_panel.q.blockSignals(True)
                        self.out_panel.q.setText(f"{ans['q']:.6g}")
                        self.out_panel.q.blockSignals(False)
                    except Exception:
                        pass
                if (
                    ans_dict
                    and "t_out_plus" in ans_dict
                    and (not self.hot_panel.t_out.text().strip())
                ):
                    try:
                        self.hot_panel.t_out.blockSignals(True)
                        self.hot_panel.t_out.setText(f"{ans_dict['t_out_plus']:.6g}")
                        self.hot_panel.t_out.blockSignals(False)
                    except Exception:
                        pass
                # update button state after potential auto-fill
                try:
                    self._update_calc_button_state()
                except Exception:
                    pass
        except Exception:
            pass

    # --- сброс данных ---
    def on_reset(self) -> None:
        """Полный сброс входных параметров и результатов в UI.
        Очищает поля потоков, таблицы смесей и поля результатов (Q, σ, K).
        """
        try:
            # clear flow panels
            for w in (
                self.cold_panel.t_in,
                self.cold_panel.t_out,
                self.cold_panel.m,
                self.cold_panel.p,
                self.hot_panel.t_in,
                self.hot_panel.t_out,
                self.hot_panel.m,
                self.hot_panel.p,
            ):
                try:
                    w.blockSignals(True)
                    w.clear()
                    w.blockSignals(False)
                    set_enabled(w, True)
                except Exception:
                    pass
            try:
                self._post_import_changed = False
                self._suppress_full_calc_after_import = False
                self.recalc_btn.hide()
            except Exception:
                pass

            # clear mixtures
            try:
                if self.cold_mix.model.rowCount() > 0:
                    self.cold_mix.model.removeRows(0, self.cold_mix.model.rowCount())
                if self.hot_mix.model.rowCount() > 0:
                    self.hot_mix.model.removeRows(0, self.hot_mix.model.rowCount())
                # сброс выбора компонента к первому (обычно "Азот")
                try:
                    self.cold_mix.comp.setCurrentIndex(0)
                except Exception:
                    pass
                try:
                    self.hot_mix.comp.setCurrentIndex(0)
                except Exception:
                    pass
                # очистка поля ввода доли
                try:
                    self.cold_mix.share.clear()
                except Exception:
                    pass
                try:
                    self.hot_mix.share.clear()
                except Exception:
                    pass
                # сброс отображения суммы
                try:
                    self.cold_mix.sum_field.setText("0.0")
                except Exception:
                    pass
                try:
                    self.hot_mix.sum_field.setText("0.0")
                except Exception:
                    pass
                # update hints/export
                try:
                    self.cold_mix.update_share_hint()
                except Exception:
                    pass
                try:
                    self.hot_mix.update_share_hint()
                except Exception:
                    pass
            except Exception:
                pass

            # clear outputs
            try:
                self.out_panel.clear_values()
                try:
                    set_enabled(self.out_panel.q, True)
                except Exception:
                    pass
            except Exception:
                # fallback: direct resets
                try:
                    self.out_panel.q.clear()
                    try:
                        set_enabled(self.out_panel.q, True)
                    except Exception:
                        pass
                except Exception:
                    pass
                try:
                    self.out_panel.sigma.setText("0.0")
                    set_enabled(self.out_panel.sigma, False)
                except Exception:
                    pass
                try:
                    self.out_panel.k.setText("0.0")
                    set_enabled(self.out_panel.k, False)
                except Exception:
                    pass

            # reset status
            try:
                self.status.showMessage("Сброшено")
            except Exception:
                pass
            # Сброс схемы к первой и запрет автосчёта sigma/k до явного вычисления
            try:
                self.hydro.rb_mix_mix.setChecked(True)
            except Exception:
                pass
            try:
                self._explicit_calc_done = False
            except Exception:
                pass
        except Exception:
            pass

    # --- Диалоги помощи ---
    def _simple_text_dialog(
        self, title: str, text: str, read_only: bool = True
    ) -> None:
        try:
            dlg = QDialog(self)
            dlg.setWindowTitle(title)
            dlg.resize(700, 500)
            layout = QVBoxLayout(dlg)
            te = QTextEdit()
            te.setPlainText(text)
            te.setReadOnly(read_only)
            layout.addWidget(te)
            buttons = QDialogButtonBox(QDialogButtonBox.Close)
            buttons.rejected.connect(dlg.reject)
            buttons.accepted.connect(dlg.accept)
            layout.addWidget(buttons)
            dlg.exec_()
        except Exception as e:
            QMessageBox.warning(self, title, str(e))

    def show_help_dialog(self) -> None:
        help_text = (
            "Справка по использованию программы:\n\n"
            "1. Введите параметры холодного и горячего потоков (температуры, расход, давление).\n"
            "2. Сформируйте смеси компонентов: выберите компонент, долю и добавьте. Сумма долей каждой смеси должна быть 1.\n"
            "3. Выберите гидродинамическую схему.\n"
            "4. Введите либо тепловую нагрузку Q, либо выходную температуру горячего потока T⁺out — второе значение будет рассчитано автоматически.\n"
            "5. Нажмите 'Вычислить' для получения σ и K.\n"
            "6. Кнопка 'Провести анализ' позволяет открыть отдельное окно для изменения долей и построения графика зависимости Q–σ.\n"
            "7. Используйте меню 'Файл' для импорта/экспорта данных в CSV или Excel. При импорте значения не преобразуются в даты.\n"
            "8. 'Очистить параметры' сбрасывает все поля.\n"
        )
        self._simple_text_dialog("Справка", help_text)

    def show_logs_dialog(self) -> None:
        try:
            if not LOG_FILE.exists():
                QMessageBox.information(self, "Логи", "Файл логов пока отсутствует.")
                return
            with LOG_FILE.open("r", encoding="utf-8", errors="ignore") as f:
                content = f.read()[-100000:]
            self._simple_text_dialog("Логи", content)
        except Exception as e:
            QMessageBox.warning(self, "Логи", str(e))

    def show_about_dialog(self) -> None:
        try:
            version_path = Path(os.path.dirname(os.path.abspath(__file__))) / "VERSION"
            version = "неизвестно"
            if version_path.exists():
                try:
                    version = version_path.read_text(encoding="utf-8").strip()
                except Exception:
                    pass
            mtime = datetime.fromtimestamp(os.path.getmtime(__file__)).strftime(
                "%Y-%m-%d %H:%M"
            )
            text = (
                f"Полное наименование: Программа анализа двухпоточного теплообменника\n"
                f"Версия: {version}\n"
                f"Дата обновления: {mtime}\n\n"
                "Описание: Инструмент для расчёта тепловой нагрузки,\n"
                "производства энтропии и коэффициента теплопередачи\n"
                "в системах теплообмена с различными гидродинамическими схемами."
            )
            QMessageBox.information(self, "О программе", text)
        except Exception as e:
            QMessageBox.warning(self, "О программе", str(e))

    def show_license_dialog(self) -> None:
        try:
            lic_path = Path(os.path.dirname(os.path.abspath(__file__))) / "Лицензионное_соглашение.txt"
            if not lic_path.exists():
                QMessageBox.information(self, "Лицензионное соглашение", "Файл лицензионного соглашения не найден.")
                return
            try:
                content = lic_path.read_text(encoding="utf-8")
            except Exception as e:
                QMessageBox.warning(self, "Лицензионное соглашение", f"Не удалось прочитать файл: {e}")
                return
            self._simple_text_dialog("Лицензионное соглашение", content)
        except Exception as e:
            QMessageBox.warning(self, "Лицензионное соглашение", str(e))

    # --- Окно анализа ---
    def open_analysis_window(self) -> None:
        try:
            from analysis_interface import AnalysisWindow  # type: ignore
        except Exception as e:
            QMessageBox.warning(
                self, "Анализ", f"Не удалось импортировать окно анализа: {e}"
            )
            return
        try:
            cold = self.cold_panel.to_dict()
            hot = self.hot_panel.to_dict()
            cold_mix = self.cold_mix.mix_rows()
            hot_mix = self.hot_mix.mix_rows()
        except Exception:
            cold = {}
            hot = {}
            cold_mix = []  # type: ignore
            hot_mix = []  # type: ignore
        # Проверим, что Q, sigma и k рассчитаны; если нет — не открываем окно анализа
        try:
            q_txt = self.out_panel.q.text().strip()
            sigma_txt = self.out_panel.sigma.text().strip()
            k_txt = self.out_panel.k.text().strip()

            def _is_calculated(t: str) -> bool:
                try:
                    return float(t) != 0.0
                except Exception:
                    return False

            if not q_txt or not _is_calculated(sigma_txt) or not _is_calculated(k_txt):
                QMessageBox.warning(
                    self,
                    "Анализ",
                    "Невозможно открыть анализ: сначала выполните полный расчёт (Q, σ и K должны быть рассчитаны).",
                )
                return
        except Exception:
            # в случае проблем с доступом к полям — не открываем анализ
            QMessageBox.warning(
                self, "Анализ", "Невозможно открыть анализ: недоступны значения Q/σ/K."
            )
            return
        try:
            self._analysis_win  # type: ignore[attr-defined]
            if self._analysis_win is not None and self._analysis_win.isVisible():  # type: ignore
                self._analysis_win.raise_()  # type: ignore
                self._analysis_win.activateWindow()  # type: ignore
                return
        except Exception:
            pass
        try:
            # приведение типов для mypy/pyright
            from typing import cast as _cast, Dict as _Dict, Any as _Any, List as _List

            cold_cast = {str(k): float(v) for k, v in cold.items()}  # type: ignore[arg-type]
            hot_cast = {str(k): float(v) for k, v in hot.items()}  # type: ignore[arg-type]
            cold_list = [dict(r) for r in cold_mix]  # type: ignore[list-item]
            hot_list = [dict(r) for r in hot_mix]  # type: ignore[list-item]
            cold_list = _cast(_List[_Dict[str, _Any]], cold_list)
            hot_list = _cast(_List[_Dict[str, _Any]], hot_list)
            self._analysis_win = AnalysisWindow(
                cold_flow=cold_cast,
                hot_flow=hot_cast,
                cold_mix=cold_list,
                hot_mix=hot_list,
                parent=self,
            )
            self._analysis_win.show()
        except Exception as e:
            QMessageBox.warning(self, "Анализ", f"Ошибка открытия окна анализа: {e}")

    # ---------- ПОМЕТКА УСТАРЕВАНИЯ РЕЗУЛЬТАТОВ ----------
    def _mark_stale_results(self) -> None:
        """Пометить, что результаты (σ, K, производные расчёты) устарели после изменения входных данных.
        Кнопка 'Перерасчёт' отображается только если уже был выполнен явный расчёт.
        """
        try:
            if getattr(self, "_explicit_calc_done", False):
                self._results_stale = True
                if self._mix_valid(self.cold_mix.mix_rows()) and self._mix_valid(
                    self.hot_mix.mix_rows()
                ):
                    self.recalc_btn.show()
        except Exception:
            pass

    def _on_recalc_clicked(self) -> None:
        try:
            self._suppress_full_calc_after_import = False
            self._post_import_changed = False
            self._results_stale = False
        except Exception:
            pass
        try:
            # Выполняем полный расчёт (как при кнопке Вычислить), но без скрытия кнопки до завершения
            self.on_calc()
        except Exception:
            pass
        try:
            self.recalc_btn.hide()
        except Exception:
            pass

    def _lock_imported_fields(self) -> None:
        """Заблокировать поля, заполненные при импорте. Разблокировка при очистке."""
        try:
            widgets = [
                self.cold_panel.t_in,
                self.cold_panel.t_out,
                self.cold_panel.m,
                self.cold_panel.p,
                self.hot_panel.t_in,
                self.hot_panel.t_out,
                self.hot_panel.m,
                self.hot_panel.p,
                self.out_panel.q,
            ]
            for w in widgets:
                if w.text().strip():
                    set_enabled(w, False)
        except Exception:
            pass

    def _normalize_input(self) -> None:
        """Нормализация числовых полей: замена запятой, удаление лишних ведущих нулей (кроме '0.'), очистка одиночного '0'."""
        edits = [
            self.cold_panel.t_in,
            self.cold_panel.t_out,
            self.cold_panel.m,
            self.hot_panel.t_in,
            self.hot_panel.t_out,
            self.hot_panel.m,
            self.out_panel.q,
        ]
        for w in edits:
            try:
                txt = w.text().strip()
                if not txt:
                    continue
                txt = txt.replace(",", ".")
                # если формат вроде 09 или 00012.3 -> убираем ведущие нули
                if txt.count(".") <= 1:
                    if (
                        txt.startswith("0")
                        and len(txt) > 1
                        and not txt.startswith("0.")
                    ):
                        # убрать все ведущие нули, оставить один перед точкой если была
                        if "." in txt:
                            int_part, frac_part = txt.split(".", 1)
                            int_part = int_part.lstrip("0") or "0"
                            txt = int_part + (
                                "." + frac_part if frac_part != "" else ""
                            )
                        else:
                            txt = txt.lstrip("0") or "0"
                w.blockSignals(True)
                w.setText(txt)
                w.blockSignals(False)
            except Exception:
                pass
        # any manual edit should lift the import-based suppression of full calculation
        try:
            self._suppress_full_calc_after_import = False
        except Exception:
            pass
        # after normalizing inputs, attempt only the minimal auto-calc helper
        try:
            self._try_auto_calc()
        except Exception:
            pass
        try:
            self._update_calc_button_state()
        except Exception:
            pass

    def _try_auto_calc(self) -> None:
        """Попытаться выполнить расчёт автоматически (вызывается после editingFinished важных полей)."""
        try:
            # Проверим, есть ли все необходимые входы для автоматического вычисления
            cold = self.cold_panel.to_dict()
            hot = self.hot_panel.to_dict()
            cold_mix = self.cold_mix.mix_rows()
            hot_mix = self.hot_mix.mix_rows()
            q_text = self.out_panel.q.text().strip()
            t_out_hot_text = self.hot_panel.t_out.text().strip()

            # use shared _mix_valid which accepts Sequence[MixRow]

            # 1) If Q is empty and we have sufficient data in either stream -> compute Q
            if not q_text:
                cold_ready = (
                    cold["t_in"] and cold["t_out"] and cold["m"]
                ) and self._mix_valid(cold_mix)
                hot_ready = (
                    hot["t_in"] and hot["t_out"] and hot["m"]
                ) and self._mix_valid(hot_mix)
                if cold_ready or hot_ready:
                    self._auto_calc_minimal()
                    return

            # 2) If t_out_hot is empty but Q is given and hot stream data + mix are valid -> compute t_out_hot
            if not t_out_hot_text and q_text:
                hot_ready_for_tout = (hot["t_in"] and hot["m"]) and self._mix_valid(
                    hot_mix
                )
                if hot_ready_for_tout:
                    self._auto_calc_minimal()
                    return
            # otherwise do nothing
        except Exception:
            pass


"""Модуль interface: содержит классы GUI (панели и главное окно).

Точка входа приложения перенесена в main.py.
"""
