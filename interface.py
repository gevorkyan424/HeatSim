# interface.py
import os
import sys
import csv
from typing import Callable, TypedDict, Any, List, Dict, Optional

from PyQt5.QtGui import QFont, QPixmap, QRegularExpressionValidator, QStandardItemModel, QStandardItem
from PyQt5.QtCore import Qt, QRegularExpression, QObject, QEvent, QModelIndex, QSortFilterProxyModel
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QGroupBox, QLabel, QLineEdit, QPushButton,
    QComboBox, QRadioButton, QButtonGroup, QMessageBox, QSizePolicy,
    QHeaderView, QTableView, QFrame
)

import logic  #модуль расчётов

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
        e.setStyleSheet('background:#f3f3f3;')
    rx = QRegularExpression(r'^$|^[0-9]{1,10}([.,][0-9]{0,5})?$')
    e.setValidator(QRegularExpressionValidator(rx))

    def fix_number():
        t = e.text().strip()
        if not t: return
        if t.endswith(',') or t.endswith('.'): t += '00'
        sep = max(t.rfind(','), t.rfind('.'))
        if sep != -1:
            i, f = t[:sep], t[sep+1:]
            t = i[:10] + t[sep] + (f or '00')[:5]
        else:
            t = t[:10]
        e.blockSignals(True); e.setText(t); e.blockSignals(False)

    e.editingFinished.connect(fix_number)
    return e

def to_float(text: str) -> float:
    try: return float(text.replace(',', '.'))
    except Exception: return 0.0

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
        le.setStyleSheet('background:#f3f3f3;')
    else:
        # enabled fields: clear style (caller may set manual highlight)
        le.setStyleSheet('')
    # keep associated lock button in sync without triggering its signals
    btn = getattr(le, '_lock_btn', None)
    if btn is not None:
        # update text only; button click will set enabled state explicitly
        btn.setText('🔒' if not enabled else '🔓')

def lock_button_for(line_edit: QLineEdit) -> QPushButton:
    btn = QPushButton()
    btn.setFixedSize(22, 22)
    btn.setToolTip('Заблокировать/разблокировать поле')

    def on_click():
        # if the field is enabled -> lock it; otherwise unlock
        if line_edit.isEnabled():
            # lock
            set_enabled(line_edit, False)
            setattr(line_edit, '_just_unlocked', False)
            # remove any temporary handler if present
            h = getattr(line_edit, '_just_unlocked_handler', None)
            if h is not None:
                try:
                    line_edit.textEdited.disconnect(h)
                except Exception:
                    pass
                try:
                    delattr(line_edit, '_just_unlocked_handler')
                except Exception:
                    pass
        else:
            # unlock — prepare flags so that an immediate editingFinished (without user typing)
            # won't auto-disable, but a real typed edit followed by editingFinished will.
            set_enabled(line_edit, True)
            try:
                # waiting flag indicates we recently unlocked and expect possible typing
                setattr(line_edit, '_just_unlocked_waiting', True)
                # clear typed flag
                if hasattr(line_edit, '_just_unlocked_typed'):
                    delattr(line_edit, '_just_unlocked_typed')
            except Exception:
                pass

            def _on_text_edited(_text: str) -> None:
                # mark that the user actually typed
                try:
                    setattr(line_edit, '_just_unlocked_typed', True)
                finally:
                    try:
                        line_edit.textEdited.disconnect(_on_text_edited)
                    except Exception:
                        pass
                    try:
                        if hasattr(line_edit, '_just_unlocked_handler'):
                            delattr(line_edit, '_just_unlocked_handler')
                    except Exception:
                        pass

            # store handler reference for cleanup and connect
            try:
                setattr(line_edit, '_just_unlocked_handler', _on_text_edited)
                line_edit.textEdited.connect(_on_text_edited)
            except Exception:
                try:
                    if hasattr(line_edit, '_just_unlocked_handler'):
                        delattr(line_edit, '_just_unlocked_handler')
                except Exception:
                    pass

    btn.clicked.connect(on_click)
    # initial text reflects current state
    btn.setText('🔒' if not line_edit.isEnabled() else '🔓')
    # attach for external sync
    setattr(line_edit, '_lock_btn', btn)
    return btn


