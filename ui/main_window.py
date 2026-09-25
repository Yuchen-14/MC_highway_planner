"""主窗口"""
import json
from pathlib import Path

from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QAction, QPixmap
from PyQt6.QtWidgets import (
    QMainWindow, QMenuBar, QStatusBar, QProgressBar,
    QMessageBox, QGraphicsPixmapItem, QFileDialog,
)

from core import game_locator
from core.block_mapper import BlockMapper
from core.terrain_scanner import TerrainScanner
from core.texture_extractor import (
    extract_block_textures, get_cache_dir, has_textures,
)
from core.world_reader import WorldReader

from ui.config_dialog import ConfigDialog
from ui.load_thread import WorldLoadThread, BLOCK_PIXEL
from ui.map_view import MapView
from ui.world_selector import WorldSelectorDialog


CONFIG_FILE = Path.home() / ".highway_planner" / "config.json"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("高速公路规划器")
        self.resize(1280, 800)

        # 状态
        self.minecraft_dir = None
        self.current_world_reader = None
        self.block_mapper = None
        self.load_thread = None
        self._loaded_regions = set()

        # 地图视图
        self.map_view = MapView(self)
        self.setCentralWidget(self.map_view)
        self.map_view.block_hovered.connect(self._on_block_hovered)
        self.map_view.mouse_left.connect(self._on_mouse_left)

        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(240)
        self.progress_bar.hide()
        self.status_bar.addPermanentWidget(self.progress_bar)

        self._build_menu()
        self._load_config()

    # ---------------- 菜单 ----------------
    def _build_menu(self):
        menubar = self.menuBar()

        # 文件
        file_menu = menubar.addMenu("文件")

        config_action = QAction("配置游戏文件夹", self)
        config_action.triggered.connect(self._on_config)
        file_menu.addAction(config_action)

        browse_action = QAction("浏览文件夹", self)
        browse_action.triggered.connect(self._on_browse)
        file_menu.addAction(browse_action)

        file_menu.addSeparator()

        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 图层
        layer_menu = menubar.addMenu("图层")

        self.texture_action = QAction("纹理图层", self, checkable=True)
        self.texture_action.setChecked(True)
        self.texture_action.triggered.connect(self._on_layer_toggle)
        layer_menu.addAction(self.texture_action)

        self.contour_action = QAction("等高线图层", self, checkable=True)
        self.contour_action.setChecked(False)
        self.contour_action.triggered.connect(self._on_layer_toggle)
        layer_menu.addAction(self.contour_action)

    # ---------------- 配置 ----------------
    def _load_config(self):
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                d = cfg.get("minecraft_dir")
                if d and Path(d).exists():
                    self.minecraft_dir = Path(d)
                    self._try_extract_textures()
        except Exception:
            pass

    def _save_config(self):
        try:
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({"minecraft_dir": str(self.minecraft_dir)}, f)
        except Exception:
            pass

    def _on_config(self):
        initial = str(self.minecraft_dir) if self.minecraft_dir else ""
        dlg = ConfigDialog(self, initial)
        if dlg.exec() == ConfigDialog.DialogCode.Accepted:
            self.minecraft_dir = Path(dlg.result_dir)
            self._save_config()
            self._try_extract_textures()
            self.status_bar.showMessage(f"已配置游戏目录：{self.minecraft_dir}")

    def _try_extract_textures(self):
        """尝试从已安装版本中提取纹理"""
        if not self.minecraft_dir:
            return

        versions = game_locator.list_installed_versions(self.minecraft_dir)
        if not versions:
            self.status_bar.showMessage("⚠ 未找到 versions，纹理提取不可用")
            return

        # 选最高的版本作为纹理源
        version_name, jar_path = versions[0]

        if not has_textures(version_name):
            self.status_bar.showMessage(f"正在提取纹理（{version_name}）...")
            try:
                count = extract_block_textures(jar_path, version_name)
                self.status_bar.showMessage(f"已从 {version_name} 提取 {count} 张纹理")
            except Exception as e:
                QMessageBox.warning(self, "纹理提取失败", str(e))
                return

        cache_dir = get_cache_dir(version_name)
        self.block_mapper = BlockMapper(cache_dir)

    # ---------------- 浏览 / 加载世界 ----------------
    def _on_browse(self):
        if not self.minecraft_dir:
            QMessageBox.information(self, "提示", "请先配置游戏文件夹")
            return

        dlg = WorldSelectorDialog(self.minecraft_dir, self)
        if dlg.exec() != WorldSelectorDialog.DialogCode.Accepted:
            return
        if not dlg.selected_world_path:
            return

        self._load_world(dlg.selected_world_path)

    def _load_world(self, world_path):
        if self.block_mapper is None:
            QMessageBox.warning(self, "缺少纹理", "未提取到纹理，请重新配置游戏文件夹")
            return

        # 清理旧状态
        if self.load_thread and self.load_thread.isRunning():
            self.load_thread.cancel()
            self.load_thread.wait()

        self.map_view.clear_map()
        self._loaded_regions.clear()

        self.current_world_reader = WorldReader(world_path)
        version = self.current_world_reader.get_world_version()
        self.setWindowTitle(f"高速公路规划器 - {Path(world_path).name} ({version})")

        # 启动后台加载
        self.load_thread = WorldLoadThread(
            self.current_world_reader, self.block_mapper, self
        )
        self.load_thread.progress.connect(self._on_load_progress)
        self.load_thread.region_ready.connect(self._on_region_ready)
        self.load_thread.finished_loading.connect(self._on_load_finished)
        self.load_thread.error.connect(self._on_load_error)

        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.load_thread.start()

    def _on_load_progress(self, current, total, message):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_bar.showMessage(message)

    def _on_region_ready(self, region_x, region_z, qimage):
        """在主线程把区域图像添加到场景"""
        pixmap = QPixmap.fromImage(qimage)
        item = QGraphicsPixmapItem(pixmap)

        # 场景坐标：1 单位 = 1 方块
        # 图像中 1 方块 = BLOCK_PIXEL 像素
        # 所以要把图像缩放到 方块单位
        scene_x = region_x * 512
        scene_z = region_z * 512
        item.setPos(scene_x, scene_z)
        item.setScale(1.0 / BLOCK_PIXEL)

        self.map_view.scene().addItem(item)
        self._loaded_regions.add((region_x, region_z))

        # 首次加载时，自动缩放到合适的视野
        if len(self._loaded_regions) == 1:
            self.map_view.fitInView(
                item, Qt.AspectRatioMode.KeepAspectRatio
            )

    def _on_load_finished(self):
        self.progress_bar.hide()
        self.status_bar.showMessage("地图加载完成")
        self.map_view._zoom = 1.0

    def _on_load_error(self, message):
        self.progress_bar.hide()
        QMessageBox.critical(self, "加载失败", message)

    # ---------------- 悬停查询 ----------------
    def _on_block_hovered(self, x, z, _, __):
        if self.current_world_reader is None:
            return
        try:
            chunk_x, chunk_z = x >> 4, z >> 4
            local_x, local_z = x & 15, z & 15
            chunk = self.current_world_reader.get_chunk(chunk_x, chunk_z)
            if chunk is None:
                self.status_bar.showMessage(f"坐标 ({x}, {z}) — 区块未加载")
                return

            from core.terrain_scanner import WORLD_MAX_Y, WORLD_MIN_Y, AIR_IDS
            for y in range(WORLD_MAX_Y, WORLD_MIN_Y - 1, -1):
                try:
                    block = chunk.get_block(local_x, y, local_z)
                except Exception:
                    continue
                if block is None:
                    continue
                if block.id not in AIR_IDS:
                    self.status_bar.showMessage(
                        f"坐标 ({x}, {y}, {z}) — {block.id}"
                    )
                    return
        except Exception:
            pass

    def _on_mouse_left(self):
        self.status_bar.showMessage("")

    # ---------------- 图层开关（占位） ----------------
    def _on_layer_toggle(self):
        # 第二阶段再实现
        pass

    # ---------------- 关闭 ----------------
    def closeEvent(self, event):
        if self.load_thread and self.load_thread.isRunning():
            self.load_thread.cancel()
            self.load_thread.wait(3000)
        super().closeEvent(event)
