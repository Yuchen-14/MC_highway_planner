"""地图视图：支持缩放、拖拽、悬停"""
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QWheelEvent


class MapView(QGraphicsView):
    block_hovered = pyqtSignal(int, int, int, str)  # x, z, y, block_id
    mouse_left = pyqtSignal()

    MIN_ZOOM = 0.02
    MAX_ZOOM = 16.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setMouseTracking(True)
        self.setBackgroundBrush(Qt.GlobalColor.black)
        self._zoom = 1.0

    def clear_map(self):
        self.scene().clear()
        self._zoom = 1.0
        self.resetTransform()

    def wheelEvent(self, event: QWheelEvent):
        delta = event.angleDelta().y()
        if delta == 0:
            return
        factor = 1.15 if delta > 0 else 1 / 1.15
        new_zoom = self._zoom * factor
        if self.MIN_ZOOM <= new_zoom <= self.MAX_ZOOM:
            self._zoom = new_zoom
            self.scale(factor, factor)

    def mouseMoveEvent(self, event):
        scene_pos = self.mapToScene(event.pos())
        bx = int(scene_pos.x())
        bz = int(scene_pos.y())
        self.block_hovered.emit(bx, bz, 0, "")  # 占位，主窗口会查询真实值
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self.mouse_left.emit()
        super().leaveEvent(event)
