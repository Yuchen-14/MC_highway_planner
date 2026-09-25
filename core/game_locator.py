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
    """列出所有世界 [(世界名, 路径), ...]"""
    saves = find_saves_dir(minecraft_dir)
    if not saves:
        return []

    worlds = []
    for folder in saves.iterdir():
        if not folder.is_dir():
            continue
        level_dat = folder / "level.dat"
        if level_dat.exists():
            worlds.append((folder.name, folder))

    worlds.sort(key=lambda x: x[0].lower())
    return worlds
