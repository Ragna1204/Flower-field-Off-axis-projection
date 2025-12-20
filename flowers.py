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

        self.z = z
        self.size = size
        self.hue = hue
        self.color_progress = 0.0
        self.depth_repeat = FLOWER_DEPTH_REPEAT

        self._time = random.uniform(0, 10.0)  # de-sync flowers
        self.breath_offset = 0.0

        self.life = 0.0
        self.petals_phase = random.uniform(0, math.pi * 2)
        self.stem_phase = random.uniform(0, math.pi * 2)

        self.stem_curve = random.uniform(0.6, 1.0)
        self.stem_twist = random.choice([-1, 1])

        self.stem_twist_phase = random.uniform(0, math.pi * 2)
        self.stem_base_radius = 0.12 + random.uniform(-0.02, 0.02)

        # ---- Rose geometry parameters ----
        self.rose_layers = 4          # number of petal rings
        self.rose_points = 20         # resolution per ring
        self.rose_radius = 0.12       # base size (3D units)
        self.rose_height = 0.10       # vertical spread
        self.rose_twist = random.uniform(0, math.pi * 2)

        self.rose_inward_bias = 0.22      # how much edge roses lean inward
        self.rose_depth_lift = 0.18       # vertical stacking illusion
        self.rose_edge_compress = 0.35    # radius compression at extreme X

        self.petal_count = random.randint(5, 7)
        self.petal_length = 0.10 + random.uniform(-0.02, 0.03)
        self.petal_spread = 0.55
        self.petal_curl = random.uniform(0.6, 1.2)
        self.core_radius = 0.025




    def update(self, dt: float, progress: float) -> None:
        """Advance color progress toward `progress` (0..1) and apply life motion."""
        
        # --- Color progression ---
        speed = 5.0
        self.color_progress = lerp(
            self.color_progress,
            progress,
            1 - math.exp(-speed * dt)
        )

        # --- Internal time ---
        self._time += dt

        # --- Depth weighting (near flowers move more) ---
        depth_factor = max(0.0, 1.0 - self.z / 10.0)

        # --- Energy-based breathing (IMPORTANT) ---
        life = self.life  # tie motion to life, not time

        self.breath_offset = (
            math.sin(self._time * 1.1 + self.x * 2.0)
            * 0.02
            * depth_factor
            * life
        )


    # def draw(
    #     self,
    #     surface: pygame.Surface,
    #     glow_surface: pygame.Surface,
    #     project_fn,
    #     screen_size=None
    # ) -> None:


    #     # 1. Convert to temporary 3D point
    #     p = TempPoint(self.x, self.y, self.z)

    #     # 2. Project into screen space
    #     proj = project_fn(p)
    #     if proj is None:
    #         return

    #     # Must be 3 values: (sx, sy, scale)
    #     try:
    #         sx, sy, scale = proj
    #     except Exception:
    #         # Projection returned only (sx, sy) -> fallback to safe scale
    #         sx, sy = proj
    #         scale = 1.0

    #     # 3. Screen culling
    #     if screen_size:
    #         sw, sh = screen_size
    #         if sx < -50 or sx > sw + 50 or sy < -50 or sy > sh + 50:
    #             return
            
    #     # ---- DEPTH-BASED SCALE FLATTENING ----
    #     flattened = scale ** 0.52

    #     # ---- DEPTH-BASED FOG STRENGTH ----
    #     fog_strength = min(1.0, (1.0 - scale) ** 1.6)

    #     # ---- FLOWER SIZE ----
    #     draw_size = int(self.size * flattened * 105)
    #     draw_size = max(1, draw_size)

    #     # ---- VOLUMETRIC FOG HALO (WAVE-GATED) ----
    #     life = self.life  # IMPORTANT: per-flower wave life

    #     fog_strength = life ** 1.4
    #     fog_alpha = int((10 + 60 * (1 - flattened) ** 1.8) * fog_strength)
    #     fog_alpha = max(0, min(70, fog_alpha))

    #     if fog_alpha > 0:
    #         fog_radius = int(draw_size * (1.0 + 0.35 * life))

    #         fog_rgb = self.hsv_to_rgb(self.hue, 0.35, 0.9)
    #         fog_color = tuple(
    #             int(lerp(60, c * 0.6, life))
    #             for c in fog_rgb
    #         )

    #         pygame.draw.circle(
    #             glow_surface,
    #             (*fog_color, fog_alpha),
    #             (sx, sy),
    #             fog_radius
    #         )


    #     # # ================= NEON PETAL SKELETON (PHASE E1) =================
    #     # if life > 0.02:
    #     #     petal_count = 5
    #     #     base_len = draw_size * (0.85 + 0.4 * life)
    #     #     thickness = max(1, int(2 + 3 * life))

    #     #     neon_rgb = self.hsv_to_rgb(self.hue, 0.9, 1.0)

    #     #     for i in range(petal_count):
    #     #         angle = (
    #     #             i * (2 * math.pi / petal_count)
    #     #             + math.sin(self._time * 0.6 + i) * 0.18
    #     #         )

    #     #         # Organic curvature
    #     #         bend = math.sin(self._time * 0.9 + i * 1.3) * 0.35

    #     #         x1, y1 = sx, sy
    #     #         x2 = sx + math.cos(angle) * base_len
    #     #         y2 = sy + math.sin(angle + bend) * base_len

    #     #         # Energy falloff toward tip
    #     #         tip_energy = 0.6 + 0.4 * life

    #     #         line_color = (
    #     #             int(neon_rgb[0] * tip_energy),
    #     #             int(neon_rgb[1] * tip_energy),
    #     #             int(neon_rgb[2] * tip_energy),
    #     #         )

    #     #         # Core line
    #     #         pygame.draw.line(
    #     #             surface,
    #     #             line_color,
    #     #             (x1, y1),
    #     #             (x2, y2),
    #     #             thickness
    #     #         )

    #     #         # Glow pass
    #     #         pygame.draw.line(
    #     #             glow_surface,
    #     #             (*line_color, int(70 * life * life)),
    #     #             (x1, y1),
    #     #             (x2, y2),
    #     #             thickness + 3
    #     #         )
    #     # # ================================================================

    #     # ---- FLOWER COLORS ----
    #     gray_center = (200, 200, 200)
    #     gray_petal  = (160, 160, 160)

    #     rgb_color = self.hsv_to_rgb(self.hue, 0.75, 0.92)
    #     depth_glow = max(0.4, scale ** 0.6)

    #     petal_color = tuple(
    #         int(
    #             lerp(gray_petal[i], rgb_color[i], life)
    #             * depth_glow
    #             * life
    #         )
    #         for i in range(3)
    #     )

    #     center_color = tuple(
    #         int(
    #             lerp(gray_center[i], (255, 230, 120)[i], life ** 1.3)
    #         )
    #         for i in range(3)
    #     )


    #     offsets = [(-0.4, 0), (0.4, 0), (0, -0.35), (0, 0.35)]
    #     for ox, oy in offsets:
    #         ox_pix = int(ox * draw_size)
    #         oy_pix = int(oy * draw_size)
    #         pygame.draw.circle(
    #             surface,
    #             petal_color,
    #             (sx + ox_pix, sy + oy_pix),
    #             max(1, int(draw_size * 0.6))
    #         )

    #     # 8. Draw center
    #     pygame.draw.circle(
    #         surface,
    #         center_color,
    #         (sx, sy),
    #         max(1, int(draw_size * 0.5))
    #     )

    def draw(
        self,
        surface: pygame.Surface,
        glow_surface: pygame.Surface,
        project_fn,
        screen_size=None
    ) -> None:

        # ---- Early exit ----
        life = self.life
        if self.life <= 0.01:
            return

        # ---- Project base point ----
        p = TempPoint(self.x, self.y, self.z)
        proj = project_fn(p)
        if proj is None:
            return

        try:
            sx, sy, scale = proj
        except ValueError:
            sx, sy = proj
            scale = 1.0

        # ---- Screen culling ----
        if screen_size:
            sw, sh = screen_size
            if sx < -100 or sx > sw + 100 or sy < -100 or sy > sh + 100:
                return

        # ---- Depth shaping ----
        flattened = scale ** 0.55
        life = self.life ** 1.4

        # Base neon thickness
        base_thickness = max(1, int(2.2 * flattened * life))

        # Colors
        petal_rgb = self.hsv_to_rgb(self.hue, 0.9, 1.0)
        core_rgb  = (255, 245, 210)
        stem_rgb  = self.hsv_to_rgb((self.hue + 0.35) % 1.0, 0.6, 0.9)

        # ---- DRAW STEM ----
        self._draw_neon_stem(
            surface,
            glow_surface,
            project_fn,
            stem_rgb,
            base_thickness
        )

        # # ---- DRAW CORE ----
        # self._draw_neon_core(
        #     surface,
        #     glow_surface,
        #     sx,
        #     sy,
        #     petal_rgb,
        #     core_rgb,
        #     base_thickness
        # )

        # # ---- DRAW PETALS ----
        # self._draw_neon_petals(
        #     surface,
        #     glow_surface,
        #     sx,
        #     sy,
        #     petal_rgb,
        #     base_thickness
        # )

        # ---- DRAW ROSE HEAD ----
        self._draw_neon_rose_head(
            surface,
            glow_surface,
            project_fn,
            petal_rgb,
            base_thickness
        )


    def _draw_neon_stem(
        self,
        surface,
        glow_surface,
        project_fn,
        color,
        thickness
    ):
        """Elegant, fast neon stem (D3.2.75)"""

        life = self.life
        if life <= 0.01:
            return

        # ---- Ground anchor glow ----
        base_proj = project_fn(TempPoint(self.x, self.y, self.z))
        if base_proj:
            bx, by = base_proj[:2]
            pygame.draw.circle(
                glow_surface,
                (*color, int(20 * life)),
                (int(bx), int(by)),
                int(5 + 6 * life)
            )

        # ---- Stem curve (3 control points, cheap + elegant) ----
        height = 0.55 + 0.15 * life
        sway = 0.18 * life
        twist = math.sin(self._time * 0.6 + self.stem_twist_phase) * sway

        control_points = [
            (self.x, self.y, self.z),
            (self.x + twist * 0.6, self.y + height * 0.5, self.z),
            (self.x - twist * 0.3, self.y + height, self.z),
        ]

        points = []
        for x, y, z in control_points:
            proj = project_fn(TempPoint(x, y, z))
            if proj:
                points.append(proj[:2])

        if len(points) < 2:
            return

        # ---- Glow (single pass only) ----
        pygame.draw.lines(
            glow_surface,
            (*color, 14),
            False,
            points,
            thickness + 3
        )

        # ---- Core ----
        pygame.draw.lines(
            surface,
            color,
            False,
            points,
            thickness
        )



    def _draw_neon_core(
        self,
        surface,
        glow_surface,
        sx,
        sy,
        petal_rgb,
        core_rgb,
        thickness
    ):
        """Neon spiral core"""

        turns = 1.5
        points = []
        radius = 6 + 6 * self.life

        for i in range(18):
            t = i / 18
            angle = t * math.pi * 2 * turns
            r = radius * t

            px = sx + math.cos(angle) * r
            py = sy + math.sin(angle) * r

            points.append((px, py))

        # Glow
        for glow_pass in (6, 3):
            pygame.draw.lines(
                glow_surface,
                (*petal_rgb, 22),
                False,
                points,
                thickness + glow_pass
            )

        # Core
        pygame.draw.lines(
            surface,
            core_rgb,
            False,
            points,
            thickness
        )

    # def _draw_neon_rose_head(
    #     self,
    #     surface,
    #     glow_surface,
    #     project_fn,
    #     petal_rgb,
    #     thickness
    # ):
        
    #     if self.z > self.depth_repeat * 0.85:
    #         return

        
    #     # Normalized lateral position (−1 … 0 … +1)
    #     field_half_width = 0.5 * (self.field_width if hasattr(self, "field_width") else 10.0)
    #     x_norm = max(-1.0, min(1.0, self.x / field_half_width))
    #     edge_factor = abs(x_norm)

    #     life = self.life
    #     active_layers = min(4, max(1, int(self.rose_layers * life)))


    #     for layer in range(active_layers):
    #         layer_t = layer / max(1, self.rose_layers - 1)

    #         # Depth-based importance fade
    #         depth_factor = 1.0 - min(1.0, self.z / self.depth_repeat)
    #         importance = 0.5 + 0.5 * depth_factor

    #         alpha = int((22 * importance) * (1.0 - layer_t * 0.6))
    #         alpha = max(8, alpha)


    #         radius = self.rose_radius * (1.0 + layer_t * 1.4)

    #         height = layer_t * self.rose_height
    #         rotation = self.rose_twist + layer * 0.9 + math.sin(self.petals_phase + layer) * 0.2

    #         points = []

    #         points_count = int(self.rose_points * (0.5 + 0.5 * importance))
    #         for i in range(points_count + 1):
    #             t = i / max(1, points_count)
    #             angle = t * math.pi * 2

    #             # ---- Petal lobe field ----
    #             petal_count = 5 + layer          # more petals on outer layers
    #             lobe = math.sin(angle * petal_count + self.petals_phase)
    #             # Sharpen petal tips, soften valleys
    #             lobe = math.copysign(abs(lobe) ** 1.6, lobe)

    #             petal_curve = lobe * (0.35 + 0.25 * layer_t)

    #             local_radius = radius * (1.0 + petal_curve * 0.6)
    #             local_radius *= (1.0 - edge_factor * self.rose_edge_compress)

    #             inward = -x_norm * self.rose_inward_bias * local_radius

    #             x = self.x + math.cos(angle + rotation) * local_radius + inward
    #             y = self.y - height + petal_curve * local_radius * (0.4 + 0.3 * layer_t)
    #             z = self.z + layer_t * self.rose_depth_lift

        
    #             proj = project_fn(TempPoint(x, y, z))
    #             if proj:
    #                 points.append(proj[:2])

    #         if len(points) < 2:
    #             continue
            

    #         # ---- Depth-based LOD ----
    #         depth_norm = min(1.0, self.z / self.depth_repeat)

    #         if depth_norm > 0.7:
    #             glow_passes = (3,)
    #         elif depth_norm > 0.4:
    #             glow_passes = (4, 2)
    #         else:
    #             glow_passes = (6, 3)

    #         # ---- Glow layers ----
    #         for glow_pass in glow_passes:
    #             pygame.draw.lines(
    #                 glow_surface,
    #                 (*petal_rgb, alpha),
    #                 False,
    #                 points,
    #                 thickness + glow_pass
    #             )

    #         # Core
    #         pygame.draw.lines(
    #             surface,
    #             petal_rgb,
    #             False,
    #             points,
    #             thickness
    #         )

    def _draw_neon_rose_head(
        self,
        surface,
        glow_surface,
        project_fn,
        petal_rgb,
        thickness
    ):
        # 1. Distance culling
        if self.z > self.depth_repeat * 0.9:
            return

        # 2. Scale check
        proj = project_fn(TempPoint(self.x, self.y, self.z))
        if proj is None:
            return
        
        try:
            _, _, scale = proj
        except ValueError:
            scale = 1.0
            
        if scale < 0.15: 
            return

        # 3. Parameters & Easing
        if self.life < 0.05:
            return
        
        life = self.life
            
        # --- DEPTH-BASED BLOOM DELAY ---
        # 1. Compute depth_norm (0=front, 1=back)
        depth_norm = max(0.0, min(1.0, self.z / self.depth_repeat))
        
        # 2. Delay factor (back flowers bloom later)
        bloom_delay = depth_norm * 0.45
        
        # 3. Local life (time since this specific flower started blooming)
        # Remap [bloom_delay..1.0] to [0.0..1.0]
        denom = 1.0 - bloom_delay
        if denom < 0.001: denom = 0.001
        
        local_life = (life - bloom_delay) / denom
        local_life = max(0.0, min(1.0, local_life))

        if local_life < 0.01:
            return

        # 4. Refined easing on LOCAL life
        if local_life < 0.35:
            eased_life = local_life * local_life * 0.4
        else:
            t = (local_life - 0.35) / 0.65
            eased_life = 0.14 + t * t * (3 - 2 * t) * 0.86

        # --- Anchor to TOP of stem ---
        # Stem uses raw life, so we must match it to attach correctly
        stem_height = 0.55 + 0.15 * life
        head_y = self.y + stem_height

        # Base dimensions (use eased_life for bloom size)
        base_radius = 0.22 * (0.6 + 0.4 * eased_life)
        petal_count = 7
        arc_span = math.pi * 0.7 
        
        # 4. Draw Radial Petals
        for i in range(petal_count):
            
            is_inner = (i % 2 == 0)
            
            # --- Staged Appearance ---
            if is_inner:
                petal_life = eased_life
            else:
                petal_life = max(0.0, (eased_life - 0.2) / 0.8)
                
            if petal_life < 0.01:
                continue
            
            # Stable radial distribution
            center_angle = (i / petal_count) * math.pi * 2 + self.rose_twist
            
            if is_inner:
                r_scale = 0.85
                y_drop = 0.02 
                steps = 5
                alpha_factor = 1.0 
            else:
                r_scale = 1.15
                y_drop = 0.08
                steps = 4 
                alpha_factor = 0.7 
            
            # Scale radius with petal_life
            r_final = base_radius * r_scale * petal_life
            
            # Generate Arc Points
            points_3d = []
            
            for k in range(steps + 1):
                t = k / steps # 0..1
                
                theta = center_angle + (t - 0.5) * arc_span
                
                px = self.x + math.cos(theta) * r_final
                pz = self.z + math.sin(theta) * r_final
                
                # --- Bowl Shape ---
                curve_drop = 0.10 * ((t - 0.5) * 2)**2
                py = head_y - (y_drop + curve_drop) * petal_life
                
                points_3d.append((px, py, pz))
            
            # Project
            screen_points = []
            for p3 in points_3d:
                proj_pt = project_fn(TempPoint(*p3))
                if proj_pt:
                    screen_points.append(proj_pt[:2])
            
            if len(screen_points) < 2:
                continue
            
            # Alpha Hierarchy
            final_color = (
                int(petal_rgb[0] * alpha_factor),
                int(petal_rgb[1] * alpha_factor),
                int(petal_rgb[2] * alpha_factor)
            )

            pygame.draw.lines(
                surface, 
                final_color, 
                False, 
                screen_points, 
                thickness
            )




    def _draw_neon_petals(
        self,
        surface,
        glow_surface,
        sx,
        sy,
        petal_rgb,
        thickness
    ):
        """Outer neon petal arcs"""

        life = self.life
        if life < 0.15:
            return

        # Number of petal arcs
        petal_count = 4

        # Base radius grows with life
        base_radius = 10 + 10 * life

        for p in range(petal_count):
            phase = self.petals_phase + p * (math.pi * 2 / petal_count)

            points = []

            # Each petal is a curved arc
            arc_len = math.pi * 0.9
            segments = 16

            for i in range(segments):
                t = i / (segments - 1)

                angle = phase + (t - 0.5) * arc_len
                radius = base_radius * (0.85 + 0.25 * t)

                x = sx + math.cos(angle) * radius
                y = sy + math.sin(angle) * radius * 0.85

                points.append((x, y))

            if len(points) < 2:
                continue

            # ---- Glow layers ----
            for glow_pass in (7, 4):
                pygame.draw.lines(
                    glow_surface,
                    (*petal_rgb, 16),
                    False,
                    points,
                    thickness + glow_pass
                )

            # ---- Core line ----
            pygame.draw.lines(
                surface,
                petal_rgb,
                False,
                points,
                thickness
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
        self.life = 0.0  # per-flower wave life (0..1)


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

    def update(self, dt: float, head_x: float, head_y: float, world_energy: float) -> None:
        """
        world_energy goes from 0 → 1 over awakening.
        A radial wave propagates from front-center into the field.
        """

        # ---- Wave tuning ----
        WAVE_WIDTH = 0.9
        RIPPLE_STRENGTH = 0.08
        RIPPLE_FREQ = 1.2

        # Convert energy to wave-front distance
        wave_front = world_energy * self.depth_repeat * 1.2

        origin_x = 0.0
        origin_z = 0.0

        max_x = max(0.001, (self.lanes - 1) * self.spacing * 0.5)

        for f in self.flowers:
            # ---- Normalized distance from wave origin ----
            dx = (f.x - origin_x) / max_x
            dz = (f.z - origin_z) / self.depth_repeat

            distance = math.sqrt(dx * dx + dz * dz)

            # ---- Wave envelope ----
            raw = (wave_front - distance * self.depth_repeat) / WAVE_WIDTH
            life_target = max(0.0, min(1.0, raw))

            # ---- Secondary echo wave ----
            echo = max(
                0.0,
                min(
                    1.0,
                    (wave_front - distance * self.depth_repeat - 1.5) / 1.2
                )
            )

            life_target = max(life_target, echo * 0.35)

            # ---- Gentle ripple on crest ----
            ripple = RIPPLE_STRENGTH * math.sin(
                f.z * RIPPLE_FREQ - world_energy * 6.0
            )

            life_target += ripple

            # ---- Final clamp ----
            life_target = max(0.0, min(1.0, life_target))

            # ---- Sharper crest, softer tail ----
            life_target = life_target ** 1.4


            # ---- Store per-flower life ----
            f.life = life_target

            # ---- Update flower internals ----
            f.update(dt, life_target)

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
