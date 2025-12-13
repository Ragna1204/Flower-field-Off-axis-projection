import pygame
import math
import random
from typing import Tuple, List
from dataclasses import dataclass


# Temporary point-like class for transforms (avoid repeated dataclass definition)
@dataclass
class TempPoint:
    x: float
    y: float
    z: float

# This module implements Flower primitives, a FlowerField manager for an
# infinite-appearing field of flowers, and a SmileDetector that computes a
# simple smile strength from MediaPipe face landmarks. It is written to be
# easy to read and tweak.

# Configuration defaults (can be overridden by importing module-level names)
FLOWER_SPACING = 1.0
FLOWER_ROWS = 7
FLOWER_COLUMNS = 10
FLOWER_DEPTH_REPEAT = 20.0
FLOWER_DRAW_LIMIT = 400
COLOR_TRANSITION_TIME = 2.0
SMILE_THRESHOLD = 0.22
SMILE_SMOOTHING = 0.08
COLOR_EASING = lambda t: t * t * (3 - 2 * t)  # smoothstep
FLOWER_LANES = 12
LANE_Y = -3.0

# Utility: linear interpolation
def lerp(a, b, t):
    return a + (b - a) * t


class SmileDetector:
    """Simple smile detector that computes a smile_strength (0..1) from
    face landmark positions provided by MediaPipe.

    Usage: call `update(landmarks)` each frame with `landmarks` being the
    landmark list from MediaPipe (or None). The detector smooths the
    instantaneous metric and exposes `smile_strength`.
    """

    def __init__(self, threshold: float = SMILE_THRESHOLD, smooth: float = SMILE_SMOOTHING):
        self.threshold = threshold
        self.smooth = smooth
        self.smile_strength = 0.0
        self.baseline = None
        self.baseline_smooth = 0.02

    def compute_mouth_aspect(self, lm) -> float:
        """Compute a simple mouth aspect ratio from landmarks.
        Expects lm to be a sequence of landmarks with .x and .y attributes.
        We'll use lip corner indices (61, 291) and top/bottom inner lip (13, 14)
        which are available when refine_landmarks=True.
        """
        try:
            left = lm[61]
            right = lm[291]
            top = lm[13]
            bottom = lm[14]
        except Exception:
            return 0.0

        # horizontal distance between corners
        h = math.hypot(right.x - left.x, right.y - left.y)
        # vertical distance between inner lips
        v = math.hypot(bottom.x - top.x, bottom.y - top.y)
        if v <= 1e-6:
            return 0.0
        return (h / v)  # larger when smiling (corners stretch)

    def update(self, landmarks) -> None:
        """Call every frame with MediaPipe landmarks or None. Produces
        `self.smile_strength` in [0,1]."""
        if not landmarks:
            target = 0.0
        else:
            metric = self.compute_mouth_aspect(landmarks)
            # initialize baseline if needed
            if self.baseline is None:
                self.baseline = metric

            # adapt baseline slowly
            self.baseline = lerp(self.baseline, metric, self.baseline_smooth)

            # compute strength relative to baseline
            # scale factor to map typical mouth-aspect changes to [0,1]
            scale = 0.5
            raw = (metric - self.baseline) / scale
            target = max(0.0, min(1.0, raw))

        # exponential smoothing (lerp)
        self.smile_strength = lerp(self.smile_strength, target, self.smooth)

    @property
    def smiling(self) -> bool:
        return self.smile_strength >= self.threshold


