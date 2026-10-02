"""道路路径生成：平滑、加密采样"""
import math


def chaikin_smooth(points, iterations=3):
    """Chaikin 细分，把折线的尖角变成平滑曲线，保留首尾点"""
    if len(points) < 3:
        return list(points)

    result = list(points)
    for _ in range(iterations):
        new_points = [result[0]]
        for i in range(len(result) - 1):
            x0, z0 = result[i]
            x1, z1 = result[i + 1]
            q = (0.75 * x0 + 0.25 * x1, 0.75 * z0 + 0.25 * z1)
            r = (0.25 * x0 + 0.75 * x1, 0.25 * z0 + 0.75 * z1)
            new_points.append(q)
            new_points.append(r)
        new_points.append(result[-1])
        result = new_points
    return result


def densify(points, step=1.0):
    """在相邻点之间插值，确保间距不超过 step"""
    if len(points) < 2:
        return list(points)

    result = [points[0]]
    for i in range(len(points) - 1):
        x0, z0 = points[i]
        x1, z1 = points[i + 1]
        dist = math.hypot(x1 - x0, z1 - z0)
        if dist < 1e-6:
            continue
        n = max(1, int(dist / step))
        for j in range(1, n + 1):
            t = j / n
            result.append((x0 + (x1 - x0) * t, z0 + (z1 - z0) * t))
    return result


def generate_smooth_path(waypoints, iterations=3, step=1.0):
    """从路点列表生成平滑的密集采样点

    waypoints: [(x, z), ...]
    返回: [(x, z), ...] 浮点坐标
    """
    if len(waypoints) < 2:
        return list(waypoints)
    smoothed = chaikin_smooth(waypoints, iterations=iterations)
    return densify(smoothed, step=step)
