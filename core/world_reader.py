"""读取 Java 版 Anvil 存档格式"""
from pathlib import Path

import anvil


class WorldReader:
    def __init__(self, world_path):
        self.world_path = Path(world_path)
        self.region_dir = self.world_path / "region"
        self._region_cache = {}
        self._chunk_cache = {}

    def list_regions(self):
        """列出所有 region 文件 [(rx, rz, path), ...]"""
        if not self.region_dir.exists():
            return []

        regions = []
        for f in sorted(self.region_dir.glob("r.*.*.mca")):
            parts = f.stem.split(".")
            if len(parts) != 3:
                continue
            try:
                rx, rz = int(parts[1]), int(parts[2])
                regions.append((rx, rz, f))
            except ValueError:
                continue
        return regions

    def _load_region(self, region_x, region_z):
        key = (region_x, region_z)
        if key in self._region_cache:
            return self._region_cache[key]

        region_file = self.region_dir / f"r.{region_x}.{region_z}.mca"
        if not region_file.exists():
            return None

        try:
            region = anvil.Region.from_file(str(region_file))
            self._region_cache[key] = region
            return region
        except Exception:
            return None

    def get_chunk(self, chunk_x, chunk_z):
        """读取指定区块"""
        key = (chunk_x, chunk_z)
        if key in self._chunk_cache:
            return self._chunk_cache[key]

        region_x = chunk_x >> 5
        region_z = chunk_z >> 5
        region = self._load_region(region_x, region_z)
        if region is None:
            self._chunk_cache[key] = None
            return None

        try:
            chunk = anvil.Chunk.from_region(region, chunk_x & 31, chunk_z & 31)
        except Exception:
            chunk = None

        self._chunk_cache[key] = chunk
        return chunk

    def clear_cache(self):
        self._region_cache.clear()
        self._chunk_cache.clear()

    def get_world_version(self):
        """读取世界版本名（从 level.dat）"""
        try:
            import nbtlib
            level_dat = self.world_path / "level.dat"
            if not level_dat.exists():
                return "未知"
            data = nbtlib.load(str(level_dat))
            version = data["Data"]["Version"]["Name"]
            return str(version)
        except Exception:
            return "未知"
