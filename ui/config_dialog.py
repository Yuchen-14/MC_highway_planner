"""配置游戏文件夹对话框"""
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFileDialog, QMessageBox,
)

from core import game_locator


class ConfigDialog(QDialog):
    def __init__(self, parent=None, initial_dir=""):
        super().__init__(parent)
        self.setWindowTitle("配置游戏文件夹")
        self.resize(520, 180)
        self.result_dir = initial_dir

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("请选择 .minecraft 文件夹（包含 saves 与 versions 的目录）："))

        row = QHBoxLayout()
        self.path_edit = QLineEdit(initial_dir)
        self.path_edit.setReadOnly(True)
        row.addWidget(self.path_edit)

        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self._on_browse)
        row.addWidget(browse_btn)

        auto_btn = QPushButton("自动检测")
        auto_btn.clicked.connect(self._on_auto)
        row.addWidget(auto_btn)

        layout.addLayout(row)

        self.info_label = QLabel("")
        layout.addWidget(self.info_label)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self._on_ok)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

        if initial_dir:
            self._refresh_info()

    def _on_browse(self):
        folder = QFileDialog.getExistingDirectory(self, "选择 .minecraft 文件夹")
        if folder:
            self.path_edit.setText(folder)
            self._refresh_info()

    def _on_auto(self):
        default = game_locator.get_default_minecraft_dir()
        if default:
            self.path_edit.setText(str(default))
            self._refresh_info()
        else:
            QMessageBox.warning(self, "未找到", "无法自动检测 .minecraft 文件夹位置")

    def _refresh_info(self):
        path = Path(self.path_edit.text())
        if not path.exists():
            self.info_label.setText("⚠ 路径不存在")
            return

        saves = game_locator.find_saves_dir(path)
        versions = game_locator.find_versions_dir(path)

        parts = []
        if saves:
            worlds = game_locator.list_worlds(path)
            parts.append(f"✓ saves 目录：{len(worlds)} 个世界")
        else:
            parts.append("✗ 未找到 saves 目录")

        if versions:
            vers = game_locator.list_installed_versions(path)
            parts.append(f"✓ versions 目录：{len(vers)} 个版本")
        else:
            parts.append("⚠ 未找到 versions 目录（纹理提取将不可用）")

        self.info_label.setText(" | ".join(parts))

    def _on_ok(self):
        path = Path(self.path_edit.text())
        if not path.exists():
            QMessageBox.warning(self, "错误", "请选择一个有效的文件夹")
            return
        if not game_locator.find_saves_dir(path):
            reply = QMessageBox.question(
                self, "警告",
                "未找到 saves 目录，是否仍要继续？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                return
        self.result_dir = str(path)
        self.accept()
