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

        self.fog = pygame.Surface((width, height), pygame.SRCALPHA)


    def project(self, p, *args):
        q = project_off_axis(p, *args)
        if q and len(q) >= 2:
            return (q[0], q[1])
        return None

    def draw_edge(self, surface, glow, fog, p1, p2, proj_args, depth_factor=1.0, mood=0.0):
        q1 = self.project(p1, *proj_args)
        q2 = self.project(p2, *proj_args)
        if not q1 or not q2:
            return

        # ---- Clamp inputs ----
        depth_factor = max(0.05, min(1.0, depth_factor))
        mood = max(0.0, min(1.0, mood))

        # ---- Flower-tinted edge color ----
        tint_strength = mood * 0.35

        flower_tint = (
            int(140 * tint_strength),
            int(180 * tint_strength),
            int(220 * tint_strength),
        )

        core_color = (
            clamp((EDGE_BASE[0] + flower_tint[0]) * depth_factor),
            clamp((EDGE_BASE[1] + flower_tint[1]) * depth_factor),
            clamp((EDGE_BASE[2] + flower_tint[2]) * depth_factor),
        )

        # ---- CORE EDGE ----
        pygame.draw.line(surface, core_color, q1, q2, 1)

        # ---- GLOW EDGE ----
        glow_alpha = int((40 + 80 * tint_strength) * depth_factor)
        glow_color = (
            clamp(core_color[0] + 40),
            clamp(core_color[1] + 60),
            clamp(core_color[2] + 90),
            glow_alpha
        )
        pygame.draw.line(glow, glow_color, q1, q2, 6)

        # ---- DEPTH FOG (THIS WAS MISSING) ----
        fog_strength = (1.0 - depth_factor) ** 1.6
        fog_alpha = int(60 * fog_strength)

        if fog_alpha > 0:
            fog_color = (
                clamp(core_color[0] * 0.5),
                clamp(core_color[1] * 0.5),
                clamp(core_color[2] * 0.5),
                fog_alpha
            )
            pygame.draw.line(fog, fog_color, q1, q2, 10)
    def draw_quad_wire(
        self,
        surface,
        glow,
        fog,
        pts,
        *,
        proj_args,
        depth_factor=1.0,
        mood=0.0
    ):
        for i in range(4):
            self.draw_edge(
                surface,
                glow,
                fog,
                pts[i],
                pts[(i + 1) % 4],
                proj_args,
                depth_factor,
                mood
            )

    def draw(self, surface, head_x, head_y,
         camera_pitch, camera_height,
         eye_depth, near_clip, unit_scale,
         width, height, world_to_camera,
         mood=0.0):
        
        self.fog.fill((0, 0, 0, 0))

        self.glow.fill((0, 0, 0, 0))
        proj_args = (
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
        self.draw_quad_wire(surface, self.glow, self.fog, floor, proj_args=proj_args, depth_factor=0.6, mood=mood)

        # ---- CEILING (lighter) ----
        ceiling = [
            Point3D(-w, h, 0),
            Point3D( w, h, 0),
            Point3D( w, h, d),
            Point3D(-w, h, d),
        ]
        self.draw_quad_wire(surface, self.glow, self.fog, ceiling, proj_args=proj_args, depth_factor=0.8, mood=mood)

        # ---- LEFT WALL ----
        left = [
            Point3D(-w, -h, 0),
            Point3D(-w,  h, 0),
            Point3D(-w,  h, d),
            Point3D(-w, -h, d),
        ]
        self.draw_quad_wire(surface, self.glow, self.fog, left, proj_args=proj_args, depth_factor=0.7, mood=mood)

        # ---- RIGHT WALL ----
        right = [
            Point3D(w, -h, 0),
            Point3D(w,  h, 0),
            Point3D(w,  h, d),
            Point3D(w, -h, d),
        ]
        self.draw_quad_wire(surface, self.glow, self.fog, right, proj_args=proj_args, depth_factor=0.7, mood=mood)


        # ---- COMPOSITE GLOW ----
        surface.blit(self.glow, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        # ---- BLUR FOG (cheap volumetric) ----
        fog_small = pygame.transform.smoothscale(
            self.fog,
            (self.width // 2, self.height // 2)
        )
        fog_blur = pygame.transform.smoothscale(
            fog_small,
            (self.width, self.height)
        )

        surface.blit(fog_blur, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        surface.blit(self.glow, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
