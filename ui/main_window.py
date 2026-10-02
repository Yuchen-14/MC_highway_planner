"""主窗口"""
import json
from pathlib import Path

from PyQt6.QtGui import QKeySequence
from core.highway import HighwayManager, Highway, Waypoint
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QAction, QPixmap, QColor, QPen, QBrush, QPolygonF
from PyQt6.QtWidgets import (
    QMainWindow, QStatusBar, QProgressBar, QMessageBox,
    QGraphicsPixmapItem, QGraphicsPathItem, QGraphicsEllipseItem,
    QGraphicsLineItem, QDockWidget,
)
from PyQt6.QtGui import QPainterPath

from core import game_locator
from core.block_mapper import BlockMapper
from core.highway import HighwayManager, Highway
from core.seed_reader import read_world_seed
from core.terrain_scanner import (
    TerrainScanner, WORLD_MAX_Y, WORLD_MIN_Y, AIR_IDS,
)
from core.texture_extractor import (
    extract_block_textures, get_cache_dir, has_textures,
)
from core.world_reader import WorldReader

from ui.config_dialog import ConfigDialog
from ui.edit_panel import EditPanel, NewHighwayDialog
from ui.load_thread import WorldLoadThread
from core.renderer import BLOCK_PIXEL
from ui.map_view import MapView
from ui.preview_thread import PreviewLoader
from ui.world_selector import WorldSelectorDialog
from ui.export_thread import ExportThread


