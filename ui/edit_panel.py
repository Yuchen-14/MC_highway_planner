"""侧边编辑面板：高速公路列表 + 新建对话框"""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QDialog, QLineEdit, QComboBox,
    QSpinBox, QDialogButtonBox, QFormLayout,
)

from core.highway import MC_COLORS, Highway


class NewHighwayDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("新建高速公路")
        self.resize(360, 260)

        layout = QFormLayout(self)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例如：京沪高速")
        layout.addRow("详细名称：", self.name_edit)

        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("例如：G2")
        layout.addRow("字母+数字简称：", self.code_edit)

        self.color_combo = QComboBox()
        for key in MC_COLORS.keys():
            self.color_combo.addItem(key, key)
        layout.addRow("底色：", self.color_combo)

        self.lanes_spin = QSpinBox()
        self.lanes_spin.setRange(1, 8)
        self.lanes_spin.setValue(2)
        layout.addRow("车道数（每侧）：", self.lanes_spin)

        self.height_spin = QSpinBox()
        self.height_spin.setRange(-64, 319)
        self.height_spin.setValue(64)
        layout.addRow("固定高度 Y：", self.height_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def build_highway(self, is_ramp=False):
        return Highway(
            name=self.name_edit.text().strip() or "未命名",
            short_code=self.code_edit.text().strip() or "X0",
            color=self.color_combo.currentData(),
            lanes=self.lanes_spin.value(),
            height=self.height_spin.value(),
            is_ramp=is_ramp,
        )


class EditPanel(QWidget):
    highway_selected = pyqtSignal(str)   # highway id
    highway_deleted = pyqtSignal(str)
    new_highway_requested = pyqtSignal()
    new_ramp_requested = pyqtSignal()

    def __init__(self, manager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.setFixedWidth(240)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        title = QLabel("道路列表")
        title.setStyleSheet("font-weight: bold; padding: 4px;")
        layout.addWidget(title)

        # 两个新建按钮
        btn_row = QHBoxLayout()
        new_hw_btn = QPushButton("＋ 高速")
        new_hw_btn.clicked.connect(self.new_highway_requested.emit)
        new_ramp_btn = QPushButton("＋ 匝道")
        new_ramp_btn.clicked.connect(self.new_ramp_requested.emit)
        btn_row.addWidget(new_hw_btn)
        btn_row.addWidget(new_ramp_btn)
        layout.addLayout(btn_row)

        # 列表
        self.list_widget = QListWidget()
        self.list_widget.currentItemChanged.connect(self._on_selection_changed)
        layout.addWidget(self.list_widget, 1)

        # 删除按钮
        del_btn = QPushButton("删除选中的道路")
        del_btn.clicked.connect(self._on_delete)
        layout.addWidget(del_btn)

        self.refresh()

    def refresh(self):
        self.list_widget.clear()
        for h in self.manager.highways:
            label = f"{h.short_code} {h.name}" + ("（匝道）" if h.is_ramp else "")
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, h.id)
            # 用颜色画一个小方块
            from PyQt6.QtGui import QPixmap, QColor, QIcon
            pix = QPixmap(12, 12)
            pix.fill(QColor(h.color_hex))
            item.setIcon(QIcon(pix))
            self.list_widget.addItem(item)

            if h.id == self.manager.active_id:
                self.list_widget.setCurrentItem(item)

    def _on_selection_changed(self, current, previous):
        if current is None:
            return
        hw_id = current.data(Qt.ItemDataRole.UserRole)
        self.highway_selected.emit(hw_id)

    def _on_delete(self):
        item = self.list_widget.currentItem()
        if item is None:
            return
        hw_id = item.data(Qt.ItemDataRole.UserRole)
        self.highway_deleted.emit(hw_id)