class Flower:
    """Simple flower primitive.

    Attributes:
      x,y,z: 3D position in scene coordinates
      size: base size in scene units
      hue: 0..1 hue offset for color variation
      color_progress: 0..1 interpolation 0=grayscale,1=full color
    """

    def __init__(self, x: float, y: float, z: float, size: float = 0.3, hue: float = 0.0):
        self.x = x

        self.base_y = y
        self.y = y
        self.breath_offset = 0.0
        self._time = random.uniform(0, math.pi * 2)

        self.z = z
        self.size = size
        self.hue = hue
        self.color_progress = 0.0

    def update(self, dt: float, progress: float) -> None:
        """Advance color progress toward `progress` (0..1)."""
        speed = 5.0  # responsiveness
        self.color_progress = lerp(self.color_progress, progress, 1 - math.exp(-speed * dt))
        # --- breathing motion (offset only, not absolute y) ---
        self._time += dt

        depth_factor = max(0.0, 1.0 - self.z / 10.0)
        self.breath_offset = math.sin(self._time * 1.1 + self.x * 2.0) * 0.02 * depth_factor


    def draw(
        self,
        surface: pygame.Surface,
        glow_surface: pygame.Surface,
        project_fn,
        screen_size=None
    ) -> None:


        # 1. Convert to temporary 3D point
        p = TempPoint(self.x, self.y, self.z)

        # 2. Project into screen space
        proj = project_fn(p)
        if proj is None:
            return

        # Must be 3 values: (sx, sy, scale)
        try:
            sx, sy, scale = proj
        except Exception:
            # Projection returned only (sx, sy) -> fallback to safe scale
            sx, sy = proj
            scale = 1.0

        # 3. Screen culling
        if screen_size:
            sw, sh = screen_size
            if sx < -50 or sx > sw + 50 or sy < -50 or sy > sh + 50:
                return
            
        # ---- DEPTH-BASED SCALE FLATTENING ----
        flattened = scale ** 0.52

        # ---- DEPTH-BASED FOG STRENGTH ----
        fog_strength = min(1.0, (1.0 - scale) ** 1.6)

        # ---- FLOWER SIZE ----
        draw_size = int(self.size * flattened * 105)
        draw_size = max(1, draw_size)

        # ---- VOLUMETRIC FOG HALO ----
        fog_radius = int(draw_size * 1.35)

        fog_alpha = int(10 + 60 * (1 - flattened) ** 1.8)
        fog_alpha = max(5, min(70, fog_alpha))

        fog_rgb = self.hsv_to_rgb(self.hue, 0.35, 0.9)
        fog_color = tuple(int(c * 0.6) for c in fog_rgb)

        pygame.draw.circle(glow_surface, (*fog_color, fog_alpha), (sx, sy), fog_radius)


        # 5. Base gray colors
        gray_center = (200, 200, 200)
        gray_petal  = (160, 160, 160)

        # 6. Fully-colored hue version blended by color_progress
        rgb_color = self.hsv_to_rgb(self.hue, 0.75, 0.92)

        # ---- DEPTH-BASED PETAL GLOW ----
        depth_glow = max(0.4, scale ** 0.6)

        petal_color = tuple(
            int(lerp(gray_petal[i], rgb_color[i], self.color_progress) * depth_glow)
            for i in range(3)
        )

        center_color = tuple(
            int(lerp(gray_center[i], (255, 230, 120)[i], self.color_progress))
            for i in range(3)
        )

        # 7. Depth-based fade (AFTER colors are computed)
        depth_fade = min(1.0, flattened * 1.2)

        petal_color = tuple(int(c * depth_fade) for c in petal_color)
        center_color = tuple(int(c * depth_fade) for c in center_color)


        # 7. Draw petals around center
        offsets = [(-0.4, 0), (0.4, 0), (0, -0.35), (0, 0.35)]
        for ox, oy in offsets:
            ox_pix = int(ox * draw_size)
            oy_pix = int(oy * draw_size)
            pygame.draw.circle(
                surface,
                petal_color,
                (sx + ox_pix, sy + oy_pix),
                max(1, int(draw_size * 0.6))
            )

        # 8. Draw center
        pygame.draw.circle(
            surface,
            center_color,
            (sx, sy),
            max(1, int(draw_size * 0.5))
        )


    def is_visible(self, project_fn, head_x: float, head_y: float, screen_size=None) -> bool:
        p = TempPoint(self.x, self.y, self.z)
        screen_pos = project_fn(p, head_x, head_y)

        if not screen_pos:
            return False

        sx, sy = screen_pos
        if screen_size:
            sw, sh = screen_size
            return -50 < sx < sw + 50 and -50 < sy < sh + 50

        return True

    @staticmethod
    def hsv_to_rgb(h, s, v) -> Tuple[int, int, int]:
        i = int(h * 6)
        f = (h * 6) - i
        p = v * (1 - s)
        q = v * (1 - f * s)
        t = v * (1 - (1 - f) * s)
        i = i % 6

        if i == 0: r, g, b = v, t, p
        elif i == 1: r, g, b = q, v, p
        elif i == 2: r, g, b = p, v, t
        elif i == 3: r, g, b = p, q, v
        elif i == 4: r, g, b = t, p, v
        else:        r, g, b = v, p, q

        return (int(r * 255), int(g * 255), int(b * 255))
