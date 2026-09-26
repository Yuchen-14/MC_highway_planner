"""后台线程：扫描存档并渲染各图层"""
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage

from core.terrain_scanner import TerrainScanner
from core.terrain_generator import PreviewTerrainGenerator
from core import renderer


class WorldLoadThread(QThread):
    """渲染已加载区块"""
    progress = pyqtSignal(int, int, str)
    region_ready = pyqtSignal(int, int, dict)  # rx, rz, {layer_name: QImage}
    finished_loading = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, world_reader, block_mapper, seed, parent=None):
        super().__init__(parent)
        self.reader = world_reader
        self.mapper = block_mapper
        self.scanner = TerrainScanner(world_reader)
        self.generator = PreviewTerrainGenerator(seed)
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        try:
            regions = self.reader.list_regions()
            if not regions:
                self.error.emit("存档中没有找到任何 region 文件")
                return

            total = len(regions)
            for i, (rx, rz, _) in enumerate(regions):
                if self._cancel:
                    return

                self.progress.emit(i, total, f"正在渲染地图... ({i+1}/{total})")

                surface = self.scanner.scan_region(
                    rx, rz, cancel_check=lambda: self._cancel
                )
                if self._cancel:
                    return

                layers = {
                    "texture": renderer.render_texture_layer(
                        surface, rx, rz, self.mapper
                    ),
                    "contour": renderer.render_contour_layer(
                        self.generator, rx, rz
                    ),
                }
                self.region_ready.emit(rx, rz, layers)

            self.progress.emit(total, total, "地图渲染完成")
            self.finished_loading.emit()

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
