"""扫描存档中的地表方块"""

# 1.18+ 世界高度范围
WORLD_MAX_Y = 319
WORLD_MIN_Y = -64

# 兼容带前缀和不带前缀两种格式
AIR_IDS = {"air", "cave_air", "void_air", "minecraft:air", "minecraft:cave_air", "minecraft:void_air"}


def normalize_block_id(block_id):
    """统一加上 minecraft: 前缀"""
    if block_id is None:
        return None
    if ":" in block_id:
        return block_id
    return f"minecraft:{block_id}"


class TerrainScanner:
    def __init__(self, world_reader):
        self.reader = world_reader

    def scan_chunk_surface(self, chunk_x, chunk_z):
        """扫描一个区块的地表，返回 [(world_x, world_z, y, block_id), ...]"""
        chunk = self.reader.get_chunk(chunk_x, chunk_z)
        if chunk is None:
            return []

        base_x = chunk_x * 16
        base_z = chunk_z * 16
        surface = []

        for x in range(16):
            for z in range(16):
                found = None
                for y in range(WORLD_MAX_Y, WORLD_MIN_Y - 1, -1):
                    try:
                        block = chunk.get_block(x, y, z)
                    except Exception:
                        continue
                    if block is None:
                        continue
                    if block.id not in AIR_IDS:
                        found = (y, normalize_block_id(block.id))
                        break

                if found is not None:
                    y, bid = found
                    surface.append((base_x + x, base_z + z, y, bid))

        return surface

    def scan_region(self, region_x, region_z, cancel_check=None):
        """扫描整个 region，返回 [(wx, wz, y, block_id), ...]"""
        result = []
        for cx in range(32):
            for cz in range(32):
                if cancel_check and cancel_check():
                    return result
                chunk_x = region_x * 32 + cx
                chunk_z = region_z * 32 + cz
                result.extend(self.scan_chunk_surface(chunk_x, chunk_z))
        return result
