"""从 Minecraft jar 文件中提取方块纹理"""
import zipfile
from pathlib import Path


# 纹理缓存根目录
CACHE_ROOT = Path.home() / ".highway_planner" / "textures"


def get_cache_dir(version_name):
    """获取某版本的纹理缓存目录"""
    return CACHE_ROOT / version_name


def extract_block_textures(jar_path, version_name):
    """从 jar 提取方块纹理到缓存目录，返回提取数量"""
    jar_path = Path(jar_path)
    if not jar_path.exists():
        raise FileNotFoundError(f"未找到 jar 文件: {jar_path}")

    output_dir = get_cache_dir(version_name)
    output_dir.mkdir(parents=True, exist_ok=True)

    extracted = 0
    prefix = "assets/minecraft/textures/block/"

    with zipfile.ZipFile(jar_path, "r") as zf:
        for name in zf.namelist():
            if not name.startswith(prefix) or not name.endswith(".png"):
                continue
            rel = name[len(prefix):]
            # 只提取顶层文件，跳过子目录（如破坏动画）
            if "/" in rel:
                continue
            target = output_dir / rel
            if target.exists():
                continue
            with zf.open(name) as src, open(target, "wb") as dst:
                dst.write(src.read())
            extracted += 1

    return extracted


def has_textures(version_name):
    """检查是否已缓存过该版本的纹理"""
    cache_dir = get_cache_dir(version_name)
    return cache_dir.exists() and any(cache_dir.glob("*.png"))
