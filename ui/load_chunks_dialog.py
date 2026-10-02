"""加载区块对话框：说明 + 参数输入"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QSpinBox, QLabel,
    QDialogButtonBox, QTextBrowser, QFormLayout, QGroupBox,
)


class LoadChunksDialog(QDialog):
    def __init__(self, repo_url="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("加载区块")
        self.resize(640, 620)

        layout = QVBoxLayout(self)

        info = QTextBrowser()
        info.setOpenExternalLinks(True)
        info.setHtml(self._help_html(repo_url))
        layout.addWidget(info, 1)

        group = QGroupBox("连接参数")
        form = QFormLayout(group)

        self.host_edit = QLineEdit("localhost")
        form.addRow("主机地址：", self.host_edit)

        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(25575)
        form.addRow("端口：", self.port_spin)

        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText("启动游戏时设置的 rcon.password")
        form.addRow("密码：", self.password_edit)

        layout.addWidget(group)

        buttons = QDialogButtonBox()
        start_btn = buttons.addButton("开始加载",
                                       QDialogButtonBox.ButtonRole.AcceptRole)
        cancel_btn = buttons.addButton("取消",
                                        QDialogButtonBox.ButtonRole.RejectRole)
        start_btn.clicked.connect(self._on_start)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(buttons)

    def _help_html(self, repo_url):
        repo_line = ""
        if repo_url:
            repo_line = (f'<p>更多细节请查看 '
                         f'<a href="{repo_url}">项目仓库</a> 的 README。</p>')
        return f"""
        <h2>📖 如何加载区块</h2>
        <p>这个功能会通过 <b>RCON</b> 让游戏提前生成道路经过的区块。
        你需要先让游戏跑起来，才能用这个功能。</p>

        <h3>🔧 第一步：用 RCON 启动游戏</h3>
        <p>启动 Minecraft 时加上这两个参数：</p>
        <pre>--rcon.port 25575 --rcon.password 你的密码</pre>
        <p>用启动器（PCL2、HMCL 等）的话，在「版本设置」里找到
        「JVM 参数」或「游戏参数」，加上这一段。</p>
        <p>服务器的话，在 <code>server.properties</code> 里设置：</p>
        <pre>enable-rcon=true
rcon.port=25575
rcon.password=你的密码</pre>

        <h3>🎮 第二步：进入世界</h3>
        <p>启动游戏后，进入你要修建高速公路的那个存档。
        <b>必须在世界里</b>，RCON 命令才会生效。</p>

        <h3>⚠️ 第三步：调低画质</h3>
        <p>区块生成会占用大量 CPU 和内存，为了避免卡顿：</p>
        <ul>
            <li>渲染距离调到 <b>2~4</b> 区块</li>
            <li>模拟距离调到 <b>4~6</b> 区块</li>
            <li>关闭光影、粒子效果</li>
            <li>如果还是卡，站着别动就好</li>
        </ul>

        <h3>🚀 第四步：填密码，点开始</h3>
        <p>把启动游戏时设置的密码填到下面的输入框里，点「开始加载」。
        程序会自动计算需要哪些区块，然后分批发给游戏。</p>
        <p>进度条走完后，<b>稍等 10 秒左右</b>，让游戏把区块数据写完，
        然后再点「出发」写入高速公路。</p>

        <h3>💡 常见问题</h3>
        <p><b>为什么连接失败？</b><br>
        游戏没运行、RCON 参数没加、密码错误、端口被防火墙拦。</p>
        <p><b>加载完能立刻修路吗？</b><br>
        可以，但推荐等 10 秒。让游戏把区块写到磁盘上更稳。</p>
        <p><b>会加载多少区块？</b><br>
        只加载道路经过的范围，通常一公里几百个区块。</p>

        {repo_line}
        """

    def _on_start(self):
        if not self.password_edit.text():
            self.password_edit.setFocus()
            return
        self.accept()

    def get_params(self):
        return {
            "host": self.host_edit.text().strip() or "localhost",
            "port": self.port_spin.value(),
            "password": self.password_edit.text(),
        }
