"""方块 ID 到纹理的映射"""
from pathlib import Path

from PIL import Image


class BlockMapper:
    def __init__(self, texture_dir):
        self.texture_dir = Path(texture_dir)
        self._path_cache = {}
        self._img_cache = {}

    def get_texture_path(self, block_id):
        if block_id in self._path_cache:
            return self._path_cache[block_id]

        # 去掉命名空间前缀
        name = block_id.split(":", 1)[-1]

        candidates = [
            self.texture_dir / f"{name}.png",
            self.texture_dir / f"{name}_top.png",
            self.texture_dir / f"{name}_side.png",
        ]
        for c in candidates:
            if c.exists():
                self._path_cache[block_id] = c
                return c

        self._path_cache[block_id] = None
        return None

    def load_texture(self, block_id, size):
        """加载并缩放到指定大小的 PIL 图像"""
        key = (block_id, size)
        if key in self._img_cache:
            return self._img_cache[key]

        path = self.get_texture_path(block_id)
        if path is None:
            return None

        try:
            img = Image.open(path).convert("RGBA")
            if img.size != (size, size):
                img = img.resize((size, size), Image.NEAREST)
        except Exception:
            return None

        self._img_cache[key] = img
        return img
