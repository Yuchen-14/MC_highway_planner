"""数据包生成器：生成包含 forceload 命令的数据包"""
import json
import zipfile

from core.road_path import generate_smooth_path


# 各版本的 pack_format 对照表
PACK_FORMATS = [
    ("1.21.11", 88),
    ("1.21.9", 88),
    ("1.21.6", 80),
    ("1.21.5", 71),
    ("1.21.4", 61),
    ("1.21.2", 57),
    ("1.21", 48),
    ("1.20.5", 41),
    ("1.20.3", 26),
    ("1.20.2", 18),
    ("1.20", 15),
    ("1.19.4", 13),
    ("1.19.3", 12),
    ("1.19", 9),
    ("1.18", 8),
    ("1.17", 7),
    ("1.16.2", 6),
    ("1.16", 5),
    ("1.13", 4),
]


def guess_pack_format(version_string):
    """从版本字符串猜 pack_format"""
    if not version_string:
        return 88
    for prefix, fmt in PACK_FORMATS:
        if version_string.startswith(prefix):
            return fmt
    return 88


def collect_region_coords(highways):
    """收集道路经过的所有 region 坐标 (rx, rz)"""
    regions = set()
    for hw in highways:
        waypoints = [(wp.x, wp.z) for wp in hw.waypoints]
        if len(waypoints) < 2:
            continue
        path = generate_smooth_path(waypoints, iterations=2, step=2.0)
        half_width = 1 + 3 * hw.lanes
        pad_chunks = (half_width + 4) // 16 + 1
        pad_regions = pad_chunks // 32 + 1

        for px, pz in path:
            rx = int(px) >> 9
            rz = int(pz) >> 9
            for dx in range(-pad_regions, pad_regions + 1):
                for dz in range(-pad_regions, pad_regions + 1):
                    regions.add((rx + dx, rz + dz))
    return regions


def build_datapack(highways, world_version, output_path, world_name=""):
    """生成数据包 zip

    返回: (成功, 消息, 区域数)
    """
    regions = collect_region_coords(highways)
    if not regions:
        return False, "没有道路需要预生成", 0

    pack_format = guess_pack_format(world_version)

    # 生成 start.mcfunction
    lines = [
        'tellraw @a {"text":"[HighwayPlanner] 开始预生成区块...","color":"green"}',
    ]
    for rx, rz in sorted(regions):
        x_min = rx * 512
        z_min = rz * 512
        x_max = x_min + 511
        z_max = z_min + 511
        lines.append(f"forceload add {x_min} {z_min} {x_max} {z_max}")

    chunk_count = len(regions) * 1024
    lines.append(
        f'tellraw @a {{"text":"[HighwayPlanner] 已请求加载 {len(regions)} 个区域'
        f'（{chunk_count} 个区块），等待游戏处理...","color":"green"}}'
    )
    lines.append(
        'tellraw @a {"text":"[HighwayPlanner] 完成后执行 /function highway_planner:cleanup","color":"yellow"}'
    )
    lines.append(
        'tellraw @a {"text":"[HighwayPlanner] 之后回到规划器点「出发」","color":"yellow"}'
    )

    start_mcfunction = "\n".join(lines) + "\n"

    cleanup_mcfunction = (
        'forceload remove all\n'
        'tellraw @a {"text":"[HighwayPlanner] 已清理 forceload 标记","color":"green"}\n'
    )

    pack_mcmeta = {
        "pack": {
            "pack_format": pack_format,
            "supported_formats": {"min_inclusive": 4, "max_inclusive": 99},
            "description": f"Highway Planner 区块预生成 {world_name}".strip()
        }
    }

    try:
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(
                "pack.mcmeta",
                json.dumps(pack_mcmeta, ensure_ascii=False, indent=2)
            )
            zf.writestr(
                "data/highway_planner/function/start.mcfunction",
                start_mcfunction
            )
            zf.writestr(
                "data/highway_planner/function/cleanup.mcfunction",
                cleanup_mcfunction
            )
    except Exception as e:
        return False, f"写入失败：{e}", 0

    return True, f"数据包已生成", len(regions)
