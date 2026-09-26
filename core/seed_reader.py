"""从 level.dat 读取世界种子"""
from pathlib import Path

import nbtlib


def read_world_seed(world_path):
    """读取世界种子，失败返回 None"""
    level_dat = Path(world_path) / "level.dat"
    if not level_dat.exists():
        return None

    try:
        data = nbtlib.load(str(level_dat))
        root = data["Data"]

        # 1.16+ 格式：Data.WorldGenSettings.seed
        if "WorldGenSettings" in root:
            ws = root["WorldGenSettings"]
            if "seed" in ws:
                return int(ws["seed"])

            # 某些版本把种子放在维度设置里
            dims = ws.get("dimensions")
            if dims:
                ow = dims.get("minecraft:overworld")
                if ow:
                    gen = ow.get("generator")
                    if gen:
                        settings = gen.get("settings")
                        if settings and "seed" in settings:
                            return int(settings["seed"])

        # 旧格式：Data.RandomSeed
        if "RandomSeed" in root:
            return int(root["RandomSeed"])

    except Exception:
        pass

    return None


def read_world_info(world_path):
    """一次性读取世界的基本信息"""
    level_dat = Path(world_path) / "level.dat"
    info = {
        "seed": None,
        "version": "未知",
        "world_name": Path(world_path).name,
        "generator": "未知",
    }

    if not level_dat.exists():
        return info

    try:
        data = nbtlib.load(str(level_dat))
        root = data["Data"]

        if "Version" in root and "Name" in root["Version"]:
            info["version"] = str(root["Version"]["Name"])

        if "LevelName" in root:
            info["world_name"] = str(root["LevelName"])

        if "WorldGenSettings" in root:
            ws = root["WorldGenSettings"]
            if "seed" in ws:
                info["seed"] = int(ws["seed"])
        elif "RandomSeed" in root:
            info["seed"] = int(root["RandomSeed"])

    except Exception:
        pass

    return info
