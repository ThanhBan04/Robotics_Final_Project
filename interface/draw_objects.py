"""
Draw Objects - Rendering functions for simulation objects on Pygame surface.

Draws: UAV, target, trajectories, FOV, velocity vectors, measurements,
       estimated positions, desired following point, grid.
"""

import pygame
import numpy as np
import math
from typing import List, Tuple, Optional


# Color constants
COLOR_BG = (15, 15, 25)
COLOR_GRID = (30, 30, 45)
COLOR_GRID_MAJOR = (45, 45, 65)
COLOR_UAV = (0, 180, 255)
COLOR_UAV_DARK = (0, 100, 180)
COLOR_TARGET = (255, 60, 60)
COLOR_TARGET_DARK = (180, 30, 30)
COLOR_GT_TRAIL = (100, 255, 100, 128)
COLOR_UAV_TRAIL = (0, 140, 255, 128)
COLOR_EKF_ESTIMATE = (255, 200, 0)
COLOR_UKF_ESTIMATE = (200, 0, 255)
COLOR_MEASUREMENT = (255, 255, 100, 150)
COLOR_FOV = (0, 255, 150, 40)
COLOR_DESIRED = (0, 255, 200)
COLOR_DISTANCE_LINE = (100, 100, 100)
COLOR_VELOCITY = (255, 180, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_TEXT = (200, 200, 200)
COLOR_LOST = (255, 50, 50)


def world_to_screen(x: float, y: float, sim_rect: pygame.Rect,
                     world_w: float, world_h: float) -> Tuple[int, int]:
    """Convert world coordinates to screen pixel coordinates."""
    sx = sim_rect.x + int((x / world_w) * sim_rect.width)
    sy = sim_rect.y + int((y / world_h) * sim_rect.height)
    return sx, sy


def world_scale(length: float, sim_rect: pygame.Rect, world_w: float) -> float:
    """Scale a world-space length to screen pixels."""
    return (length / world_w) * sim_rect.width


def draw_grid(surface: pygame.Surface, sim_rect: pygame.Rect,
              world_w: float, world_h: float, spacing: float = 100.0):
    """Draw coordinate grid."""
    for wx in np.arange(0, world_w + 1, spacing):
        sx, _ = world_to_screen(wx, 0, sim_rect, world_w, world_h)
        color = COLOR_GRID_MAJOR if wx % (spacing * 5) < 1 else COLOR_GRID
        pygame.draw.line(surface, color, (sx, sim_rect.y), (sx, sim_rect.y + sim_rect.height))
    for wy in np.arange(0, world_h + 1, spacing):
        _, sy = world_to_screen(0, wy, sim_rect, world_w, world_h)
        color = COLOR_GRID_MAJOR if wy % (spacing * 5) < 1 else COLOR_GRID
        pygame.draw.line(surface, color, (sim_rect.x, sy), (sim_rect.x + sim_rect.width, sy))


def draw_uav(surface: pygame.Surface, x: float, y: float, heading: float,
             sim_rect: pygame.Rect, world_w: float, world_h: float, size: int = 12):
    """Draw UAV as a triangle/arrow."""
    sx, sy = world_to_screen(x, y, sim_rect, world_w, world_h)
    # Triangle points
    pts = []
    for angle_offset in [0, 140, -140]:
        a = heading + math.radians(angle_offset)
        px = sx + int(size * math.cos(a))
        py = sy + int(size * math.sin(a))
        pts.append((px, py))
    pygame.draw.polygon(surface, COLOR_UAV, pts)
    pygame.draw.polygon(surface, COLOR_UAV_DARK, pts, 2)
    # Center dot
    pygame.draw.circle(surface, COLOR_WHITE, (sx, sy), 2)


def draw_target(surface: pygame.Surface, x: float, y: float,
                sim_rect: pygame.Rect, world_w: float, world_h: float, radius: int = 8):
    """Draw target as a circle with crosshair."""
    sx, sy = world_to_screen(x, y, sim_rect, world_w, world_h)
    pygame.draw.circle(surface, COLOR_TARGET, (sx, sy), radius)
    pygame.draw.circle(surface, COLOR_TARGET_DARK, (sx, sy), radius, 2)
    # Crosshair
    pygame.draw.line(surface, COLOR_TARGET_DARK, (sx - radius - 3, sy), (sx + radius + 3, sy), 1)
    pygame.draw.line(surface, COLOR_TARGET_DARK, (sx, sy - radius - 3), (sx, sy + radius + 3), 1)


def draw_trail(surface: pygame.Surface, positions: List[Tuple[float, float]],
               color: Tuple[int, ...], sim_rect: pygame.Rect,
               world_w: float, world_h: float, max_points: int = 200):
    """Draw trail of positions with fading effect."""
    if len(positions) < 2:
        return
    pts = positions[-max_points:]
    screen_pts = [world_to_screen(p[0], p[1], sim_rect, world_w, world_h) for p in pts]
    n = len(screen_pts)
    for i in range(1, n):
        alpha = int(255 * i / n)
        c = (min(color[0], 255), min(color[1], 255), min(color[2], 255))
        fade = tuple(max(15, int(cc * alpha / 255)) for cc in c)
        pygame.draw.line(surface, fade, screen_pts[i - 1], screen_pts[i], 2)


def draw_estimated_position(surface: pygame.Surface, x: float, y: float, color: Tuple,
                              sim_rect: pygame.Rect, world_w: float, world_h: float,
                              label: str = ""):
    """Draw estimated position as dashed circle."""
    sx, sy = world_to_screen(x, y, sim_rect, world_w, world_h)
    pygame.draw.circle(surface, color, (sx, sy), 6, 2)
    pygame.draw.circle(surface, color, (sx, sy), 2)
    if label:
        font = pygame.font.SysFont("consolas", 11)
        txt = font.render(label, True, color)
        surface.blit(txt, (sx + 8, sy - 6))


def draw_fov(surface: pygame.Surface, uav_x: float, uav_y: float,
             heading: float, fov_angle: float, max_range: float,
             sim_rect: pygame.Rect, world_w: float, world_h: float,
             detected: bool = True):
    """Draw camera field of view cone."""
    sx, sy = world_to_screen(uav_x, uav_y, sim_rect, world_w, world_h)
    range_px = world_scale(max_range, sim_rect, world_w)
    half_fov = fov_angle / 2

    n_segments = 20
    pts = [(sx, sy)]
    for i in range(n_segments + 1):
        a = heading - half_fov + (fov_angle * i / n_segments)
        px = sx + int(range_px * math.cos(a))
        py = sy + int(range_px * math.sin(a))
        pts.append((px, py))

    # Semi-transparent fill
    fov_surface = pygame.Surface((sim_rect.width, sim_rect.height), pygame.SRCALPHA)
    color = (0, 255, 150, 25) if detected else (255, 50, 50, 25)
    adjusted_pts = [(p[0] - sim_rect.x, p[1] - sim_rect.y) for p in pts]
    if len(adjusted_pts) >= 3:
        pygame.draw.polygon(fov_surface, color, adjusted_pts)
    surface.blit(fov_surface, (sim_rect.x, sim_rect.y))

    # Outline
    outline_color = (0, 200, 120, 100) if detected else (200, 50, 50, 100)
    for i in range(len(pts) - 1):
        pygame.draw.line(surface, outline_color, pts[i], pts[i + 1], 1)


def draw_velocity_vector(surface: pygame.Surface, x: float, y: float,
                          vx: float, vy: float, color: Tuple,
                          sim_rect: pygame.Rect, world_w: float, world_h: float,
                          scale: float = 1.0):
    """Draw velocity vector arrow."""
    sx, sy = world_to_screen(x, y, sim_rect, world_w, world_h)
    dvx = world_scale(vx * scale, sim_rect, world_w)
    dvy = world_scale(vy * scale, sim_rect, world_h)
    ex, ey = int(sx + dvx), int(sy + dvy)
    pygame.draw.line(surface, color, (sx, sy), (ex, ey), 2)
    # Arrowhead
    angle = math.atan2(dvy, dvx)
    head_len = 6
    for da in [2.5, -2.5]:
        hx = ex - int(head_len * math.cos(angle + da))
        hy = ey - int(head_len * math.sin(angle + da))
        pygame.draw.line(surface, color, (ex, ey), (hx, hy), 2)


def draw_distance_line(surface: pygame.Surface,
                        x1: float, y1: float, x2: float, y2: float,
                        sim_rect: pygame.Rect, world_w: float, world_h: float):
    """Draw dashed line between UAV and target with distance label."""
    s1 = world_to_screen(x1, y1, sim_rect, world_w, world_h)
    s2 = world_to_screen(x2, y2, sim_rect, world_w, world_h)
    # Dashed line
    dx = s2[0] - s1[0]
    dy = s2[1] - s1[1]
    dist_px = math.sqrt(dx**2 + dy**2)
    if dist_px < 1:
        return
    dash_len = 8
    n_dashes = max(1, int(dist_px / (dash_len * 2)))
    for i in range(n_dashes):
        t1 = (i * 2) / (n_dashes * 2)
        t2 = min((i * 2 + 1) / (n_dashes * 2), 1.0)
        p1 = (int(s1[0] + dx * t1), int(s1[1] + dy * t1))
        p2 = (int(s1[0] + dx * t2), int(s1[1] + dy * t2))
        pygame.draw.line(surface, COLOR_DISTANCE_LINE, p1, p2, 1)

    # Distance label
    dist_world = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
    mx, my = (s1[0] + s2[0]) // 2, (s1[1] + s2[1]) // 2
    font = pygame.font.SysFont("consolas", 11)
    txt = font.render(f"{dist_world:.1f}m", True, COLOR_TEXT)
    surface.blit(txt, (mx + 5, my - 8))


def draw_desired_point(surface: pygame.Surface, x: float, y: float,
                        sim_rect: pygame.Rect, world_w: float, world_h: float):
    """Draw desired following position marker."""
    sx, sy = world_to_screen(x, y, sim_rect, world_w, world_h)
    pygame.draw.circle(surface, COLOR_DESIRED, (sx, sy), 5, 2)
    # Small cross
    pygame.draw.line(surface, COLOR_DESIRED, (sx - 4, sy), (sx + 4, sy), 1)
    pygame.draw.line(surface, COLOR_DESIRED, (sx, sy - 4), (sx, sy + 4), 1)


def draw_measurement_point(surface: pygame.Surface, x: float, y: float,
                            sim_rect: pygame.Rect, world_w: float, world_h: float):
    """Draw measurement point marker."""
    sx, sy = world_to_screen(x, y, sim_rect, world_w, world_h)
    pygame.draw.circle(surface, COLOR_MEASUREMENT[:3], (sx, sy), 3)


def draw_covariance_ellipse(surface: pygame.Surface, x: float, y: float,
                              cov: np.ndarray, color: Tuple,
                              sim_rect: pygame.Rect, world_w: float, world_h: float,
                              n_std: float = 2.0):
    """Draw covariance ellipse (2D position component)."""
    if cov is None or cov.shape[0] < 2:
        return
    pos_cov = cov[:2, :2]
    try:
        eigenvalues, eigenvectors = np.linalg.eigh(pos_cov)
    except np.linalg.LinAlgError:
        return
    eigenvalues = np.maximum(eigenvalues, 0)

    width = world_scale(n_std * 2 * np.sqrt(eigenvalues[0]), sim_rect, world_w)
    height = world_scale(n_std * 2 * np.sqrt(eigenvalues[1]), sim_rect, world_w)
    angle = math.degrees(math.atan2(eigenvectors[1, 0], eigenvectors[0, 0]))

    sx, sy = world_to_screen(x, y, sim_rect, world_w, world_h)
    w, h = max(2, int(width)), max(2, int(height))

    ellipse_surface = pygame.Surface((w * 2, h * 2), pygame.SRCALPHA)
    pygame.draw.ellipse(ellipse_surface, (*color[:3], 40), (0, 0, w * 2, h * 2))
    pygame.draw.ellipse(ellipse_surface, (*color[:3], 120), (0, 0, w * 2, h * 2), 1)
    rotated = pygame.transform.rotate(ellipse_surface, -angle)
    rect = rotated.get_rect(center=(sx, sy))
    surface.blit(rotated, rect.topleft)
