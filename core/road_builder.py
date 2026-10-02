"""道路方块生成：把一条高速公路转成一堆方块变更"""
import math

from core.block_palette import (
    AIR, BLUE_ICE, BLACK_CONCRETE, END_ROD, GLASS,
    GREEN_CONCRETE, STONE_WALL, SNOW_BLOCK, SNOW_LAYER,
    STONE_BRICK_SLAB, STONE, pick_leaf, pick_support,
)
from core.road_path import generate_smooth_path


class BlockChange:
    __slots__ = ("x", "y", "z", "block_id")

    def __init__(self, x, y, z, block_id):
        self.x = int(x)
        self.y = int(y)
        self.z = int(z)
        self.block_id = block_id

    def __repr__(self):
        return f"BlockChange({self.x},{self.y},{self.z},{self.block_id})"


class RoadBuilder:
    def __init__(self, highway, height_map_fn=None):
        """
        highway: Highway 对象
        height_map_fn: 可选，函数 (x, z) -> 近似地表高度，用于开山搭桥
        """
        self.highway = highway
        self.height_map_fn = height_map_fn
        self.changes = []

    # ---------------- 主入口 ----------------
    def generate(self):
        """生成这条道路的所有方块变更"""
        self.changes = []

        waypoints = [(wp.x, wp.z) for wp in self.highway.waypoints]
        if len(waypoints) < 2:
            return self.changes

        path = generate_smooth_path(waypoints, iterations=3, step=1.0)
        if not path:
            return self.changes

        if self.highway.is_ramp:
            self._build_ramp(path)
        else:
            self._build_highway(path)

        return self.changes

    # ---------------- 高速公路 ----------------
    def _build_highway(self, path):
        hw = self.highway
        y = hw.height
        lanes = max(1, hw.lanes)

        # 计算横向宽度（格数）
        # 中心 1 + 每侧 (1 + 3*lanes) 格
        # 例如 N=1: 中心 + 左右各 4 格 = 9 格
        half_width = 1 + 3 * lanes  # 单侧宽度（含外侧黑混凝土）
        total_width = half_width * 2 + 1  # 加中心

        for i, (px, pz) in enumerate(path):
            # 计算方向向量
            if i == 0:
                dx = path[1][0] - path[0][0]
                dz = path[1][1] - path[0][1]
            elif i == len(path) - 1:
                dx = path[-1][0] - path[-2][0]
                dz = path[-1][1] - path[-2][1]
            else:
                dx = path[i + 1][0] - path[i - 1][0]
                dz = path[i + 1][1] - path[i - 1][1]

            length = math.hypot(dx, dz)
            if length < 1e-6:
                continue
            # 垂直向量（指向左侧）
            nx = -dz / length
            nz = dx / length

            cx = int(round(px))
            cz = int(round(pz))

            # 逐格放置横截面
            for offset in range(-half_width, half_width + 1):
                bx = int(round(cx + nx * offset))
                bz = int(round(cz + nz * offset))

                block = self._cross_section_block(offset, lanes)
                self.changes.append(BlockChange(bx, y, bz, block))

            # 护栏与装饰
            self._place_railings(cx, cz, nx, nz, half_width, lanes, y)

            # 自动开山搭桥
            if self.height_map_fn:
                self._auto_terrain(cx, cz, nx, nz, half_width, y)

    def _cross_section_block(self, offset, lanes):
        """给定横向偏移，返回路面方块"""
        if offset == 0:
            return BLACK_CONCRETE  # 中心分隔线

        side = 1 if offset > 0 else -1
        abs_off = abs(offset)

        # 外侧边缘
        if abs_off == 1 + 3 * lanes:
            return BLACK_CONCRETE

        # 车道之间
        # 位置规律：外侧边缘 → 蓝冰×3 → 黑 → 蓝冰×3 → 黑 → ... → 中心
        # 从中心向外数：0=中心黑，1..3=蓝冰，4=黑，5..7=蓝冰，8=黑，...
        pos_from_center = abs_off
        # 每个"车道+分隔线"块宽度为 4，除了最内侧只有蓝冰
        remainder = (pos_from_center - 1) % 4
        if remainder == 3:
            return BLACK_CONCRETE
        return BLUE_ICE

    def _place_railings(self, cx, cz, nx, nz, half_width, lanes, y):
        # 中心：末地烛 + 树叶
        self.changes.append(BlockChange(cx, y + 1, cz, END_ROD))
        leaf = pick_leaf(cx, cz)
        self.changes.append(BlockChange(cx, y + 2, cz, leaf))

        # 两侧外侧边缘：玻璃 + 黑混凝土
        for side in (-1, 1):
            ox = int(round(cx + nx * half_width * side))
            oz = int(round(cz + nz * half_width * side))
            self.changes.append(BlockChange(ox, y + 1, oz, GLASS))
            self.changes.append(BlockChange(ox, y + 2, oz, BLACK_CONCRETE))

    def _auto_terrain(self, cx, cz, nx, nz, half_width, y):
        """开山搭桥"""
        for offset in range(-half_width, half_width + 1):
            bx = int(round(cx + nx * offset))
            bz = int(round(cz + nz * offset))

            try:
                ground_y = self.height_map_fn(bx, bz)
            except Exception:
                continue
            if ground_y is None:
                continue

            # 开山：地表高于路面的部分要清除
            if ground_y > y:
                for clear_y in range(y + 1, ground_y + 1):
                    self.changes.append(BlockChange(bx, clear_y, bz, AIR))

            # 搭桥：地表远低于路面，要加支撑
            elif ground_y < y - 2:
                # 只在外侧边缘和中心加桥墩，避免每格都加
                if offset in (-half_width, 0, half_width):
                    for support_y in range(ground_y + 1, y):
                        block = pick_support(bx, support_y, bz)
                        self.changes.append(BlockChange(bx, support_y, bz, block))

    # ---------------- 匝道 ----------------
    def _build_ramp(self, path):
        hw = self.highway
        base_y = hw.height

        for i, (px, pz) in enumerate(path):
            cx = int(round(px))
            cz = int(round(pz))
            y = base_y

            # 蓝冰 + 下方支撑
            self.changes.append(BlockChange(cx, y, cz, BLUE_ICE))
            self.changes.append(BlockChange(cx, y - 1, cz, pick_support(cx, y - 1, cz)))

            # 上方三层雪
            for dy in (1, 2, 3):
                self.changes.append(BlockChange(cx, y + dy, cz, SNOW_BLOCK))

            # 半砖 + 雪
            self.changes.append(BlockChange(cx, y + 4, cz, STONE_BRICK_SLAB))
            self.changes.append(BlockChange(cx, y + 5, cz, SNOW_LAYER))

            # 下方支撑填到地面
            if self.height_map_fn:
                try:
                    ground_y = self.height_map_fn(cx, cz)
                except Exception:
                    ground_y = None
                if ground_y is not None and ground_y < y - 1:
                    for support_y in range(ground_y + 1, y - 1):
                        self.changes.append(
                            BlockChange(cx, support_y, cz, pick_support(cx, support_y, cz))
                        )
