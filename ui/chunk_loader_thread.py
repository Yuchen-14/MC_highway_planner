"""后台线程：通过 RCON 让游戏加载道路经过的区块"""
from PyQt6.QtCore import QThread, pyqtSignal

from core.rcon_client import RCONClient, RCONError
from core.road_path import generate_smooth_path


# 一批最多处理多少个区块
BATCH_SIZE = 128


class ChunkLoaderThread(QThread):
    progress = pyqtSignal(int, int, str)
    finished_loading = pyqtSignal(int)
    error = pyqtSignal(str)

    def __init__(self, highways, host, port, password, parent=None):
        super().__init__(parent)
        self.highways = highways
        self.host = host
        self.port = port
        self.password = password
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def _collect_chunks(self):
        """收集道路经过的所有区块坐标"""
        chunks = set()
        for hw in self.highways:
            waypoints = [(wp.x, wp.z) for wp in hw.waypoints]
            if len(waypoints) < 2:
                continue
            path = generate_smooth_path(waypoints, iterations=2, step=2.0)
            # 道路宽度 + 安全边距
            half_width = 1 + 3 * hw.lanes
            pad = (half_width + 4) // 16 + 1

            for px, pz in path:
                cx = int(px) >> 4
                cz = int(pz) >> 4
                for dx in range(-pad, pad + 1):
                    for dz in range(-pad, pad + 1):
                        chunks.add((cx + dx, cz + dz))
        return chunks

    def _ordered_batches(self, chunks):
        """按空间顺序排序后切成若干批，避免跨地图跳跃"""
        sorted_chunks = sorted(chunks)
        return [sorted_chunks[i:i + BATCH_SIZE]
                for i in range(0, len(sorted_chunks), BATCH_SIZE)]

    @staticmethod
    def _batch_to_command(batch):
        """把一批区块转换成 /forceload add 命令"""
        xs = [c[0] for c in batch]
        zs = [c[1] for c in batch]
        min_cx, max_cx = min(xs), max(xs)
        min_cz, max_cz = min(zs), max(zs)
        return (f"/forceload add "
                f"{min_cx * 16} {min_cz * 16} "
                f"{max_cx * 16 + 15} {max_cz * 16 + 15}")

    def run(self):
        try:
            chunks = self._collect_chunks()
            if not chunks:
                self.error.emit("没有任何道路需要加载区块")
                return

            total = len(chunks)
            self.progress.emit(0, total, f"共需加载 {total} 个区块，正在连接游戏...")

            client = RCONClient(self.host, self.port, self.password)
            try:
                client.connect()
            except RCONError as e:
                self.error.emit(str(e))
                return

            self.progress.emit(0, total, "已连接，开始发送加载命令...")

            batches = self._ordered_batches(chunks)
            loaded = 0

            for batch in batches:
                if self._cancel:
                    break
                cmd = self._batch_to_command(batch)
                try:
                    client.send_command(cmd)
                    loaded += len(batch)
                except Exception as e:
                    self.error.emit(f"发送命令失败：{e}")
                    break
                self.progress.emit(loaded, total,
                                   f"已请求加载 {loaded}/{total} 个区块...")

            # 让游戏把生成好的区块写入磁盘
            try:
                client.send_command("/save-all flush")
            except Exception:
                pass

            client.close()
            self.finished_loading.emit(loaded)

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