def auto_disable_handler(line_edit: QLineEdit) -> Callable[[], None]:
    def _handler() -> None:
        # if we just unlocked for editing, only skip auto-disable when no typing occurred
        if getattr(line_edit, '_just_unlocked_waiting', False):
            # if user typed, proceed to disable and clear flags
            if getattr(line_edit, '_just_unlocked_typed', False):
                try:
                    delattr(line_edit, '_just_unlocked_typed')
                except Exception:
                    pass
                try:
                    delattr(line_edit, '_just_unlocked_waiting')
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
        grid.addWidget(QLabel(f'Температура на входе ({title.lower()}), T<sub>{sign}</sub><sup>in</sup> [ K ]'), row, 0)
        h0 = QHBoxLayout()
        h0.setContentsMargins(0,0,0,0)
        h0.addWidget(self.t_in); h0.addWidget(self.t_in_lock)
        grid.addLayout(h0, row, 1)

        row += 1
        grid.addWidget(QLabel(f'Температура на выходе ({title.lower()}), T<sub>{sign}</sub><sup>out</sup> [ K ]'), row, 0)
        h1 = QHBoxLayout()
        h1.setContentsMargins(0,0,0,0)
        h1.addWidget(self.t_out); h1.addWidget(self.t_out_lock)
        grid.addLayout(h1, row, 1)

        row += 1
        grid.addWidget(QLabel(f'Расход потока ({title.lower()}), g<sub>{sign}</sub> [ кг/сек ]'), row, 0)
        h2 = QHBoxLayout()
        h2.setContentsMargins(0,0,0,0)
        h2.addWidget(self.m); h2.addWidget(self.m_lock)
        grid.addLayout(h2, row, 1)

        row += 1
        grid.addWidget(QLabel(f'Давление ({title.lower()}), P<sub>{sign}</sub> [ кг/м² ]'), row, 0)
        h3 = QHBoxLayout()
        h3.setContentsMargins(0,0,0,0)
        h3.addWidget(self.p); h3.addWidget(self.p_lock)
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
        return FlowData({
            "t_in": to_float(self.t_in.text()),
            "t_out": to_float(self.t_out.text()),
            "m": to_float(self.m.text()),
            "p": to_float(self.p.text()),
        })

# ===================== DELETE FILTER =====================
class KeyDeleteFilter(QObject):
    def __init__(self, callback: Callable[[], None]):
        super().__init__()
        self.callback: Callable[[], None] = callback

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # type: ignore[override]
        if event.type() == QEvent.KeyPress and getattr(event, 'key', lambda: None)() == Qt.Key_Delete:
            self.callback()
            return True
        return super().eventFilter(obj, event)

