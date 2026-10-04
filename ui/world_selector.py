"""世界选择对话框：树状显示 版本 → 世界"""
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QLineEdit, QMessageBox,
)

from core import game_locator
from core.world_reader import WorldReader


class WorldSelectorDialog(QDialog):
    def __init__(self, minecraft_dir, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择存档")
        self.resize(660, 600)
        self.minecraft_dir = Path(minecraft_dir)
        self.selected_world_path = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("展开版本，选择要加载的世界。"))

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("搜索："))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入版本号或世界名...")
        self.search_edit.textChanged.connect(self._on_search_changed)
        search_row.addWidget(self.search_edit)
        layout.addLayout(search_row)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["名称", "位置"])
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
        # 收集版本
        versions = game_locator.list_installed_versions(self.minecraft_dir)
        version_names = [v[0] for v in versions]

        # 收集世界（4 元组）
        worlds = game_locator.list_worlds(self.minecraft_dir)

        # 版本文件夹 -> [(world_name, path), ...]
        version_to_worlds = {}
        unmatched = []   # 全局存档或找不到版本的存档

        for name, path, version_folder, isolated in worlds:
            if isolated and version_folder in version_names:
                # 直接归到它的版本文件夹
                version_to_worlds.setdefault(version_folder, []).append((name, path))
            else:
                # 全局存档，尝试按 level.dat 里的版本匹配
                try:
                    reader = WorldReader(path)
                    wv = reader.get_world_version()
                except Exception:
                    wv = "未知"

                matched = False
                for vn in version_names:
                    if vn == wv or vn.startswith(wv + "-") or vn.startswith(wv + " "):
                        version_to_worlds.setdefault(vn, []).append((name, path))
                        matched = True
                        break

                if not matched:
                    unmatched.append((name, path, wv))

        # 构建树
        self.tree.clear()
        sorted_versions = sorted(versions, key=lambda x: x[0], reverse=True)

        for version_name, _jar in sorted_versions:
            child_worlds = version_to_worlds.get(version_name, [])
            label = f"{version_name}  ({len(child_worlds)} 个存档)"
            version_item = QTreeWidgetItem([label, version_name])

            if child_worlds:
                for wname, wpath in child_worlds:
                    child = QTreeWidgetItem([wname, "版本隔离" if "versions" in str(wpath) else "全局"])
                    child.setData(0, 0x0100, str(wpath))
                    version_item.addChild(child)
            else:
                placeholder = QTreeWidgetItem(["（此版本下没有存档）", ""])
                placeholder.setForeground(0, Qt.GlobalColor.gray)
                placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
                version_item.addChild(placeholder)

            self.tree.addTopLevelItem(version_item)

        if unmatched:
            other = QTreeWidgetItem([f"其他（未匹配版本）  ({len(unmatched)} 个)", ""])
            for wname, wpath, wv in unmatched:
                child = QTreeWidgetItem([wname, wv])
                child.setData(0, 0x0100, str(wpath))
                other.addChild(child)
            self.tree.addTopLevelItem(other)

        self.tree.resizeColumnToContents(0)

    def _on_search_changed(self, text):
        text = text.strip().lower()
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            top_text = top.text(0).lower()

            if not text:
                top.setHidden(False)
                top.setExpanded(False)
                for j in range(top.childCount()):
                    top.child(j).setHidden(False)
                continue

            if text in top_text:
                top.setHidden(False)
                top.setExpanded(True)
                for j in range(top.childCount()):
                    top.child(j).setHidden(False)
                continue

            any_child_match = False
            for j in range(top.childCount()):
                child = top.child(j)
                if text in child.text(0).lower():
                    child.setHidden(False)
                    any_child_match = True
                else:
                    child.setHidden(True)

            if any_child_match:
                top.setHidden(False)
                top.setExpanded(True)
            else:
                top.setHidden(True)

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
        else:
            QMessageBox.information(self, "提示", "请展开版本，双击一个世界名来加载。")
