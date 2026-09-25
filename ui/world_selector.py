"""世界选择对话框：树状显示 版本 → 世界"""
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel,
)

from core import game_locator
from core.world_reader import WorldReader


class WorldSelectorDialog(QDialog):
    def __init__(self, minecraft_dir, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择存档")
        self.resize(560, 480)
        self.minecraft_dir = Path(minecraft_dir)
        self.selected_world_path = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("展开版本，选择要加载的世界："))

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["名称", "版本"])
        self.tree.itemDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self.tree)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        load_btn = QPushButton("加载")
        load_btn.clicked.connect(self._on_load)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(load_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

        self._populate()

    def _populate(self):
        worlds = game_locator.list_worlds(self.minecraft_dir)
        if not worlds:
            item = QTreeWidgetItem(["（未找到任何世界）", ""])
            self.tree.addTopLevelItem(item)
            return

        # 按版本分组
        grouped = {}
        for name, path in worlds:
            reader = WorldReader(path)
            version = reader.get_world_version()
            grouped.setdefault(version, []).append((name, path))

        # 按版本号倒序
        for version in sorted(grouped.keys(), reverse=True):
            version_item = QTreeWidgetItem([f"{version}", ""])
            version_item.setExpanded(True)
            for name, path in grouped[version]:
                child = QTreeWidgetItem([name, version])
                child.setData(0, 0x0100, str(path))
                version_item.addChild(child)
            self.tree.addTopLevelItem(version_item)

        self.tree.resizeColumnToContents(0)

    def _on_double_click(self, item, column):
        path_str = item.data(0, 0x0100)
        if path_str:
            self.selected_world_path = path_str
            self.accept()

    def _on_load(self):
        item = self.tree.currentItem()
        if item is None:
            return
        path_str = item.data(0, 0x0100)
        if path_str:
            self.selected_world_path = path_str
            self.accept()
