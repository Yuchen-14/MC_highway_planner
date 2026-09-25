"""后台线程：扫描存档并渲染区域图像"""
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage, QColor

from core.terrain_scanner import TerrainScanner


# 每个方块在渲染图像中的像素尺寸
BLOCK_PIXEL = 4


class WorldLoadThread(QThread):
    progress = pyqtSignal(int, int, str)           # 当前, 总数, 消息
    region_ready = pyqtSignal(int, int, QImage)    # rx, rz, image
    finished_loading = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, world_reader, block_mapper, parent=None):
        super().__init__(parent)
        self.reader = world_reader
        self.mapper = block_mapper
        self.scanner = TerrainScanner(world_reader)
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def _render_region(self, region_x, region_z):
        """渲染一个 region 为 QImage"""
        size_px = 512 * BLOCK_PIXEL  # 32 chunks * 16 blocks * BLOCK_PIXEL
        image = QImage(size_px, size_px, QImage.Format.Format_ARGB32)
        image.fill(QColor(0, 0, 0, 0))

        surface = self.scanner.scan_region(
            region_x, region_z,
            cancel_check=lambda: self._cancel,
        )

        if self._cancel:
            return image

        for wx, wz, wy, bid in surface:
            # 转换成 region 内的局部像素坐标
            local_x = wx - region_x * 512
            local_z = wz - region_z * 512
            px = local_x * BLOCK_PIXEL
            pz = local_z * BLOCK_PIXEL

            tex = self.mapper.load_texture(bid, BLOCK_PIXEL)
            if tex is None:
                # 无法找到纹理时，用一个灰色方块占位
                color = QColor(128, 128, 128, 255)
                for dx in range(BLOCK_PIXEL):
                    for dz in range(BLOCK_PIXEL):
                        image.setPixelColor(px + dx, pz + dz, color)
                continue

            # PIL.Image → QImage
            tex_rgba = tex.convert("RGBA")
            tex_bytes = tex_rgba.tobytes("raw", "RGBA")
            tex_qimg = QImage(
                tex_bytes,
                BLOCK_PIXEL, BLOCK_PIXEL,
                BLOCK_PIXEL * 4,
                QImage.Format.Format_RGBA8888,
            )
            tex_qimg = tex_qimg.copy()  # 复制以避免内存被释放

            from PyQt6.QtGui import QPainter
            painter = QPainter(image)
            painter.drawImage(px, pz, tex_qimg)
            painter.end()

        return image

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
                image = self._render_region(rx, rz)
                if self._cancel:
                    return
                self.region_ready.emit(rx, rz, image)

            self.progress.emit(total, total, "地图渲染完成")
            self.finished_loading.emit()

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