class FlowerField:
    """Manages a pool of Flower objects arranged in lanes near the bottom
    of the room and multiple depth layers to create a flower-field effect.
    """

    def __init__(self, lanes: int = FLOWER_LANES, lane_y: float = LANE_Y, spacing: float = FLOWER_SPACING, depth_repeat: float = FLOWER_DEPTH_REPEAT, depth_layers: int = 8):
        self.lanes = lanes
        self.lane_y = lane_y
        self.spacing = spacing
        self.depth_repeat = depth_repeat
        self.flowers: List[Flower] = []
        self.color_progress = 0.0

        # center lanes across X and create a few depth layers per lane
        x_start = -(lanes - 1) / 2.0 * spacing
        max_layers = max(1, min(depth_layers, int(self.depth_repeat // self.spacing)))
        for i in range(lanes):
            x = x_start + i * spacing
            for k in range(max_layers):
                t = k / max(1, max_layers - 1)
                z = (t ** 1.7) * self.depth_repeat
                # small horizontal/vertical jitter for natural look
                hx = x + random.uniform(-0.06, 0.06)
                hy = lane_y + random.uniform(-0.03, 0.03)
                hue = (i % 12) / 12.0 + random.uniform(-0.03, 0.03)
                f = Flower(hx, hy, z, size=0.25 + random.uniform(-0.05, 0.05), hue=hue % 1.0)
                self.flowers.append(f)

        # cap the number of flowers if needed
        if len(self.flowers) > FLOWER_DRAW_LIMIT:
            self.flowers = self.flowers[:FLOWER_DRAW_LIMIT]

    def update(self, dt: float, head_x: float, head_y: float, smile_strength: float) -> None:
        # target color progress driven by smile strength
        target = max(0.0, min(1.0, smile_strength))
        # smooth global progress
        speed = 1.0 / max(0.001, COLOR_TRANSITION_TIME)
        self.color_progress = lerp(self.color_progress, target, 1 - math.exp(-speed * dt))

        # update each flower with the eased progress but weighted by depth so
        # near flowers light up first
        eased = COLOR_EASING(self.color_progress)
        for f in self.flowers:
            # depth priority: 1 for z=0 (near), 0 for z=depth_repeat (far)
            depth_priority = max(0.0, min(1.0, 1.0 - (f.z / max(1e-6, self.depth_repeat))))
            # per-flower target scales eased progress by depth priority to light
            # nearer flowers earlier
            per_target = eased * (0.3 + 0.7 * depth_priority)
            f.update(dt, per_target)
            depth_norm = min(1.0, f.z / self.depth_repeat)
            f.y = self.lane_y * (1 - 0.35 * depth_norm)
            f.y += f.breath_offset

    def draw(
        self,
        surface: pygame.Surface,
        glow_surface: pygame.Surface,
        project_fn,
        screen_size=None
    ) -> None:
        """Draw flowers sorted by camera-space depth (far to near) for correct occlusion.
        
        Computes per-flower z_cam and total_depth to:
        1. Sort flowers by depth (painter's algorithm: far first, near last).
        2. Compute projection-consistent pixel sizes based on depth.
        3. Pass depth info to Flower.draw for consistent perspective.
        """
        drawn = 0
        if screen_size is None:
            sw_sh = surface.get_size()
        else:
            sw_sh = screen_size
        
        # Import camera helpers from 3d grid module
        try:
            from __main__ import (
                world_to_camera, camera_depth_for_point, 
                eye_depth, unit_scale, camera_pitch, camera_height, near_clip
            )
        except ImportError:
            # Fallback: draw without sorting (old behavior)
            for f in self.flowers:
                if drawn >= FLOWER_DRAW_LIMIT:
                    break
                if f.is_visible(project_fn, head_x, head_y, screen_size=sw_sh):
                    f.draw(surface, project_fn, head_x, head_y, screen_size=sw_sh)
                    drawn += 1
            return
        
        # Compute depth for each flower and build sortable list
        items = []
        for f in self.flowers:
            try:
                # Use temp point for world_to_camera
                p = TempPoint(f.x, f.y, f.z)
                x_cam, y_cam, z_cam = world_to_camera(p, camera_pitch, camera_height)
                total_depth = eye_depth + z_cam
                
                # Cull flowers behind near plane
                if total_depth <= near_clip:
                    continue
                
                items.append((z_cam, total_depth, f))
            except Exception:
                # Fallback to unsorted draw
                items.append((f.z, f.z, f))
        
        # Sort by camera-space depth: farthest first (painter's algorithm)
        items.sort(key=lambda t: t[0], reverse=True)
        
        # Draw in sorted order with depth-based sizing
        for z_cam, total_depth, f in items:
            if drawn >= FLOWER_DRAW_LIMIT:
                break
            
            # Compute perspective-based pixel size
            perspective_scale = eye_depth / total_depth
            draw_size = max(1, int(f.size * unit_scale * perspective_scale))
            
            # Draw flower with computed depth info
            f.draw(
                surface,
                glow_surface,
                project_fn,
                screen_size=sw_sh
            )
            drawn += 1



# small self-test when file is run directly
if __name__ == "__main__":
    print("flowers.py: module test - nothing to run interactively here.")
