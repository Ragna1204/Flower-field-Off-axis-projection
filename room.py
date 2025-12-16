import pygame
from geometry import Point3D
from projection import project_off_axis

# ---- COLOR PALETTE ----
WALL_BASE = (20, 22, 30)
EDGE_BASE = (70, 100, 200)

def clamp(v, lo=0, hi=255):
    return max(lo, min(hi, int(v)))

def edge_variation(p1, p2):
    """Stable pseudo-random variation based on edge geometry"""
    seed = int(
        (p1.x * 13 + p1.y * 17 + p1.z * 19 +
         p2.x * 23 + p2.y * 29 + p2.z * 31) * 1000
    )
    return 0.7 + (seed % 100) / 300.0  # range ~0.7 → 1.03


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
        # Subtle parallax exaggeration (depth only)
        parallax = 1.0 + (p.z / self.d) * 0.04
        p = Point3D(p.x * parallax, p.y, p.z)

        q = project_off_axis(p, *args)
        if q and len(q) >= 2:
            return (q[0], q[1])
        return None

    def draw_edge(
        self,
        surface,
        glow,
        fog,
        p1,
        p2,
        proj_args,      # <-- ALWAYS tuple
        depth_factor=1.0,
        energy=0.0      # <-- rename mood → energy
    ):
        q1 = self.project(p1, *proj_args)
        q2 = self.project(p2, *proj_args)
        if not q1 or not q2:
            return

        # ---- Clamp inputs ----
        depth_factor = max(0.05, min(1.0, depth_factor))
        energy = max(0.0, min(1.0, energy))


        variation = edge_variation(p1, p2)

        # ---- Flower-tinted edge color ----
        tint_strength = energy * 0.2

        flower_tint = (
            int(140 * tint_strength),
            int(180 * tint_strength),
            int(220 * tint_strength),
        )

        intensity = depth_factor * variation

        core_color = (
            clamp((EDGE_BASE[0] + flower_tint[0]) * intensity),
            clamp((EDGE_BASE[1] + flower_tint[1]) * intensity),
            clamp((EDGE_BASE[2] + flower_tint[2]) * intensity),
        )

        # ---- CORE EDGE ----
        pygame.draw.line(surface, core_color, q1, q2, 1)
        pygame.draw.line(surface, core_color, q1, q2, 1)

        # ---- STATIC ARCHITECTURAL ACCENT (always on) ----
        accent_alpha = int(10 * intensity)
        accent_color = (
            clamp(EDGE_BASE[0] + 20),
            clamp(EDGE_BASE[1] + 30),
            clamp(EDGE_BASE[2] + 40),
            accent_alpha
        )
        pygame.draw.line(glow, accent_color, q1, q2, 2)

        # ---- GLOW EDGE ----
        glow_alpha = int((20 + 40 * tint_strength) * intensity)
        glow_color = (
            clamp(core_color[0] + 40),
            clamp(core_color[1] + 60),
            clamp(core_color[2] + 90),
            glow_alpha
        )
        pygame.draw.line(glow, glow_color, q1, q2, 4)

        # ---- DEPTH FOG (THIS WAS MISSING) ----
        fog_strength = (1.0 - depth_factor) ** 1.6
        fog_alpha = int(25 * (1.0 - depth_factor) * energy)

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
        proj_args,
        depth_factor=1.0,
        energy=0.0
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
                energy
            )

    def draw_room_fog(self, surface, energy):
        """
        Volumetric room fog that fills space.
        Reacts softly to energy (smile).
        """

        if energy <= 0.01:
            return

        # Fog intensity scales gently with energy
        fog_alpha = int(18 + 30 * energy)

        # Cool neon mist color (NOT flower color yet)
        fog_color = (50, 80, 160, fog_alpha)

        # Create full-screen fog layer
        fog_layer = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        fog_layer.fill(fog_color)

        # Downscale → upscale for cheap volumetric blur
        fog_small = pygame.transform.smoothscale(
            fog_layer,
            (self.width // 3, self.height // 3)
        )
        fog_blur = pygame.transform.smoothscale(
            fog_small,
            (self.width, self.height)
        )

        # Additive blend so it feels like light in air
        surface.blit(fog_blur, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)



    def draw(self, surface, head_x, head_y,
         camera_pitch, camera_height,
         eye_depth, near_clip, unit_scale,
         width, height, world_to_camera,
         energy=0.0):
        
        energy = 0
        
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
        self.draw_quad_wire(surface, self.glow, self.fog, floor, proj_args=proj_args, depth_factor=0.45, energy=energy)

        # ---- CEILING (lighter) ----
        ceiling = [
            Point3D(-w, h, 0),
            Point3D( w, h, 0),
            Point3D( w, h, d),
            Point3D(-w, h, d),
        ]
        self.draw_quad_wire(surface, self.glow, self.fog, ceiling, proj_args=proj_args, depth_factor=0.8, energy=energy)

        # ---- LEFT WALL ----
        left = [
            Point3D(-w, -h, 0),
            Point3D(-w,  h, 0),
            Point3D(-w,  h, d),
            Point3D(-w, -h, d),
        ]
        self.draw_quad_wire(surface, self.glow, self.fog, left, proj_args=proj_args, depth_factor=0.6, energy=energy)

        # ---- RIGHT WALL ----
        right = [
            Point3D(w, -h, 0),
            Point3D(w,  h, 0),
            Point3D(w,  h, d),
            Point3D(w, -h, d),
        ]
        self.draw_quad_wire(surface, self.glow, self.fog, right, proj_args=proj_args, depth_factor=0.6, energy=energy)

        # ---- BACK WALL (farthest plane) ----
        back = [
            Point3D(-w, -h, d),
            Point3D( w, -h, d),
            Point3D( w,  h, d),
            Point3D(-w,  h, d),
        ]
        self.draw_quad_wire(surface, self.glow, self.fog, back, proj_args=proj_args, depth_factor=0.9, energy=energy)


        # ---- WALL RIBS (architectural detail) ----
        rib_spacing = 0.7
        z = 0.0
        while z <= d:
            # Left wall ribs
            self.draw_edge(
                surface,
                self.glow,
                self.fog,
                Point3D(-w, -h, z),
                Point3D(-w,  h, z),
                proj_args,
                depth_factor=0.55,
                energy=energy
            )

            # Right wall ribs
            self.draw_edge(
                surface,
                self.glow,
                self.fog,
                Point3D(w, -h, z),
                Point3D(w,  h, z),
                proj_args,
                depth_factor=0.55,
                energy=energy
            )

            z += rib_spacing


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

        # surface.blit(fog_blur, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        surface.blit(self.glow, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        # self.draw_room_fog(surface, energy)
