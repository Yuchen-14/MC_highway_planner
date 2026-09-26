"""基于噪声的预览地形生成

重要说明：
这不是 Minecraft 的精确地形生成算法，而是用相似思路做的近似预览。
目的是让用户在未加载区域也能判断"大概有没有山、有没有谷"。
"""
import math


class SimpleNoise:
    """基于整数哈希的 2D 值噪声"""

    def __init__(self, seed):
        self.seed = int(seed) & 0xFFFFFFFF

    def _hash(self, x, y):
        n = (x * 374761393 + y * 668265263 + self.seed) & 0xFFFFFFFF
        n = (n ^ (n >> 13)) * 1274126177 & 0xFFFFFFFF
        return ((n ^ (n >> 16)) & 0x7FFFFFFF) / 0x7FFFFFFF

    @staticmethod
    def _smooth(t):
        return t * t * (3 - 2 * t)

    def noise2(self, x, y):
        x0 = math.floor(x)
        y0 = math.floor(y)
        x1 = x0 + 1
        y1 = y0 + 1

        sx = self._smooth(x - x0)
        sy = self._smooth(y - y0)

        n00 = self._hash(x0, y0)
        n10 = self._hash(x1, y0)
        n01 = self._hash(x0, y1)
        n11 = self._hash(x1, y1)

        nx0 = n00 * (1 - sx) + n10 * sx
        nx1 = n01 * (1 - sx) + n11 * sx
        return nx0 * (1 - sy) + nx1 * sy


class PreviewTerrainGenerator:
    """预览地形生成器

    用多层噪声叠加，模拟大陆、丘陵、山脉三个尺度的地形。
    返回的高度大致在 [50, 180] 区间，接近 Minecraft 地表范围。
    """

    def __init__(self, seed):
        self.seed = int(seed) if seed is not None else 0
        self.noise = SimpleNoise(self.seed)

    def _fbm(self, x, z, scale, octaves, persistence):
        """分形噪声"""
        total = 0.0
        amplitude = 1.0
        frequency = 1.0 / scale
        max_amp = 0.0
        for _ in range(octaves):
            total += self.noise.noise2(x * frequency, z * frequency) * amplitude
            max_amp += amplitude
            amplitude *= persistence
            frequency *= 2.0
        return (total / max_amp) * 2.0 - 1.0

    def height_at(self, x, z):
        """返回该坐标的近似地表高度"""
        # 大陆层：极低频，决定整体是海洋还是陆地
        continent = self._fbm(x, z, scale=2048, octaves=3, persistence=0.5) * 30
        # 丘陵层：中频，决定小起伏
        hills = self._fbm(x + 5000, z, scale=256, octaves=4, persistence=0.5) * 25
        # 山脉层：高频 + 脊状，决定山脊
        mountain = abs(self._fbm(x, z + 5000, scale=512, octaves=3, persistence=0.45)) * 45

        base = 64.0
        return int(base + continent + hills + mountain)

    def biome_hint(self, x, z):
        """根据高度给出一个粗糙的群系提示"""
        h = self.height_at(x, z)
        if h < 58:
            return "ocean"
        if h < 64:
            return "beach"
        if h < 90:
            return "plains"
        if h < 130:
            return "forest"
        return "mountain"