# ===================== МОДЕЛЬ СМЕСИ =====================
class MixModel(QStandardItemModel):
    COL_NAME, COL_SHARE, COL_TB, COL_CF, COL_CP, COL_RF = range(6)
    HEADERS = ["Компонент", "Доля", "Tb, K", "C_f, кДж/кг·K", "C_p, кДж/кг·K", "r_f, кДж/кг"]
    SORT_ROLE = Qt.UserRole + 1

    def __init__(self, parent=None):
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

    def add_or_update(self, name: str, share: float, tb: float, cf: float, cp: float, rf: float) -> int:
        row = self._row_by_name(name)
        if row >= 0:
            idx_share = self.index(row, self.COL_SHARE)
            cur_share = float(self.data(idx_share, Qt.DisplayRole).replace(',', '.'))
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
        self.setItem(r, self.COL_TB,    self._num_item(tb))
        self.setItem(r, self.COL_CF,    self._num_item(cf))
        self.setItem(r, self.COL_CP,    self._num_item(cp))
        self.setItem(r, self.COL_RF,    self._num_item(rf))
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
            def v(c):
                txt = self.data(self.index(r, c), Qt.DisplayRole) or "0"
                return float(txt.replace(',', '.')) if c != self.COL_NAME else txt
            out.append(MixRow({
                "name": v(self.COL_NAME),  # type: ignore[arg-type]
                "share": v(self.COL_SHARE),  # type: ignore[arg-type]
                "tb": v(self.COL_TB),  # type: ignore[arg-type]
                "cf": v(self.COL_CF),  # type: ignore[arg-type]
                "cp": v(self.COL_CP),  # type: ignore[arg-type]
                "rf": v(self.COL_RF),  # type: ignore[arg-type]
            }))
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
        top.setContentsMargins(0,0,0,0)
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
        top.addWidget(self.comp); top.addStretch(1)
        top.addWidget(QLabel("Доля")); top.addWidget(self.share); top.addSpacing(8)
        top.addWidget(QLabel("Сумма")); top.addWidget(self.sum_field); top.addSpacing(8)
        top.addWidget(self.add_btn)
        v.addLayout(top)

        # источник параметров
        src = QHBoxLayout(); src.setContentsMargins(0,0,0,0); src.setSpacing(8)
        self.rb_group = QButtonGroup(self.box)
        self.rb_db = QRadioButton("Взять параметры из справочника NIST Chemistry WebBook")
        self.rb_manual = QRadioButton("Ввести параметры вручную")
        self.rb_group.addButton(self.rb_db, 0); self.rb_group.addButton(self.rb_manual, 1)
        self.rb_db.setChecked(True)
        src.addWidget(self.rb_db); src.addWidget(self.rb_manual); src.addStretch(1)
        v.addLayout(src)

        # параметры
        grid = QGridLayout(); grid.setHorizontalSpacing(12); grid.setVerticalSpacing(6)
        self.tb = num_edit(read_only=True); self.cf = num_edit(read_only=True)
        self.cp = num_edit(read_only=True); self.rf = num_edit(read_only=True)
        grid.addWidget(QLabel("Температура кипения, Tb  [ K ]"), 0, 0); grid.addWidget(self.tb, 0, 1)
        grid.addWidget(QLabel("Удельная теплоёмкость жидкости, C_f  [ кДж/кг·K ]"), 1, 0); grid.addWidget(self.cf, 1, 1)
        grid.addWidget(QLabel("Удельная теплоёмкость пара, C_p  [ кДж/кг·K ]"), 2, 0); grid.addWidget(self.cp, 2, 1)
        grid.addWidget(QLabel("Скрытая теплота фазового перехода, r_f  [ кДж/кг ]"), 3, 0); grid.addWidget(self.rf, 3, 1)
        v.addLayout(grid)

        # таблица
        self.model = MixModel()
        self.proxy = QSortFilterProxyModel(); self.proxy.setSourceModel(self.model)
        self.proxy.setSortRole(MixModel.SORT_ROLE); self.proxy.setDynamicSortFilter(True)
        self.view = QTableView(); self.view.setModel(self.proxy)
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
        table_font  = QFont("Consolas", 9)
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
            if hasattr(w, '_lock_btn'):
                delattr(w, '_lock_btn')

        self.update_share_hint(); self._resort()

    def widget(self) -> QGroupBox: return self.box

    # сортировка по Tb автоматически
    def _resort(self) -> None:
        col = MixModel.COL_TB
        order = Qt.DescendingOrder if self.is_hot else Qt.AscendingOrder
        self.proxy.sort(col, order)

    def _on_model_changed(self, *args: Any) -> None:
        self.update_share_hint(); self._resort(); self._auto_export_csv()

    def _auto_export_csv(self) -> None:
        try:
            with open(self.export_path, "w", newline="", encoding="utf-8-sig") as f:
                wr = csv.writer(f, delimiter=';')
                wr.writerow(["Компонент","Доля","Tb, K","C_f, кДж/кг·K","C_p, кДж/кг·K","r_f, кДж/кг"])
                for r in range(self.model.rowCount()):
                    row=[]
                    for c in range(self.model.columnCount()):
                        txt = self.model.data(self.model.index(r,c), Qt.DisplayRole) or ""
                        if c!=0: txt = txt.replace('.', ',')
                        row.append(txt)
                    wr.writerow(row)
        except Exception:
            pass

    def current_sum(self) -> float:
        s=0.0
        for r in range(self.model.rowCount()):
            txt = self.model.data(self.model.index(r, MixModel.COL_SHARE), Qt.DisplayRole) or "0"
            s += float(txt.replace(',', '.'))
        return s

    def update_share_hint(self) -> None:
        remaining = max(0.0, 1.0 - self.current_sum())
        self.share.setPlaceholderText(f"≤ {remaining:.5f}")
        self.sum_field.setText(f"{1.0-remaining:.5f}")

    def on_mode_change(self, _checked: bool) -> None:
        manual = self.rb_manual.isChecked()
        for w in (self.tb, self.cf, self.cp, self.rf):
            set_enabled(w, manual)
        if self.rb_db.isChecked():
            self.fill_from_db(self.comp.currentText())

        try:
            if manual:
                highlight_style = 'QLineEdit { background: #fff7d6; }'
                for w in (self.tb, self.cf, self.cp, self.rf):
                    w.setStyleSheet(highlight_style)
            else:
                for w in (self.tb, self.cf, self.cp, self.rf):
                    if not w.isEnabled():
                        w.setStyleSheet('background:#f3f3f3;')
                    else:
                        w.setStyleSheet('')
        except Exception:
            pass

    def fill_from_db(self, name: str) -> None:
        props = COMPONENT_DB.get(name)
        if props:
            tb, cf, cp, rf = props
            self.tb.setText(f"{tb}"); self.cf.setText(f"{cf}")
            self.cp.setText(f"{cp}"); self.rf.setText(f"{rf}")
        else:
            for w in (self.tb, self.cf, self.cp, self.rf): w.setText("0.0")

    def validate_share_max1(self) -> None:
        val = to_float(self.share.text())
        if val>1.0:
            QMessageBox.warning(self.box,"Доля","Доля компонента не может превышать 1. Повторите ввод.")
            self.share.clear(); self.share.setFocus()

    def on_add(self) -> None:
        remaining = max(0.0, 1.0 - self.current_sum())
        share_val = to_float(self.share.text())
        if share_val > 1.0 + 1e-12:
            QMessageBox.warning(self.box,"Доля","Доля компонента не может превышать 1. Повторите ввод.")
            self.share.clear(); self.share.setFocus(); return
        if share_val <= 0.0:
            QMessageBox.warning(self.box,"Доля","Введите положительную долю > 0."); return
        if share_val > remaining + 1e-12:
            if remaining <= 0.0:
                QMessageBox.warning(self.box,"Сумма долей","Сумма долей уже равна 1.0."); return
            share_val = remaining; self.share.setText(f"{share_val:.5f}")

        name = self.comp.currentText()
        if self.rb_db.isChecked():
            tb,cf,cp,rf = COMPONENT_DB[name]
        else:
            tb,cf,cp,rf = (to_float(self.tb.text()), to_float(self.cf.text()),
                           to_float(self.cp.text()), to_float(self.rf.text()))
        self.model.add_or_update(name, share_val, tb, cf, cp, rf)
        self.share.clear()

    def ask_delete(self, count:int) -> bool:
        return QMessageBox.question(self.box,"Удаление",f"Удалить {count} строку(и)?",
                                    QMessageBox.Yes|QMessageBox.No,QMessageBox.No)==QMessageBox.Yes

    def selected_source_rows(self) -> List[int]:
        rows: List[int] = []
        for proxy_index in self.view.selectionModel().selectedRows():
            src_idx = self.proxy.mapToSource(proxy_index); rows.append(src_idx.row())
        return sorted(set(rows), reverse=True)

    def delete_selected_rows(self) -> None:
        rows = self.selected_source_rows()
        if not rows:
            QMessageBox.information(self.box,"Удаление","Выберите строку(и) для удаления."); return
        if not self.ask_delete(len(rows)): return
        self.model.remove_rows(rows)

    def on_double_click(self, index: QModelIndex) -> None:
        if not index.isValid(): return
        if not self.ask_delete(1): return
        self.model.removeRow(self.proxy.mapToSource(index).row())

    def mix_rows(self) -> List[MixRow]: return self.model.rows_as_dicts()

