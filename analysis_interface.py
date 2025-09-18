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
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QBrush, QColor

try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas  # type: ignore
except Exception:  # fallback older name
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas  # type: ignore
from matplotlib.figure import Figure
from matplotlib.axes import Axes

# NOTE: analysis_logic will be integrated later for advanced variation logic
# from analysis_logic import vary_component_shares


class AnalysisWindow(QDialog):
    def __init__(
        self,
        cold_flow: Dict[str, float],
        hot_flow: Dict[str, float],
        cold_mix: List[Dict[str, Any]],
        hot_mix: List[Dict[str, Any]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Анализ состава смесей")
        # Remove question mark help button
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        # Larger, resizable window
        self.resize(1400, 900)
        self.setSizeGripEnabled(True)

        self._cold_mix = [dict(r) for r in cold_mix]
        self._hot_mix = [dict(r) for r in hot_mix]
        layout = QVBoxLayout(self)

        # Tables with per-table controls (верх)
        tables_box = QHBoxLayout()
        layout.addLayout(tables_box, 0)
        cold_group = QGroupBox("Холодный поток")
        hot_group = QGroupBox("Горячий поток")
        cold_group.setStyleSheet("")
        hot_group.setStyleSheet("")
        tables_box.addWidget(cold_group)
        tables_box.addWidget(hot_group)
        cold_box = QVBoxLayout(cold_group)
        hot_box = QVBoxLayout(hot_group)

        self.cold_table = self._create_table(self._cold_mix)
        self.hot_table = self._create_table(self._hot_mix)
        cold_box.addWidget(self.cold_table)
        hot_box.addWidget(self.hot_table)

        # Buttons under each table
        self.cold_edit_btn = QPushButton("Редактировать")
        self.cold_apply_btn = QPushButton("Утвердить")
        self.hot_edit_btn = QPushButton("Редактировать")
        self.hot_apply_btn = QPushButton("Утвердить")
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
        self.run_btn = QPushButton("Построить графики")
        self.run_btn.hide()
        self.run_btn.setStyleSheet("background-color: gold; font-weight: bold;")
        layout.addWidget(self.run_btn)

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

        # Figure with 3 subplots (внизу)
        self.fig = Figure(figsize=(12, 5))
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.canvas, 1)
        self.ax_q = self.fig.add_subplot(131)
        self.ax_sigma = self.fig.add_subplot(132)
        self.ax_k = self.fig.add_subplot(133)
        for ax, title in [
            (self.ax_q, "Q (кВт)"),
            (self.ax_sigma, "σ (кВт/К)"),
            (self.ax_k, "K (кВт/К)"),
        ]:
            ax.set_title(title)
            ax.set_xlabel("Доля компонента (сценарий)")
            ax.grid(True, linestyle=":", alpha=0.5)

        # Description label (пояснение)
        self.desc_label = QPushButton()
        self.desc_label.setEnabled(False)
        self.desc_label.setText(
            "Каждая кривая: независимый сценарий варьирования доли одного компонента от 0 до 1 с равным распределением остатка."
        )
        layout.addWidget(self.desc_label)

        # Connections
        self.cold_edit_btn.clicked.connect(
            lambda: self._on_edit_clicked(self.cold_table, "cold")
        )
        self.hot_edit_btn.clicked.connect(
            lambda: self._on_edit_clicked(self.hot_table, "hot")
        )
        self.cold_apply_btn.clicked.connect(
            lambda: self._apply_table(self.cold_table, which="cold")
        )
        self.hot_apply_btn.clicked.connect(
            lambda: self._apply_table(self.hot_table, which="hot")
        )
        self.run_btn.clicked.connect(self._on_run_clicked)

        self._cold_locked = False
        self._hot_locked = False
        # initial state: editing enabled for share column
        self._set_table_editable(self.cold_table, True)
        self._set_table_editable(self.hot_table, True)
        # ensure normal visual (not grey) at start
        self._set_table_locked_visual(self.cold_table, False)
        self._set_table_locked_visual(self.hot_table, False)

        # Initial empty plot (will fill once both approved and run clicked)
        empty: Dict[str, List[float]] = {}
        self._update_plot(empty, empty, empty, empty)

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
            QMessageBox.information(self, "Анализ", "Сначала утвердите обе таблицы.")
            return
        self._read_tables()
        # Prepare scenarios for each component in both mixes
        scenarios = self._build_scenarios()
        import logic

        cold_flow = {"t_in": 0.0, "t_out": 0.0, "m": 0.0, "p": 0.0}
        hot_flow = {"t_in": 0.0, "t_out": 0.0, "m": 0.0, "p": 0.0}
        series_q: Dict[str, List[float]] = {}
        series_sigma: Dict[str, List[float]] = {}
        series_k: Dict[str, List[float]] = {}
        series_x: Dict[str, List[float]] = {}
        for label, (shares, cold_mix_var, hot_mix_var) in scenarios.items():
            q_vals: List[float] = []
            sigma_vals: List[float] = []
            k_vals: List[float] = []
            for mix_c, mix_h in zip(cold_mix_var, hot_mix_var):
                ans = logic.calculate(
                    cold=cold_flow,
                    hot=hot_flow,
                    cold_mix=mix_c,
                    hot_mix=mix_h,
                    q=0.0,
                    schema="Schema1",
                )
                q_vals.append(float(ans.get("q", 0.0)))
                sigma_vals.append(float(ans.get("sigma", 0.0)))
                k_vals.append(float(ans.get("k", 0.0)))
            series_x[label] = shares
            series_q[label] = q_vals
            series_sigma[label] = sigma_vals
            series_k[label] = k_vals
        self._update_plot(series_x, series_q, series_sigma, series_k)
        self.run_btn.hide()

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
                    ax.plot(
                        xs,
                        ys,
                        marker="o",
                        linestyle="-",
                        label=label,
                        color=color,
                        markersize=3,
                    )
            ax.set_xlabel("Доля компонента")
            ax.grid(True, linestyle=":", alpha=0.4)

        plot_series(self.ax_q, series_x, "Q")
        plot_series(self.ax_sigma, series_x, "Sigma")
        plot_series(self.ax_k, series_x, "K")
        self.ax_q.set_title("Q (кВт)")
        self.ax_sigma.set_title("σ (кВт/К)")
        self.ax_k.set_title("K (кВт/К)")
        # Легенды компактно
        for ax in (self.ax_q, self.ax_sigma, self.ax_k):
            ax.legend(fontsize=7, loc="best")
        self.fig.tight_layout()
        self.canvas.draw_idle()

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
            QMessageBox.warning(self, "Анализ", "Некорректные значения долей.")
            return
        if abs(total - 1.0) > 1e-6:
            QMessageBox.warning(
                self,
                "Анализ",
                f"Сумма долей должна быть = 1.0 (текущая: {total:.6f}).",
            )
            return
        self._set_table_editable(table, False)
        if which == "cold":
            self._cold_locked = True
        else:
            self._hot_locked = True
        self._set_table_locked_visual(table, True)
        self._read_tables()
        # Enable and show run button only if both locked
        can_show = self._cold_locked and self._hot_locked
        self.run_btn.setEnabled(can_show)
        if can_show:
            self.run_btn.show()
            self._blink_on = False
            self.run_btn.setStyleSheet(self._blink_base_style)
            self._blink_timer.start()
        QMessageBox.information(
            self,
            "Анализ",
            f"Таблица '{'Холодный' if which=='cold' else 'Горячий'} поток' утверждена.",
        )

    def _on_edit_clicked(self, table: QTableWidget, which: str):
        if which == "cold":
            self._cold_locked = False
        else:
            self._hot_locked = False
        self.run_btn.hide()
        self._blink_timer.stop()
        self._set_table_locked_visual(table, False)
        self._set_table_editable(table, True)

    def _on_run_clicked(self):
        self.recalculate()
        self._blink_timer.stop()
        self._blink_on = False
        self.run_btn.setStyleSheet(self._blink_base_style)


__all__ = ["AnalysisWindow"]
