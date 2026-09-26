"""地图视图：支持缩放、拖拽、悬停、点击"""
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene
from PyQt6.QtCore import Qt, pyqtSignal, QPointF
from PyQt6.QtGui import QPainter, QWheelEvent


class MapView(QGraphicsView):
    block_hovered = pyqtSignal(int, int, int, str)
    mouse_left = pyqtSignal()
    viewport_changed = pyqtSignal()
    block_clicked = pyqtSignal(int, int)  # 世界坐标 x, z

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
            self.viewport_changed.emit()

    def mouseMoveEvent(self, event):
        scene_pos = self.mapToScene(event.pos())
        bx = int(scene_pos.x())
        bz = int(scene_pos.y())
        self.block_hovered.emit(bx, bz, 0, "")
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # ScrollHandDrag 模式下也要能捕获点击
            scene_pos = self.mapToScene(event.pos())
            bx = int(scene_pos.x())
            bz = int(scene_pos.y())
            self.block_clicked.emit(bx, bz)
        super().mousePressEvent(event)

    def scrollContentsBy(self, dx, dy):
        super().scrollContentsBy(dx, dy)
        self.viewport_changed.emit()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.viewport_changed.emit()

    def leaveEvent(self, event):
        self.mouse_left.emit()
        super().leaveEvent(event)

    def visible_region_range(self):
        """返回当前视口覆盖的 region 坐标范围 (rx_min, rx_max, rz_min, rz_max)"""
        rect = self.mapToScene(self.viewport().rect()).boundingRect()
        rx_min = int(rect.left()) // 512
        rx_max = int(rect.right()) // 512
        rz_min = int(rect.top()) // 512
        rz_max = int(rect.bottom()) // 512
        return rx_min, rx_max, rz_min, rz_max
