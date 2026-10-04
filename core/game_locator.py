"""定位 Minecraft 游戏文件夹"""
import platform
from pathlib import Path


def get_default_minecraft_dir():
    """根据操作系统返回默认的 .minecraft 目录"""
    system = platform.system()
    home = Path.home()

    if system == "Windows":
        candidate = home / "AppData" / "Roaming" / ".minecraft"
    elif system == "Darwin":
        candidate = home / "Library" / "Application Support" / "minecraft"
    else:
        candidate = home / ".minecraft"

    return candidate if candidate.exists() else None


def find_saves_dir(minecraft_dir):
    """返回 saves 目录（如果存在）"""
    saves = Path(minecraft_dir) / "saves"
    return saves if saves.exists() and saves.is_dir() else None


def find_versions_dir(minecraft_dir):
    """返回 versions 目录（如果存在）"""
    versions = Path(minecraft_dir) / "versions"
    return versions if versions.exists() and versions.is_dir() else None


def list_installed_versions(minecraft_dir):
    """列出所有已安装版本 [(版本名, jar路径), ...]"""
    versions_dir = find_versions_dir(minecraft_dir)
    if not versions_dir:
        return []

    result = []
    for folder in versions_dir.iterdir():
        if not folder.is_dir():
            continue
        version_name = folder.name
        jar_path = folder / f"{version_name}.jar"
        if jar_path.exists():
            result.append((version_name, jar_path))

    # 按版本号倒序（新的在前）
    result.sort(key=lambda x: x[0], reverse=True)
    return result


def list_worlds(minecraft_dir):
    """列出所有世界 [(世界名, 路径, 所属版本, 是否隔离), ...]

    同时扫描：
    1. .minecraft/saves/           —— 未隔离的全局存档
    2. .minecraft/versions/*/saves/ —— 版本隔离后的存档
    """
    minecraft_dir = Path(minecraft_dir)
    worlds = []

    # 1. 全局 saves
    global_saves = minecraft_dir / "saves"
    if global_saves.exists() and global_saves.is_dir():
        for folder in global_saves.iterdir():
            if folder.is_dir() and (folder / "level.dat").exists():
                worlds.append((folder.name, folder, None, False))

    # 2. 各版本下的 saves
    versions_dir = minecraft_dir / "versions"
    if versions_dir.exists() and versions_dir.is_dir():
        for version_folder in versions_dir.iterdir():
            if not version_folder.is_dir():
                continue
            version_saves = version_folder / "saves"
            if not version_saves.exists() or not version_saves.is_dir():
                continue
            for folder in version_saves.iterdir():
                if folder.is_dir() and (folder / "level.dat").exists():
                    # 用 (版本名, 世界名) 组合避免重名
                    worlds.append((folder.name, folder, version_folder.name, True))

    # 排序：先按版本，再按世界名
    worlds.sort(key=lambda x: ((x[2] or ""), x[0].lower()))
    return worlds

    worlds = []
    for folder in saves.iterdir():
        if not folder.is_dir():
            continue
        level_dat = folder / "level.dat"
        if level_dat.exists():
            worlds.append((folder.name, folder))

    worlds.sort(key=lambda x: x[0].lower())
    return worlds
