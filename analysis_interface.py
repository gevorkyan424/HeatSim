"""analysis_interface.py

Графическое окно анализа вариаций долей компонентов.
"""

from __future__ import annotations

from typing import List, Dict, Any, Tuple
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QWidget,
    QSizePolicy,
    QGroupBox,
    QCheckBox,
    QStyledItemDelegate,
    QLineEdit,
    QLabel,
    QFileDialog,
)
from PyQt5.QtCore import Qt, QTimer, QRegularExpression
from PyQt5.QtGui import QBrush, QColor, QRegularExpressionValidator

try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas  # type: ignore
except Exception:  # fallback older name
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas  # type: ignore
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from matplotlib.backends.backend_pdf import PdfPages
import os
from datetime import datetime

# NOTE: analysis_logic will be integrated later for advanced variation logic
# from analysis_logic import vary_component_shares


class AnalysisWindow(QDialog):
    def __init__(
        self,
        cold_flow: Dict[str, float],
        hot_flow: Dict[str, float],
        cold_mix: List[Dict[str, Any]],
        hot_mix: List[Dict[str, Any]],
        schema: str = "Schema1",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Анализ состава смесей"))
        # Remove question mark help button
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        # Larger, resizable window
        self.resize(1400, 900)
        self.setSizeGripEnabled(True)

        # keep copies of the original mixes (from main window) and working copies
        self._base_cold_mix = [dict(r) for r in cold_mix]
        self._base_hot_mix = [dict(r) for r in hot_mix]
        self._cold_mix = [dict(r) for r in cold_mix]
        self._hot_mix = [dict(r) for r in hot_mix]
        # store original flow states (from main window)
        self._base_cold_flow = dict(cold_flow)
        self._base_hot_flow = dict(hot_flow)
        self._schema = str(schema or "Schema1")
        layout = QVBoxLayout(self)

        # Tables with per-table controls (верх)
        tables_box = QHBoxLayout()
        layout.addLayout(tables_box, 0)
        self.cold_group = QGroupBox(self.tr("Холодный поток"))
        self.hot_group = QGroupBox(self.tr("Горячий поток"))
        # начальная нейтральная тема
        self.cold_group.setStyleSheet("")
        self.hot_group.setStyleSheet("")
        tables_box.addWidget(self.cold_group)
        tables_box.addWidget(self.hot_group)
        cold_box = QVBoxLayout(self.cold_group)
        hot_box = QVBoxLayout(self.hot_group)

        self.cold_table = self._create_table(self._cold_mix)
        self.hot_table = self._create_table(self._hot_mix)
        cold_box.addWidget(self.cold_table)
        hot_box.addWidget(self.hot_table)
        # Labels showing remaining share to 1.0 for each table
        self.cold_remaining_label = QLabel(self.tr("Остаток доли: 1.000000"))
        self.hot_remaining_label = QLabel(self.tr("Остаток доли: 1.000000"))
        self.cold_remaining_label.setStyleSheet("color: #555;")
        self.hot_remaining_label.setStyleSheet("color: #555;")
        cold_box.addWidget(self.cold_remaining_label)
        hot_box.addWidget(self.hot_remaining_label)

        # Buttons under each table
        self.cold_edit_btn = QPushButton(self.tr("Редактировать"))
        self.cold_apply_btn = QPushButton(self.tr("Утвердить"))
        self.hot_edit_btn = QPushButton(self.tr("Редактировать"))
        self.hot_apply_btn = QPushButton(self.tr("Утвердить"))
        cbh = QHBoxLayout()
        cbh.addStretch(1)
        cbh.addWidget(self.cold_edit_btn)
        cbh.addWidget(self.cold_apply_btn)
        cbh.addStretch(1)
        hbh = QHBoxLayout()
        hbh.addStretch(1)
        hbh.addWidget(self.hot_edit_btn)
        hbh.addWidget(self.hot_apply_btn)
        hbh.addStretch(1)
        cold_box.addLayout(cbh)
        hot_box.addLayout(hbh)

        # Global recalc button (hidden until both approved)
        self.run_btn = QPushButton(self.tr("Построить графики"))
        self.run_btn.hide()
        self.run_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.run_btn.setStyleSheet("background-color: gold; font-weight: bold;")
        # Чекбокс на одном уровне с кнопкой; текст сверху, галка снизу
        self.split_label = QLabel(self.tr("Разделить компоненты по графикам"))
        self.split_checkbox = QCheckBox("")
        self.split_container = QWidget()
        _sv = QVBoxLayout(self.split_container)
        _sv.setContentsMargins(0, 0, 0, 0)
        _sv.addWidget(self.split_label, alignment=Qt.AlignHCenter)
        _sv.addWidget(self.split_checkbox, alignment=Qt.AlignHCenter)
        # Строка: кнопка занимает всю доступную ширину, контейнер справа
        btn_row = QHBoxLayout()
        btn_row.addWidget(self.run_btn, 1)
        btn_row.addWidget(self.split_container, 0, alignment=Qt.AlignVCenter)
        # Кнопка экспорта отчёта в PDF (появляется после построения)
        self.export_btn = QPushButton(self.tr("Сформировать отчёт (PDF)"))
        self.export_btn.setEnabled(False)
        self.export_btn.hide()
        btn_row.addWidget(self.export_btn, 0, alignment=Qt.AlignVCenter)
        layout.addLayout(btn_row)
        # Чекбокс появляется только после первого построения и далее не скрывается
        self.split_container.hide()
        self._split_available = False
        self.split_checkbox.setChecked(False)
        self.split_checkbox.toggled.connect(self._on_split_toggled)

        # Blinking timer for the run button
        self._blink_timer = QTimer(self)
        self._blink_timer.setInterval(600)
        self._blink_on = False
        self._blink_base_style = "background-color: gold; font-weight: bold;"
        self._blink_alt_style = "background-color: #ffe066; font-weight: bold;"
        self._blink_timer.timeout.connect(self._toggle_blink)

        # Prevent Enter/Return from triggering buttons implicitly
        for btn in (
            self.cold_edit_btn,
            self.cold_apply_btn,
            self.hot_edit_btn,
            self.hot_apply_btn,
            self.run_btn,
        ):
            btn.setAutoDefault(False)
            btn.setDefault(False)

        # Guard to avoid recursive itemChanged handling
        self._block_item_slot = False
        # React on share edits to keep sum <= 1 and update remaining labels
        self.cold_table.itemChanged.connect(self._on_table_item_changed)
        self.hot_table.itemChanged.connect(self._on_table_item_changed)

        # Figure with 3 subplots (внизу)
        self.fig = Figure(figsize=(12, 5))
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.canvas, 1)
        self._ensure_main_axes()

        # Description label (пояснение)
        self.desc_label = QPushButton()
        self.desc_label.setEnabled(False)
        self.desc_label.setText(
            self.tr(
                "Каждая кривая: независимый сценарий варьирования доли одного компонента от 0 до 1 с равным распределением остатка."
            )
        )
        layout.addWidget(self.desc_label)

        # Connections
        # Оба переходят в режим редактирования
        self.cold_edit_btn.clicked.connect(self._enter_edit_mode)
        self.hot_edit_btn.clicked.connect(self._enter_edit_mode)
        self.cold_apply_btn.clicked.connect(
            lambda: self._apply_table(self.cold_table, which="cold")
        )
        self.hot_apply_btn.clicked.connect(
            lambda: self._apply_table(self.hot_table, which="hot")
        )
        # Кнопка построения отключена (построение выполняется автоматически)
        # Экспорт отчёта (PDF)
        self.export_btn.clicked.connect(self._on_export_pdf)
        # Закрыть раздельное окно при уничтожении основного
        try:
            self.destroyed.connect(self._on_destroyed)
        except Exception:
            pass

        self._cold_locked = False
        self._hot_locked = False
        # initial state: editing enabled for share column
        self._set_table_editable(self.cold_table, True)
        self._set_table_editable(self.hot_table, True)
        # ensure normal visual (not grey) at start
        self._set_table_locked_visual(self.cold_table, False)
        self._set_table_locked_visual(self.hot_table, False)
        # начальная подсветка: редактирование активно => жёлтый фон
        self._set_group_highlight("cold", "editing")
        self._set_group_highlight("hot", "editing")
        # Ограничение ввода: только числа [0..1] (точка или запятая)
        share_delegate = _Share01Delegate(self)
        self.cold_table.setItemDelegateForColumn(1, share_delegate)
        self.hot_table.setItemDelegateForColumn(1, share_delegate)

        # Initial empty plot (will fill once both approved and run clicked)
        empty: Dict[str, List[float]] = {}
        self._update_plot(empty, empty, empty, empty)
        # Отдельное окно для раздельных графиков
        self._split_window = None  # type: ignore[var-annotated]
        # Кэш последних данных графиков для мгновенного переключения вида
        self._last_series_x = {}
        self._last_series_q = {}
        self._last_series_sigma = {}
        self._last_series_k = {}
        # Initial remaining recalculation
        self._recalc_remaining_for(self.cold_table, self.cold_remaining_label)
        self._recalc_remaining_for(self.hot_table, self.hot_remaining_label)

    def _ensure_main_axes(self) -> None:
        # (Re)create the standard 1x3 axes layout
        try:
            self.fig.clear()
        except Exception:
            pass
        self.ax_q = self.fig.add_subplot(131)
        self.ax_sigma = self.fig.add_subplot(132)
        self.ax_k = self.fig.add_subplot(133)
        for ax, title in [
            (self.ax_q, self.tr("Q (кВт)")),
            (self.ax_sigma, self.tr("σ (кВт/К)")),
            (self.ax_k, self.tr("K (кВт/К)")),
        ]:
            ax.set_title(title)
            ax.set_xlabel(self.tr("Доля компонента (сценарий)"))
            ax.grid(True, linestyle=":", alpha=0.5)
        self.fig.tight_layout()
        self.canvas.draw_idle()

    def _enter_edit_mode(self) -> None:
        # Сброс блокировок обеих таблиц
        self._cold_locked = False
        self._hot_locked = False
        # Визуал и редактирование
        self._set_table_locked_visual(self.cold_table, False)
        self._set_table_locked_visual(self.hot_table, False)
        self._set_table_editable(self.cold_table, True)
        self._set_table_editable(self.hot_table, True)
        # Подсветка
        self._set_group_highlight("cold", "editing")
        self._set_group_highlight("hot", "editing")
        # Кнопка построения скрыта; построение будет выполняться автоматически
        # Оставляем чекбокс как есть; если окно раздельных графиков открыто — оно остаётся и обновится после пересчета
        # Останавливаем мигание
        self._blink_timer.stop()
        self._blink_on = False
        self.run_btn.setStyleSheet(self._blink_base_style)
        # Обновить комбинированные графики с последними данными
        self._ensure_main_axes()
        try:
            if self._last_series_x:
                self._update_plot(
                    self._last_series_x,
                    self._last_series_q,
                    self._last_series_sigma,
                    self._last_series_k,
                )
        except Exception:
            pass

    def _toggle_blink(self) -> None:
        if not self.run_btn.isVisible():
            return
        self._blink_on = not self._blink_on
        self.run_btn.setStyleSheet(
            self._blink_alt_style if self._blink_on else self._blink_base_style
        )

    def _create_table(self, data: List[Dict[str, Any]]):
        table = QTableWidget()
        headers = [
            "Компонент",
            "Доля",
            "Tb, K",
            "C_f, кДж/(кг·К)",
            "C_p, кДж/(кг·К)",
            "r_f, кДж/кг",
        ]
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        hdr = table.horizontalHeader()
        hf = hdr.font()
        hf.setBold(True)
        hdr.setFont(hf)
        # enforce constant bold regardless of selection state
        hdr.setStyleSheet("QHeaderView::section { font-weight: bold; }")
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setRowCount(len(data))
        for r, row in enumerate(data):
            keys = ["name", "share", "tb", "cf", "cp", "rf"]
            for c, key in enumerate(keys):
                val = row.get(key, "")
                # Форматируем долю без лишних нулей
                if key == "share":
                    try:
                        sval = self._fmt_num(float(val))
                    except Exception:
                        sval = str(val)
                    item = QTableWidgetItem(sval)
                else:
                    item = QTableWidgetItem(str(val))
                if key != "share":
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                table.setItem(r, c, item)
        table.resizeColumnsToContents()
        table.setColumnWidth(0, 175)
        table.setColumnWidth(1, 70)
        table.setColumnWidth(2, 70)
        table.horizontalHeader().setStretchLastSection(True)
        return table

    def _read_tables(self):
        # only read from tables (editing may be disabled per-table)

        def read(tbl: QTableWidget) -> List[Dict[str, Any]]:
            out: List[Dict[str, Any]] = []
            for r in range(tbl.rowCount()):
                try:
                    it0 = tbl.item(r, 0)
                    it1 = tbl.item(r, 1)
                    it2 = tbl.item(r, 2)
                    it3 = tbl.item(r, 3)
                    it4 = tbl.item(r, 4)
                    it5 = tbl.item(r, 5)
                    if not all([it0, it1, it2, it3, it4, it5]):
                        continue
                    name = it0.text() if it0 else ""
                    share = float(it1.text().replace(",", ".")) if it1 else 0.0
                    tb = float(it2.text().replace(",", ".")) if it2 else 0.0
                    cf = float(it3.text().replace(",", ".")) if it3 else 0.0
                    cp = float(it4.text().replace(",", ".")) if it4 else 0.0
                    rf = float(it5.text().replace(",", ".")) if it5 else 0.0
                except Exception:
                    continue
                out.append(
                    {
                        "name": name,
                        "share": share,
                        "tb": tb,
                        "cf": cf,
                        "cp": cp,
                        "rf": rf,
                    }
                )
            return out

        # keep existing meta (rf) default 0.0
        self._cold_mix = read(self.cold_table)
        self._hot_mix = read(self.hot_table)

    def recalculate(self):
        # Only run if both tables locked (approved)
        if not (self._cold_locked and self._hot_locked):
            QMessageBox.information(
                self, self.tr("Анализ"), self.tr("Сначала утвердите обе таблицы.")
            )
            return
        # read approved tables (analysis window values)
        self._read_tables()
        import logic

        series_q: Dict[str, List[float]] = {}
        series_sigma: Dict[str, List[float]] = {}
        series_k: Dict[str, List[float]] = {}
        series_x: Dict[str, List[float]] = {}

        def gen_axis(start: float, end: float, step_abs: float = 0.1) -> List[float]:
            # generate list of values from start to end with steps of magnitude step_abs
            if abs(end - start) < 1e-9:
                return [round(start, 6)]
            vals: List[float] = []
            sgn = 1 if end > start else -1
            step = sgn * abs(step_abs)
            v = start
            vals.append(round(v, 6))
            # step until we pass end
            while True:
                v_next = v + step
                if (sgn > 0 and v_next < end - 1e-9) or (
                    sgn < 0 and v_next > end + 1e-9
                ):
                    vals.append(round(v_next, 6))
                    v = v_next
                    continue
                break
            if abs(vals[-1] - end) > 1e-9:
                vals.append(round(end, 6))
            # clamp to [0,1]
            vals = [min(max(0.0, float(x)), 1.0) for x in vals]
            return vals

        # helper to build mix variant when varying index idx in base_mix to value val
        def build_variant(
            base_mix: List[Dict[str, Any]], idx: int, val: float
        ) -> List[Dict[str, Any]]:
            others = [j for j in range(len(base_mix)) if j != idx]
            if others:
                rest = (1.0 - val) / len(others)
            else:
                rest = 0.0
            new_mix: List[Dict[str, Any]] = []
            for j, comp in enumerate(base_mix):
                if j == idx:
                    new_mix.append({**comp, "share": float(val)})
                else:
                    new_mix.append({**comp, "share": float(rest)})
            return new_mix

        # For cold components: vary from main-window base to approved value; hot mix kept as approved
        for i, comp in enumerate(self._cold_mix):
            name = comp.get("name", f"c{i}")
            # find original share from base mix by name (fallback to index)
            orig_share = 0.0
            try:
                orig_share = float(
                    next(
                        (
                            c.get("share", 0.0)
                            for c in self._base_cold_mix
                            if c.get("name") == name
                        ),
                        self._base_cold_mix[i].get("share", 0.0),
                    )
                )
            except Exception:
                orig_share = float(self._base_cold_mix[i].get("share", 0.0))
            approved_share = float(comp.get("share", 0.0))
            axis = gen_axis(orig_share, approved_share, 0.1)
            q_vals: List[float] = []
            sigma_vals: List[float] = []
            k_vals: List[float] = []
            for v in axis:
                mix_c = build_variant(self._base_cold_mix, i, v)
                mix_h = [dict(r) for r in self._hot_mix]
                ans = logic.calculate(
                    cold=self._base_cold_flow,
                    hot=self._base_hot_flow,
                    cold_mix=mix_c,
                    hot_mix=mix_h,
                    q=0.0,
                    schema=self._schema,
                )
                q_vals.append(float(ans.get("q", 0.0)))
                sigma_vals.append(float(ans.get("sigma", 0.0)))
                k_vals.append(float(ans.get("k", 0.0)))
            label = f"C:{name}"
            series_x[label] = axis
            series_q[label] = q_vals
            series_sigma[label] = sigma_vals
            series_k[label] = k_vals

        # For hot components: vary from main-window base to approved value; cold mix kept as approved
        for i, comp in enumerate(self._hot_mix):
            name = comp.get("name", f"h{i}")
            try:
                orig_share = float(
                    next(
                        (
                            c.get("share", 0.0)
                            for c in self._base_hot_mix
                            if c.get("name") == name
                        ),
                        self._base_hot_mix[i].get("share", 0.0),
                    )
                )
            except Exception:
                orig_share = float(self._base_hot_mix[i].get("share", 0.0))
            approved_share = float(comp.get("share", 0.0))
            axis = gen_axis(orig_share, approved_share, 0.1)
            q_vals: List[float] = []
            sigma_vals: List[float] = []
            k_vals: List[float] = []
            for v in axis:
                mix_h = build_variant(self._base_hot_mix, i, v)
                mix_c = [dict(r) for r in self._cold_mix]
                ans = logic.calculate(
                    cold=self._base_cold_flow,
                    hot=self._base_hot_flow,
                    cold_mix=mix_c,
                    hot_mix=mix_h,
                    q=0.0,
                    schema=self._schema,
                )
                q_vals.append(float(ans.get("q", 0.0)))
                sigma_vals.append(float(ans.get("sigma", 0.0)))
                k_vals.append(float(ans.get("k", 0.0)))
            label = f"H:{name}"
            series_x[label] = axis
            series_q[label] = q_vals
            series_sigma[label] = sigma_vals
            series_k[label] = k_vals

        # Update plot(s)
        # Сохраняем кэш для дальнейшего быстрого переключения
        self._last_series_x = series_x
        self._last_series_q = series_q
        self._last_series_sigma = series_sigma
        self._last_series_k = series_k

        # Показываем переключатель разделения после построения (каждый раз)
        if hasattr(self, "split_container"):
            self.split_container.show()
        else:
            self.split_checkbox.show()
        self._split_available = True

        # Всегда обновляем комбинированный вид в основном окне
        self._ensure_main_axes()
        self._update_plot(
            self._last_series_x,
            self._last_series_q,
            self._last_series_sigma,
            self._last_series_k,
        )
        # Если раздельное окно активно — обновляем и его
        if self.split_checkbox.isChecked():
            try:
                self._open_or_update_split_window(
                    self._last_series_x,
                    self._last_series_q,
                    self._last_series_sigma,
                    self._last_series_k,
                )
            except Exception:
                pass
        # Показать и активировать экспорт PDF, когда данные готовы
        try:
            self.export_btn.setEnabled(bool(self._last_series_x))
            if self._last_series_x:
                self.export_btn.show()
        except Exception:
            pass
        # Кнопка построения не используется — скрываем (на случай, если она где-то стала видимой)
        try:
            self.run_btn.hide()
        except Exception:
            pass

    def _on_split_toggled(self, checked: bool) -> None:
        # Переключение отдельного окна раздельных графиков
        if not self._split_available:
            return
        if checked:
            if not (
                self._last_series_x
                or self._last_series_q
                or self._last_series_sigma
                or self._last_series_k
            ):
                # Если данных нет, но обе таблицы утверждены — пробуем пересчитать
                if self._cold_locked and self._hot_locked:
                    self.recalculate()
                    return
                else:
                    return
            self._open_or_update_split_window(
                self._last_series_x,
                self._last_series_q,
                self._last_series_sigma,
                self._last_series_k,
            )
        else:
            # Закрыть доп окно, если открыто
            try:
                sw = getattr(self, "_split_window", None)
                if sw is not None:
                    sw.close()
                    self._split_window = None
            except Exception:
                pass

    def _build_scenarios(
        self,
    ) -> Dict[
        str, Tuple[List[float], List[List[Dict[str, Any]]], List[List[Dict[str, Any]]]]
    ]:
        scenarios: Dict[
            str,
            Tuple[List[float], List[List[Dict[str, Any]]], List[List[Dict[str, Any]]]],
        ] = {}
        n_points = 21

        # Helper to generate varied mixes for one component index
        def vary_mix(
            base_mix: List[Dict[str, Any]], idx: int
        ) -> Tuple[List[float], List[List[Dict[str, Any]]]]:
            if not base_mix:
                return [], []
            others = [i for i in range(len(base_mix)) if i != idx]
            shares_axis: List[float] = []
            variants: List[List[Dict[str, Any]]] = []
            for i in range(n_points):
                val = i / (n_points - 1)
                if others:
                    rest_share = (1.0 - val) / len(others)
                else:
                    rest_share = 0.0
                new_mix: List[Dict[str, Any]] = []
                for j, comp in enumerate(base_mix):
                    if j == idx:
                        new_comp = {**comp, "share": val}
                        new_mix.append(new_comp)
                    else:
                        new_comp = {**comp, "share": rest_share}
                        new_mix.append(new_comp)
                shares_axis.append(val)
                variants.append(new_mix)
            return shares_axis, variants

        # Build scenarios for cold components
        for i, comp in enumerate(self._cold_mix):
            shares_axis, variants_cold = vary_mix(self._cold_mix, i)
            # hot stays base
            hot_variants = [self._hot_mix for _ in variants_cold]
            label = f"C:{comp.get('name','c'+str(i))}"
            scenarios[label] = (shares_axis, variants_cold, hot_variants)
        # Build scenarios for hot components
        for i, comp in enumerate(self._hot_mix):
            shares_axis, variants_hot = vary_mix(self._hot_mix, i)
            cold_variants = [self._cold_mix for _ in variants_hot]
            label = f"H:{comp.get('name','h'+str(i))}"
            scenarios[label] = (shares_axis, cold_variants, variants_hot)
        return scenarios

    def _update_plot(
        self,
        series_x: Dict[str, List[float]],
        series_q: Dict[str, List[float]],
        series_sigma: Dict[str, List[float]],
        series_k: Dict[str, List[float]],
    ) -> None:
        for ax in (self.ax_q, self.ax_sigma, self.ax_k):
            ax.clear()
        color_cycle = [
            "#1f77b4",
            "#ff7f0e",
            "#2ca02c",
            "#d62728",
            "#9467bd",
            "#8c564b",
            "#e377c2",
            "#7f7f7f",
            "#bcbd22",
            "#17becf",
        ]

        def plot_series(
            ax: Axes, data_dict: Dict[str, List[float]], y_label: str
        ) -> None:
            total = len(data_dict)
            for idx, (label, xs) in enumerate(data_dict.items()):
                color = color_cycle[idx % len(color_cycle)]
                ys = None
                if y_label == "Q":
                    ys = series_q.get(label, [])
                elif y_label == "Sigma":
                    ys = series_sigma.get(label, [])
                else:
                    ys = series_k.get(label, [])
                if xs and ys:
                    # apply tiny horizontal offset per series to avoid exact overlap of markers
                    try:
                        jitter = 0.001
                        offset = (idx - (total - 1) / 2.0) * jitter
                        xs_plot = [min(max(0.0, float(x) + offset), 1.0) for x in xs]
                    except Exception:
                        xs_plot = xs
                    ax.plot(
                        xs_plot,
                        ys,
                        marker="o",
                        linestyle="-",
                        label=label,
                        color=color,
                        markersize=3,
                    )
            # Ось X локализуем, как и на экране
            ax.set_xlabel(self.tr("Доля компонента (сценарий)"))
            ax.grid(True, linestyle=":", alpha=0.4)

        plot_series(self.ax_q, series_x, "Q")
        plot_series(self.ax_sigma, series_x, "Sigma")
        plot_series(self.ax_k, series_x, "K")
        self.ax_q.set_title(self.tr("Q (кВт)"))
        self.ax_sigma.set_title(self.tr("σ (кВт/К)"))
        self.ax_k.set_title(self.tr("K (кВт/К)"))
        # Легенды компактно
        for ax in (self.ax_q, self.ax_sigma, self.ax_k):
            ax.legend(fontsize=7, loc="best")
        self.fig.tight_layout()
        self.canvas.draw_idle()

    def _open_or_update_split_window(
        self,
        series_x: Dict[str, List[float]],
        series_q: Dict[str, List[float]],
        series_sigma: Dict[str, List[float]],
        series_k: Dict[str, List[float]],
    ) -> None:
        # Создать окно при необходимости
        if getattr(self, "_split_window", None) is None:
            self._split_window = _SplitPlotsWindow(self)
            # Позиционирование: по центру относительно экрана
            try:
                self._split_window.position_centered(self)
            except Exception:
                pass
            self._split_window.show()
        # Обновить наполнение
        sw = getattr(self, "_split_window", None)
        if sw is not None:
            sw.update_plots(series_x, series_q, series_sigma, series_k)

    def _set_table_editable(self, table: QTableWidget, editable: bool):
        for r in range(table.rowCount()):
            # only column 1 (share)
            it = table.item(r, 1)
            if it:
                if editable:
                    it.setFlags(it.flags() | Qt.ItemIsEditable)
                else:
                    it.setFlags(it.flags() & ~Qt.ItemIsEditable)
        table.viewport().update()

    def _fmt_num(self, x: float, decimals: int = 6) -> str:
        try:
            s = f"{float(x):.{decimals}f}"
            s = s.rstrip("0").rstrip(".")
            return s if s else "0"
        except Exception:
            return str(x)

    def _recalc_remaining_for(self, table: QTableWidget, label: QLabel) -> None:
        total = 0.0
        try:
            for r in range(table.rowCount()):
                it = table.item(r, 1)
                if not it:
                    continue
                v = float(it.text().replace(",", "."))
                total += max(0.0, v)
        except Exception:
            pass
        excess = total - 1.0
        try:
            if excess > 1e-9:
                label.setText(f"Перебор: {self._fmt_num(excess)}")
                label.setStyleSheet("color: #d32f2f; font-weight: bold;")
            else:
                remaining = max(0.0, 1.0 - total)
                label.setText(f"Остаток доли: {self._fmt_num(remaining)}")
                label.setStyleSheet("color: #555;")
        except Exception:
            pass

    def _on_table_item_changed(self, it: QTableWidgetItem) -> None:
        if self._block_item_slot:
            return
        tbl = it.tableWidget()
        # update only for share column
        if it.column() != 1:
            # still refresh remaining to reflect any dependencies
            if tbl is self.cold_table:
                self._recalc_remaining_for(self.cold_table, self.cold_remaining_label)
            elif tbl is self.hot_table:
                self._recalc_remaining_for(self.hot_table, self.hot_remaining_label)
            return
        # parse current value
        txt = it.text() or ""
        try:
            val = float(txt.replace(",", ".")) if txt else 0.0
            if val < 0:
                val = 0.0
        except Exception:
            val = 0.0
        # only clamp per-cell to [0..1], allow временное превышение суммы
        new_val = min(max(0.0, val), 1.0)
        # write back if clamped or normalization/formatting differs
        new_txt = self._fmt_num(new_val)
        if abs(new_val - val) > 1e-12 or (txt and "," in txt) or (txt != new_txt):
            try:
                self._block_item_slot = True
                it.setText(new_txt)
            finally:
                self._block_item_slot = False
        # update remaining label
        if tbl is self.cold_table:
            self._recalc_remaining_for(self.cold_table, self.cold_remaining_label)
        elif tbl is self.hot_table:
            self._recalc_remaining_for(self.hot_table, self.hot_remaining_label)

    def _set_table_locked_visual(self, table: QTableWidget, locked: bool) -> None:
        color = QColor("#9e9e9e") if locked else QColor("#000000")
        brush = QBrush(color)
        rows = table.rowCount()
        cols = table.columnCount()
        for r in range(rows):
            for c in range(cols):
                it = table.item(r, c)
                if it:
                    it.setForeground(brush)
        table.viewport().update()

    def _set_group_highlight(self, which: str, mode: str) -> None:
        """Подсветка группбокса таблицы: editing -> жёлтый, approved -> зелёный, other -> сброс."""
        gb = self.cold_group if which == "cold" else self.hot_group
        if mode == "editing":
            gb.setStyleSheet(
                "QGroupBox { background-color: #fff3cd; border: 1px solid #e0a800; border-radius: 4px; margin-top: 6px; }"
                "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }"
            )
        elif mode == "approved":
            gb.setStyleSheet(
                "QGroupBox { background-color: #d4edda; border: 1px solid #28a745; border-radius: 4px; margin-top: 6px; }"
                "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }"
            )
        else:
            gb.setStyleSheet("")

    def _apply_table(self, table: QTableWidget, which: str):
        # validate sum of shares == 1
        total = 0.0
        try:
            for r in range(table.rowCount()):
                it = table.item(r, 1)
                if not it:
                    continue
                val = float(it.text().replace(",", "."))
                if val < 0:
                    raise ValueError("Отрицательная доля")
                total += val
        except Exception:
            QMessageBox.warning(
                self, self.tr("Анализ"), self.tr("Некорректные значения долей.")
            )
            return
        if abs(total - 1.0) > 1e-6:
            QMessageBox.warning(
                self,
                self.tr("Анализ"),
                self.tr("Сумма долей должна быть = 1.0 (текущая: {val:.6f}).").format(val=total),
            )
            return
        self._set_table_editable(table, False)
        if which == "cold":
            self._cold_locked = True
        else:
            self._hot_locked = True
        self._set_table_locked_visual(table, True)
        # зелёная подсветка после утверждения
        try:
            self._set_group_highlight(which, "approved")
        except Exception:
            pass
        self._read_tables()
        # Автоматическое построение: если обе таблицы утверждены — сразу пересчитываем и строим
        can_recalc = self._cold_locked and self._hot_locked
        if can_recalc:
            try:
                self.recalculate()
            except Exception:
                pass
        part = self.tr("Холодный") if which == "cold" else self.tr("Горячий")
        QMessageBox.information(
            self,
            self.tr("Анализ"),
            self.tr("Таблица '{part}' поток' утверждена.").format(part=part),
        )

    def _on_edit_clicked(self, table: QTableWidget, which: str):
        if which == "cold":
            self._cold_locked = False
        else:
            self._hot_locked = False
        # жёлтая подсветка при редактировании
        try:
            self._set_group_highlight(which, "editing")
        except Exception:
            pass
        # Кнопка построения скрыта (не используется)
        # Оставляем переключатель и окно раздельных графиков доступными
        # (обновятся после следующего пересчета)
        # Остановить мигание и вернуть базовый стиль
        self._blink_timer.stop()
        self._blink_on = False
        self.run_btn.setStyleSheet(self._blink_base_style)
        # Разблокировать визуал и редактирование
        self._set_table_locked_visual(table, False)
        self._set_table_editable(table, True)
        # Вернуть 3 основных графика (если были раздельные)
        self._ensure_main_axes()
        try:
            if self._last_series_x:
                self._update_plot(
                    self._last_series_x,
                    self._last_series_q,
                    self._last_series_sigma,
                    self._last_series_k,
                )
                # И обновим окно раздельных графиков, если активно
                if self.split_checkbox.isChecked():
                    try:
                        sw = getattr(self, "_split_window", None)
                        if sw is not None:
                            sw.update_plots(
                                self._last_series_x,
                                self._last_series_q,
                                self._last_series_sigma,
                                self._last_series_k,
                            )
                    except Exception:
                        pass
        except Exception:
            pass

    def _on_run_clicked(self):
        self.recalculate()
        self._blink_timer.stop()
        self._blink_on = False
        self.run_btn.setStyleSheet(self._blink_base_style)

    def _on_destroyed(self) -> None:
        # При уничтожении окна анализа закрыть и окно раздельных графиков
        try:
            sw = getattr(self, "_split_window", None)
            if sw is not None:
                sw.close()
                self._split_window = None
        except Exception:
            pass

    def _on_export_pdf(self) -> None:
        # Экспорт текущих графиков в PDF: опции — комбинированный, раздельный, оба; + титульная страница
        try:
            default_name = os.path.join(os.path.expanduser("~"), "analysis_report.pdf")
            path, _ = QFileDialog.getSaveFileName(
                self,
                self.tr("Сохранить отчёт (PDF)"),
                default_name,
                "PDF (*.pdf)"
            )
            if not path:
                return
            # гарантируем расширение .pdf
            if not path.lower().endswith(".pdf"):
                path = f"{path}.pdf"
            # Выбор страниц для экспорта
            choice = _ExportPdfOptionsDialog.ask(self)
            if choice is None:
                return
            # Создание PDF
            with PdfPages(path) as pdf:
                # Страница 1: титульная с исходными данными
                try:
                    fig_hdr = self._generate_header_figure()
                    pdf.savefig(fig_hdr)
                except Exception:
                    pass
                # Далее: выбранные страницы с графиками
                include_combined, include_split = choice
                if include_combined:
                    # Комбинированные
                    try:
                        self.fig.tight_layout()
                    except Exception:
                        pass
                    pdf.savefig(self.fig)
                try:
                    if include_split:
                        sw = getattr(self, "_split_window", None)
                        if sw is None:
                            # Создать временное окно (не показывать) и нарисовать данные
                            sw = _SplitPlotsWindow(None)
                            try:
                                sw.update_plots(
                                    self._last_series_x,
                                    self._last_series_q,
                                    self._last_series_sigma,
                                    self._last_series_k,
                                )
                            except Exception:
                                pass
                        try:
                            sw.fig.tight_layout()
                        except Exception:
                            pass
                        pdf.savefig(sw.fig)
                except Exception:
                    pass
                # Метаданные
                try:
                    pdf.infodict()["Title"] = "HeatSim Analysis Report"
                    pdf.infodict()["Author"] = "HeatSim"
                    pdf.infodict()["Subject"] = "Component share variation analysis"
                    # Используем текущую дату/время как строку ISO для совместимости
                    pdf.infodict()["CreationDate"] = datetime.now().isoformat()
                except Exception:
                    pass
            QMessageBox.information(
                self,
                self.tr("Экспорт PDF"),
                self.tr("Отчёт успешно сохранён: {path}").format(path=path),
            )
        except Exception as e:
            QMessageBox.warning(
                self,
                self.tr("Экспорт PDF"),
                self.tr("Ошибка сохранения отчёта: {e}").format(e=e),
            )

    def _generate_header_figure(self) -> Figure:
        # Создаёт титульную страницу с исходными параметрами и схемой
        fig = Figure(figsize=(8.27, 11.69))  # A4 портретная
        ax = fig.add_subplot(111)
        ax.axis('off')
        # Заголовки/текст
        title = self.tr("Отчёт анализа HeatSim")
        schema_txt = f"{self.tr('Схема')}: {self._schema}"
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        when = f"{self.tr('Дата/время')}: {ts}"
        # Потоки
        def fmt_flow(name: str, flow: Dict[str, float]) -> str:
            t_in = flow.get('t_in', 0.0)
            t_out = flow.get('t_out', 0.0)
            m = flow.get('m', 0.0)
            return f"{name}: T_in={t_in:.3f} K, T_out={t_out:.3f} K, m={m:.6f} kg/s"
        cold_line = fmt_flow(self.tr('Холодный поток'), self._base_cold_flow)
        hot_line = fmt_flow(self.tr('Горячий поток'), self._base_hot_flow)
        # Смеси: имя и доля
        def fmt_mix(title: str, mix: List[Dict[str, Any]]) -> str:
            parts: List[str] = []
            for comp in mix:
                name = str(comp.get('name', ''))
                share = float(comp.get('share', 0.0))
                parts.append(f"- {name}: {share:.4f}")
            return title + "\n" + "\n".join(parts)
        cold_mix_txt = fmt_mix(self.tr('Состав холодной смеси'), self._base_cold_mix)
        hot_mix_txt = fmt_mix(self.tr('Состав горячей смеси'), self._base_hot_mix)
        text = (
            f"{title}\n\n"
            f"{schema_txt}\n{when}\n\n"
            f"{cold_line}\n{hot_line}\n\n"
            f"{cold_mix_txt}\n\n{hot_mix_txt}"
        )
        ax.text(0.05, 0.95, text, va='top', ha='left', fontsize=11)
        return fig


