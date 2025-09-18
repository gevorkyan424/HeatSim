"""analysis_interface.py

Графическое окно анализа вариаций долей компонентов.
"""

from __future__ import annotations

from typing import List, Dict, Any
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QSpinBox,
    QDoubleSpinBox,
    QMessageBox,
    QWidget,
)
from PyQt5.QtCore import Qt

try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas  # type: ignore
except Exception:  # fallback older name
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas  # type: ignore
from matplotlib.figure import Figure

from analysis_logic import vary_component_shares


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
        self.setWindowTitle("Анализ изменения долей компонентов смеси")
        self.resize(900, 600)
        self._cold_mix = [dict(r) for r in cold_mix]
        self._hot_mix = [dict(r) for r in hot_mix]
        layout = QVBoxLayout(self)

        # Plot figure
        self.fig = Figure(figsize=(5, 3))
        self.canvas = FigureCanvas(self.fig)
        layout.addWidget(self.canvas, 1)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_xlabel("Q, кВт")
        self.ax.set_ylabel("σ, кВт/К")
        self.ax.grid(True, linestyle=":", alpha=0.5)

        # Tables side-by-side
        tbl_layout = QHBoxLayout()
        layout.addLayout(tbl_layout)
        self.cold_table = self._create_table("Холодный поток", self._cold_mix)
        self.hot_table = self._create_table("Горячий поток", self._hot_mix)
        tbl_layout.addWidget(self.cold_table)
        tbl_layout.addWidget(self.hot_table)

        ctrl = QHBoxLayout()
        layout.addLayout(ctrl)
        ctrl.addWidget(QLabel("Шаг доли"))
        self.step_box = QDoubleSpinBox()
        self.step_box.setRange(0.01, 1.0)
        self.step_box.setSingleStep(0.01)
        self.step_box.setValue(0.1)
        ctrl.addWidget(self.step_box)
        ctrl.addWidget(QLabel("Макс. точек"))
        self.limit_box = QSpinBox()
        self.limit_box.setRange(10, 10000)
        self.limit_box.setValue(200)
        ctrl.addWidget(self.limit_box)
        self.run_btn = QPushButton("Пересчитать")
        self.lock_btn = QPushButton("Утвердить")
        ctrl.addWidget(self.run_btn)
        ctrl.addWidget(self.lock_btn)
        ctrl.addStretch(1)

        self.run_btn.clicked.connect(self.recalculate)
        self.lock_btn.clicked.connect(self.lock_tables)

        self._tables_locked = False
        self.recalculate()

    def _create_table(self, title: str, data: List[Dict[str, Any]]):
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels([f"{title}", "Доля", "Tb", "C_f", "C_p"])
        table.verticalHeader().setVisible(False)
        table.setRowCount(len(data))
        for r, row in enumerate(data):
            for c, key in enumerate(["name", "share", "tb", "cf", "cp"]):
                item = QTableWidgetItem(str(row.get(key, "")))
                if key != "share":
                    # allow editing only share
                    if key != "name":
                        item.setFlags(item.flags() | Qt.ItemIsEditable)
                table.setItem(r, c, item)
            # name not editable
            it_name = table.item(r, 0)
            if it_name:
                it_name.setFlags(it_name.flags() & ~Qt.ItemIsEditable)
        table.resizeColumnsToContents()
        return table

    def _read_tables(self):
        if self._tables_locked:
            return

        def read(tbl: QTableWidget) -> List[Dict[str, Any]]:
            out: List[Dict[str, Any]] = []
            for r in range(tbl.rowCount()):
                try:
                    it0 = tbl.item(r, 0)
                    it1 = tbl.item(r, 1)
                    it2 = tbl.item(r, 2)
                    it3 = tbl.item(r, 3)
                    it4 = tbl.item(r, 4)
                    if not all([it0, it1, it2, it3, it4]):
                        continue
                    name = it0.text() if it0 else ""
                    share = float(it1.text().replace(",", ".")) if it1 else 0.0
                    tb = float(it2.text().replace(",", ".")) if it2 else 0.0
                    cf = float(it3.text().replace(",", ".")) if it3 else 0.0
                    cp = float(it4.text().replace(",", ".")) if it4 else 0.0
                except Exception:
                    continue
                out.append(
                    {
                        "name": name,
                        "share": share,
                        "tb": tb,
                        "cf": cf,
                        "cp": cp,
                        "rf": 0.0,
                    }
                )
            return out

        self._cold_mix = read(self.cold_table)
        self._hot_mix = read(self.hot_table)

    def recalculate(self):
        self._read_tables()
        step = float(self.step_box.value())
        limit = int(self.limit_box.value())
        if not self._cold_mix or not self._hot_mix:
            QMessageBox.warning(self, "Анализ", "Нет данных смесей.")
            return
        pts = vary_component_shares(
            self._cold_mix, self._hot_mix, step=step, limit=limit
        )
        self.ax.clear()
        self.ax.set_xlabel("Q, кВт")
        self.ax.set_ylabel("σ, кВт/К")
        self.ax.grid(True, linestyle=":", alpha=0.5)
        if pts:
            xs, ys = zip(*pts)
            self.ax.plot(xs, ys, marker="o", linestyle="-")
        self.canvas.draw_idle()

    def lock_tables(self):
        self._read_tables()
        self._tables_locked = True
        for tbl in (self.cold_table, self.hot_table):
            for r in range(tbl.rowCount()):
                for c in range(tbl.columnCount()):
                    it = tbl.item(r, c)
                    if it:
                        it.setFlags(it.flags() & ~Qt.ItemIsEditable)
        self.lock_btn.setEnabled(False)
        QMessageBox.information(self, "Анализ", "Таблицы заблокированы.")


__all__ = ["AnalysisWindow"]
