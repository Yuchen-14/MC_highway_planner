"""存档写入：把方块变更写回 Anvil 存档"""
from collections import defaultdict
from pathlib import Path

import anvil


class WorldWriter:
    def __init__(self, world_path):
        self.world_path = Path(world_path)
        self.region_dir = self.world_path / "region"

    def apply_changes(self, changes, progress_callback=None):
        """把 BlockChange 列表写回存档

        changes: [BlockChange, ...]
        返回: (成功数, 失败数)
        """
        # 按 region 分组
        regions = defaultdict(list)
        for ch in changes:
            rx = ch.x >> 9   # x // 512
            rz = ch.z >> 9
            regions[(rx, rz)].append(ch)

        total_regions = len(regions)
        success = 0
        failed = 0

        for idx, ((rx, rz), region_changes) in enumerate(regions.items()):
            if progress_callback:
                progress_callback(idx, total_regions,
                                  f"正在写入区域 ({rx}, {rz})...")

            region_file = self.region_dir / f"r.{rx}.{rz}.mca"
            if not region_file.exists():
                # 该区域没有已加载的区块，跳过
                failed += len(region_changes)
                continue

            try:
                region = anvil.Region.from_file(str(region_file))
            except Exception:
                failed += len(region_changes)
                continue

            # 按 chunk 分组
            chunks = defaultdict(list)
            for ch in region_changes:
                cx = (ch.x >> 4) & 31
                cz = (ch.z >> 4) & 31
                chunks[(cx, cz)].append(ch)

            for (cx, cz), chunk_changes in chunks.items():
                try:
                    chunk = anvil.Chunk.from_region(region, cx, cz)
                except Exception:
                    failed += len(chunk_changes)
                    continue

                for ch in chunk_changes:
                    local_x = ch.x & 15
                    local_z = ch.z & 15
                    try:
                        chunk.set_block(local_x, ch.y, local_z, ch.block_id)
                        success += 1
                    except Exception:
                        failed += 1

                try:
                    chunk.save()
                except Exception:
                    failed += len(chunk_changes)
                    success -= len(chunk_changes)
                    if success < 0:
                        success = 0

            try:
                region.save(str(region_file))
            except Exception:
                pass

        return success, failed
