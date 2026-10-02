"""极简 RCON 客户端，只做 Minecraft 需要的那点事"""
import socket
import struct


class RCONError(Exception):
    pass


class RCONClient:
    LOGIN = 3
    COMMAND = 2

    def __init__(self, host, port, password, timeout=15):
        self.host = host
        self.port = int(port)
        self.password = password
        self.timeout = timeout
        self._socket = None
        self._req_id = 0

    def connect(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.settimeout(self.timeout)
        try:
            self._socket.connect((self.host, self.port))
        except (socket.error, OSError) as e:
            raise RCONError(f"无法连接到 {self.host}:{self.port} - {e}")
        self._login()

    def _next_id(self):
        self._req_id += 1
        return self._req_id

    def _send_packet(self, req_id, pkt_type, payload):
        data = payload.encode("utf-8") + b"\x00\x00"
        header = struct.pack("<ii", req_id, pkt_type)
        packet = struct.pack("<i", len(header) + len(data)) + header + data
        self._socket.sendall(packet)

    def _recv_exact(self, n):
        buf = b""
        while len(buf) < n:
            chunk = self._socket.recv(n - len(buf))
            if not chunk:
                raise RCONError("连接被服务器关闭")
            buf += chunk
        return buf

    def _recv_packet(self):
        length_bytes = self._recv_exact(4)
        length = struct.unpack("<i", length_bytes)[0]
        data = self._recv_exact(length)
        req_id, _ = struct.unpack("<ii", data[:8])
        payload = data[8:-2].decode("utf-8", errors="replace")
        return req_id, payload

    def _login(self):
        req_id = self._next_id()
        self._send_packet(req_id, self.LOGIN, self.password)
        resp_id, _ = self._recv_packet()
        if resp_id == -1:
            raise RCONError("密码错误")

    def send_command(self, command):
        req_id = self._next_id()
        self._send_packet(req_id, self.COMMAND, command)
        _, payload = self._recv_packet()
        return payload

    def close(self):
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None