class _ExportPdfOptionsDialog(QDialog):
    """Диалог выбора страниц для экспорта PDF."""
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr('Экспорт PDF'))
        self.setModal(True)
        v = QVBoxLayout(self)
        self.lbl = QLabel(self.tr('Что экспортировать?'))
        v.addWidget(self.lbl)
        hb = QHBoxLayout()
        v.addLayout(hb)
        self.btn_combined = QPushButton(self.tr('Комбинированные'))
        self.btn_split = QPushButton(self.tr('Раздельные'))
        self.btn_both = QPushButton(self.tr('Оба'))
        hb.addWidget(self.btn_combined)
        hb.addWidget(self.btn_split)
        hb.addWidget(self.btn_both)
        # Результат
        self._choice: tuple[bool, bool] | None = None
        self.btn_combined.clicked.connect(lambda: self._set_choice(True, False))
        self.btn_split.clicked.connect(lambda: self._set_choice(False, True))
        self.btn_both.clicked.connect(lambda: self._set_choice(True, True))

    def _set_choice(self, combined: bool, split: bool) -> None:
        self._choice = (combined, split)
        self.accept()

    @staticmethod
    def ask(parent: QWidget) -> tuple[bool, bool] | None:
        dlg = _ExportPdfOptionsDialog(parent)
        rc = dlg.exec_()
        return dlg._choice if rc == QDialog.Accepted else None


