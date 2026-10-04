"""预生成区块：说明对话框"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QDialogButtonBox, QTextBrowser,
)


class PregenerateDialog(QDialog):
    def __init__(self, region_count, parent=None):
        super().__init__(parent)
        self.setWindowTitle("预生成区块")
        self.resize(640, 560)

        layout = QVBoxLayout(self)

        info = QTextBrowser()
        info.setOpenExternalLinks(True)
        info.setHtml(self._html(region_count))
        layout.addWidget(info, 1)

        buttons = QDialogButtonBox()
        gen_btn = buttons.addButton("生成数据包",
                                     QDialogButtonBox.ButtonRole.AcceptRole)
        cancel_btn = buttons.addButton("取消",
                                        QDialogButtonBox.ButtonRole.RejectRole)
        gen_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(buttons)

    def _html(self, count):
        chunk_count = count * 1024
        return f"""
        <h2>📦 预生成区块</h2>
        <p>道路经过 <b>{count} 个区域</b>（约 {chunk_count} 个区块）。
        这些区块如果游戏还没生成过，「出发」时会写入失败。</p>

        <p>这个功能会生成一个 <b>数据包</b>，让游戏自己把这些区块加载出来。</p>

        <h3>🔧 使用步骤</h3>
        <ol>
            <li><b>点「生成数据包」</b>，程序会生成一个 zip 文件</li>
            <li><b>找到存档的 datapacks 目录</b>：<br>
                <code>saves/你的世界/datapacks/</code></li>
            <li><b>把 zip 放进去</b>（不要解压）</li>
            <li><b>进入游戏</b>，如果已经在游戏里，执行 <code>/reload</code></li>
            <li><b>执行命令</b>：<br>
                <code>/function highway_planner:start</code></li>
            <li>游戏开始加载区块，<b>等待 30 秒到几分钟</b>（看区块数量）</li>
            <li>执行清理命令：<br>
                <code>/function highway_planner:cleanup</code></li>
            <li>回到规划器，点 <b>🚀 出发</b></li>
        </ol>

        <h3>⚠️ 注意事项</h3>
        <ul>
            <li>加载期间游戏可能<b>卡顿</b>，建议先调低渲染距离</li>
            <li>区块越多，等待时间越长</li>
            <li>完成后可以删掉数据包，不影响已经加载的区块</li>
            <li>写入存档前<b>务必先退出游戏</b></li>
        </ul>

        <h3>💡 为什么不用 RCON？</h3>
        <p>Minecraft 单人游戏客户端<b>不支持 RCON</b>，
        只有独立服务器才支持。数据包是单人游戏唯一可行的方案。</p>
        """

    def accept(self):
        super().accept()
