"""方块调色板：定义道路生成用到的所有方块 ID"""

AIR = "minecraft:air"

# 路面
BLUE_ICE = "minecraft:blue_ice"
BLACK_CONCRETE = "minecraft:black_concrete"

# 护栏
END_ROD = "minecraft:end_rod"
GLASS = "minecraft:glass"

# 标志牌
GREEN_CONCRETE = "minecraft:green_concrete"
STONE_WALL = "minecraft:stone_brick_wall"

# 匝道
SNOW_BLOCK = "minecraft:snow_block"
SNOW_LAYER = "minecraft:snow"
STONE_BRICK_SLAB = "minecraft:stone_brick_slab"

# 支撑
SUPPORT_BLOCKS = [
    "minecraft:stone",
    "minecraft:cobblestone",
    "minecraft:andesite",
    "minecraft:diorite",
    "minecraft:granite",
]

# 树叶（道路每隔一段换一款）
LEAF_TYPES = [
    "minecraft:oak_leaves",
    "minecraft:spruce_leaves",
    "minecraft:birch_leaves",
    "minecraft:jungle_leaves",
    "minecraft:acacia_leaves",
    "minecraft:dark_oak_leaves",
]

# 隧道
STONE = "minecraft:stone"


def pick_leaf(x, z, block_size=100):
    """根据坐标选一款树叶，每 block_size 格换一次"""
    index = (abs(x) // block_size + abs(z) // block_size) % len(LEAF_TYPES)
    return LEAF_TYPES[index]


def pick_support(x, y, z):
    """根据坐标确定性选一个支撑方块"""
    index = (abs(x) * 31 + abs(y) * 17 + abs(z)) % len(SUPPORT_BLOCKS)
    return SUPPORT_BLOCKS[index]