class _SplitPlotsWindow(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Графики по компонентам"))
        # Немодальное отдельное окно
        self.setModal(False)
        self.setWindowModality(Qt.NonModal)
        self.setWindowFlags(self.windowFlags() | Qt.Window)
        self.setAttribute(Qt.WA_DeleteOnClose, True)

        v = QVBoxLayout(self)
        self.fig = Figure(figsize=(10, 6))
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        v.addWidget(self.canvas)

    def closeEvent(self, event):  # type: ignore[override]
        # Сообщаем родителю, что окно закрыто — сброс чекбокса, но оставляем возможность открыть снова
        try:
            parent = self.parent()
            if isinstance(parent, AnalysisWindow):
                # Сбрасываем чекбокс, но не ломаем логику пересчета
                try:
                    parent.split_checkbox.blockSignals(True)
                    parent.split_checkbox.setChecked(False)
                finally:
                    parent.split_checkbox.blockSignals(False)
                # через публичный путь
                setattr(parent, "_split_window", None)
        except Exception:
            pass
        try:
            super().closeEvent(event)  # type: ignore[arg-type]
        except Exception:
            pass

    def position_next_to(self, anchor: QWidget) -> None:
        try:
            ag = anchor.frameGeometry()
            scr = anchor.screen()
            avail = scr.availableGeometry()
            w = max(900, min(1100, avail.width() // 2))
            h = min(max(600, anchor.height()), avail.height() - 40)
            # сначала пробуем справа
            x_right = ag.x() + ag.width() + 10
            x = x_right
            y = ag.y()
            # если не помещается справа — открываем слева
            if x + w > avail.x() + avail.width():
                x_left = ag.x() - w - 10
                if x_left >= avail.x():
                    x = x_left
                else:
                    # fallback: прижаться к правому краю экрана
                    x = avail.x() + avail.width() - w - 10
            # вертикальные рамки
            if y + h > avail.y() + avail.height():
                y = max(avail.y(), avail.y() + avail.height() - h - 10)
            self.setGeometry(x, y, w, h)
        except Exception:
            pass

    def position_centered(self, anchor: QWidget) -> None:
        """Разместить окно по центру доступной области экрана якорного окна."""
        try:
            scr = anchor.screen()
            avail = scr.availableGeometry()
            # Размеры окна: используем разумные границы
            w = max(900, min(1100, int(avail.width() * 0.6)))
            h = max(600, min(int(avail.height() * 0.7), avail.height() - 40))
            x = avail.x() + (avail.width() - w) // 2
            y = avail.y() + (avail.height() - h) // 2
            self.setGeometry(x, y, w, h)
        except Exception:
            # Fallback — сохраняем текущее положение
            pass

    def update_plots(
        self,
        series_x: Dict[str, List[float]],
        series_q: Dict[str, List[float]],
        series_sigma: Dict[str, List[float]],
        series_k: Dict[str, List[float]],
    ) -> None:
        try:
            labels = [lbl for lbl in sorted(series_x.keys()) if series_x.get(lbl)]
            n = len(labels)
            self.fig.clear()
            if n == 0:
                self.canvas.draw_idle()
                return
            for row, label in enumerate(labels, start=1):
                xs = series_x.get(label, [])
                qs = series_q.get(label, [])
                sg = series_sigma.get(label, [])
                ks = series_k.get(label, [])
                ax1 = self.fig.add_subplot(n, 3, (row - 1) * 3 + 1)
                ax2 = self.fig.add_subplot(n, 3, (row - 1) * 3 + 2)
                ax3 = self.fig.add_subplot(n, 3, (row - 1) * 3 + 3)
                if xs and qs:
                    ax1.plot(xs, qs, marker="o", linestyle="-", color="#1f77b4")
                ax1.set_title(f"{label} — {self.tr('Q (кВт)')}")
                ax1.set_xlabel(self.tr("Доля компонента"))
                ax1.grid(True, linestyle=":", alpha=0.4)

                if xs and sg:
                    ax2.plot(xs, sg, marker="o", linestyle="-", color="#d62728")
                ax2.set_title(f"{label} — {self.tr('σ (кВт/К)')}")
                ax2.set_xlabel(self.tr("Доля компонента"))
                ax2.grid(True, linestyle=":", alpha=0.4)

                if xs and ks:
                    ax3.plot(xs, ks, marker="o", linestyle="-", color="#2ca02c")
                ax3.set_title(f"{label} — {self.tr('K (кВт/К)')}")
                ax3.set_xlabel(self.tr("Доля компонента"))
                ax3.grid(True, linestyle=":", alpha=0.4)

            self.fig.tight_layout()
            self.canvas.draw_idle()
        except Exception:
            try:
                self.fig.clear()
                self.canvas.draw_idle()
            except Exception:
                pass


class _Share01Delegate(QStyledItemDelegate):
    """Разрешает ввод только чисел в диапазоне [0..1] в колонке доли.
    Допустимы точка или запятая как разделитель."""

    def createEditor(self, parent, option, index):  # type: ignore[override]
        if index.column() == 1:
            editor = QLineEdit(parent)
            # 0 | .x | 0.x | 1 | 1.0...
            rx = QRegularExpression(r"^\s*(?:0|0?[\.,]\d{1,6}|1(?:[\.,]0{1,6})?)\s*$")
            editor.setValidator(QRegularExpressionValidator(rx, editor))
            editor.setPlaceholderText("0..1")
            return editor
        return super().createEditor(parent, option, index)


__all__ = ["AnalysisWindow"]