CONFIG_FILE = Path.home() / ".highway_planner" / "config.json"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("高速公路规划器")
        self.resize(1360, 840)

        # 状态
        self.minecraft_dir = None
        self.current_world_reader = None
        self.block_mapper = None
        self.load_thread = None
        self.preview_thread = None
        self.world_seed = None
        self._undo_stack = []          # 撤销快照栈
        self.export_thread = None

        # 道路数据
        self.highway_manager = HighwayManager()

        # 已加载的 region
        self._region_layers = {}       # (rx, rz) -> {layer: QGraphicsPixmapItem}
        self._loaded_regions = set()   # 已渲染过的 region（真实或预览）
        self._real_regions = set()     # 来自存档的 region
        self._queued_regions = set()

        # 编辑状态
        self._edit_mode = False
        self._temp_waypoint_items = []  # 预览线相关的图元
        self._preview_line_item = None
        self._preview_last_pos = None

        # 图层可见性
        self._layer_visibility = {
            "preview": True,
            "texture": True,
            "contour": False,
            "road": True,
        }

        # 地图
        self.map_view = MapView(self)
        self.setCentralWidget(self.map_view)
        self.map_view.block_hovered.connect(self._on_block_hovered)
        self.map_view.mouse_left.connect(self._on_mouse_left)
        self.map_view.viewport_changed.connect(self._on_viewport_changed)
        self.map_view.block_clicked.connect(self._on_block_clicked)

        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(240)
        self.progress_bar.hide()
        self.status_bar.addPermanentWidget(self.progress_bar)

        # 编辑面板（dock）
        self.edit_panel = EditPanel(self.highway_manager, self)
        self.edit_panel.highway_selected.connect(self._on_highway_selected)
        self.edit_panel.highway_deleted.connect(self._on_highway_deleted)
        self.edit_panel.new_highway_requested.connect(self._on_new_highway)
        self.edit_panel.new_ramp_requested.connect(self._on_new_ramp)
        self.edit_panel.export_requested.connect(self._on_export)

        self.edit_dock = QDockWidget("编辑", self)
        self.edit_dock.setWidget(self.edit_panel)
        self.edit_dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.edit_dock)
        self.edit_dock.hide()  # 默认隐藏，通过菜单打开

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

        self.texture_action = QAction("纹理图层", self, checkable=True, checked=True)
        self.texture_action.triggered.connect(self._on_layer_toggle)
        layer_menu.addAction(self.texture_action)

        self.contour_action = QAction("等高线图层", self, checkable=True, checked=False)
        self.contour_action.triggered.connect(self._on_layer_toggle)
        layer_menu.addAction(self.contour_action)

        self.preview_action = QAction("预览地形图层", self, checkable=True, checked=True)
        self.preview_action.triggered.connect(self._on_layer_toggle)
        layer_menu.addAction(self.preview_action)

        self.road_action = QAction("道路图层", self, checkable=True, checked=True)
        self.road_action.triggered.connect(self._on_layer_toggle)
        layer_menu.addAction(self.road_action)

        # 编辑
        edit_menu = menubar.addMenu("编辑")

        open_panel_action = QAction("打开菜单", self)
        open_panel_action.triggered.connect(self._on_open_edit_panel)
        edit_menu.addAction(open_panel_action)

        edit_menu.addSeparator()

        new_hw_action = QAction("新建高速公路", self)
        new_hw_action.triggered.connect(self._on_new_highway)
        edit_menu.addAction(new_hw_action)

        new_ramp_action = QAction("新建匝道", self)
        new_ramp_action.triggered.connect(self._on_new_ramp)
        edit_menu.addAction(new_ramp_action)
                edit_menu.addSeparator()

        undo_action = QAction("撤销", self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)  # Ctrl+Z
        undo_action.triggered.connect(self._on_undo)
        edit_menu.addAction(undo_action)
        self.addAction(undo_action)   # 让快捷键在整个窗口生效

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
        if not self.minecraft_dir:
            return
        versions = game_locator.list_installed_versions(self.minecraft_dir)
        if not versions:
            self.status_bar.showMessage("⚠ 未找到 versions，纹理提取不可用")
            return

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

    # ---------------- 加载世界 ----------------
    def _on_browse(self):
        if not self.minecraft_dir:
            QMessageBox.information(self, "提示", "请先配置游戏文件夹")
            return
        dlg = WorldSelectorDialog(self.minecraft_dir, self)
        if dlg.exec() != WorldSelectorDialog.DialogCode.Accepted:
            return
        if dlg.selected_world_path:
            self._load_world(dlg.selected_world_path)

    def _load_world(self, world_path):
        if self.block_mapper is None:
            QMessageBox.warning(self, "缺少纹理", "未提取到纹理，请重新配置游戏文件夹")
            return

        if self.load_thread and self.load_thread.isRunning():
            self.load_thread.cancel()
            self.load_thread.wait()

        if self.preview_thread:
            self.preview_thread.stop()
            self.preview_thread.wait()

        self.map_view.clear_map()
        self._region_layers.clear()
        self._loaded_regions.clear()
        self._real_regions.clear()
        self._queued_regions.clear()

        self.current_world_reader = WorldReader(world_path)
        self.world_seed = read_world_seed(world_path)
        if self.world_seed is None:
            self.status_bar.showMessage("⚠ 未能读取世界种子，预览地形可能不准")
            self.world_seed = 0

        version = self.current_world_reader.get_world_version()
        self.setWindowTitle(
            f"高速公路规划器 - {Path(world_path).name} ({version})"
        )

        # 启动预览线程
        self.preview_thread = PreviewLoader(self.world_seed, self)
        self.preview_thread.region_ready.connect(self._on_preview_ready)
        self.preview_thread.start()

        # 启动主加载线程
        self.load_thread = WorldLoadThread(
            self.current_world_reader, self.block_mapper, self.world_seed, self
        )
        self.load_thread.progress.connect(self._on_load_progress)
        self.load_thread.region_ready.connect(self._on_real_region_ready)
        self.load_thread.finished_loading.connect(self._on_load_finished)
        self.load_thread.error.connect(self._on_load_error)

        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.load_thread.start()

    # ---------------- 加载回调 ----------------
    def _on_load_progress(self, current, total, message):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_bar.showMessage(message)

    def _on_real_region_ready(self, region_x, region_z, layers):
        """来自存档的真实区块"""
        self._real_regions.add((region_x, region_z))
        self._add_region_items(region_x, region_z, layers)
        self._loaded_regions.add((region_x, region_z))

        # 首次加载时自动缩放到合适视野
        if len(self._loaded_regions) == 1 and "texture" in layers:
            from PyQt6.QtWidgets import QGraphicsPixmapItem
            key = (region_x, region_z)
            if key in self._region_layers and "texture" in self._region_layers[key]:
                self.map_view.fitInView(
                    self._region_layers[key]["texture"],
                    Qt.AspectRatioMode.KeepAspectRatio,
                )

    def _on_preview_ready(self, region_x, region_z, layers):
        """来自预览线程的区块"""
        self._add_region_items(region_x, region_z, layers)
        self._loaded_regions.add((region_x, region_z))

    def _add_region_items(self, region_x, region_z, layers):
        """把一组图层 QImage 添加到场景"""
        key = (region_x, region_z)
        scene_x = region_x * 512
        scene_z = region_z * 512

        if key not in self._region_layers:
            self._region_layers[key] = {}

        for layer_name, qimage in layers.items():
            pixmap = QPixmap.fromImage(qimage)
            item = QGraphicsPixmapItem(pixmap)
            item.setPos(scene_x, scene_z)
            item.setScale(1.0 / BLOCK_PIXEL)
            item.setZValue(self._layer_z(layer_name))
            item.setVisible(self._layer_visibility.get(layer_name, True))

            # 移除同层旧图元
            old = self._region_layers[key].get(layer_name)
            if old is not None and old.scene() is not None:
                old.scene().removeItem(old)

            self.map_view.scene().addItem(item)
            self._region_layers[key][layer_name] = item

    @staticmethod
    def _layer_z(layer_name):
        return {
            "preview": 0,
            "texture": 10,
            "contour": 20,
            "road": 100,
        }.get(layer_name, 0)

    def _on_load_finished(self):
        self.progress_bar.hide()
        self.status_bar.showMessage("地图加载完成")
        self.map_view._zoom = 1.0

    def _on_load_error(self, message):
        self.progress_bar.hide()
        QMessageBox.critical(self, "加载失败", message)

    # ---------------- 动态加载 ----------------
    def _on_viewport_changed(self):
        """检测视口范围，为缺块请求预览地形"""
        if self.current_world_reader is None:
            return
        if self.preview_thread is None:
            return

        rx_min, rx_max, rz_min, rz_max = self.map_view.visible_region_range()

        # 限制一次请求的最大数量，防止快速拖动时瞬间爆队列
        count = 0
        for rx in range(rx_min, rx_max + 1):
            for rz in range(rz_min, rz_max + 1):
                if count >= 16:
                    return
                if (rx, rz) in self._loaded_regions:
                    continue
                if (rx, rz) in self._queued_regions:
                    continue
                self._queued_regions.add((rx, rz))
                self.preview_thread.request(rx, rz)
                count += 1

    # ---------------- 悬停 ----------------
    def _on_block_hovered(self, x, z, _, __):
        if self.current_world_reader is None:
            return

        # 编辑模式：显示光标坐标
        if self._edit_mode:
            active = self.highway_manager.get_active()
            if active:
                self.status_bar.showMessage(
                    f"坐标 ({x}, {z}) — 正在绘制 [{active.short_code}] {active.name}"
                )
                # 更新预览线
                if active.waypoints and self._preview_last_pos:
                    self._update_preview_line(x, z)
                return

        try:
            chunk_x, chunk_z = x >> 4, z >> 4
            local_x, local_z = x & 15, z & 15
            chunk = self.current_world_reader.get_chunk(chunk_x, chunk_z)
            if chunk is None:
                self.status_bar.showMessage(f"坐标 ({x}, {z}) — 预览地形")
                return

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
        if not self._edit_mode:
            self.status_bar.showMessage("")

    # ---------------- 编辑功能 ----------------
    def _on_open_edit_panel(self):
        self.edit_dock.show()

    def _on_new_highway(self):
        self._create_road(is_ramp=False)

    def _on_new_ramp(self):
        # 自动编号：R1、R2、R3 ...
        count = sum(1 for h in self.highway_manager.highways if h.is_ramp) + 1

        ramp = Highway(
            name=f"匝道 {count}",
            short_code=f"R{count}",
            color="light_gray",
            lanes=1,
            height=64,
            is_ramp=True,
        )
        self.highway_manager.add(ramp)
        self.edit_panel.refresh()
        self.edit_dock.show()

        # 立即进入编辑模式
        self._edit_mode = True
        self.status_bar.showMessage(
            f"已创建 [{ramp.short_code}]，点击地图开始绘制匝道"
        )

    def _create_road(self, is_ramp):
        dlg = NewHighwayDialog(self)
        if is_ramp:
            dlg.setWindowTitle("新建匝道")
            dlg.lanes_spin.setValue(1)
            dlg.lanes_spin.setEnabled(False)
        if dlg.exec() != NewHighwayDialog.DialogCode.Accepted:
            return

        hw = dlg.build_highway(is_ramp=is_ramp)
        self.highway_manager.add(hw)
        self.edit_panel.refresh()
        self.edit_dock.show()

        # 进入编辑模式
        self._edit_mode = True
        self.status_bar.showMessage(
            f"已创建 [{hw.short_code}] {hw.name}，点击地图放置第一个点"
        )

    def _on_highway_selected(self, hw_id):
        self.highway_manager.set_active(hw_id)
        self._edit_mode = True
        hw = self.highway_manager.get(hw_id)
        if hw:
            self.status_bar.showMessage(
                f"已选中 [{hw.short_code}] {hw.name}，点击地图继续添加点"
            )
        self._redraw_all_highways()

    def _on_highway_deleted(self, hw_id):
        # 先移除这条道路的所有图元
        if hasattr(self, "_highway_items"):
            for item in self._highway_items.pop(hw_id, []):
                if item.scene() is not None:
                    item.scene().removeItem(item)

        self.highway_manager.remove(hw_id)
        self.edit_panel.refresh()
        self._redraw_all_highways()

        # 如果删除的是当前正在编辑的道路，退出编辑模式
        if self.highway_manager.get_active() is None:
            self._edit_mode = False
            self._clear_preview_line()

    def _on_block_clicked(self, x, z):
        """编辑模式下点击地图，添加路点"""
        if not self._edit_mode:
            return
        active = self.highway_manager.get_active()
        if active is None:
            return

        self._push_undo()          # ← 新增
        active.add_waypoint(x, z)

        active.add_waypoint(x, z)
        self.status_bar.showMessage(
            f"[{active.short_code}] 已添加点 ({x}, {z})，共 {len(active.waypoints)} 个"
        )
        self._redraw_highway(active)
        # 清掉预览线
        self._clear_preview_line()

    def _redraw_highway(self, hw):
        """重绘一条高速的所有线段"""
        # 先移除旧图元
        if not hasattr(self, "_highway_items"):
            self._highway_items = {}
        for item in self._highway_items.pop(hw.id, []):
            if item.scene() is not None:
                item.scene().removeItem(item)

        items = []

        if len(hw.waypoints) >= 2:
            path = QPainterPath()
            first = hw.waypoints[0]
            path.moveTo(first.x, first.z)
            for wp in hw.waypoints[1:]:
                path.lineTo(wp.x, wp.z)

            line_item = QGraphicsPathItem(path)
            pen = QPen(QColor(hw.color_hex))
            pen.setWidthF(3.0 if not hw.is_ramp else 1.5)
            pen.setCosmetic(True)  # 缩放时线宽不变
            line_item.setPen(pen)
            line_item.setZValue(self._layer_z("road"))
            line_item.setVisible(self._layer_visibility.get("road", True))
            self.map_view.scene().addItem(line_item)
            items.append(line_item)

        # 每个路点画一个小圆
        for wp in hw.waypoints:
            dot = QGraphicsEllipseItem(wp.x - 2, wp.z - 2, 4, 4)
            dot.setBrush(QBrush(QColor(hw.color_hex)))
            dot.setPen(QPen(Qt.GlobalColor.white, 0.5))
            dot.setZValue(self._layer_z("road") + 1)
            dot.setVisible(self._layer_visibility.get("road", True))
            self.map_view.scene().addItem(dot)
            items.append(dot)

        self._highway_items[hw.id] = items

    def _redraw_all_highways(self):
        for hw in self.highway_manager.highways:
            self._redraw_highway(hw)

    def _update_preview_line(self, x, z):
        """绘制从最后一个路点到鼠标的预览线"""
        active = self.highway_manager.get_active()
        if active is None or not active.waypoints:
            return

        self._clear_preview_line()

        last = active.waypoints[-1]
        line = QGraphicsLineItem(last.x, last.z, x, z)
        pen = QPen(QColor(active.color_hex))
        pen.setStyle(Qt.PenStyle.DashLine)
        pen.setWidthF(2.0)
        pen.setCosmetic(True)
        line.setPen(pen)
        line.setZValue(self._layer_z("road") - 1)
        self.map_view.scene().addItem(line)
        self._preview_line_item = line

    def _clear_preview_line(self):
        if self._preview_line_item is not None:
            if self._preview_line_item.scene() is not None:
                self._preview_line_item.scene().removeItem(self._preview_line_item)
            self._preview_line_item = None

    # ---------------- 图层 ----------------
    def _on_layer_toggle(self):
        self._layer_visibility["texture"] = self.texture_action.isChecked()
        self._layer_visibility["contour"] = self.contour_action.isChecked()
        self._layer_visibility["preview"] = self.preview_action.isChecked()
        self._layer_visibility["road"] = self.road_action.isChecked()

        for items in self._region_layers.values():
            for name, item in items.items():
                item.setVisible(self._layer_visibility.get(name, True))

        if hasattr(self, "_highway_items"):
            for items in self._highway_items.values():
                for item in items:
                    item.setVisible(self._layer_visibility.get("road", True))

    # ---------------- 关闭 ----------------
    def closeEvent(self, event):
        if self.load_thread and self.load_thread.isRunning():
            self.load_thread.cancel()
            self.load_thread.wait(3000)
        if self.preview_thread:
            self.preview_thread.stop()
            self.preview_thread.wait(3000)
        if self.export_thread and self.export_thread.isRunning():
            self.export_thread.cancel()
            self.export_thread.wait(3000)
        super().closeEvent(event)
            # ---------------- 撤销 ----------------
    def _push_undo(self):
        """把当前所有道路的路点状态压入撤销栈"""
        snapshot = {}
        for hw in self.highway_manager.highways:
            snapshot[hw.id] = [(wp.x, wp.z, wp.y) for wp in hw.waypoints]
        self._undo_stack.append(snapshot)
        # 只保留最近 50 步
        if len(self._undo_stack) > 50:
            self._undo_stack.pop(0)

    def _on_undo(self):
        if not self._undo_stack:
            self.status_bar.showMessage("没有可撤销的操作")
            return

        snapshot = self._undo_stack.pop()

        # 恢复每条道路的路点
        for hw in self.highway_manager.highways:
            if hw.id in snapshot:
                hw.waypoints = [
                    Waypoint(x, z, y) for x, z, y in snapshot[hw.id]
                ]

        self._redraw_all_highways()
        self._clear_preview_line()
        self.status_bar.showMessage("已撤销")
    def _on_export(self):
        if not self.highway_manager.highways:
            QMessageBox.information(self, "没有道路", "请先创建至少一条道路")
            return
        if self.current_world_reader is None:
            QMessageBox.information(self, "没有存档", "请先加载一个世界")
            return
        if self.export_thread and self.export_thread.isRunning():
            QMessageBox.information(self, "正在导出", "上一次导出还没完成")
            return

        reply = QMessageBox.warning(
            self,
            "准备写入存档",
            "写入前请确认：\n\n"
            "1. 已退出 Minecraft 游戏\n"
            "2. 已备份存档\n\n"
            "⚠ 如果游戏正在运行，退出时游戏会覆盖你的修改！\n\n"
            "是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        # 地形高度函数（用预览生成器，够用）
        def height_fn(x, z):
            try:
                from core.terrain_generator import PreviewTerrainGenerator
                if not hasattr(self, "_height_gen"):
                    self._height_gen = PreviewTerrainGenerator(self.world_seed or 0)
                return self._height_gen.height_at(x, z)
            except Exception:
                return None

        world_path = str(self.current_world_reader.world_path)

        self.export_thread = ExportThread(
            self.highway_manager.highways,
            world_path,
            height_map_fn=height_fn,
            parent=self,
        )
        self.export_thread.progress.connect(self._on_load_progress)
        self.export_thread.finished_export.connect(self._on_export_finished)
        self.export_thread.error.connect(self._on_export_error)

        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.status_bar.showMessage("开始导出...")
        self.export_thread.start()

    def _on_export_finished(self, success, failed):
        self.progress_bar.hide()
        QMessageBox.information(
            self,
            "导出完成",
            f"成功写入 {success} 个方块\n"
            f"失败 {failed} 个（通常是区域未加载）\n\n"
            f"现在可以启动游戏查看了。"
        )
        self.status_bar.showMessage(
            f"导出完成：成功 {success}，失败 {failed}"
        )

    def _on_export_error(self, message):
        self.progress_bar.hide()
        QMessageBox.critical(self, "导出失败", message)
