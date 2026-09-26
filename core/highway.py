"""高速公路数据模型"""
import uuid
from dataclasses import dataclass, field

# Minecraft 基础 16 色
MC_COLORS = {
    "white":      "#F9FFFE",
    "orange":     "#F9801D",
    "magenta":    "#C74EBD",
    "light_blue": "#3AB3DA",
    "yellow":     "#FED83D",
    "lime":       "#80C71F",
    "pink":       "#F38BAA",
    "gray":       "#474F52",
    "light_gray": "#9D9D97",
    "cyan":       "#169C9C",
    "purple":     "#8932B8",
    "blue":       "#3C44AA",
    "brown":      "#835432",
    "green":      "#5E7C16",
    "red":        "#B02E26",
    "black":      "#1D1D21",
}


@dataclass
class Waypoint:
    x: int
    z: int
    y: int = 64


@dataclass
class Highway:
    name: str
    short_code: str
    color: str          # MC_COLORS 的 key
    lanes: int = 2
    height: int = 64
    is_ramp: bool = False
    waypoints: list = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    @property
    def color_hex(self):
        return MC_COLORS.get(self.color, "#FFFFFF")

    def add_waypoint(self, x, z):
        self.waypoints.append(Waypoint(x, z, self.height))

    def remove_last_waypoint(self):
        if self.waypoints:
            self.waypoints.pop()

    def clear(self):
        self.waypoints.clear()


class HighwayManager:
    def __init__(self):
        self.highways = []
        self.active_id = None

    def add(self, highway):
        self.highways.append(highway)
        self.active_id = highway.id

    def remove(self, highway_id):
        self.highways = [h for h in self.highways if h.id != highway_id]
        if self.active_id == highway_id:
            self.active_id = None

    def get_active(self):
        for h in self.highways:
            if h.id == self.active_id:
                return h
        return None

    def get(self, highway_id):
        for h in self.highways:
            if h.id == highway_id:
                return h
        return None

    def set_active(self, highway_id):
        self.active_id = highway_id
