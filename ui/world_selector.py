"""世界选择对话框：树状显示 版本 → 世界"""
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QLineEdit,
)

from core import game_locator
from core.world_reader import WorldReader


class WorldSelectorDialog(QDialog):
    def __init__(self, minecraft_dir, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择存档")
        self.resize(620, 560)
        self.minecraft_dir = Path(minecraft_dir)
        self.selected_world_path = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("展开版本，选择要加载的世界。没有存档的版本会显示为灰色。"))

        # 搜索框
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("搜索："))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入版本号或世界名...")
        self.search_edit.textChanged.connect(self._on_search_changed)
        search_row.addWidget(self.search_edit)
        layout.addLayout(search_row)

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

    # ---------------- 构建树 ----------------
    def _populate(self):
        # 1. 收集所有版本
        versions = game_locator.list_installed_versions(self.minecraft_dir)
        version_names = [v[0] for v in versions]

        # 2. 收集所有世界，读出它们的游戏版本
        worlds = game_locator.list_worlds(self.minecraft_dir)
        world_infos = []  # [(world_name, path, world_version), ...]
        for name, path in worlds:
            try:
                reader = WorldReader(path)
                wv = reader.get_world_version()
            except Exception:
                wv = "未知"
            world_infos.append((name, path, wv))

        # 3. 把每个世界归到匹配的版本文件夹下
        #    世界版本 1.21.10 应匹配 1.21.10、1.21.10-NeoForge_xxx 等
        version_to_worlds = {}   # version_folder_name -> [(world_name, path), ...]
        unmatched = []           # 没找到对应版本文件夹的世界

        for name, path, wv in world_infos:
            matched = False
            for vn in version_names:
                if vn == wv or vn.startswith(wv + "-") or vn.startswith(wv + " "):
                    version_to_worlds.setdefault(vn, []).append((name, path))
                    matched = True
            if not matched:
                unmatched.append((name, path, wv))

        # 4. 构建树：版本文件夹按名字倒序（新的在上）
        self.tree.clear()
        sorted_versions = sorted(versions, key=lambda x: x[0], reverse=True)

        for version_name, _jar in sorted_versions:
            child_worlds = version_to_worlds.get(version_name, [])
            label = f"{version_name}  ({len(child_worlds)} 个存档)"
            version_item = QTreeWidgetItem([label, version_name])

            if child_worlds:
                # 有存档：正常颜色
                for wname, wpath in child_worlds:
                    child = QTreeWidgetItem([wname, version_name])
                    child.setData(0, 0x0100, str(wpath))
                    version_item.addChild(child)
            else:
                # 没存档：灰色提示
                placeholder = QTreeWidgetItem(["（此版本下没有存档）", ""])
                placeholder.setForeground(0, Qt.GlobalColor.gray)
                placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
                version_item.addChild(placeholder)

            self.tree.addTopLevelItem(version_item)

        # 5. 未匹配的世界单独放一组
        if unmatched:
            other = QTreeWidgetItem([f"其他（未找到对应版本）  ({len(unmatched)} 个)", ""])
            for wname, wpath, wv in unmatched:
                child = QTreeWidgetItem([wname, wv])
                child.setData(0, 0x0100, str(wpath))
                other.addChild(child)
            self.tree.addTopLevelItem(other)

        self.tree.resizeColumnToContents(0)

    # ---------------- 搜索 ----------------
    def _on_search_changed(self, text):
        text = text.strip().lower()
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            top_text = top.text(0).lower()

            if not text:
                # 清空搜索：恢复所有，折叠
                top.setHidden(False)
                top.setExpanded(False)
                for j in range(top.childCount()):
                    top.child(j).setHidden(False)
                continue

            # 版本名匹配 → 整个展开
            if text in top_text:
                top.setHidden(False)
                top.setExpanded(True)
                for j in range(top.childCount()):
                    top.child(j).setHidden(False)
                continue

            # 检查子世界是否匹配
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

    # ---------------- 选择 ----------------
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
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self, "提示",
                "请展开版本，双击一个世界名来加载。"
            )