# ===================== ПАНЕЛЬ ГИДРОДИНАМИКИ =====================
class HydroPanel(QGroupBox):
    def __init__(self, title: str = "Гидродинамика потоков", parent: Optional[QWidget] = None):
        super().__init__(title, parent)
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'images')
        self._images = {
            "mix_mix": os.path.join(base,"one.png"),
            "parallel": os.path.join(base,"two.png"),
            "mix_cold_disp_hot": os.path.join(base,"three.png"),
            "mix_hot_disp_cold": os.path.join(base,"four.png"),
            "counter": os.path.join(base,"five.png"),
        }
        root = QHBoxLayout(self)
        root.setContentsMargins(6,6,6,6)
        root.setSpacing(6)
        left = QVBoxLayout(); right = QVBoxLayout()
        left.setContentsMargins(4,4,4,4); right.setContentsMargins(4,4,4,4)
        root.addLayout(left)
        root.addLayout(right)
        root.setStretch(0, 0)
        root.setStretch(1, 0)

        self.rb_mix_mix = QRadioButton("Смешение - смешение")
        self.rb_parallel = QRadioButton("Вытеснение - вытеснение (прямоток)")
        self.rb_mix_cold = QRadioButton("Смешение (хол.) - вытеснение (гор.)")
        self.rb_mix_hot  = QRadioButton("Смешение (гор.) - вытеснение (хол.)")
        self.rb_counter  = QRadioButton("Вытеснение - вытеснение (противоток)")
        for rb in (self.rb_mix_mix,self.rb_parallel,self.rb_mix_cold,self.rb_mix_hot,self.rb_counter):
            left.addWidget(rb)
        left.addStretch(1)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setFixedSize(350,175)
        self.image_label.setFrameShape(QFrame.Box)
        self.image_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        right.addWidget(self.image_label, 0, Qt.AlignVCenter | Qt.AlignHCenter)

        self.rb_mix_mix.toggled.connect(lambda on: on and self._set_mode("mix_mix"))
        self.rb_parallel.toggled.connect(lambda on: on and self._set_mode("parallel"))
        self.rb_mix_cold.toggled.connect(lambda on: on and self._set_mode("mix_cold_disp_hot"))
        self.rb_mix_hot.toggled.connect(lambda on: on and self._set_mode("mix_hot_disp_cold"))
        self.rb_counter.toggled.connect(lambda on: on and self._set_mode("counter"))

        self.rb_mix_mix.setChecked(True); self._set_mode("mix_mix")

    def _set_mode(self, key: str) -> None:
        pix = QPixmap(self._images.get(key,""))
        if pix.isNull():
            self.image_label.setText("Нет изображения"); self.image_label.setPixmap(QPixmap()); return
        self.image_label.setPixmap(pix.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def resizeEvent(self, e: QEvent) -> None:  # type: ignore[override]
        super().resizeEvent(e)  # type: ignore[arg-type]
        if   self.rb_mix_mix.isChecked():    self._set_mode("mix_mix")
        elif self.rb_parallel.isChecked():   self._set_mode("parallel")
        elif self.rb_mix_cold.isChecked():   self._set_mode("mix_cold_disp_hot")
        elif self.rb_mix_hot.isChecked():    self._set_mode("mix_hot_disp_cold")
        elif self.rb_counter.isChecked():    self._set_mode("counter")

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
        self.sigma.setText("0.0"); set_enabled(self.sigma, False)
        self.k.setText("0.0"); set_enabled(self.k, False)
        g.addWidget(QLabel("Тепловая нагрузка, Q [кВт]"), 0, 0)
        hq = QHBoxLayout(); hq.setContentsMargins(0,0,0,0); hq.addWidget(self.q); hq.addWidget(self.q_lock)
        g.addLayout(hq, 0, 1)
        g.addWidget(QLabel("Производство энтропии, σ [кВт/К]"), 1, 0)
        g.addWidget(self.sigma, 1, 1)
        g.addWidget(QLabel("Коэффициент теплопередачи, K [кВт/К]"), 2, 0)
        g.addWidget(self.k, 2, 1)
        # remove stale lock attributes if any
        for w in (self.sigma, self.k):
            if hasattr(w, '_lock_btn'):
                delattr(w, '_lock_btn')
        # auto-disable Q after editingFinished
        try:
            self.q.editingFinished.connect(auto_disable_handler(self.q))
        except Exception:
            pass

    def clear_values(self) -> None:
        for w in (self.q,):
            w.clear()
        # сохранить sigma/k как read-only 0.0
        self.sigma.setText("0.0"); set_enabled(self.sigma, False)
        self.k.setText("0.0"); set_enabled(self.k, False)

# ===================== ГЛАВНОЕ ОКНО =====================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Двухпоточный теплообмен")
        self.setFixedSize(1600, 875)

        central = QWidget(); self.setCentralWidget(central)
        layout = QVBoxLayout(); central.setLayout(layout)

        # потоки
        row1 = QHBoxLayout(); layout.addLayout(row1)
        self.cold_panel = FlowPanel("Холодный поток", sign="−")
        self.hot_panel  = FlowPanel("Горячий поток",  sign="+")
        row1.addWidget(self.cold_panel.widget()); row1.addWidget(self.hot_panel.widget())

        # смеси
        row2 = QHBoxLayout(); layout.addLayout(row2)
        self.cold_mix = MixPanel("холодного потока", is_hot=False,
                                 export_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'csv', 'cold_mix.csv'))
        self.hot_mix  = MixPanel("горячего потока",  is_hot=True,
                                 export_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'csv', 'hot_mix.csv'))
        row2.addWidget(self.cold_mix.widget()); row2.addWidget(self.hot_mix.widget())

        # гидродинамика + правый столбец (OutputPanel + кнопки)
        row3 = QHBoxLayout(); row3.setSpacing(12); layout.addLayout(row3)
        self.hydro = HydroPanel(); row3.addWidget(self.hydro, 1)

        # правая колонка: OutputPanel + кнопки (чуть шире)
        right_col = QVBoxLayout()
        right_col.setContentsMargins(0,0,0,0); right_col.setSpacing(8)
        self.out_panel = OutputPanel()
        self.out_panel.setMinimumWidth(750)
        right_col.addWidget(self.out_panel)
        btns = QHBoxLayout(); btns.setContentsMargins(0,0,0,0); btns.setSpacing(12)
        self.calc_btn  = QPushButton("Вычислить")
        self.reset_btn = QPushButton("Очистить входные параметры")
        self.calc_btn.setMinimumHeight(36); self.reset_btn.setMinimumHeight(36)
        btns.addWidget(self.calc_btn); btns.addWidget(self.reset_btn)
        right_col.addLayout(btns)
        right_col.addStretch(1)
        row3.addLayout(right_col, 0)

        # связи
        self.calc_btn.clicked.connect(self.on_calc)
        self.reset_btn.clicked.connect(self.on_reset)
        # взаимная блокировка: ввод Q блокирует T+out и наоборот
        try:
            # используем editingFinished — расчёт выполняется после завершения ввода
            self.out_panel.q.editingFinished.connect(self._on_q_edit_finished)
            self.hot_panel.t_out.editingFinished.connect(self._on_tplus_out_edit_finished)
        except Exception:
            pass
        # Подключим auto-calc при завершении ввода основных входных полей
        try:
            for w in (self.cold_panel.t_in, self.cold_panel.t_out, self.cold_panel.m,
                      self.hot_panel.t_in,  self.hot_panel.t_out,  self.hot_panel.m):
                w.editingFinished.connect(self._try_auto_calc)
        except Exception:
            pass
        # Also trigger auto-calc when mixtures change (components/dolya edited or rows changed)
        try:
            self.cold_mix.model.dataChanged.connect(self._try_auto_calc)
            self.cold_mix.model.rowsInserted.connect(self._try_auto_calc)
            self.cold_mix.model.rowsRemoved.connect(self._try_auto_calc)
            self.hot_mix.model.dataChanged.connect(self._try_auto_calc)
            self.hot_mix.model.rowsInserted.connect(self._try_auto_calc)
            self.hot_mix.model.rowsRemoved.connect(self._try_auto_calc)
        except Exception:
            pass

        # update calc button appearance when inputs change
        try:
            for w in (self.cold_panel.t_in, self.cold_panel.t_out, self.cold_panel.m,
                      self.hot_panel.t_in,  self.hot_panel.t_out,  self.hot_panel.m,
                      self.cold_mix.model, self.hot_mix.model, self.out_panel.q):
                # models provide signals; widgets provide editingFinished
                try:
                    w.editingFinished.connect(self._update_calc_button_state)
                except Exception:
                    try:
                        w.dataChanged.connect(self._update_calc_button_state)
                    except Exception:
                        pass
        except Exception:
            pass

        # initial update of button state
        self._update_calc_button_state()

    def _can_compute_sigma_k(self) -> bool:
        """Return True if we have enough validated inputs to compute sigma and k."""
        cold = self.cold_panel.to_dict(); hot = self.hot_panel.to_dict()
        cold_mix = self.cold_mix.mix_rows(); hot_mix = self.hot_mix.mix_rows()

        def mix_valid(mix: list) -> bool:
            try:
                if not mix: return False
                s = sum(float(item.get('share', 0.0)) for item in mix)
                return abs(s - 1.0) <= 1e-3
            except Exception:
                return False

        # require Q present
        if not self.out_panel.q.text().strip():
            return False
        # require both streams to have t_in and t_out and m and valid mixes
        cold_ok = (cold['t_in'] and cold['t_out'] and cold['m']) and mix_valid(cold_mix)
        hot_ok = (hot['t_in'] and hot['t_out'] and hot['m']) and mix_valid(hot_mix)
        return cold_ok and hot_ok

    def _update_calc_button_state(self) -> None:
        """Highlight `self.calc_btn` when sigma/k can be computed by pressing it."""
        try:
            ready = self._can_compute_sigma_k()
            if ready:
                # highlight: yellow background and bold
                self.calc_btn.setStyleSheet('background: #ffec8b; font-weight: 700;')
            else:
                self.calc_btn.setStyleSheet('')
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
                cold = self.cold_panel.to_dict(); hot = self.hot_panel.to_dict()
                cold_mix = self.cold_mix.mix_rows(); hot_mix = self.hot_mix.mix_rows()
                q_val = to_float(self.out_panel.q.text())
                res = getattr(logic, "calculate", None)
                if callable(res):
                    ans = res(cold=cold, hot=hot, cold_mix=cold_mix, hot_mix=hot_mix, q=q_val)
                    if "t_out_plus" in ans:
                        # временно блокируем сигналы при записи
                        self.hot_panel.t_out.blockSignals(True)
                        self.hot_panel.t_out.setText(f"{ans['t_out_plus']:.6g}")
                        self.hot_panel.t_out.blockSignals(False)
        except Exception:
            pass

    def _on_tplus_out_edit_finished(self) -> None:
        # при завершении ввода T+out — блокируем Q и попытка вычислить Q автоматически
        try:
            has_tout = self.hot_panel.t_out.text().strip() != ""
            set_enabled(self.out_panel.q, not has_tout)
            if has_tout:
                cold = self.cold_panel.to_dict(); hot = self.hot_panel.to_dict()
                cold_mix = self.cold_mix.mix_rows(); hot_mix = self.hot_mix.mix_rows()
                q_val = to_float(self.out_panel.q.text())
                res = getattr(logic, "calculate", None)
                if callable(res):
                    ans = res(cold=cold, hot=hot, cold_mix=cold_mix, hot_mix=hot_mix, q=q_val)
                    if "q" in ans:
                        self.out_panel.q.blockSignals(True)
                        self.out_panel.q.setText(f"{ans['q']:.6g}")
                        self.out_panel.q.blockSignals(False)
        except Exception:
            pass

    def on_calc(self) -> None:
        cold = self.cold_panel.to_dict()
        hot  = self.hot_panel.to_dict()
        cold_mix = self.cold_mix.mix_rows()
        hot_mix  = self.hot_mix.mix_rows()
        q_val = to_float(self.out_panel.q.text())

        try:
            res = getattr(logic, "calculate", None)
            if callable(res):
                ans = res(cold=cold, hot=hot, cold_mix=cold_mix, hot_mix=hot_mix, q=q_val)
                if "sigma" in ans:
                    self.out_panel.sigma.setText(format_num(ans['sigma']))
                    set_enabled(self.out_panel.sigma, False)
                if "k"     in ans:
                    self.out_panel.k.setText(format_num(ans['k']))
                    set_enabled(self.out_panel.k, False)
                if "q" in ans:
                    # записываем Q и делаем T+out недоступным для ввода
                    try:
                        self.out_panel.q.blockSignals(True)
                        self.out_panel.q.setText(f"{ans['q']:.6g}")
                        self.out_panel.q.blockSignals(False)
                    except Exception:
                        pass
                    set_enabled(self.hot_panel.t_out, False)
                if "t_out_plus" in ans:
                    self.hot_panel.t_out.setText(f"{ans['t_out_plus']:.6g}")
                    set_enabled(self.out_panel.q, False)
            else:
                QMessageBox.information(self, "Расчёт", "Функция расчёта в logic.py не найдена. Заполните её.")
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
        try:
            res = getattr(logic, "calculate", None)
            if callable(res):
                ans = res(cold=cold, hot=hot, cold_mix=cold_mix, hot_mix=hot_mix, q=q_val)
                # Only apply q or t_out_plus if provided by calculation
                if "q" in ans and (not self.out_panel.q.text().strip()):
                    try:
                        self.out_panel.q.blockSignals(True)
                        self.out_panel.q.setText(f"{ans['q']:.6g}")
                        self.out_panel.q.blockSignals(False)
                    except Exception:
                        pass
                if "t_out_plus" in ans and (not self.hot_panel.t_out.text().strip()):
                    try:
                        self.hot_panel.t_out.blockSignals(True)
                        self.hot_panel.t_out.setText(f"{ans['t_out_plus']:.6g}")
                        self.hot_panel.t_out.blockSignals(False)
                    except Exception:
                        pass
        except Exception:
            pass

    # --- сброс данных ---
    def on_reset(self) -> None:
        # входные поля потоков
        for w in (self.cold_panel.t_in, self.cold_panel.t_out, self.cold_panel.m, self.cold_panel.p,
                  self.hot_panel.t_in,  self.hot_panel.t_out,  self.hot_panel.m,  self.hot_panel.p):
            w.clear(); set_enabled(w, True)
        # смеси
        self.cold_mix.model.removeRows(0, self.cold_mix.model.rowCount())
        self.hot_mix.model.removeRows(0, self.hot_mix.model.rowCount())
        self.cold_mix.update_share_hint(); self.hot_mix.update_share_hint()
        # гидродинамика по умолчанию
        self.hydro.rb_mix_mix.setChecked(True)
        # выходные параметры
        self.out_panel.clear_values()
        set_enabled(self.out_panel.q, True)
        set_enabled(self.hot_panel.t_out, True)

    def _try_auto_calc(self) -> None:
        """Попытаться выполнить расчёт автоматически (вызывается после editingFinished важных полей)."""
        try:
            # Проверим, есть ли все необходимые входы для автоматического вычисления
            cold = self.cold_panel.to_dict(); hot = self.hot_panel.to_dict()
            cold_mix = self.cold_mix.mix_rows(); hot_mix = self.hot_mix.mix_rows()
            q_text = self.out_panel.q.text().strip()
            t_out_hot_text = self.hot_panel.t_out.text().strip()

            def mix_valid(mix: list) -> bool:
                try:
                    if not mix: return False
                    s = sum(float(item.get('share', 0.0)) for item in mix)
                    return abs(s - 1.0) <= 1e-3
                except Exception:
                    return False

            # 1) If Q is empty and we have sufficient data in either stream -> compute Q
            if not q_text:
                cold_ready = (cold['t_in'] and cold['t_out'] and cold['m']) and mix_valid(cold_mix)
                hot_ready = (hot['t_in'] and hot['t_out'] and hot['m']) and mix_valid(hot_mix)
                if cold_ready or hot_ready:
                    self._auto_calc_minimal(); return

            # 2) If t_out_hot is empty but Q is given and hot stream data + mix are valid -> compute t_out_hot
            if not t_out_hot_text and q_text:
                hot_ready_for_tout = (hot['t_in'] and hot['m']) and mix_valid(hot_mix)
                if hot_ready_for_tout:
                    self._auto_calc_minimal(); return
            # otherwise do nothing
        except Exception:
            pass

"""Модуль interface: содержит классы GUI (панели и главное окно).

Точка входа приложения перенесена в main.py.
"""
