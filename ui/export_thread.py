"""后台线程：生成道路方块并写入存档"""
from PyQt6.QtCore import QThread, pyqtSignal

from core.road_builder import RoadBuilder
from core.world_writer import WorldWriter


class ExportThread(QThread):
    progress = pyqtSignal(int, int, str)
    finished_export = pyqtSignal(int, int)   # success, failed
    error = pyqtSignal(str)

    def __init__(self, highways, world_path, height_map_fn=None, parent=None):
        super().__init__(parent)
        self.highways = highways
        self.world_path = world_path
        self.height_map_fn = height_map_fn
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        try:
            all_changes = []

            # 第一步：生成所有道路的方块变更
            total = len(self.highways)
            for i, hw in enumerate(self.highways):
                if self._cancel:
                    return
                self.progress.emit(i, total,
                                   f"正在生成 [{hw.short_code}] {hw.name} ...")
                builder = RoadBuilder(hw, height_map_fn=self.height_map_fn)
                all_changes.extend(builder.generate())

            if self._cancel:
                return

            # 第二步：去重（后面的覆盖前面的）
            dedup = {}
            for ch in all_changes:
                dedup[(ch.x, ch.y, ch.z)] = ch
            final_changes = list(dedup.values())

            self.progress.emit(total, total,
                               f"共 {len(final_changes)} 个方块变更，开始写入存档...")

            # 第三步：写入
            writer = WorldWriter(self.world_path)
            success, failed = writer.apply_changes(
                final_changes,
                progress_callback=lambda i, n, msg:
                    self.progress.emit(i, n, msg)
            )

            self.finished_export.emit(success, failed)

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
