"""后台线程：按需生成预览地形区块"""
from collections import deque

from PyQt6.QtCore import QThread, pyqtSignal

from core.terrain_generator import PreviewTerrainGenerator
from core import renderer


class PreviewLoader(QThread):
    """监听请求队列，一次渲染一个预览 region"""
    region_ready = pyqtSignal(int, int, dict)  # rx, rz, {layer: QImage}

    def __init__(self, seed, parent=None):
        super().__init__(parent)
        self.generator = PreviewTerrainGenerator(seed)
        self._queue = deque()
        self._pending = set()
        self._cancel = False

    def request(self, region_x, region_z):
        key = (region_x, region_z)
        if key in self._pending:
            return
        self._pending.add(key)
        self._queue.append(key)
        if not self.isRunning():
            self.start()

    def cancel_all(self):
        self._queue.clear()
        self._pending.clear()

    def stop(self):
        self._cancel = True
        self._queue.clear()
        self._pending.clear()

    def run(self):
        while not self._cancel:
            if not self._queue:
                # 空闲 200ms 后退出线程
                self.msleep(200)
                if not self._queue:
                    break
                continue

            rx, rz = self._queue.popleft()
            self._pending.discard((rx, rz))

            if self._cancel:
                break

            # 生成预览层和等高线层
            preview_img = renderer.render_preview_layer(self.generator, rx, rz)
            contour_img = renderer.render_contour_layer(self.generator, rx, rz)

            self.region_ready.emit(rx, rz, {
                "preview": preview_img,
                "contour": contour_img,
            })
