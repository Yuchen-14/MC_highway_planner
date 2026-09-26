"""统一渲染器：把地形数据渲染成各图层的 QImage"""
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QColor, QPainter, QPen

# 每个方块在图像中的像素尺寸
BLOCK_PIXEL = 4

# 等高线间隔（每多少格画一条）
CONTOUR_STEP = 16

# 预览地形方块高度对应的颜色（用于在不显示纹理时占位）
PREVIEW_COLORS = {
    "ocean":    QColor(40, 80, 150, 180),
    "beach":    QColor(220, 210, 160, 180),
    "plains":   QColor(120, 180, 90, 180),
    "forest":   QColor(60, 130, 70, 180),
    "mountain": QColor(130, 120, 110, 180),
}


def render_texture_layer(surface_blocks, region_x, region_z, block_mapper):
    """渲染纹理图层
    surface_blocks: [(wx, wz, y, block_id), ...]
    """
    size_px = 512 * BLOCK_PIXEL
    image = QImage(size_px, size_px, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)

    painter = QPainter(image)

    for wx, wz, wy, bid in surface_blocks:
        local_x = wx - region_x * 512
        local_z = wz - region_z * 512
        if not (0 <= local_x < 512 and 0 <= local_z < 512):
            continue

        px = local_x * BLOCK_PIXEL
        pz = local_z * BLOCK_PIXEL

        tex = block_mapper.load_texture(bid, BLOCK_PIXEL)
        if tex is None:
            painter.fillRect(px, pz, BLOCK_PIXEL, BLOCK_PIXEL,
                             QColor(128, 128, 128, 255))
            continue

        tex_rgba = tex.convert("RGBA")
        tex_bytes = tex_rgba.tobytes("raw", "RGBA")
        tex_qimg = QImage(tex_bytes, BLOCK_PIXEL, BLOCK_PIXEL,
                          BLOCK_PIXEL * 4, QImage.Format.Format_RGBA8888).copy()
        painter.drawImage(px, pz, tex_qimg)

    painter.end()
    return image


def render_preview_layer(generator, region_x, region_z):
    """渲染预览地形图层（未加载区块）"""
    size_px = 512 * BLOCK_PIXEL
    image = QImage(size_px, size_px, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)

    painter = QPainter(image)
    base_x = region_x * 512
    base_z = region_z * 512

    for lx in range(512):
        for lz in range(512):
            wx = base_x + lx
            wz = base_z + lz
            hint = generator.biome_hint(wx, wz)
            color = PREVIEW_COLORS.get(hint, QColor(100, 100, 100, 180))
            painter.fillRect(lx * BLOCK_PIXEL, lz * BLOCK_PIXEL,
                             BLOCK_PIXEL, BLOCK_PIXEL, color)

    painter.end()
    return image


def render_contour_layer(generator, region_x, region_z):
    """渲染等高线图层

    只在高度跨越 CONTOUR_STEP 倍数的地方画线，避免整片染色。
    """
    size_px = 512 * BLOCK_PIXEL
    image = QImage(size_px, size_px, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)

    painter = QPainter(image)
    pen = QPen(QColor(0, 0, 0, 120))
    pen.setWidth(1)
    painter.setPen(pen)

    base_x = region_x * 512
    base_z = region_z * 512

    # 先算一遍高度缓存，避免重复计算
    heights = {}
    for lx in range(512):
        for lz in range(512):
            heights[(lx, lz)] = generator.height_at(base_x + lx, base_z + lz)

    for lx in range(512):
        for lz in range(512):
            h = heights[(lx, lz)]
            line_index = h // CONTOUR_STEP

            # 检查右邻居和下邻居是否跨层
            if lx + 1 < 512:
                hr = heights[(lx + 1, lz)]
                if hr // CONTOUR_STEP != line_index:
                    px = (lx + 1) * BLOCK_PIXEL
                    painter.drawLine(px, lz * BLOCK_PIXEL,
                                     px, (lz + 1) * BLOCK_PIXEL)

            if lz + 1 < 512:
                hd = heights[(lx, lz + 1)]
                if hd // CONTOUR_STEP != line_index:
                    pz = (lz + 1) * BLOCK_PIXEL
                    painter.drawLine(lx * BLOCK_PIXEL, pz,
                                     (lx + 1) * BLOCK_PIXEL, pz)

    painter.end()
    return image
