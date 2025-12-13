import pygame
from geometry import Point3D
from projection import project_off_axis

# ---- COLOR PALETTE ----
WALL_BASE = (20, 22, 30)
EDGE_BASE = (90, 130, 255)

def clamp(v, lo=0, hi=255):
    return max(lo, min(hi, int(v)))


class RoomRenderer:
    def __init__(self, width, height):
        self.width = width
        self.height = height

        # World dimensions
        self.w = 3.5
        self.h = 2.4
        self.d = 10.0

        # Glow buffer
        self.glow = pygame.Surface((width, height), pygame.SRCALPHA)

    def project(self, p, *args):
        q = project_off_axis(p, *args)
        if q and len(q) >= 2:
            return (q[0], q[1])
        return None

    def draw_edge(self, surface, glow, p1, p2, args, depth_factor=1.0, mood=0.0):
        q1 = self.project(p1, *args)
        q2 = self.project(p2, *args)
        if not q1 or not q2:
            return

        # Depth-faded brightness
        fade = max(0.15, depth_factor)

        # Subtle flower-tinted edge color
        tint_strength = max(0.0, min(1.0, mood)) * 0.35

        flower_tint = (
            int(140 * tint_strength),   # warm red
            int(180 * tint_strength),   # soft green
            int(220 * tint_strength),   # cool blue
        )

        core_color = (
            clamp((EDGE_BASE[0] + flower_tint[0]) * depth_factor),
            clamp((EDGE_BASE[1] + flower_tint[1]) * depth_factor),
            clamp((EDGE_BASE[2] + flower_tint[2]) * depth_factor),
        )


        # Core edge (thin)
        pygame.draw.line(surface, core_color, q1, q2, 1)

        # Glow edge (soft + depth based)
        alpha = int((50 + 90 * tint_strength) * depth_factor)
        glow_color = (
            clamp(core_color[0] + 40),
            clamp(core_color[1] + 60),
            clamp(core_color[2] + 90),
            clamp(alpha)
        )
        pygame.draw.line(glow, glow_color, q1, q2, 6)

    def draw_quad_wire(self, surface, glow, pts, args, depth_factor=1.0, mood=0.0):
        for i in range(4):
            self.draw_edge(
                surface,
                glow,
                pts[i],
                pts[(i + 1) % 4],
                args,
                depth_factor,
                mood
            )

    def draw(self, surface, head_x, head_y,
         camera_pitch, camera_height,
         eye_depth, near_clip, unit_scale,
         width, height, world_to_camera,
         mood=0.0):

        self.glow.fill((0, 0, 0, 0))
        args = (
            head_x, head_y,
            camera_pitch, camera_height,
            eye_depth, near_clip,
            unit_scale,
            width, height,
            world_to_camera
        )

        w, h, d = self.w, self.h, self.d

        # ---- FLOOR (darker, heavier) ----
        floor = [
            Point3D(-w, -h, 0),
            Point3D( w, -h, 0),
            Point3D( w, -h, d),
            Point3D(-w, -h, d),
        ]
        self.draw_quad_wire(surface, self.glow, floor, args, depth_factor=0.6, mood=mood)

        # ---- CEILING (lighter) ----
        ceiling = [
            Point3D(-w, h, 0),
            Point3D( w, h, 0),
            Point3D( w, h, d),
            Point3D(-w, h, d),
        ]
        self.draw_quad_wire(surface, self.glow, ceiling, args, depth_factor=0.8, mood=mood)

        # ---- LEFT WALL ----
        left = [
            Point3D(-w, -h, 0),
            Point3D(-w,  h, 0),
            Point3D(-w,  h, d),
            Point3D(-w, -h, d),
        ]
        self.draw_quad_wire(surface, self.glow, left, args, depth_factor=0.7, mood=mood)

        # ---- RIGHT WALL ----
        right = [
            Point3D(w, -h, 0),
            Point3D(w,  h, 0),
            Point3D(w,  h, d),
            Point3D(w, -h, d),
        ]
        self.draw_quad_wire(surface, self.glow, right, args, depth_factor=0.7, mood=mood)


        # ---- COMPOSITE GLOW ----
        surface.blit(self.glow, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
